"""Provider-neutral groundwork for importing public tournament brackets.

The four supported providers expose different shapes and levels of detail.  This
module deliberately keeps imported data separate from the rendering models: a
bracket can be useful even when it contains no character or costume data.
Network/authentication is left to the future UI or service layer; pass the JSON
returned by a provider to the appropriate parser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import json
import os
import re

import requests
from models import Character, DoublesTeam, Entrant, SinglesEntrant, Tournament, TournamentFormat


class BracketProvider(StrEnum):
    START_GG = "start.gg"
    CHALLONGE = "challonge"
    TONAMEL = "tonamel"
    PARRY_GG = "parry.gg"


class CharacterEvidence(StrEnum):
    REPORTED = "reported"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    tournament_name: bool = True
    event_name: bool = True
    date: bool = False
    location: bool = False
    entrant_count: bool = True
    placements: bool = True
    seeds: bool = False
    player_handles: bool = False
    characters: bool = False
    costumes: bool = False
    notes: str = ""


CAPABILITIES: dict[BracketProvider, ProviderCapabilities] = {
    BracketProvider.START_GG: ProviderCapabilities(
        date=True, location=True, seeds=True, player_handles=True, characters=True,
        notes="Game selections can report characters. Costume/color is not a documented field; never assume it is exact.",
    ),
    BracketProvider.CHALLONGE: ProviderCapabilities(
        date=True, seeds=True,
        notes="The standard bracket API supplies participant and result data, not Smash character selections.",
    ),
    BracketProvider.TONAMEL: ProviderCapabilities(
        notes="Competition-result data supplies placements and participant display names; exact event metadata varies by competition.",
    ),
    BracketProvider.PARRY_GG: ProviderCapabilities(
        date=True, location=True,
        notes="Placement records can include player tags and country. Character and costume choices are not exposed by its placement API.",
    ),
}


@dataclass(frozen=True, slots=True)
class BracketLink:
    provider: BracketProvider
    url: str
    tournament_slug: str
    event_slug: str | None = None
    phase_group_id: str | None = None


@dataclass(frozen=True, slots=True)
class ImportedCharacter:
    name: str
    costume: str | None = None
    evidence: CharacterEvidence = CharacterEvidence.REPORTED


@dataclass(frozen=True, slots=True)
class ImportedMember:
    """One player belonging to an imported team entrant."""

    tag: str
    characters: tuple[ImportedCharacter, ...] = ()
    x_handle: str | None = None
    country: str | None = None


@dataclass(frozen=True, slots=True)
class ImportedPlayer:
    tag: str
    placement: int | None = None
    seed: int | None = None
    characters: tuple[ImportedCharacter, ...] = ()
    x_handle: str | None = None
    country: str | None = None
    provider_id: str | None = None
    members: tuple[ImportedMember, ...] = ()


@dataclass(frozen=True, slots=True)
class BracketImport:
    link: BracketLink
    tournament_name: str
    event_name: str | None
    date: datetime | None
    location: str | None
    entrants_count: int | None
    players: tuple[ImportedPlayer, ...]
    event_format: TournamentFormat = TournamentFormat.UNKNOWN
    extra: Mapping[str, Any] = field(default_factory=dict)

    def to_tournament(self) -> Tournament:
        """Create display metadata once the provider has supplied a player count."""
        if not self.entrants_count:
            raise ValueError("This import has no entrant count to build a Tournament")
        title, subtitle = split_tournament_name(self.tournament_name)
        return Tournament(
            title=title,
            event=self.event_name,
            date=self.date.date() if self.date else "Date unavailable",
            entrants_count=self.entrants_count,
            subtitle=subtitle or self.location,
            link=self.link.url,
            event_format=self.event_format,
        )

    def to_singles_entrants(self) -> tuple[SinglesEntrant, ...]:
        """Convert verified Melee character data to renderer models.

        Players without a reported character are rejected rather than being
        rendered with a made-up main.  The UI can ask for those choices before
        calling this method.
        """
        missing = [player.tag for player in self.players if not player.characters or player.placement is None]
        if missing:
            raise ValueError("Character and placement required for: " + ", ".join(missing))
        return tuple(
            SinglesEntrant(
                tag=player.tag,
                placement=player.placement,  # type: ignore[arg-type]
                seed=player.seed,
                x_handle=player.x_handle,
                characters=[Character(character.name, color=character.costume) for character in player.characters],
            )
            for player in self.players
        )

    def to_doubles_teams(
        self, *, characters_by_member: Mapping[str, list[Character]]
    ) -> tuple[DoublesTeam, ...]:
        """Convert a verified doubles import to renderable teams.

        Bracket sites do not reliably identify each doubles player's Melee
        character, so the caller supplies the reviewed character selection for
        each member.  ``ImportedPlayer.tag`` remains the provider's team name.
        """
        if self.event_format != TournamentFormat.DOUBLES:
            raise ValueError("This import is not identified as a doubles event")
        teams = []
        for team in self.players:
            if team.placement is None or len(team.members) != 2:
                raise ValueError(f"Doubles team {team.tag!r} needs two identified members and a placement")
            members = []
            for member in team.members:
                characters = characters_by_member.get(member.tag)
                if not characters:
                    raise ValueError(f"Character selection required for doubles player {member.tag!r}")
                members.append(Entrant(tag=member.tag, characters=characters, x_handle=member.x_handle))
            teams.append(DoublesTeam(seed=team.seed, placement=team.placement, entrant_1=members[0], entrant_2=members[1], team_name=team.tag))
        return tuple(teams)


def split_tournament_name(name: str) -> tuple[str, str | None]:
    """Split a provider title into a display title and optional subtitle."""
    title, separator, subtitle = name.partition(":")
    if not separator:
        return name.strip(), None
    return title.strip() or name.strip(), subtitle.strip() or None


def identify_bracket_link(url: str) -> BracketLink:
    """Validate a public bracket URL and retain its provider slugs."""
    parsed = urlparse(url)
    host = parsed.netloc.casefold().removeprefix("www.")
    parts = [part for part in parsed.path.split("/") if part]
    clean_url = url.split("?", 1)[0].rstrip("/")
    if host == "start.gg":
        try:
            # Start.gg uses both its older ``/event/<slug>`` route and its
            # current bracket route, ``/events/<slug>/brackets/...``.
            event_index = next(index for index, part in enumerate(parts) if part in {"event", "events"})
            tournament_index = parts.index("tournament")
            bracket_index = parts.index("brackets") if "brackets" in parts else None
            phase_group_id = parts[bracket_index + 2] if bracket_index is not None and len(parts) > bracket_index + 2 else None
            return BracketLink(BracketProvider.START_GG, clean_url, parts[tournament_index + 1], parts[event_index + 1], phase_group_id)
        except (StopIteration, ValueError, IndexError) as error:
            raise ValueError("A start.gg event URL must contain /tournament/<slug>/event(s)/<slug>") from error
    if host.endswith("challonge.com") and parts:
        # Challonge's API represents a hosted bracket as
        # ``subdomain-tournament_slug``.
        subdomain = "" if host == "challonge.com" else host.removesuffix(".challonge.com")
        tournament_slug = f"{subdomain}-{parts[0]}" if subdomain else parts[0]
        return BracketLink(BracketProvider.CHALLONGE, clean_url, tournament_slug)
    if host == "tonamel.com" and len(parts) >= 2 and parts[0] == "competition":
        return BracketLink(BracketProvider.TONAMEL, clean_url, parts[1])
    if host == "parry.gg" and len(parts) >= 2:
        return BracketLink(BracketProvider.PARRY_GG, clean_url, parts[0], parts[1])
    raise ValueError("Unsupported bracket URL. Expected start.gg, challonge.com, tonamel.com, or parry.gg")


def startgg_query(tournament_slug: str, event_slug: str) -> dict[str, Any]:
    """Return the GraphQL request needed for a Start.gg Melee event import."""
    return {"query": """
query MeleePodiumImport($slug: String!) {
  event(slug: $slug) {
    id name numEntrants startAt entrantSizeMin
    videogame { id name }
    tournament { name city countryCode slug }
    standings(query: {page: 1, perPage: 64, sortBy: "standing"}) {
      nodes { placement entrant { id name initialSeedNum participants { gamerTag user { authorizations(types: TWITTER) { externalUsername } } } } }
    }
  }
}""", "variables": {"slug": f"tournament/{tournament_slug}/event/{event_slug}"}}


def startgg_phase_group_query(phase_group_id: int | str) -> dict[str, Any]:
    """Return standings and entrant count for one Start.gg bracket."""
    return {"query": """
query MeleePodiumPhaseGroup($id: ID!) {
  phaseGroup(id: $id) {
    standings(query: {page: 1, perPage: 64}) {
      nodes { placement entrant { id name initialSeedNum participants { gamerTag user { authorizations(types: TWITTER) { externalUsername } } } } }
    }
    seeds(query: {page: 1, perPage: 1}) { pageInfo { total } }
  }
}""", "variables": {"id": phase_group_id}}


def startgg_phase_group_sets_query(phase_group_id: int | str, page: int, per_page: int = 50) -> dict[str, Any]:
    """Return one page of games played in one Start.gg bracket."""
    return {"query": """
query MeleePodiumPhaseGroupCharacters($id: ID!, $page: Int!, $perPage: Int!) {
  phaseGroup(id: $id) {
    sets(page: $page, perPage: $perPage, sortType: STANDARD) {
      pageInfo { total }
      nodes { games { winnerId selections { entrant { id } character { name } } } }
    }
  }
}""", "variables": {"id": phase_group_id, "page": page, "perPage": per_page}}

def startgg_sets_query(event_id: int | str, page: int, per_page: int = 50) -> dict[str, Any]:
    """Return one page of the games played in a Start.gg event."""
    return {"query": """
query MeleePodiumSetCharacters($eventId: ID!, $page: Int!, $perPage: Int!) {
  event(id: $eventId) {
    sets(page: $page, perPage: $perPage, sortType: STANDARD) {
      pageInfo { total }
      nodes { games { winnerId selections { entrant { id } character { name } } } }
    }
  }
}""", "variables": {"eventId": event_id, "page": page, "perPage": per_page}}


def _startgg_request(request_body: Mapping[str, Any], token: str) -> Mapping[str, Any]:
    request = Request("https://api.start.gg/gql/alpha", data=json.dumps(request_body).encode("utf-8"), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise ValueError(f"Start.gg API request failed ({error.code})") from error
    except URLError as error:
        raise ValueError("Could not reach the Start.gg API") from error
    errors = payload.get("errors") if isinstance(payload, Mapping) else None
    if errors:
        message = errors[0].get("message") if isinstance(errors, list) and errors and isinstance(errors[0], Mapping) else "unknown error"
        raise ValueError(f"Start.gg API error: {message}")
    if not isinstance(payload, Mapping):
        raise ValueError("Start.gg returned an invalid response")
    return payload


def _winning_character_usage(event_id: int | str, top_entrant_ids: set[str], token: str, *, phase_group_id: str | None = None) -> dict[str, list[Mapping[str, Any]]]:
    """Collect reported characters from games won by the requested entrants."""
    usage: dict[str, list[Mapping[str, Any]]] = {entrant_id: [] for entrant_id in top_entrant_ids}
    page, per_page, total, seen_sets = 1, 50, None, 0
    while total is None or seen_sets < total:
        query = startgg_phase_group_sets_query(phase_group_id, page, per_page) if phase_group_id else startgg_sets_query(event_id, page, per_page)
        payload = _startgg_request(query, token)
        try:
            sets = payload["data"]["phaseGroup" if phase_group_id else "event"]["sets"]
            nodes = sets.get("nodes") or []
            total = sets.get("pageInfo", {}).get("total", 0)
        except (KeyError, TypeError) as error:
            raise ValueError("Start.gg returned an incomplete sets response") from error
        if not nodes:
            break
        seen_sets += len(nodes)
        for set_data in nodes:
            for game in set_data.get("games") or []:
                winner_id = str(game.get("winnerId"))
                if winner_id not in top_entrant_ids:
                    continue
                for selection in game.get("selections") or []:
                    entrant = selection.get("entrant") or {}
                    if str(entrant.get("id")) == winner_id:
                        usage[winner_id].append(selection)
        page += 1
    return usage


def fetch_startgg(link: BracketLink, *, top_entrants: int = 8) -> BracketImport:
    """Fetch an event plus its winning character selections for top placers."""
    token = os.environ.get("START_GG_TOKEN")
    if not token:
        raise ValueError("START_GG_TOKEN is not configured on the server")
    if not link.event_slug:
        raise ValueError("The Start.gg URL does not identify an event")
    try:
        payload = _startgg_request(startgg_query(link.tournament_slug, link.event_slug), token)
        event = payload["data"]["event"]
        if link.phase_group_id:
            phase_group = _startgg_request(startgg_phase_group_query(link.phase_group_id), token)["data"]["phaseGroup"]
            # Keep the event-wide entrant count from the first query. A phase
            # group only reports entrants in that phase (for example, a top 8).
            event["standings"] = phase_group["standings"]
        standings = event["standings"]["nodes"]
        # The event confirms whether this is doubles before we choose how many
        # placers need character data. Singles always retains the top eight;
        # doubles is limited to the supported top-four layout.
        character_import_count = 4 if _event_format(event.get("entrantSizeMin")) is TournamentFormat.DOUBLES else 8
        top_ids = {str(item["entrant"]["id"]) for item in standings[:character_import_count]}
        usage = _winning_character_usage(event["id"], top_ids, token, phase_group_id=link.phase_group_id)
        return parse_startgg(payload, link, character_usage=usage)
    except (KeyError, TypeError) as error:
        raise ValueError("Start.gg returned an incomplete event response") from error

def parse_startgg(payload: Mapping[str, Any], link: BracketLink, *, character_names: Mapping[int | str, str] | None = None, character_usage: Mapping[str, list[Mapping[str, Any]]] | None = None) -> BracketImport:
    event = payload["data"]["event"]
    tournament = event["tournament"]
    usage = character_usage or {}
    players = []
    for standing in event["standings"]["nodes"]:
        entrant = standing["entrant"]
        participants = entrant.get("participants") or [{}]
        participant = participants[0]
        authorizations = ((participant.get("user") or {}).get("authorizations") or [])
        handle = authorizations[0].get("externalUsername") if authorizations else None
        members = tuple(
            ImportedMember(
                item.get("gamerTag") or entrant["name"],
                x_handle=(
                    f"@{item['user']['authorizations'][0]['externalUsername']}"
                    if ((item.get("user") or {}).get("authorizations") or [])
                    else None
                ),
            )
            for item in participants
        )
        characters = tuple(_startgg_characters(usage.get(str(entrant.get("id")), usage.get(entrant["name"], [])), character_names))
        players.append(ImportedPlayer(entrant["name"], standing.get("placement"), entrant.get("initialSeedNum"), characters, f"@{handle}" if handle else None, provider_id=str(entrant.get("id")), members=members))
    entrant_size = event.get("entrantSizeMin")
    event_format = _event_format(entrant_size)
    return BracketImport(link, tournament["name"], event.get("name"), _unix_time(event.get("startAt")), tournament.get("city") or tournament.get("countryCode"), event.get("numEntrants"), tuple(sorted(players, key=lambda player: player.placement or 999999)), event_format, {"game": event.get("videogame"), "entrant_size_min": entrant_size})


def fetch_challonge(link: BracketLink) -> BracketImport:
    """Fetch and parse a public Challonge tournament with its v1 API key."""
    api_key = os.environ.get("CHALLONGE_API_KEY")
    if not api_key:
        raise ValueError("CHALLONGE_API_KEY is not configured on the server")
    endpoint = f"https://api.challonge.com/v1/tournaments/{link.tournament_slug}.json"
    try:
        response = requests.get(
            endpoint,
            params={"api_key": api_key, "include_participants": "1"},
            headers={"Accept": "application/json", "User-Agent": "MeleePodiumTemplate/1.0"},
            timeout=20,
        )
    except requests.RequestException as error:
        raise ValueError("Could not reach the Challonge API") from error
    if response.status_code == 401:
        raise ValueError("Challonge rejected CHALLONGE_API_KEY")
    if response.status_code == 403:
        raise ValueError("Challonge denied access to this bracket (403). Confirm that the bracket is public.")
    if response.status_code == 404:
        raise ValueError("Challonge tournament was not found or is not accessible with this API key")
    if not response.ok:
        raise ValueError(f"Challonge API request failed ({response.status_code})")
    try:
        return parse_challonge(response.json(), link)
    except (KeyError, TypeError, requests.JSONDecodeError) as error:
        raise ValueError("Challonge returned an incomplete tournament response") from error

def parse_challonge(payload: Mapping[str, Any], link: BracketLink) -> BracketImport:
    tournament = payload.get("tournament", payload)
    participants = tournament.get("participants", [])
    players = tuple(ImportedPlayer(p["participant"].get("display_name") or p["participant"]["name"], p["participant"].get("final_rank"), p["participant"].get("seed"), provider_id=str(p["participant"].get("id"))) for p in participants)
    return BracketImport(link, tournament["name"], None, _iso_time(tournament.get("completed_at") or tournament.get("started_at")), None, len(players), tuple(sorted(players, key=lambda player: player.placement or 999999)), TournamentFormat.UNKNOWN, {"bracket_type": tournament.get("tournament_type")})


def parse_tonamel(payload: Mapping[str, Any], link: BracketLink) -> BracketImport:
    places = payload.get("places", [])
    players = []
    for index, place in enumerate(places, start=1):
        participant = place.get("participant", {})
        players.append(ImportedPlayer(participant.get("entry_name") or participant.get("player_name") or "Unknown", place.get("place") or place.get("rank") or index, provider_id=str(participant.get("id")) if participant.get("id") else None))
    return BracketImport(link, payload.get("competition_name") or payload.get("name") or link.tournament_slug, payload.get("event_name"), _iso_time(payload.get("start_date") or payload.get("date")), None, payload.get("entrant_count") or len(places), tuple(players), TournamentFormat.UNKNOWN)


def parse_parrygg(payload: Mapping[str, Any], link: BracketLink) -> BracketImport:
    tournament = payload.get("tournament", payload)
    placements = payload.get("placements", tournament.get("placements", []))
    players = []
    for placement in placements:
        event_entrant = placement.get("event_entrant", placement.get("eventEntrant", {}))
        entrant = event_entrant.get("entrant", {})
        users = entrant.get("users") or []
        tag = event_entrant.get("name") or " / ".join(user.get("gamer_tag") or user.get("gamerTag", "") for user in users)
        members = tuple(ImportedMember(user.get("gamer_tag") or user.get("gamerTag") or "Unknown", country=user.get("location_country")) for user in users)
        players.append(ImportedPlayer(tag or "Unknown", placement.get("placement"), country=(users[0].get("location_country") if len(users) == 1 else None), members=members))
    event_format = _event_format(payload.get("entrant_size_min") or payload.get("entrantSizeMin"))
    if event_format == TournamentFormat.UNKNOWN and players and all(len(player.members) == 2 for player in players):
        event_format = TournamentFormat.DOUBLES
    return BracketImport(link, tournament.get("name", link.tournament_slug), payload.get("event_name") or link.event_slug, _protobuf_time(tournament.get("start_date") or tournament.get("startDate")), tournament.get("city") or tournament.get("country"), payload.get("entrant_count") or tournament.get("num_attendees"), tuple(sorted(players, key=lambda player: player.placement or 999999)), event_format)


def _startgg_characters(selections: list[Mapping[str, Any]], names: Mapping[int | str, str] | None) -> list[ImportedCharacter]:
    result = []
    for selection in selections:
        character = selection.get("character") or {}
        raw = selection.get("selectionValue")
        name = character.get("name") if isinstance(character, Mapping) else None
        name = name or (names or {}).get(raw)
        if name and name not in {item.name for item in result}:
            result.append(ImportedCharacter(name))
    return result


def _event_format(entrant_size: Any) -> TournamentFormat:
    if entrant_size == 1:
        return TournamentFormat.SINGLES
    if entrant_size == 2:
        return TournamentFormat.DOUBLES
    return TournamentFormat.UNKNOWN


def _unix_time(value: Any) -> datetime | None:
    return datetime.fromtimestamp(value, UTC) if isinstance(value, (int, float)) else None


def _iso_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _protobuf_time(value: Any) -> datetime | None:
    return _unix_time(value.get("seconds")) if isinstance(value, Mapping) else _iso_time(value)

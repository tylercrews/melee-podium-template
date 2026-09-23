"""Provider-neutral models and parsers for importing public tournament brackets.

The supported providers expose different shapes and levels of detail. This
module keeps imported data separate from rendering models, while small provider
clients handle authenticated network requests.
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
from models import Character, DoublesTeam, Entrant, MELEE_FIGHTERS, SinglesEntrant, Tournament, TournamentFormat
from startgg_usb_reporting import canonical_fighter_name, costume_for_usb_score


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
        date=True, location=True, seeds=True, player_handles=True, characters=True, costumes=True,
        notes="Game selections report characters. Replay Reporter USB scores can also carry verified costume indices.",
    ),
    BracketProvider.CHALLONGE: ProviderCapabilities(
        date=True, seeds=True,
        notes="The standard bracket API supplies participant and result data, not Smash character selections.",
    ),
    BracketProvider.TONAMEL: ProviderCapabilities(
        notes="Competition-result data supplies placements and participant display names; exact event metadata varies by competition.",
    ),
    BracketProvider.PARRY_GG: ProviderCapabilities(
        date=True, location=True, seeds=True, characters=True, costumes=True,
        notes="Placements include seeds and team members. Per-game reports can include each member's character and costume color.",
    ),
}


@dataclass(frozen=True, slots=True)
class BracketLink:
    provider: BracketProvider
    url: str
    tournament_slug: str
    event_slug: str | None = None
    phase_group_id: str | None = None
    phase_slug: str | None = None
    bracket_slug: str | None = None


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
    if host == "parry.gg" and parts:
        # Public routes are /<tournament>, /<tournament>/<event>/_standings,
        # and /<tournament>/<event>/<phase>/<bracket>. Accept the explicit
        # /event(s)/ form too so older/shared links remain useful.
        tournament_slug = parts[0]
        remainder = parts[1:]
        if remainder and remainder[0] == "events":
            remainder = remainder[1:]
        event_slug = remainder[0] if remainder and remainder[0] != "_standings" else None
        phase_slug = remainder[1] if len(remainder) >= 3 and remainder[1] != "_standings" else None
        bracket_slug = remainder[2] if len(remainder) >= 3 else None
        return BracketLink(
            BracketProvider.PARRY_GG,
            clean_url,
            tournament_slug,
            event_slug,
            phase_slug=phase_slug,
            bracket_slug=bracket_slug,
        )
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
      nodes {
        slots { entrant { id } }
        games { winnerId entrant1Score entrant2Score selections { entrant { id } character { name } } }
      }
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
      nodes {
        slots { entrant { id } }
        games { winnerId entrant1Score entrant2Score selections { entrant { id } character { name } } }
      }
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


def _reported_character_usage(event_id: int | str, top_entrant_ids: set[str], token: str, *, phase_group_id: str | None = None) -> dict[str, list[Mapping[str, Any]]]:
    """Collect reported selections and entrant scores for requested entrants."""
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
            slots = set_data.get("slots") or []
            score_field_by_entrant = {}
            for slot_index, slot in enumerate(slots[:2]):
                entrant = slot.get("entrant") if isinstance(slot, Mapping) else None
                if isinstance(entrant, Mapping) and entrant.get("id") is not None:
                    score_field_by_entrant[str(entrant["id"])] = f"entrant{slot_index + 1}Score"
            for game in set_data.get("games") or []:
                for selection in game.get("selections") or []:
                    entrant = selection.get("entrant") or {}
                    entrant_id = str(entrant.get("id"))
                    if entrant_id not in top_entrant_ids:
                        continue
                    enriched_selection = dict(selection)
                    score_field = score_field_by_entrant.get(entrant_id)
                    if score_field:
                        enriched_selection["_startgg_score"] = game.get(score_field)
                    usage[entrant_id].append(enriched_selection)
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
        usage = _reported_character_usage(event["id"], top_ids, token, phase_group_id=link.phase_group_id)
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
            params={
                "api_key": api_key,
                "include_participants": "1",
                "include_matches": "1",
            },
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

def _challonge_provisional_ranks(tournament: Mapping[str, Any]) -> dict[str, int]:
    """Derive final ranks from completed elimination matches.

    Challonge leaves ``final_rank`` empty while a completed bracket is in its
    ``awaiting_review`` state. In that state the participant array remains in
    seed order. Only return ranks when the completed match graph proves that
    every participant except one has been eliminated.
    """
    tournament_type = str(tournament.get("tournament_type") or "").casefold()
    if "double elimination" in tournament_type:
        losses_to_eliminate = 2
    elif "single elimination" in tournament_type:
        losses_to_eliminate = 1
    else:
        return {}

    participant_ids = {
        str(participant["participant"].get("id"))
        for participant in tournament.get("participants", [])
        if isinstance(participant, Mapping)
        and isinstance(participant.get("participant"), Mapping)
        and participant["participant"].get("id") is not None
    }
    matches = []
    for index, wrapped_match in enumerate(tournament.get("matches", [])):
        if not isinstance(wrapped_match, Mapping):
            continue
        match = wrapped_match.get("match", wrapped_match)
        if not isinstance(match, Mapping) or match.get("state") != "complete":
            continue
        winner_id = match.get("winner_id")
        loser_id = match.get("loser_id")
        if winner_id is None or loser_id is None:
            continue
        play_order = match.get("suggested_play_order")
        match_id = match.get("id")
        matches.append((
            play_order if isinstance(play_order, int) else 1_000_000 + index,
            match_id if isinstance(match_id, int) else index,
            index,
            match,
        ))
    matches.sort(key=lambda item: item[:3])
    if not participant_ids or not matches:
        return {}

    losses = {participant_id: 0 for participant_id in participant_ids}
    elimination_groups: list[tuple[int, list[str]]] = []
    group_by_round: dict[int, list[str]] = {}
    group_order: list[int] = []
    for _, _, _, match in matches:
        loser_id = str(match["loser_id"])
        if loser_id not in losses:
            continue
        losses[loser_id] += 1
        if losses[loser_id] != losses_to_eliminate:
            continue
        round_number = match.get("round")
        group_key = round_number if isinstance(round_number, int) else len(group_order)
        if group_key not in group_by_round:
            group_by_round[group_key] = []
            group_order.append(group_key)
        group_by_round[group_key].append(loser_id)

    survivors = [
        participant_id
        for participant_id, loss_count in losses.items()
        if loss_count < losses_to_eliminate
    ]
    eliminated_count = sum(len(group_by_round[key]) for key in group_order)
    if len(survivors) != 1 or eliminated_count != len(participant_ids) - 1:
        return {}

    elimination_groups.extend(
        (round_number, group_by_round[round_number])
        for round_number in reversed(group_order)
    )
    ranks = {survivors[0]: 1}
    placement = 2
    for _, eliminated_ids in elimination_groups:
        for participant_id in eliminated_ids:
            ranks[participant_id] = placement
        placement += len(eliminated_ids)
    return ranks


def parse_challonge(payload: Mapping[str, Any], link: BracketLink) -> BracketImport:
    tournament = payload.get("tournament", payload)
    participants = tournament.get("participants", [])
    provisional_ranks = _challonge_provisional_ranks(tournament)
    players = tuple(
        ImportedPlayer(
            p["participant"].get("display_name") or p["participant"]["name"],
            p["participant"].get("final_rank")
            or provisional_ranks.get(str(p["participant"].get("id"))),
            p["participant"].get("seed"),
            provider_id=str(p["participant"].get("id")),
        )
        for p in participants
    )
    return BracketImport(link, tournament["name"], None, _iso_time(tournament.get("completed_at") or tournament.get("started_at")), None, len(players), tuple(sorted(players, key=lambda player: player.placement or 999999)), TournamentFormat.UNKNOWN, {"bracket_type": tournament.get("tournament_type")})


def parse_tonamel(payload: Mapping[str, Any], link: BracketLink) -> BracketImport:
    places = payload.get("places", [])
    players = []
    for index, place in enumerate(places, start=1):
        participant = place.get("participant", {})
        players.append(ImportedPlayer(participant.get("entry_name") or participant.get("player_name") or "Unknown", place.get("place") or place.get("rank") or index, provider_id=str(participant.get("id")) if participant.get("id") else None))
    return BracketImport(link, payload.get("competition_name") or payload.get("name") or link.tournament_slug, payload.get("event_name"), _iso_time(payload.get("start_date") or payload.get("date")), None, payload.get("entrant_count") or len(places), tuple(players), TournamentFormat.UNKNOWN)


def fetch_parrygg(link: BracketLink, *, top_entrants: int = 8) -> BracketImport:
    """Fetch a parry.gg event, including reported per-game character colors."""
    if link.provider is not BracketProvider.PARRY_GG:
        raise ValueError("fetch_parrygg requires a parry.gg link")
    from parrygg_api import fetch_parrygg_data

    payload = fetch_parrygg_data(
        link.tournament_slug,
        event_slug=link.event_slug,
        phase_slug=link.phase_slug,
        bracket_slug=link.bracket_slug,
    )
    return parse_parrygg(payload, link, top_entrants=top_entrants)


_PARRY_FIGHTER_BY_SLUG = {
    re.sub(r"[^a-z0-9]+", "-", fighter.casefold()).strip("-"): fighter
    for fighter in MELEE_FIGHTERS
}
_PARRY_FIGHTER_BY_SLUG.update({
    "doctor-mario": "Dr. Mario",
    "mr-game-watch": "Mr. Game and Watch",
    "mr-game-and-watch": "Mr. Game and Watch",
})


def _parry_character(character: Mapping[str, Any]) -> ImportedCharacter | None:
    slug = str(character.get("slug") or character.get("characterSlug") or "").casefold()
    raw_name = str(character.get("name") or "").strip()
    name = _PARRY_FIGHTER_BY_SLUG.get(slug)
    if name is None:
        name = next((fighter for fighter in MELEE_FIGHTERS if fighter.casefold() == raw_name.casefold()), None)
    if name is None:
        return None

    colors: list[str] = []
    variants = [character.get("variant"), character.get("metadata")]
    variants.extend(
        image.get("variant")
        for image in character.get("images", [])
        if isinstance(image, Mapping)
    )
    direct_color = character.get("color")
    if direct_color is not None:
        colors.append(str(direct_color))
    for variant in variants:
        if isinstance(variant, Mapping) and variant.get("color") is not None:
            colors.append(str(variant["color"]))
    normalized = {color.strip().casefold() for color in colors if color.strip()}
    # A reported selection without variant metadata is the neutral costume.
    # Multiple image variants would be ambiguous, so only accept one color.
    costume = next(iter(normalized)) if len(normalized) == 1 else "default" if not normalized else None
    return ImportedCharacter(name, costume=costume)


def _parry_character_usage(brackets: Any) -> dict[str, tuple[ImportedCharacter, ...]]:
    usage: dict[str, list[ImportedCharacter]] = {}
    for bracket in brackets if isinstance(brackets, list) else []:
        if not isinstance(bracket, Mapping):
            continue
        for match in bracket.get("matches", []):
            if not isinstance(match, Mapping):
                continue
            for game in match.get("matchGames", match.get("match_games", [])):
                if not isinstance(game, Mapping):
                    continue
                for slot in game.get("slots", []):
                    if not isinstance(slot, Mapping):
                        continue
                    for participant in slot.get("participants", []):
                        if not isinstance(participant, Mapping):
                            continue
                        user_id = participant.get("userId") or participant.get("user_id")
                        if not user_id:
                            continue
                        selected = usage.setdefault(str(user_id), [])
                        for raw_character in participant.get("characters", []):
                            if not isinstance(raw_character, Mapping):
                                continue
                            character = _parry_character(raw_character)
                            if character is not None and character not in selected:
                                selected.append(character)
    return {user_id: tuple(characters) for user_id, characters in usage.items()}


def _parry_location(tournament: Mapping[str, Any]) -> str | None:
    address = tournament.get("address")
    if isinstance(address, Mapping):
        locality = address.get("locality")
        region = address.get("administrativeAreaLevel1") or address.get("administrative_area_level_1")
        country = address.get("countryCode") or address.get("country_code") or address.get("country")
        concise = ", ".join(str(value) for value in (locality, region, country) if value)
        if concise:
            return concise
        formatted = address.get("formattedAddress") or address.get("formatted_address")
        if formatted:
            return str(formatted)
    venue = tournament.get("venueAddress") or tournament.get("venue_address")
    return str(venue) if venue else None


def parse_parrygg(
    payload: Mapping[str, Any],
    link: BracketLink,
    *,
    top_entrants: int = 8,
) -> BracketImport:
    """Normalize the combined responses returned by :mod:`parrygg_api`."""
    tournament = payload.get("tournament", payload)
    if not isinstance(tournament, Mapping):
        raise ValueError("parry.gg returned an incomplete tournament response")
    event = payload.get("event", {})
    if not isinstance(event, Mapping):
        event = {}
    placements = payload.get("placements", tournament.get("placements", []))
    usage = _parry_character_usage(payload.get("brackets", []))
    players = []
    for placement in placements if isinstance(placements, list) else []:
        if not isinstance(placement, Mapping):
            continue
        event_entrant = placement.get("eventEntrant", placement.get("event_entrant", {}))
        if not isinstance(event_entrant, Mapping):
            event_entrant = {}
        entrant = event_entrant.get("entrant", {})
        if not isinstance(entrant, Mapping):
            entrant = {}
        users = [user for user in entrant.get("users", []) if isinstance(user, Mapping)]
        members = tuple(
            ImportedMember(
                str(user.get("gamerTag") or user.get("gamer_tag") or "Unknown"),
                characters=usage.get(str(user.get("id")), ()),
                country=user.get("locationCountry") or user.get("location_country"),
            )
            for user in users
        )
        tag = event_entrant.get("name") or " / ".join(member.tag for member in members)
        player_characters = members[0].characters if len(members) == 1 else ()
        players.append(ImportedPlayer(
            str(tag or "Unknown"),
            placement.get("placement"),
            placement.get("seed") or event_entrant.get("seed"),
            player_characters,
            country=members[0].country if len(members) == 1 else None,
            provider_id=str(event_entrant.get("id") or entrant.get("id") or "") or None,
            members=members,
        ))

    entrant_size = event.get("entrantSize") or event.get("entrant_size")
    event_format = _event_format(entrant_size)
    if event_format == TournamentFormat.UNKNOWN and players and all(len(player.members) == 2 for player in players):
        event_format = TournamentFormat.DOUBLES
    sorted_players = tuple(sorted(players, key=lambda player: player.placement or 999999))
    return BracketImport(
        link,
        str(tournament.get("name") or link.tournament_slug),
        str(event.get("name") or link.event_slug) if (event.get("name") or link.event_slug) else None,
        _protobuf_time(event.get("startDate") or event.get("start_date") or tournament.get("startDate") or tournament.get("start_date")),
        _parry_location(tournament),
        event.get("entrantCount") or event.get("entrant_count") or len(sorted_players) or tournament.get("numAttendees") or tournament.get("num_attendees"),
        sorted_players,
        event_format,
        {
            "game": event.get("game"),
            "reported_character_players": sum(bool(player.characters) for player in sorted_players[:top_entrants]),
        },
    )


def _startgg_characters(selections: list[Mapping[str, Any]], names: Mapping[int | str, str] | None) -> list[ImportedCharacter]:
    ordered_names: list[str] = []
    costume_counts: dict[str, dict[str, int]] = {}
    for selection in selections:
        character = selection.get("character") or {}
        raw = selection.get("selectionValue")
        name = character.get("name") if isinstance(character, Mapping) else None
        name = name or (names or {}).get(raw)
        if not name:
            continue
        name = canonical_fighter_name(str(name))
        if name not in costume_counts:
            ordered_names.append(name)
            costume_counts[name] = {}
        costume = costume_for_usb_score(name, selection.get("_startgg_score"))
        if costume:
            costume_counts[name][costume] = costume_counts[name].get(costume, 0) + 1
    return [
        ImportedCharacter(
            name,
            costume=max(costume_counts[name], key=costume_counts[name].get) if costume_counts[name] else None,
        )
        for name in ordered_names
    ]


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

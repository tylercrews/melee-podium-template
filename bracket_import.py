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
from urllib.parse import urlparse
import re

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
        return Tournament(
            title=self.tournament_name,
            event=self.event_name,
            date=self.date.date() if self.date else "Date unavailable",
            entrants_count=self.entrants_count,
            subtitle=self.location,
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


def identify_bracket_link(url: str) -> BracketLink:
    """Validate a public bracket URL and retain its provider slugs."""
    parsed = urlparse(url)
    host = parsed.netloc.casefold().removeprefix("www.")
    parts = [part for part in parsed.path.split("/") if part]
    clean_url = url.split("?", 1)[0].rstrip("/")
    if host == "start.gg":
        try:
            event_index = parts.index("event")
            tournament_index = parts.index("tournament")
            return BracketLink(BracketProvider.START_GG, clean_url, parts[tournament_index + 1], parts[event_index + 1])
        except (ValueError, IndexError) as error:
            raise ValueError("A start.gg event URL must contain /tournament/<slug>/event/<slug>") from error
    if host.endswith("challonge.com") and parts:
        return BracketLink(BracketProvider.CHALLONGE, clean_url, parts[0])
    if host == "tonamel.com" and len(parts) >= 2 and parts[0] == "competition":
        return BracketLink(BracketProvider.TONAMEL, clean_url, parts[1])
    if host == "parry.gg" and len(parts) >= 2:
        return BracketLink(BracketProvider.PARRY_GG, clean_url, parts[0], parts[1])
    raise ValueError("Unsupported bracket URL. Expected start.gg, challonge.com, tonamel.com, or parry.gg")


def startgg_query(event_slug: str) -> dict[str, Any]:
    """Return the GraphQL request needed for a Start.gg Melee event import."""
    return {"query": """
query MeleePodiumImport($slug: String!) {
  event(slug: $slug) {
    name numEntrants startAt entrantSizeMin
    videogame { id name }
    tournament { name city countryCode slug }
    standings(query: {page: 1, perPage: 64, sortBy: "standing"}) {
      nodes { placement entrant { id name initialSeedNum participants { gamerTag user { authorizations(types: TWITTER) { externalUsername } } } } }
    }
  }
}""", "variables": {"slug": event_slug}}


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
        characters = tuple(_startgg_characters(usage.get(entrant["name"], []), character_names))
        players.append(ImportedPlayer(entrant["name"], standing.get("placement"), entrant.get("initialSeedNum"), characters, f"@{handle}" if handle else None, provider_id=str(entrant.get("id")), members=members))
    entrant_size = event.get("entrantSizeMin")
    event_format = _event_format(entrant_size)
    return BracketImport(link, tournament["name"], event.get("name"), _unix_time(event.get("startAt")), tournament.get("city") or tournament.get("countryCode"), event.get("numEntrants"), tuple(sorted(players, key=lambda player: player.placement or 999999)), event_format, {"game": event.get("videogame"), "entrant_size_min": entrant_size})


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
        raw = selection.get("selectionValue")
        name = (names or {}).get(raw)
        if name and name not in {item.name for item in result}:
            result.append(ImportedCharacter(name))
    return result


def _event_format(entrant_size: Any) -> TournamentFormat:
    if entrant_size == 1:
        return TournamentFormat.SINGLES
    if entrant_size == 2:
        return TournamentFormat.DOUBLES
    if isinstance(entrant_size, int) and entrant_size > 2:
        return TournamentFormat.TEAMS
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

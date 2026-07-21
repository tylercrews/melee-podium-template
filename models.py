"""Data models used to describe podium entrants and their characters."""

from dataclasses import dataclass
from datetime import date


MELEE_FIGHTERS = (
    "Bowser",
    "Captain Falcon",
    "Donkey Kong",
    "Dr. Mario",
    "Falco",
    "Fox",
    "Ganondorf",
    "Ice Climbers",
    "Jigglypuff",
    "Kirby",
    "Link",
    "Luigi",
    "Mario",
    "Marth",
    "Mewtwo",
    "Mr. Game and Watch",
    "Ness",
    "Peach",
    "Pichu",
    "Pikachu",
    "Roy",
    "Samus",
    "Sheik",
    "Yoshi",
    "Young Link",
    "Zelda",
)


def _validate_seed(seed: int | None) -> None:
    if seed is not None and seed <= 0:
        raise ValueError("Seed must be greater than 0 or None")


def _validate_placement(placement: int) -> None:
    if placement <= 0:
        raise ValueError("Placement must be greater than 0")


def _validate_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class Tournament:
    """Metadata displayed around a podium image."""

    title: str
    entrants_count: int
    date: str | date
    subtitle: str | None = None
    event: str | None = None
    link: str | None = None

    def __post_init__(self) -> None:
        _validate_text(self.title, "Tournament title")
        if self.subtitle is not None:
            _validate_text(self.subtitle, "Tournament subtitle")
        if self.event is not None:
            _validate_text(self.event, "Tournament event")
        if self.link is not None:
            _validate_text(self.link, "Tournament link")
        if self.entrants_count <= 0:
            raise ValueError("Entrants count must be greater than 0")


@dataclass(frozen=True, slots=True)
class Character:
    """A Melee fighter costume and portrait pose.

    An explicit ``None`` for ``color`` or ``pose`` requests a random available
    selection. Omitting them remains predictable: default color and Pose A.
    """

    melee_fighter_name: str
    color: str | None = "default"
    pose: str | None = "a"

    def __post_init__(self) -> None:
        if self.melee_fighter_name not in MELEE_FIGHTERS:
            choices = ", ".join(MELEE_FIGHTERS)
            raise ValueError(
                f"Unknown Melee fighter {self.melee_fighter_name!r}. "
                f"Expected one of: {choices}"
            )
        if self.color is not None:
            _validate_text(self.color, "Character color")
            object.__setattr__(self, "color", self.color.strip().lower())
        if self.pose is not None:
            _validate_text(self.pose, "Character pose")
            object.__setattr__(self, "pose", self.pose.strip().lower())


@dataclass(frozen=True, slots=True, kw_only=True)
class Entrant:
    """A player and the characters they used in an event.

    Character-selection and rendering policies are intentionally left to the
    drawing layer; this model only retains the full selection.
    """

    characters: list[Character]
    tag: str
    bluesky_handle: str | None = None
    x_handle: str | None = None

    def __post_init__(self) -> None:
        if not self.characters:
            raise ValueError("Entrant must have at least one character")
        if any(not isinstance(character, Character) for character in self.characters):
            raise TypeError("Entrant characters must all be Character instances")
        _validate_text(self.tag, "Entrant tag")
        if self.bluesky_handle is not None:
            _validate_text(self.bluesky_handle, "Bluesky handle")
        if self.x_handle is not None:
            _validate_text(self.x_handle, "X handle")


@dataclass(frozen=True, slots=True, kw_only=True)
class SinglesEntrant(Entrant):
    """An entrant's result in a singles bracket."""

    seed: int | None
    placement: int

    def __post_init__(self) -> None:
        super(SinglesEntrant, self).__post_init__()
        _validate_seed(self.seed)
        _validate_placement(self.placement)


@dataclass(frozen=True, slots=True)
class DoublesTeam:
    seed: int | None
    placement: int
    entrant_1: Entrant
    entrant_2: Entrant
    team_name: str
    team_color: str | None = None

    def __post_init__(self) -> None:
        _validate_seed(self.seed)
        _validate_placement(self.placement)
        if not isinstance(self.entrant_1, Entrant):
            raise TypeError("First team member must be an Entrant")
        if not isinstance(self.entrant_2, Entrant):
            raise TypeError("Second team member must be an Entrant")
        _validate_text(self.team_name, "Team name")
        if self.team_color is not None:
            _validate_text(self.team_color, "Team color")
            normalized_color = self.team_color.strip().lower()
            if normalized_color not in {"red", "blue", "green"}:
                raise ValueError("Team color must be one of: red, blue, green, or None")
            object.__setattr__(self, "team_color", normalized_color)

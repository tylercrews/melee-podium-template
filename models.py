"""Data models used to describe podium entrants and their characters."""

from dataclasses import dataclass


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


@dataclass(frozen=True, slots=True)
class SinglesEntrant:
    seed: int | None
    placement: int
    character: Character
    tag: str

    def __post_init__(self) -> None:
        _validate_seed(self.seed)
        _validate_placement(self.placement)
        _validate_text(self.tag, "Entrant tag")


@dataclass(frozen=True, slots=True)
class DoublesTeam:
    seed: int | None
    placement: int
    character_1: Character
    character_2: Character
    tag_1: str
    tag_2: str
    team_name: str

    def __post_init__(self) -> None:
        _validate_seed(self.seed)
        _validate_placement(self.placement)
        _validate_text(self.tag_1, "First entrant tag")
        _validate_text(self.tag_2, "Second entrant tag")
        _validate_text(self.team_name, "Team name")

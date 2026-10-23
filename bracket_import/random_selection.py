"""Replace reported Random picks with the paired wireframe stand-ins."""

from dataclasses import replace
from random import Random
from typing import Any, TypeVar

from wireframe_fighters import WIREFRAME_FEMALE, WIREFRAME_MALE, random_wireframe_poses


Character = TypeVar("Character", bound=Any)

RANDOM_SELECTION = "Random"
# Start.gg reports "Random Character"; Parry.gg identifies characters by slug.
_RANDOM_SPELLINGS = {"random", "random character", "random-character"}


def is_random_selection(name: str) -> bool:
    return name.strip().casefold() in _RANDOM_SPELLINGS


def expand_random_selections(
    *histories: tuple[Character, ...], rng: Random | None = None
) -> tuple[tuple[Character, ...], ...]:
    """Expand Random into Male then Female wireframes sharing one pose pair.

    Pass every history for one player together so played and winning
    selections keep the same poses when the import mode changes.
    """

    male_pose, female_pose = random_wireframe_poses(rng)

    def expand(history: tuple[Character, ...]) -> tuple[Character, ...]:
        expanded: list[Character] = []
        for character in history:
            if character.name != RANDOM_SELECTION:
                expanded.append(character)
                continue
            expanded.append(replace(character, name=WIREFRAME_MALE, costume="default", pose=male_pose))
            expanded.append(replace(character, name=WIREFRAME_FEMALE, costume="default", pose=female_pose))
        return tuple(expanded)

    return tuple(expand(history) for history in histories)

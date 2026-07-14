"""Color palette sampled from the podium artwork."""

from dataclasses import dataclass
from typing import Final, TypeAlias


RGB: TypeAlias = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class PodiumBoxColors:
    """The exterior border, interior border, and panel fill for one box."""

    exterior_line: RGB
    interior_line: RGB
    background: RGB


FIRST_PLACE_BOX: Final = PodiumBoxColors((217, 3, 0), (60, 1, 0), (20, 0, 0))
SECOND_PLACE_BOX: Final = PodiumBoxColors((91, 89, 248), (17, 11, 37), (7, 5, 20))
THIRD_PLACE_BOX: Final = PodiumBoxColors((255, 216, 5), (49, 35, 12), (26, 20, 5))
FOURTH_PLACE_BOX: Final = PodiumBoxColors((127, 237, 12), (3, 17, 1), (5, 18, 0))
FIFTH_PLACE_ORANGE_BOX: Final = PodiumBoxColors((251, 139, 0), (92, 32, 0), (37, 12, 0))
FIFTH_PLACE_TEAL_BOX: Final = PodiumBoxColors((0, 205, 195), (1, 53, 52), (0, 27, 25))
SEVENTH_PLACE_MAGENTA_BOX: Final = PodiumBoxColors((255, 0, 255), (78, 4, 72), (35, 2, 35))
SEVENTH_PLACE_GRAY_BOX: Final = PodiumBoxColors((141, 141, 141), (48, 44, 57), (20, 16, 24))

# Visual order on the top-8 background. This also corresponds to podium slots
# in top 3/top 4, so renderers can safely select a box by slot number.
PODIUM_BOX_COLORS_BY_SLOT: Final = (
    FIRST_PLACE_BOX,
    SECOND_PLACE_BOX,
    THIRD_PLACE_BOX,
    FOURTH_PLACE_BOX,
    FIFTH_PLACE_ORANGE_BOX,
    FIFTH_PLACE_TEAL_BOX,
    SEVENTH_PLACE_MAGENTA_BOX,
    SEVENTH_PLACE_GRAY_BOX,
)

# Placement numeral colors from the background art.
NON_FIRST_PLACE_LETTER_GRAY: Final[RGB] = (174, 173, 173)
FIRST_PLACE_LETTER_YELLOW: Final[RGB] = (254, 235, 131)

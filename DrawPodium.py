"""Draw singles and doubles results onto the podium backgrounds.

The public convenience functions cover doubles top 3/top 4 and singles top
3/top 4/top 8. ``draw_podium`` is the shared lower-level entry point.
Tournament text is accepted and validated now; its eventual drawing belongs in
``_draw_text_fields`` so it can be added without changing the public API.
"""

from collections.abc import Sequence
from datetime import date, time
from enum import Enum
from pathlib import Path
from random import choice
import re

from PIL import Image

from models import Character, DoublesTeam, SinglesEntrant
from portrait_scale_adjustment_for_each_mode import get_mode_portrait_scale
from portrait_scale_adjustment_to_character_relativity import get_pose_scale


PROJECT_ROOT = Path(__file__).resolve().parent
CHARACTER_FOLDER = PROJECT_ROOT / "char_poses_meleecsproject"

# Positive values move every portrait's bottom anchor farther down onto the
# podium. Keep this centralized so the vertical position is easy to tune.
PORTRAIT_ANCHOR_Y_OFFSET = 9

class PodiumMode(str, Enum):
    DOUBLES_TOP_3 = "doubles_top_3"
    DOUBLES_TOP_4 = "doubles_top_4"
    SINGLES_TOP_3 = "singles_top_3"
    SINGLES_TOP_4 = "singles_top_4"
    SINGLES_TOP_8 = "singles_top_8"

    @property
    def is_doubles(self) -> bool:
        return self.value.startswith("doubles_")

    @property
    def placement_count(self) -> int:
        return int(self.value.rsplit("_", 1)[1])


# Each point is the center of a white star in podium_char_position_markings.
# Pillow has a top-left origin; character bottoms are centered on these points.
SINGLES_ANCHORS = {
    3: {
        1: (828, 526),
        2: (443, 577),
        3: (1200, 612),
    },
    4: {
        1: (312, 486),
        2: (668, 543),
        3: (1023, 587),
        4: (1375, 644),
    },
    8: {
        1: (181, 491),
        2: (376, 550),
        3: (566, 586),
        4: (754, 613),
        5: (939, 632),
        6: (1126, 634),
        7: (1305, 653),
        8: (1491, 656),
    },
}

DOUBLES_ANCHORS = {
    3: {
        1: ((753, 523), (918, 526)),
        2: ((363, 581), (519, 582)),
        3: ((1137, 616), (1272, 613)),
    },
    4: {
        1: ((252, 492), (375, 490)),
        2: ((609, 544), (735, 544)),
        3: ((962, 586), (1098, 586)),
        4: ((1305, 642), (1423, 642)),
    },
}

_POSE_FILENAME = re.compile(
    r"^(?P<color_code>\d+)(?P<pose>[a-z]+)_(?P<color>[^_]+)_",
    re.IGNORECASE,
)


def _background_path(mode: PodiumMode) -> Path:
    return PROJECT_ROOT / f"top_{mode.placement_count}.png"


def _resolve_character_path(character: Character) -> Path:
    folder = CHARACTER_FOLDER / character.melee_fighter_name
    if not folder.is_dir():
        raise FileNotFoundError(f"Character folder does not exist: {folder}")

    matches: list[Path] = []
    available: set[str] = set()
    requested_color = character.color.casefold() if character.color is not None else None
    requested_pose = character.pose.casefold() if character.pose is not None else None
    random_color = requested_color is None
    random_pose = requested_pose is None

    for path in sorted(folder.glob("*.png")):
        match = _POSE_FILENAME.match(path.name)
        if match is None:
            continue

        color_code = match.group("color_code").casefold()
        color_name = match.group("color").casefold()
        pose = match.group("pose").casefold()
        available.add(f"{color_name}/{pose}")

        pose_matches = random_pose or pose == requested_pose
        color_matches = random_color or requested_color in {
            color_name,
            color_code,
            f"{color_code}_{color_name}",
        }
        if pose_matches and color_matches:
            matches.append(path)

    if not matches:
        options = ", ".join(sorted(available)) or "none"
        raise ValueError(
            f"No {character.melee_fighter_name} image exists for color "
            f"{character.color!r} and pose {character.pose!r}. "
            f"Available color/pose combinations: {options}"
        )
    if random_color or random_pose:
        return choice(matches)
    if len(matches) > 1:
        raise ValueError(
            f"Expected one {character.melee_fighter_name} image for color "
            f"{character.color!r} and pose {character.pose!r}; found {len(matches)}"
        )
    return matches[0]


def _load_character(character: Character, mode_scale: float) -> Image.Image:
    path = _resolve_character_path(character)
    image = Image.open(path).convert("RGBA")
    selected = _POSE_FILENAME.match(path.name)
    if selected is None:
        raise ValueError(f"Cannot determine pose from portrait filename: {path.name}")
    selected_pose = selected.group("pose").casefold()
    pose_scale = get_pose_scale(
        character.melee_fighter_name,
        f"00{selected_pose}",
    )
    # Scaling always happens in two stages: first character relativity, then
    # the size appropriate for the selected singles/doubles podium layout.
    total_scale = pose_scale * mode_scale
    size = (
        max(1, round(image.width * total_scale)),
        max(1, round(image.height * total_scale)),
    )
    return image.resize(size, Image.Resampling.LANCZOS)


def _place_character(
    canvas: Image.Image,
    character: Character,
    anchor: tuple[int, int],
    mode_scale: float,
) -> None:
    image = _load_character(character, mode_scale)
    x = round(anchor[0] - image.width / 2)
    y = anchor[1] + PORTRAIT_ANCHOR_Y_OFFSET - image.height
    canvas.alpha_composite(image, (x, y))


def _validate_placements(
    entrants: Sequence[SinglesEntrant] | Sequence[DoublesTeam],
    expected_count: int,
) -> None:
    if len(entrants) != expected_count:
        raise ValueError(
            f"This layout requires {expected_count} placements; got {len(entrants)}"
        )
    actual = [entrant.placement for entrant in entrants]
    sequential = list(range(1, expected_count + 1))
    accepted = [sequential]
    if expected_count == 8:
        accepted.append([1, 2, 3, 4, 5, 5, 7, 7])
    if actual not in accepted:
        choices = " or ".join(str(placements) for placements in accepted)
        raise ValueError(
            f"Entrants must be supplied in placement order {choices}; got {actual}"
        )


def _draw_text_fields(
    canvas: Image.Image,
    entrants: Sequence[SinglesEntrant] | Sequence[DoublesTeam],
    *,
    tournament_name: str,
    tournament_date: str | date,
    entrants_count: int,
    location: str | None,
    tournament_time: str | time | None,
) -> None:
    """Reserved for the tournament and entrant text layout added later."""
    del (
        canvas,
        entrants,
        tournament_name,
        tournament_date,
        entrants_count,
        location,
        tournament_time,
    )


def draw_podium(
    mode: PodiumMode,
    entrants: Sequence[SinglesEntrant] | Sequence[DoublesTeam],
    *,
    tournament_name: str,
    tournament_date: str | date,
    entrants_count: int,
    location: str | None = None,
    tournament_time: str | time | None = None,
    character_scale: float | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    """Draw entrants for one of the five supported podium modes."""
    if not isinstance(mode, PodiumMode):
        try:
            mode = PodiumMode(mode)
        except ValueError as error:
            choices = ", ".join(item.value for item in PodiumMode)
            raise ValueError(f"Unknown podium mode. Expected one of: {choices}") from error
    if not tournament_name.strip():
        raise ValueError("Tournament name cannot be empty")
    if entrants_count < mode.placement_count:
        raise ValueError(
            f"Entrants count must be at least {mode.placement_count} for this layout"
        )
    mode_scale = (
        get_mode_portrait_scale(mode) if character_scale is None else character_scale
    )
    if mode_scale <= 0:
        raise ValueError("Character scale must be greater than 0")

    _validate_placements(entrants, mode.placement_count)
    expected_type = DoublesTeam if mode.is_doubles else SinglesEntrant
    if any(not isinstance(entrant, expected_type) for entrant in entrants):
        raise TypeError(
            f"{mode.value} requires every entrant to be a {expected_type.__name__}"
        )

    background = Image.open(_background_path(mode)).convert("RGBA")
    if mode.is_doubles:
        anchors = DOUBLES_ANCHORS[mode.placement_count]
        # Draw lower placements first so higher placements remain in front.
        for podium_slot, team in reversed(list(enumerate(entrants, start=1))):
            assert isinstance(team, DoublesTeam)
            first_anchor, second_anchor = anchors[podium_slot]
            _place_character(background, team.character_1, first_anchor, mode_scale)
            _place_character(background, team.character_2, second_anchor, mode_scale)
    else:
        anchors = SINGLES_ANCHORS[mode.placement_count]
        for podium_slot, entrant in reversed(list(enumerate(entrants, start=1))):
            assert isinstance(entrant, SinglesEntrant)
            _place_character(
                background,
                entrant.character,
                anchors[podium_slot],
                mode_scale,
            )

    _draw_text_fields(
        background,
        entrants,
        tournament_name=tournament_name,
        tournament_date=tournament_date,
        entrants_count=entrants_count,
        location=location,
        tournament_time=tournament_time,
    )

    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        background.save(destination)
    return background


def draw_doubles_top_3(
    first_place_team: DoublesTeam,
    second_place_team: DoublesTeam,
    third_place_team: DoublesTeam,
    *,
    tournament_name: str,
    tournament_date: str | date,
    entrants_count: int,
    location: str | None = None,
    tournament_time: str | time | None = None,
    character_scale: float | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    return draw_podium(
        PodiumMode.DOUBLES_TOP_3,
        [first_place_team, second_place_team, third_place_team],
        tournament_name=tournament_name,
        tournament_date=tournament_date,
        entrants_count=entrants_count,
        location=location,
        tournament_time=tournament_time,
        character_scale=character_scale,
        output_path=output_path,
    )


def draw_doubles_top_4(
    first_place_team: DoublesTeam,
    second_place_team: DoublesTeam,
    third_place_team: DoublesTeam,
    fourth_place_team: DoublesTeam,
    *,
    tournament_name: str,
    tournament_date: str | date,
    entrants_count: int,
    location: str | None = None,
    tournament_time: str | time | None = None,
    character_scale: float | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    return draw_podium(
        PodiumMode.DOUBLES_TOP_4,
        [first_place_team, second_place_team, third_place_team, fourth_place_team],
        tournament_name=tournament_name,
        tournament_date=tournament_date,
        entrants_count=entrants_count,
        location=location,
        tournament_time=tournament_time,
        character_scale=character_scale,
        output_path=output_path,
    )


def draw_singles_top_3(
    first_place_entrant: SinglesEntrant,
    second_place_entrant: SinglesEntrant,
    third_place_entrant: SinglesEntrant,
    *,
    tournament_name: str,
    tournament_date: str | date,
    entrants_count: int,
    location: str | None = None,
    tournament_time: str | time | None = None,
    character_scale: float | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    return draw_podium(
        PodiumMode.SINGLES_TOP_3,
        [first_place_entrant, second_place_entrant, third_place_entrant],
        tournament_name=tournament_name,
        tournament_date=tournament_date,
        entrants_count=entrants_count,
        location=location,
        tournament_time=tournament_time,
        character_scale=character_scale,
        output_path=output_path,
    )


def draw_singles_top_4(
    first_place_entrant: SinglesEntrant,
    second_place_entrant: SinglesEntrant,
    third_place_entrant: SinglesEntrant,
    fourth_place_entrant: SinglesEntrant,
    *,
    tournament_name: str,
    tournament_date: str | date,
    entrants_count: int,
    location: str | None = None,
    tournament_time: str | time | None = None,
    character_scale: float | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    return draw_podium(
        PodiumMode.SINGLES_TOP_4,
        [
            first_place_entrant,
            second_place_entrant,
            third_place_entrant,
            fourth_place_entrant,
        ],
        tournament_name=tournament_name,
        tournament_date=tournament_date,
        entrants_count=entrants_count,
        location=location,
        tournament_time=tournament_time,
        character_scale=character_scale,
        output_path=output_path,
    )


def draw_singles_top_8(
    first_place_entrant: SinglesEntrant,
    second_place_entrant: SinglesEntrant,
    third_place_entrant: SinglesEntrant,
    fourth_place_entrant: SinglesEntrant,
    fifth_place_entrant: SinglesEntrant,
    sixth_place_entrant: SinglesEntrant,
    seventh_place_entrant: SinglesEntrant,
    eighth_place_entrant: SinglesEntrant,
    *,
    tournament_name: str,
    tournament_date: str | date,
    entrants_count: int,
    location: str | None = None,
    tournament_time: str | time | None = None,
    character_scale: float | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    return draw_podium(
        PodiumMode.SINGLES_TOP_8,
        [
            first_place_entrant,
            second_place_entrant,
            third_place_entrant,
            fourth_place_entrant,
            fifth_place_entrant,
            sixth_place_entrant,
            seventh_place_entrant,
            eighth_place_entrant,
        ],
        tournament_name=tournament_name,
        tournament_date=tournament_date,
        entrants_count=entrants_count,
        location=location,
        tournament_time=tournament_time,
        character_scale=character_scale,
        output_path=output_path,
    )

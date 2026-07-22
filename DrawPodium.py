"""Draw singles and doubles results onto the podium backgrounds.

The public convenience functions cover doubles top 3/top 4 and singles top
3/top 4/top 8. ``draw_podium`` is the shared lower-level entry point.
Tournament text is accepted and validated now; its eventual drawing belongs in
``_draw_text_fields`` so it can be added without changing the public API.
"""

from collections.abc import Sequence
from dataclasses import replace
from enum import Enum
from pathlib import Path
from random import choice
import re

from PIL import Image, ImageDraw, ImageFont

from constants import PODIUM_BOX_COLORS_BY_SLOT
from models import Character, DoublesTeam, SinglesEntrant, Tournament
from portrait_scale_adjustment_for_each_mode import get_mode_portrait_scale
from portrait_scale_adjustment_to_character_relativity import get_pose_scale


PROJECT_ROOT = Path(__file__).resolve().parent
CHARACTER_FOLDER = PROJECT_ROOT / "char_poses_meleecsproject"
FONT_PATH = PROJECT_ROOT / "Tyrowo-Inked-Regular.ttf"

# Positive values move every portrait's bottom anchor farther down onto the
# podium. Keep this centralized so the vertical position is easy to tune.
PORTRAIT_ANCHOR_Y_OFFSET = 2
DOUBLES_TEAM_NAME_Y_OFFSET = -30

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


# Each point is centered on the front (lower) edge of a podium's top surface.
# Pillow has a top-left origin; character bottoms are centered on these points.
SINGLES_ANCHORS = {
    3: {
        1: (817, 497),
        2: (393, 579),
        3: (1321, 614),
    },
    4: {
        1: (236, 505),
        2: (645, 540),
        3: (1054, 577),
        4: (1440, 618),
    },
    8: {
        1: (139, 525),
        2: (354, 552),
        3: (553, 583),
        4: (755, 604),
        5: (955, 628),
        6: (1150, 630),
        7: (1345, 659),
        8: (1545, 662),
    },
}

DOUBLES_ANCHORS = {
    3: {
        1: ((743, 497), (911, 497)),
        2: ((316, 579), (490, 579)),
        3: ((1242, 614), (1400, 614)),
    },
    4: {
        1: ((176, 505), (316, 505)),
        2: ((585, 540), (725, 540)),
        3: ((980, 577), (1128, 577)),
        4: ((1370, 618), (1510, 618)),
    },
}

# Text is deliberately kept in its own maps so individual background layouts
# can be fine-tuned without affecting character placement.
PODIUM_TEXT_ANCHORS = {
    3: {
        1: {"label": (825, 840), "seed": (1005, 767)},
        2: {"label": (335, 840), "seed": (528, 767)},
        3: {"label": (1295, 840), "seed": (1470, 770)},
    },
    4: {
        1: {"label": (236, 848), "seed": (390, 785)},
        2: {"label": (630, 848), "seed": (785, 785)},
        3: {"label": (1020, 848), "seed": (1175, 785)},
        4: {"label": (1415, 848), "seed": (1560, 785)},
    },
    8: {
        1: {"label": (125, 848), "seed": (215, 792)},
        2: {"label": (338, 848), "seed": (422, 794)},
        3: {"label": (542, 848), "seed": (622, 795)},
        4: {"label": (740, 848), "seed": (824, 796)},
        5: {"label": (940, 848), "seed": (1023, 799)},
        6: {"label": (1140, 848), "seed": (1222, 800)},
        7: {"label": (1338, 848), "seed": (1417, 802)},
        8: {"label": (1538, 848), "seed": (1618, 804)},
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


def _place_image(
    canvas: Image.Image,
    image: Image.Image,
    anchor: tuple[int, int],
) -> tuple[int, int, Image.Image]:
    x = round(anchor[0] - image.width / 2)
    y = anchor[1] + PORTRAIT_ANCHOR_Y_OFFSET - image.height
    canvas.alpha_composite(image, (x, y))
    return x, y, image


def _place_characters(
    canvas: Image.Image,
    characters: Sequence[Character],
    anchor: tuple[int, int],
    mode_scale: float,
) -> tuple[int, int, Image.Image]:
    """Layer an entrant's portraits from tallest to shortest at one anchor.

    Python's stable sort preserves the supplied character order when two
    portraits have equal rendered heights.
    """
    loaded_characters = [
        _load_character(character, mode_scale) for character in characters
    ]
    draw_order = sorted(
        loaded_characters,
        key=lambda image: image.height,
        reverse=True,
    )
    placements = [_place_image(canvas, image, anchor) for image in draw_order]
    # The first placement is the tallest portrait, which provides the
    # outermost silhouette and therefore the best location for the entrant tag.
    return placements[0]


def _character_with_team_color(character: Character, team_color: str | None) -> Character:
    """Apply a doubles color override without mutating the entrant's character."""
    return character if team_color is None else replace(character, color=team_color)


def _font_to_fit(text: str, max_width: int, preferred_size: int) -> ImageFont.FreeTypeFont:
    for size in range(preferred_size, 11, -1):
        font = ImageFont.truetype(FONT_PATH, size)
        if max(font.getlength(line) for line in text.splitlines()) <= max_width:
            return font
    return ImageFont.truetype(FONT_PATH, 11)


def _wrap_text(text: str, max_width: int, preferred_size: int) -> str:
    """Wrap whole words to a podium's available label width."""
    font = ImageFont.truetype(FONT_PATH, preferred_size)
    words = text.split()
    if not words:
        return text

    lines: list[str] = []
    line = words[0]
    for word in words[1:]:
        candidate = f"{line} {word}"
        if font.getlength(candidate) <= max_width:
            line = candidate
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return "\n".join(lines)


def _draw_text(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    *,
    anchor: str,
    max_width: int,
    preferred_size: int,
    wrap: bool = False,
    fill: tuple[int, int, int] | str = "white",
) -> None:
    if wrap:
        text = _wrap_text(text, max_width, preferred_size)
    font = _font_to_fit(text, max_width, preferred_size)
    draw.multiline_text(
        position,
        text,
        font=font,
        fill=fill,
        # The project has only a regular font; a same-color stroke gives it a
        # single-pass bold weight without desynchronizing wrapped text lines.
        stroke_width=1,
        stroke_fill=fill,
        anchor=anchor,
        align="center",
    )


def _display_link(link: str) -> str:
    """Make a footer URL compact without changing the stored source link."""
    return re.sub(r"^(?:https?://)?(?:www\.)?", "", link, flags=re.IGNORECASE)


def _tag_anchor(x: int, y: int, image: Image.Image) -> tuple[int, int]:
    """Return a point just above the visible (non-transparent) portrait pixels."""
    alpha_bounds = image.getchannel("A").getbbox()
    top = 0 if alpha_bounds is None else alpha_bounds[1]
    return x + image.width // 2, y + top - 10


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
    character_tags: Sequence[tuple[tuple[int, int], str]],
    *,
    tournament: Tournament,
) -> None:
    draw = ImageDraw.Draw(canvas)
    width = canvas.width
    _draw_text(draw, (45, 38), tournament.title, anchor="la", max_width=width // 2, preferred_size=62)
    if tournament.subtitle is not None:
        _draw_text(
            draw,
            (45, 111),
            tournament.subtitle,
            anchor="la",
            max_width=width // 2,
            preferred_size=48,
        )
    is_doubles = isinstance(entrants[0], DoublesTeam)
    event_label = tournament.event or ("DOUBLES!!" if is_doubles else "SINGLES!")
    count_label = "Teams" if is_doubles else "Entrants"
    _draw_text(
        draw,
        (width - 45, 38),
        event_label,
        anchor="ra",
        max_width=width // 3,
        preferred_size=42,
    )
    _draw_text(
        draw,
        (width - 45, 92),
        str(tournament.date),
        anchor="ra",
        max_width=width // 3,
        preferred_size=36,
    )
    _draw_text(
        draw,
        (width - 45, 140),
        f"{tournament.entrants_count} {count_label}",
        anchor="ra",
        max_width=width // 3,
        preferred_size=32,
    )
    if tournament.link is not None:
        # Keep the source bracket present but visually subordinate to results.
        # ``ra`` locks its right edge to the image margin even for long URLs.
        _draw_text(
            draw,
            (width - 10, canvas.height - 34),
            _display_link(tournament.link),
            anchor="ra",
            max_width=width - 36,
            preferred_size=18,
            fill=(210, 210, 210),
        )

    # Character tags are collected while the portraits are placed, then drawn
    # last so they remain readable over any overlapping portrait.
    for position, tag in character_tags:
        _draw_text(draw, position, tag, anchor="ms", max_width=210, preferred_size=28)

    placement_count = len(entrants)
    for podium_slot, entrant in enumerate(entrants, start=1):
        anchors = PODIUM_TEXT_ANCHORS[placement_count][podium_slot]
        if isinstance(entrant, DoublesTeam):
            _draw_text(
                draw,
                (
                    anchors["label"][0],
                    anchors["label"][1] + DOUBLES_TEAM_NAME_Y_OFFSET,
                ),
                entrant.team_name,
                anchor="ma",
                max_width=300,
                preferred_size=42, # doubles team font size
                wrap=True,
            )
        else:
            _draw_text(
                draw,
                anchors["label"],
                entrant.characters[0].melee_fighter_name,
                anchor="ma",
                max_width=180 if placement_count == 8 else 290,
                preferred_size=28 if placement_count == 8 else 34,
                wrap=True,
            )
        if entrant.seed is not None:
            _draw_text(
                draw,
                anchors["seed"],
                f"{entrant.seed}s",
                anchor="ra",
                max_width=80,
                preferred_size=20 if placement_count == 8 else 24,
                fill=PODIUM_BOX_COLORS_BY_SLOT[podium_slot - 1].exterior_line,
            )


def draw_podium(
    mode: PodiumMode,
    entrants: Sequence[SinglesEntrant] | Sequence[DoublesTeam],
    *,
    tournament: Tournament,
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
    if tournament.entrants_count < mode.placement_count:
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
    character_tags: list[tuple[tuple[int, int], str]] = []
    if mode.is_doubles:
        anchors = DOUBLES_ANCHORS[mode.placement_count]
        # Draw lower placements first so higher placements remain in front.
        for podium_slot, team in reversed(list(enumerate(entrants, start=1))):
            assert isinstance(team, DoublesTeam)
            first_anchor, second_anchor = anchors[podium_slot]
            first_characters = [
                _character_with_team_color(character, team.team_color)
                for character in team.entrant_1.characters
            ]
            second_characters = [
                _character_with_team_color(character, team.team_color)
                for character in team.entrant_2.characters
            ]
            first_x, first_y, first_image = _place_characters(
                background, first_characters, first_anchor, mode_scale
            )
            second_x, second_y, second_image = _place_characters(
                background, second_characters, second_anchor, mode_scale
            )
            character_tags.extend(
                [
                    (_tag_anchor(first_x, first_y, first_image), team.entrant_1.tag),
                    (_tag_anchor(second_x, second_y, second_image), team.entrant_2.tag),
                ]
            )
    else:
        anchors = SINGLES_ANCHORS[mode.placement_count]
        for podium_slot, entrant in reversed(list(enumerate(entrants, start=1))):
            assert isinstance(entrant, SinglesEntrant)
            x, y, image = _place_characters(
                background,
                entrant.characters,
                anchors[podium_slot],
                mode_scale,
            )
            character_tags.append((_tag_anchor(x, y, image), entrant.tag))

    _draw_text_fields(
        background,
        entrants,
        character_tags,
        tournament=tournament,
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
    tournament: Tournament,
    character_scale: float | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    return draw_podium(
        PodiumMode.DOUBLES_TOP_3,
        [first_place_team, second_place_team, third_place_team],
        tournament=tournament,
        character_scale=character_scale,
        output_path=output_path,
    )


def draw_doubles_top_4(
    first_place_team: DoublesTeam,
    second_place_team: DoublesTeam,
    third_place_team: DoublesTeam,
    fourth_place_team: DoublesTeam,
    *,
    tournament: Tournament,
    character_scale: float | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    return draw_podium(
        PodiumMode.DOUBLES_TOP_4,
        [first_place_team, second_place_team, third_place_team, fourth_place_team],
        tournament=tournament,
        character_scale=character_scale,
        output_path=output_path,
    )


def draw_singles_top_3(
    first_place_entrant: SinglesEntrant,
    second_place_entrant: SinglesEntrant,
    third_place_entrant: SinglesEntrant,
    *,
    tournament: Tournament,
    character_scale: float | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    return draw_podium(
        PodiumMode.SINGLES_TOP_3,
        [first_place_entrant, second_place_entrant, third_place_entrant],
        tournament=tournament,
        character_scale=character_scale,
        output_path=output_path,
    )


def draw_singles_top_4(
    first_place_entrant: SinglesEntrant,
    second_place_entrant: SinglesEntrant,
    third_place_entrant: SinglesEntrant,
    fourth_place_entrant: SinglesEntrant,
    *,
    tournament: Tournament,
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
        tournament=tournament,
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
    tournament: Tournament,
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
        tournament=tournament,
        character_scale=character_scale,
        output_path=output_path,
    )

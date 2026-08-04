"""Draw singles and doubles results onto the podium backgrounds.

The public convenience functions cover doubles top 3/top 4 and singles top
3/top 4/top 8 layouts. ``draw_podium`` is the shared lower-level entry point.
Tournament text is accepted and validated now; its eventual drawing belongs in
``_draw_text_fields`` so it can be added without changing the public API.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum
from functools import partial
from math import ceil
from pathlib import Path
from random import choice
import re

from PIL import Image, ImageDraw, ImageFont

from constants import PODIUM_BOX_COLORS_BY_SLOT
from models import Character, DoublesTeam, SinglesEntrant, Tournament, TournamentFormat
from portrait_scale_adjustment_for_each_mode import get_mode_portrait_scale
from portrait_scale_adjustment_to_character_relativity import get_pose_scale


PROJECT_ROOT = Path(__file__).resolve().parent
CHARACTER_FOLDER = PROJECT_ROOT / "char_assets" / "renders"
STOCK_ICON_FOLDER = PROJECT_ROOT / "char_assets" / "stock_icons"


class PodiumFont(str, Enum):
    """Typeface choices accepted by the renderer and render API."""

    TYROWO = "tyrowo"
    IMPACT = "impact"
    UBUNTU = "ubuntu"


FONT_CONFIG = {
    PodiumFont.TYROWO: ("Tyrowo-Inked-Regular.ttf", 0),
    PodiumFont.IMPACT: ("Impact.ttf", 8),
    PodiumFont.UBUNTU: ("Ubuntu-Regular.ttf", 1),
}

# Positive values move every portrait's bottom anchor farther down onto the
# podium. Keep this centralized so the vertical position is easy to tune.
PORTRAIT_ANCHOR_Y_OFFSET = 2
# When an entrant has several characters, draw their largest portraits at the
# primary anchor, then offset the next two left and right. Subsequent, smaller
# portraits repeat this pattern and layer over the initial silhouette.
MULTI_CHARACTER_X_OFFSETS_WIDE = (0, -75, 75)
MULTI_CHARACTER_X_OFFSETS_NARROW = (0, -35, 35)
TWO_CHARACTER_X_OFFSETS = (-70, 70)
DOUBLES_TEAM_NAME_Y_OFFSET = -30
SINGLES_CHARACTER_NAME_Y_OFFSET = -30
SINGLES_TOP_8_CHARACTER_NAME_Y_OFFSET = -22
TAG_COLLISION_GUTTER = 12
TAG_PREFERRED_SIZE = 56
# Give player tags a little more horizontal room than the podium face beneath
# them. Short tags can use the full preferred size; longer tags shrink to fit.
SINGLES_TAG_WIDTHS = {3: 460, 4: 430, 8: 230}
DOUBLES_TAG_WIDTHS = {3: 280, 4: 265}


@dataclass(frozen=True)
class CharacterTag:
    """A player tag waiting to be composited over its entrant's portraits."""

    position: tuple[int, int]
    text: str
    glow_fill: tuple[int, int, int]
    max_width: int


class PodiumMode(str, Enum):
    DOUBLES_TOP_3 = "doubles_top_3"
    DOUBLES_TOP_4 = "doubles_top_4"
    SINGLES_TOP_3 = "singles_top_3"
    SINGLES_TOP_4 = "singles_top_4"
    SINGLES_TOP_8 = "singles_top_8"
    SINGLES_TOP_8_FOUR_PODIUM = "singles_top_8_four_podium"

    @property
    def is_doubles(self) -> bool:
        return self.value.startswith("doubles_")

    @property
    def placement_count(self) -> int:
        if self is PodiumMode.SINGLES_TOP_8_FOUR_PODIUM:
            return 8
        return int(self.value.rsplit("_", 1)[1])

    @property
    def layout_count(self) -> int:
        """Number of podium boxes and portrait anchors in the background."""
        return (
            4
            if self is PodiumMode.SINGLES_TOP_8_FOUR_PODIUM
            else self.placement_count
        )


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
    return PROJECT_ROOT / f"top_{mode.layout_count}.png"


def _resolve_character_path(character: Character) -> Path:
    folder = CHARACTER_FOLDER / character.melee_fighter_name
    if not folder.is_dir():
        raise FileNotFoundError(f"Character folder does not exist: {folder}")

    matches: list[Path] = []
    available: set[str] = set()
    requested_color = (
        character.color.casefold() if character.color is not None else None
    )
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
    multi_character_x_offsets: tuple[int, int, int] = MULTI_CHARACTER_X_OFFSETS_WIDE,
) -> tuple[int, int, Image.Image]:
    # The offset set is supplied by the caller for Top 8 singles.
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
    offsets = multi_character_x_offsets[1:] if len(draw_order) == 2 else multi_character_x_offsets

    placements = [
        _place_image(
            canvas,
            image,
            (
                anchor[0] + offsets[index % len(offsets)],
                anchor[1],
            ),
        )
        for index, image in enumerate(draw_order)
    ]
    # The first placement is the tallest portrait, which provides the
    # outermost silhouette and therefore the best location for the entrant tag.
    return placements[0]


def _character_with_team_color(character: Character, team_color: str | None) -> Character:
    """Apply a doubles color override without mutating the entrant's character."""
    return character if team_color is None else replace(character, color=team_color)


def _font_settings(font: PodiumFont) -> tuple[Path, int]:
    filename, size_adjustment = FONT_CONFIG[font]
    return PROJECT_ROOT / "fonts" / filename, size_adjustment


def _adjusted_font_size(preferred_size: int, font: PodiumFont) -> int:
    """Apply the selected typeface's visual-size correction."""
    _, size_adjustment = _font_settings(font)
    return max(11, preferred_size + size_adjustment)


def _font_to_fit(
    text: str, max_width: int, preferred_size: int, font: PodiumFont
) -> ImageFont.FreeTypeFont:
    font_path, _ = _font_settings(font)
    for size in range(_adjusted_font_size(preferred_size, font), 10, -1):
        loaded_font = ImageFont.truetype(font_path, size)
        if max(loaded_font.getlength(line) for line in text.splitlines()) <= max_width:
            return loaded_font
    return ImageFont.truetype(font_path, 11)


def _wrap_text(
    text: str, max_width: int, preferred_size: int, font: PodiumFont
) -> str:
    """Wrap whole words to a podium's available label width."""
    font_path, _ = _font_settings(font)
    loaded_font = ImageFont.truetype(font_path, _adjusted_font_size(preferred_size, font))
    words = text.split()
    if not words:
        return text

    lines: list[str] = []
    line = words[0]
    for word in words[1:]:
        candidate = f"{line} {word}"
        if loaded_font.getlength(candidate) <= max_width:
            line = candidate
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return "\n".join(lines)


def _wrap_url(
    text: str, max_width: int, preferred_size: int, font: PodiumFont
) -> str:
    """Wrap a URL at path separators, falling back to character breaks."""
    font_path, _ = _font_settings(font)
    loaded_font = ImageFont.truetype(font_path, _adjusted_font_size(preferred_size, font))
    lines: list[str] = []
    line = ""

    for segment in re.findall(r"[^/]+/?", text):
        candidate = f"{line}{segment}"
        if loaded_font.getlength(candidate) <= max_width:
            line = candidate
            continue

        if line:
            lines.append(line)
            line = ""
        for character in segment:
            if line and loaded_font.getlength(f"{line}{character}") > max_width:
                lines.append(line)
                line = character
            else:
                line += character

    if line:
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
    font: PodiumFont,
    wrap: bool = False,
    fill: tuple[int, int, int] | str = "white",
    glow_fill: tuple[int, int, int] | None = None,
    align: str = "center",
) -> None:
    if wrap:
        text = _wrap_text(text, max_width, preferred_size, font)
    loaded_font = _font_to_fit(text, max_width, preferred_size, font)

    draw.multiline_text(
        position,
        text,
        font=loaded_font,
        fill=glow_fill or fill,
        # Pillow has no numeric font-weight control for this font file. A
        # same-color stroke gives Tyrowo its intended bold (700-like) weight
        # without desynchronizing wrapped text lines.
        stroke_width=(1.33 if font is PodiumFont.TYROWO 
                        else 0.69 if font is PodiumFont.UBUNTU 
                        else 0),
        stroke_fill=glow_fill or fill,
        anchor=anchor,
        align=align,

    )


def _display_link(link: str) -> str:
    """Make a footer URL compact without changing the stored source link."""
    compact = re.sub(r"\s+", "", link)
    return re.sub(r"^(?:https?://)?(?:www\.)?", "", compact, flags=re.IGNORECASE)


def _tag_anchor(x: int, y: int, image: Image.Image, *, center_x: int | None = None) -> tuple[int, int]:
    """Return a point just above the visible (non-transparent) portrait pixels."""
    alpha_bounds = image.getchannel("A").getbbox()
    top = 0 if alpha_bounds is None else alpha_bounds[1]
    return center_x if center_x is not None else x + image.width // 2, y + top - 15


def _draw_character_tag(
    draw: ImageDraw.ImageDraw,
    character_tag: CharacterTag,
    font: PodiumFont,
) -> None:
    """Draw a sponsored tag with its placement color as a halo."""
    position = character_tag.position
    tag = character_tag.text
    glow_fill = character_tag.glow_fill
    max_width = character_tag.max_width
    sponsor, separator, player_tag = tag.partition("|")
    if not separator or not player_tag.strip():
        _draw_text(
            draw,
            position,
            tag,
            anchor="ms",
            max_width=max_width,
            preferred_size=TAG_PREFERRED_SIZE,
            font=font,
            glow_fill=glow_fill,
        )
        return

    player_tag = player_tag.strip()
    sponsor_tag = f"{sponsor.rstrip()} |"
    _draw_text(
        draw,
        position,
        player_tag,
        anchor="ms",
        max_width=max_width,
        preferred_size=TAG_PREFERRED_SIZE,
        font=font,
        glow_fill=glow_fill,
    )

    player_font = _font_to_fit(player_tag, max_width, TAG_PREFERRED_SIZE, font)
    player_bounds = player_font.getbbox(player_tag)
    player_height = player_bounds[3] - player_bounds[1]
    sponsor_position = (position[0], position[1] - player_height - 6)
    _draw_text(
        draw,
        sponsor_position,
        sponsor_tag,
        anchor="ms",
        max_width=max_width,
        preferred_size=TAG_PREFERRED_SIZE,
        font=font,
        glow_fill=glow_fill,
    )


def _character_tag_bounds(
    draw: ImageDraw.ImageDraw,
    character_tag: CharacterTag,
    font: PodiumFont,
) -> tuple[int, int, int, int]:
    """Measure the same one- or two-line geometry used to draw a tag."""
    position = character_tag.position
    tag = character_tag.text
    max_width = character_tag.max_width
    sponsor, separator, player_tag = tag.partition("|")
    stroke_width = 2  # Include the visible halo in collision detection.
    if not separator or not player_tag.strip():
        loaded_font = _font_to_fit(tag, max_width, TAG_PREFERRED_SIZE, font)
        return draw.multiline_textbbox(
            position, tag, font=loaded_font, anchor="ms", stroke_width=stroke_width
        )

    player_tag = player_tag.strip()
    sponsor_tag = f"{sponsor.rstrip()} |"
    player_font = _font_to_fit(player_tag, max_width, TAG_PREFERRED_SIZE, font)
    player_bounds = draw.multiline_textbbox(
        position, player_tag, font=player_font, anchor="ms", stroke_width=stroke_width
    )
    player_font_bounds = player_font.getbbox(player_tag)
    player_height = player_font_bounds[3] - player_font_bounds[1]
    sponsor_position = (position[0], position[1] - player_height - 6)
    sponsor_font = _font_to_fit(sponsor_tag, max_width, TAG_PREFERRED_SIZE, font)
    sponsor_bounds = draw.multiline_textbbox(
        sponsor_position,
        sponsor_tag,
        font=sponsor_font,
        anchor="ms",
        stroke_width=stroke_width,
    )
    return (
        min(player_bounds[0], sponsor_bounds[0]),
        min(player_bounds[1], sponsor_bounds[1]),
        max(player_bounds[2], sponsor_bounds[2]),
        max(player_bounds[3], sponsor_bounds[3]),
    )


def _resolve_doubles_tag_collisions(
    draw: ImageDraw.ImageDraw,
    character_tags: Sequence[CharacterTag],
    font: PodiumFont,
    canvas_width: int,
) -> list[CharacterTag]:
    """Keep each teammate tag on its side while preserving outer tag room."""
    resolved = list(character_tags)
    for index in range(0, len(resolved), 2):
        if index + 1 >= len(resolved):
            break
        first, second = resolved[index], resolved[index + 1]
        first_is_left = first.position[0] <= second.position[0]
        left, right = (first, second) if first_is_left else (second, first)
        left_bounds = _character_tag_bounds(draw, left, font)
        right_bounds = _character_tag_bounds(draw, right, font)

        # Treat the midpoint between teammates as the inner edge of each tag's
        # box. Only shift tags that cross it, so short names remain centered.
        divider_x = (left.position[0] + right.position[0]) / 2
        left_inner_limit = divider_x - TAG_COLLISION_GUTTER / 2
        right_inner_limit = divider_x + TAG_COLLISION_GUTTER / 2
        left_room = max(0, left_bounds[0])
        right_room = max(0, canvas_width - right_bounds[2])
        left_overflow = max(0, left_bounds[2] - left_inner_limit - left_room)
        right_overflow = max(0, right_inner_limit - right_bounds[0] - right_room)

        # At a canvas edge there may not be enough outer room to shift the
        # whole tag. Narrow only that tag enough to preserve its inner limit.
        if left_overflow:
            left = replace(
                left,
                max_width=max(11, left.max_width - ceil(left_overflow)),
            )
            left_bounds = _character_tag_bounds(draw, left, font)
        if right_overflow:
            right = replace(
                right,
                max_width=max(11, right.max_width - ceil(right_overflow)),
            )
            right_bounds = _character_tag_bounds(draw, right, font)

        left_room = max(0, left_bounds[0])
        right_room = max(0, canvas_width - right_bounds[2])
        left_shift = min(max(0, left_bounds[2] - left_inner_limit), left_room)
        right_shift = min(max(0, right_inner_limit - right_bounds[0]), right_room)

        moved_left = replace(
            left,
            position=(left.position[0] - round(left_shift), left.position[1]),
        )
        moved_right = replace(
            right,
            position=(right.position[0] + round(right_shift), right.position[1]),
        )
        if first_is_left:
            resolved[index], resolved[index + 1] = moved_left, moved_right
        else:
            resolved[index], resolved[index + 1] = moved_right, moved_left
    return resolved


_STOCK_ICON_FILENAME = re.compile(
    r"^(?P<color_code>\d+)_(?P<color>[^_]+)_", re.IGNORECASE
)


def _stock_icon_slug(fighter_name: str) -> str:
    return fighter_name.lower().replace(".", "").replace(" ", "_")


def _resolve_stock_icon_path(character: Character) -> Path:
    """Find the stock icon matching a character's selected costume."""
    folder = STOCK_ICON_FOLDER / _stock_icon_slug(character.melee_fighter_name)
    if not folder.is_dir():
        raise FileNotFoundError(f"Stock icon folder does not exist: {folder}")

    requested_color = (
        character.color.casefold() if character.color is not None else None
    )
    matches: list[Path] = []
    available: set[str] = set()
    for path in sorted(folder.glob("*.png")):
        match = _STOCK_ICON_FILENAME.match(path.name)
        if match is None:
            continue
        color_code = match.group("color_code").casefold()
        color_name = match.group("color").casefold()
        available.add(color_name)
        if requested_color is None or requested_color in {
            color_code,
            color_name,
            f"{color_code}_{color_name}",
        }:
            matches.append(path)

    if not matches:
        choices = ", ".join(sorted(available)) or "none"
        raise ValueError(
            f"No {character.melee_fighter_name} stock icon exists for color "
            f"{character.color!r}. Available colors: {choices}"
        )
    return choice(matches) if requested_color is None else matches[0]


def _load_stock_icon(character: Character, size: int = 36) -> Image.Image:
    with Image.open(_resolve_stock_icon_path(character)) as source:
        return source.convert("RGBA").resize((size, size), Image.Resampling.NEAREST)


def _draw_stock_icons(
    canvas: Image.Image,
    icons: Sequence[Image.Image],
    *,
    center_x: int,
    center_y: int,
    gap: int = 5,
) -> None:
    if not icons:
        return
    width = sum(icon.width for icon in icons) + gap * (len(icons) - 1)
    x = round(center_x - width / 2)
    for icon in icons:
        canvas.alpha_composite(icon, (x, round(center_y - icon.height / 2)))
        x += icon.width + gap


def _draw_lower_entrant_summary(
    canvas: Image.Image,
    entrant: SinglesEntrant,
    *,
    anchor: tuple[int, int],
    fill: tuple[int, int, int],
    font: PodiumFont,
) -> None:
    """Draw one 5th/7th-place tag, seed, and character stock-icon list."""
    max_width = 370
    icon_gap = 5
    icons = [_load_stock_icon(character) for character in entrant.characters]
    first_line_icons = icons[:2]
    second_line_icons = icons[2:]
    seed = f" [#{entrant.seed}]" if entrant.seed is not None else ""
    label = f"{entrant.placement}th: {entrant.tag}{seed}"
    icon_width = sum(icon.width for icon in first_line_icons)
    if first_line_icons:
        icon_width += icon_gap * len(first_line_icons)
    loaded_font = _font_to_fit(
        label,
        max(80, max_width - icon_width),
        28,
        font,
    )
    draw = ImageDraw.Draw(canvas)
    text_width = round(draw.textlength(label, font=loaded_font))
    row_width = text_width + icon_width
    x = round(anchor[0] - row_width / 2)
    first_line_y = anchor[1] - 29
    draw.text(
        (x, first_line_y),
        label,
        font=loaded_font,
        fill=fill,
        stroke_width=1 if font is PodiumFont.TYROWO else 0,
        stroke_fill=fill,
        anchor="lm",
    )
    if first_line_icons:
        icon_center_x = x + text_width + icon_gap + (
            sum(icon.width for icon in first_line_icons)
            + icon_gap * (len(first_line_icons) - 1)
        ) / 2
        _draw_stock_icons(
            canvas,
            first_line_icons,
            center_x=round(icon_center_x),
            center_y=first_line_y,
            gap=icon_gap,
        )
    if second_line_icons:
        available_icon_width = max_width - icon_gap * (len(second_line_icons) - 1)
        icon_size = min(36, max(12, available_icon_width // len(second_line_icons)))
        resized_icons = [
            icon.resize((icon_size, icon_size), Image.Resampling.NEAREST)
            for icon in second_line_icons
        ]
        _draw_stock_icons(
            canvas,
            resized_icons,
            center_x=anchor[0],
            center_y=first_line_y + 40,
            gap=icon_gap,
        )


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


def _draw_tournament_subtitle(
    canvas: Image.Image,
    tournament: Tournament,
    font: PodiumFont,
    placement_count: int,
) -> None:
    """Draw the subtitle below portraits and player tags in the layer stack."""
    if tournament.subtitle is None:
        return

    width = canvas.width
    right_aligned = placement_count != 3
    _draw_text(
        ImageDraw.Draw(canvas),
        (width * 2 // 3, 110) if right_aligned else (45, 110),
        tournament.subtitle,
        anchor="ra" if right_aligned else "la",
        max_width=width // 2,
        preferred_size=48,
        font=font,
    )

def _draw_text_fields(
    canvas: Image.Image,
    entrants: Sequence[SinglesEntrant] | Sequence[DoublesTeam],
    *,
    tournament: Tournament,
    font: PodiumFont,
    mode: PodiumMode,
) -> None:
    draw = ImageDraw.Draw(canvas)
    draw_text = partial(_draw_text, font=font)
    width = canvas.width
    placement_count = mode.layout_count
    title_max_width = width * 2 // 3
    link_max_width = width - title_max_width - 25
    title_right_aligned = placement_count != 3
    draw_text(
        draw,
        (title_max_width, 5) if title_right_aligned else (15, 5),
        tournament.title,
        anchor="ra" if title_right_aligned else "la",
        max_width=title_max_width,
        preferred_size=92,
    )
    is_doubles = isinstance(entrants[0], DoublesTeam)
    event_label = tournament.event or ("DOUBLES!!" if is_doubles else "SINGLES!")
    count_label = "Teams" if is_doubles else "Entrants"
    metadata_top = 10
    if tournament.link is not None:
        source_link = _wrap_url(
            _display_link(tournament.link), link_max_width, 14, font
        )
        source_link_font = _font_to_fit(source_link, link_max_width, 14, font)
        link_line_height = source_link_font.getbbox("Ag")[3] - source_link_font.getbbox("Ag")[1] + 4
        metadata_top = max(10, 2 + link_line_height * len(source_link.splitlines()) + 12)
        draw_text(
            draw,
            (width - 10, 2),
            source_link,
            anchor="ra",
            max_width=link_max_width,
            preferred_size=14,
            fill=(210, 210, 210),
            align="right",
        )
    draw_text(
        draw,
        (width - 15, metadata_top),
        event_label,
        anchor="ra",
        max_width=width // 3,
        preferred_size=42,
    )
    draw_text(
        draw,
        (width - 15, metadata_top + 54),
        str(tournament.date),
        anchor="ra",
        max_width=width // 3,
        preferred_size=36,
    )
    draw_text(
        draw,
        (width - 15, metadata_top + 102),
        f"{tournament.entrants_count} {count_label}",
        anchor="ra",
        max_width=width // 3,
        preferred_size=32,
    )
    draw_text(
        draw,
        (width - 10, canvas.height - 30),
        "make your own podium at tyro.work/melee-podium-template",
        anchor="ra",
        max_width=width - 36,
        preferred_size=18,
        fill=(25, 25, 25),
    )

    for podium_slot, entrant in enumerate(entrants[:placement_count], start=1):
        anchors = PODIUM_TEXT_ANCHORS[placement_count][podium_slot]
        glow_fill = PODIUM_BOX_COLORS_BY_SLOT[podium_slot - 1].exterior_line
        if isinstance(entrant, DoublesTeam):
            draw_text(
                draw,
                (
                    anchors["label"][0],
                    anchors["label"][1] + DOUBLES_TEAM_NAME_Y_OFFSET,
                ),
                entrant.team_name,
                anchor="ma",
                max_width=440 if placement_count == 3 else 370,
                preferred_size=42,
                wrap=True,
                glow_fill=glow_fill,
            )
        elif mode is not PodiumMode.SINGLES_TOP_8_FOUR_PODIUM:
            label_y_offset = (
                SINGLES_TOP_8_CHARACTER_NAME_Y_OFFSET
                if placement_count == 8
                else SINGLES_CHARACTER_NAME_Y_OFFSET
            )
            draw_text(
                draw,
                (
                    anchors["label"][0],
                    anchors["label"][1] + label_y_offset,
                ),
                entrant.characters[0].melee_fighter_name,
                anchor="ma",
                max_width=180 if placement_count == 8 else 290,
                preferred_size=28 if placement_count == 8 else 34,
                wrap=True,
                glow_fill=glow_fill,
            )
        if entrant.seed is not None:
            draw_text(
                draw,
                anchors["seed"],
                f"{entrant.seed}s",
                anchor="ra",
                max_width=80,
                preferred_size=20 if placement_count == 8 else 24,
                fill=PODIUM_BOX_COLORS_BY_SLOT[podium_slot - 1].exterior_line,
            )

    if mode is PodiumMode.SINGLES_TOP_8_FOUR_PODIUM:
        for summary_slot, entrant in enumerate(entrants[4:], start=1):
            assert isinstance(entrant, SinglesEntrant)
            _draw_lower_entrant_summary(
                canvas,
                entrant,
                anchor=PODIUM_TEXT_ANCHORS[4][summary_slot]["label"],
                fill=PODIUM_BOX_COLORS_BY_SLOT[summary_slot + 3].exterior_line,
                font=font,
            )


def draw_podium(
    mode: PodiumMode,
    entrants: Sequence[SinglesEntrant] | Sequence[DoublesTeam],
    *,
    tournament: Tournament,
    font: PodiumFont | str = PodiumFont.TYROWO,
    character_scale: float | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    """Draw entrants for one of the six supported podium modes."""
    if not isinstance(mode, PodiumMode):
        try:
            mode = PodiumMode(mode)
        except ValueError as error:
            choices = ", ".join(item.value for item in PodiumMode)
            raise ValueError(f"Unknown podium mode. Expected one of: {choices}") from error
    if not isinstance(font, PodiumFont):
        try:
            font = PodiumFont(font)
        except ValueError as error:
            choices = ", ".join(item.value for item in PodiumFont)
            raise ValueError(f"Unknown font. Expected one of: {choices}") from error
    if tournament.entrants_count < mode.placement_count:
        raise ValueError(
            f"Entrants count must be at least {mode.placement_count} for this layout"
        )
    if tournament.event_format == TournamentFormat.DOUBLES and not mode.is_doubles:
        raise ValueError("A doubles Tournament must use a doubles podium mode")
    if tournament.event_format == TournamentFormat.SINGLES and mode.is_doubles:
        raise ValueError("A singles Tournament must use a singles podium mode")
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
    # The subtitle sits below the interleaved portrait/tag pass. The title is
    # drawn later so it remains above player tags.
    _draw_tournament_subtitle(
        background,
        tournament,
        font,
        mode.layout_count,
    )
    tag_draw = ImageDraw.Draw(background)
    if mode.is_doubles:
        anchors = DOUBLES_ANCHORS[mode.placement_count]
        tag_max_width = DOUBLES_TAG_WIDTHS[mode.placement_count]
        # Composite each lower-place team and its names before moving upward.
        # The next higher team's portraits therefore cover any tag overhang.
        for podium_slot, team in reversed(list(enumerate(entrants, start=1))):
            assert isinstance(team, DoublesTeam)
            glow_fill = PODIUM_BOX_COLORS_BY_SLOT[podium_slot - 1].exterior_line
            first_anchor, second_anchor = anchors[podium_slot]
            team_color = (
                choice(["red", "green", "blue"])
                if team.team_color == "random"
                else team.team_color
            )
            first_characters = [
                _character_with_team_color(character, team_color)
                for character in team.entrant_1.characters
            ]
            second_characters = [
                _character_with_team_color(character, team_color)
                for character in team.entrant_2.characters
            ]
            first_x, first_y, first_image = _place_characters(
                background,
                first_characters,
                first_anchor,
                mode_scale,
                MULTI_CHARACTER_X_OFFSETS_NARROW,
            )
            second_x, second_y, second_image = _place_characters(
                background,
                second_characters,
                second_anchor,
                mode_scale,
                MULTI_CHARACTER_X_OFFSETS_NARROW,
            )
            team_tags = _resolve_doubles_tag_collisions(
                tag_draw,
                [
                    CharacterTag(
                        _tag_anchor(
                            first_x,
                            first_y,
                            first_image,
                            center_x=first_anchor[0],
                        ),
                        team.entrant_1.tag,
                        glow_fill,
                        tag_max_width,
                    ),
                    CharacterTag(
                        _tag_anchor(
                            second_x,
                            second_y,
                            second_image,
                            center_x=second_anchor[0],
                        ),
                        team.entrant_2.tag,
                        glow_fill,
                        tag_max_width,
                    ),
                ],
                font,
                background.width,
            )
            for character_tag in team_tags:
                _draw_character_tag(tag_draw, character_tag, font)
    else:
        anchors = SINGLES_ANCHORS[mode.layout_count]
        tag_max_width = SINGLES_TAG_WIDTHS[mode.layout_count]
        # Render lowest to highest, interleaving each portrait group and tag.
        for podium_slot, entrant in reversed(
            list(enumerate(entrants[:mode.layout_count], start=1))
        ):
            assert isinstance(entrant, SinglesEntrant)
            glow_fill = PODIUM_BOX_COLORS_BY_SLOT[podium_slot - 1].exterior_line
            x, y, image = _place_characters(
                background,
                entrant.characters,
                anchors[podium_slot],
                mode_scale,
                multi_character_x_offsets=(
                    MULTI_CHARACTER_X_OFFSETS_NARROW
                    if mode.layout_count == 8
                    else MULTI_CHARACTER_X_OFFSETS_WIDE
                ),
            )
            character_tag = CharacterTag(
                _tag_anchor(
                    x,
                    y,
                    image,
                    center_x=anchors[podium_slot][0],
                ),
                entrant.tag,
                glow_fill,
                tag_max_width,
            )
            _draw_character_tag(tag_draw, character_tag, font)

    _draw_text_fields(
        background,
        entrants,
        tournament=tournament,
        font=font,
        mode=mode,
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
    font: PodiumFont | str = PodiumFont.TYROWO,
    character_scale: float | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    return draw_podium(
        PodiumMode.DOUBLES_TOP_3,
        [first_place_team, second_place_team, third_place_team],
        tournament=tournament,
        font=font,
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
    font: PodiumFont | str = PodiumFont.TYROWO,
    character_scale: float | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    return draw_podium(
        PodiumMode.DOUBLES_TOP_4,
        [first_place_team, second_place_team, third_place_team, fourth_place_team],
        tournament=tournament,
        font=font,
        character_scale=character_scale,
        output_path=output_path,
    )


def draw_singles_top_3(
    first_place_entrant: SinglesEntrant,
    second_place_entrant: SinglesEntrant,
    third_place_entrant: SinglesEntrant,
    *,
    tournament: Tournament,
    font: PodiumFont | str = PodiumFont.TYROWO,
    character_scale: float | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    return draw_podium(
        PodiumMode.SINGLES_TOP_3,
        [first_place_entrant, second_place_entrant, third_place_entrant],
        tournament=tournament,
        font=font,
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
    font: PodiumFont | str = PodiumFont.TYROWO,
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
        font=font,
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
    font: PodiumFont | str = PodiumFont.TYROWO,
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
        font=font,
        character_scale=character_scale,
        output_path=output_path,
    )


def draw_singles_top_8_four_podium(
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
    font: PodiumFont | str = PodiumFont.TYROWO,
    character_scale: float | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    return draw_podium(
        PodiumMode.SINGLES_TOP_8_FOUR_PODIUM,
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
        font=font,
        character_scale=character_scale,
        output_path=output_path,
    )

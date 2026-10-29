"""Generate the reviewed Flying V Singles Top 8 and Doubles Top 3 preferences."""

from __future__ import annotations

import json
from dataclasses import replace
from functools import cache
from pathlib import Path

from PIL import Image

from background_builder import PixelRect, PixelSize
from constants import PODIUM_BOX_COLORS_BY_SLOT
from creation_modes import FLYING_V_VERTICALLY_REVERSED, CreationMode, ModeOptions, ModeSelection
from flying_v_content_renderer import BETWEEN_NAMES_SUFFIX, WATERMARK_REGION
from flying_v_lineup import STANDING_FRAME
from mode_preferences import (
    CharacterPlacement,
    FormattingAssetPlacement,
    ModePreferences,
    PixelPoint,
    PlacementTagPlacement,
    TextPlacement,
)
from models import TournamentFormat
from placement_numbering import ordinal_asset_id, placement_rank
from portrait_assets import CHARACTER_FOLDER, PORTRAIT_FILENAME
from portrait_scale_adjustment_to_character_relativity import get_pose_scale


HEADER_REGION = "flying_v_header_region"
SINGLES_CANVAS = PixelSize(1440, 1920)
DOUBLES_CANVAS = PixelSize(1920, 1080)
# Shared assignment keys: top_left is the bottom-left corner, top_middle is the
# top center, and top_right is the bottom-right corner.
SINGLES_HEADER_BOXES = {
    "top_left": PixelRect(16, 1612, 396, 1904),
    "top_middle": PixelRect(420, 48, 1020, 246),
    "top_right": PixelRect(1044, 1612, 1424, 1904),
}
# Vertically reversed Singles flips the layout: logo and metadata take the top
# corners and the title moves to the bottom center.
REVERSED_SINGLES_HEADER_BOXES = {
    "top_left": PixelRect(16, 16, 396, 308),
    "top_middle": PixelRect(420, 1674, 1020, 1872),
    "top_right": PixelRect(1044, 16, 1424, 308),
}
DOUBLES_HEADER_BOXES = {
    "top_left": PixelRect(16, 800, 456, 1064),
    "top_middle": PixelRect(660, 48, 1260, 230),
    "top_right": PixelRect(1464, 800, 1904, 1064),
}
# The attribution owns a slim row in the right half of the top edge, or of the
# bottom edge when the layout is vertically reversed.
SINGLES_WATERMARK_ROW = PixelRect(720, 0, 1424, 44)
REVERSED_SINGLES_WATERMARK_ROW = PixelRect(720, 1876, 1424, 1920)
DOUBLES_WATERMARK_ROW = PixelRect(960, 0, 1904, 44)
# Width-to-height ratios of the canonical ordinal artwork, keyed by rank.
ORDINAL_ASPECTS = {1: .95, 2: 1.15, 3: 1.26, 4: 1.26, 5: 1.36, 7: 1.1}
NAME_ABOVE_HEAD_OFFSET = 15


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}FF".format(*rgb)


def _slot_color(slot: int) -> str:
    # Entrant text defaults to the Smash Player Colors used by legacy podiums.
    return _hex(PODIUM_BOX_COLORS_BY_SLOT[slot - 1].exterior_line)


def _header_regions(boxes: dict[str, PixelRect], watermark_row: PixelRect) -> list[FormattingAssetPlacement]:
    return [*(FormattingAssetPlacement(f"header_{position}", HEADER_REGION, box) for position, box in boxes.items()),
            FormattingAssetPlacement("watermark", WATERMARK_REGION, watermark_row)]


@cache
def tallest_render_height() -> float:
    """Return the tallest character render's visible height at a tier scale of 1."""
    tallest = 0.0
    for folder in CHARACTER_FOLDER.iterdir():
        for path in folder.glob("*.png"):
            match = PORTRAIT_FILENAME.match(path.name)
            if match is None:
                continue
            with Image.open(path) as source:
                visible = source.convert("RGBA").getbbox()
            if visible is not None:
                scale = get_pose_scale(folder.name, f"00{match.group('pose').casefold()}")
                tallest = max(tallest, (visible[3] - visible[1]) * scale)
    return tallest


def _fill_scale(frame: PixelRect) -> float:
    """Scale a tier so only the tallest render reaches the frame top; everyone stands on the art."""
    return round(frame.height / tallest_render_height() - .00005, 4)


def _badge_width(slot: int, height: int) -> int:
    return round(height * ORDINAL_ASPECTS[placement_rank(slot)] * 1.1)


def _badge(slot: int, center: PixelPoint, height: int, suffix: str = "", z_index: int = 60) -> PlacementTagPlacement:
    return PlacementTagPlacement(f"number_{slot}{suffix}", ordinal_asset_id(placement_rank(slot)), center,
                                 PixelSize(_badge_width(slot, height), height), z_index=z_index)


def _text(slot: int, slot_id: str, field: str, anchor: PixelPoint, width: int, pillow_anchor: str, size: int,
          member: int | None = None) -> TextPlacement:
    return TextPlacement(slot_id, field, anchor, width, entrant_slot=slot, member_slot=member, pillow_anchor=pillow_anchor,
                         preferred_size=size, z_index=60, color=_slot_color(slot))


def _seed_size(name_size: int) -> int:
    return max(20, min(36, name_size * 11 // 20))


def _sponsor(slot: int, center_x: int, badge_y: int, badge_height: int, name_size: int, name_width: int) -> TextPlacement:
    """Put a smaller sponsor on the placement row, left of the art, mirroring the seed."""
    right = center_x - _badge_width(slot, badge_height) // 2 - 8
    # Stay within the name's column so a long sponsor never reaches a header corner.
    column_left = max(8, center_x - name_width // 2)
    return _text(slot, f"sponsor_{slot}", "entrant.sponsor", PixelPoint(right, badge_y),
                 max(60, right - column_left), "rm", max(20, name_size * 3 // 5))


def _number_above_name(slot: int, center_x: int, line: int, badge_height: int, name_size: int, name_width: int,
                       name_field: str) -> tuple[PlacementTagPlacement, list[TextPlacement]]:
    """Cover the feet with the placement art and put the name just below the line."""
    badge_y = line + 2 - badge_height // 2
    return _badge(slot, PixelPoint(center_x, badge_y), badge_height), [
        _text(slot, f"name_{slot}", name_field, PixelPoint(center_x, line + 6), name_width, "ma", name_size),
        _text(slot, f"seed_{slot}", "entrant.seed", PixelPoint(center_x + _badge_width(slot, badge_height) // 2 + 8, badge_y),
              140, "lm", _seed_size(name_size)),
    ]


# slot: frame, tier scale, z, badge height, name size, name width. Every figure
# stands on its frame bottom, where its placement art covers its feet and its
# name sits just below. A scale of None fills the frame with only the tallest
# render: second place's tallest characters reach the title, never past it.
SINGLES_TIERS = {
    1: (PixelRect(260, 680, 1180, 1830), 1.16, 50, 180, 64, 620),
    2: (PixelRect(400, 246, 1040, 860), None, 40, 64, 54, 520),
    3: (PixelRect(0, 830, 420, 1300), .6, 30, 56, 48, 420),
    4: (PixelRect(1020, 830, 1440, 1300), .6, 30, 56, 48, 420),
    5: (PixelRect(10, 380, 330, 760), .45, 20, 48, 42, 320),
    6: (PixelRect(1110, 380, 1430, 760), .45, 20, 48, 42, 320),
    7: (PixelRect(0, 50, 270, 320), .3, 10, 40, 36, 270),
    8: (PixelRect(1170, 50, 1440, 320), .3, 10, 40, 36, 270),
}
# Flipped top to bottom: first place leads from the top, second stands beneath
# its name (its tallest render reaching up to that name), and the flanking
# tiers fly downward toward the bottom corners. Each back-row name still ends
# above the frames of the figures below it.
REVERSED_SINGLES_TIERS = {
    1: (PixelRect(260, 20, 1180, 1040), 1.16, 50, 180, 64, 620),
    2: (PixelRect(400, 1130, 1040, 1594), None, 40, 64, 54, 520),
    3: (PixelRect(0, 570, 420, 1040), .6, 30, 56, 48, 420),
    4: (PixelRect(1020, 570, 1440, 1040), .6, 30, 56, 48, 420),
    5: (PixelRect(10, 1108, 330, 1488), .45, 20, 48, 42, 320),
    6: (PixelRect(1110, 1108, 1430, 1488), .45, 20, 48, 42, 320),
    7: (PixelRect(0, 1550, 270, 1820), .3, 10, 40, 36, 270),
    8: (PixelRect(1170, 1550, 1440, 1820), .3, 10, 40, 36, 270),
}

# team slot: (member frame, figure center x) pairs, tier scale, z, badge height,
# name size, name width. Upper frames start low enough that a sponsored name
# above the tallest head stays out of the watermark's top row. The 2nd and 3rd
# frames hold the largest render (Bowser's victory pose) at their tier scale,
# so no member shrinks; figures keep their spacing by centering on their own x
# and slide inward only when a wide pose would leave the frame.
DOUBLES_TIERS = {
    1: (((PixelRect(520, 320, 1040, 1080), 780), (PixelRect(880, 320, 1400, 1080), 1140)), .8, 20, 175, 56, 900),
    2: (((PixelRect(0, 146, 560, 691), 170), (PixelRect(100, 146, 660, 691), 430)), .46, 10, 50, 44, 900),
    3: (((PixelRect(1260, 146, 1820, 691), 1490), (PixelRect(1360, 146, 1920, 691), 1750)), .46, 10, 50, 44, 900),
}
# The winning team's name sits on the canvas bottom.
DOUBLES_LEADER_NAME_BASELINE = 1066
# Back team names hug their outer canvas edge and sit behind the winning team,
# so a name running toward the center disappears under its figures.
DOUBLES_SIDE_MARGIN = 16
DOUBLES_SIDE_NAME_Z = DOUBLES_TIERS[1][2] - 5


def flying_v_singles_preferences(vertically_reversed: bool = False) -> ModePreferences:
    tiers = REVERSED_SINGLES_TIERS if vertically_reversed else SINGLES_TIERS
    frames = _header_regions(REVERSED_SINGLES_HEADER_BOXES if vertically_reversed else SINGLES_HEADER_BOXES,
                             REVERSED_SINGLES_WATERMARK_ROW if vertically_reversed else SINGLES_WATERMARK_ROW)
    characters, tags, text = [], [], []
    for slot, (frame, scale, z_index, badge, size, width) in tiers.items():
        center_x = (frame.left + frame.right) // 2
        frames.append(FormattingAssetPlacement(f"entrant_{slot}", STANDING_FRAME, frame, z_index))
        characters.append(CharacterPlacement(f"entrant_{slot}", slot, PixelPoint(center_x, frame.bottom),
                                             scale=_fill_scale(frame) if scale is None else scale, z_index=z_index))
        # Names show only the player tag; any sponsor moves to the placement row.
        badge_tag, label_text = _number_above_name(slot, center_x, frame.bottom, badge, size, width, "entrant.player_tag")
        tags.append(badge_tag)
        text.extend(label_text)
        text.append(_sponsor(slot, center_x, badge_tag.anchor.y, badge, size, width))
    variant = FLYING_V_VERTICALLY_REVERSED if vertically_reversed else None
    return ModePreferences(
        ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.SINGLES, 8, variant)), SINGLES_CANVAS, ready=True,
        formatting_assets=tuple(frames), placement_tags=tuple(tags), character_slots=tuple(characters), text_slots=tuple(text),
    )


def _side_team_label(slot: int, left_side: bool, line: int, badge_height: int, name_size: int,
                     name_width: int) -> tuple[PlacementTagPlacement, list[TextPlacement]]:
    """Align a back team's name and placement art to its outer edge.

    The name wraps early, stacking extra lines upward from the feet so the
    placement art below never moves; the seed sits on the art's inner side.
    """
    side = "l" if left_side else "r"
    direction = 1 if left_side else -1
    edge = DOUBLES_SIDE_MARGIN if left_side else DOUBLES_CANVAS.width - DOUBLES_SIDE_MARGIN
    badge_width = _badge_width(slot, badge_height)
    badge_x = edge + direction * (badge_width // 2)
    badge_y = line + 10 + badge_height // 2
    name = _text(slot, f"name_{slot}", "entrant.team_name", PixelPoint(edge, line + 6), name_width, f"{side}d", name_size)
    return _badge(slot, PixelPoint(badge_x, badge_y), badge_height), [
        replace(name, wrap=True, z_index=DOUBLES_SIDE_NAME_Z),
        _text(slot, f"seed_{slot}", "entrant.seed", PixelPoint(badge_x + direction * (badge_width // 2 + 8), badge_y),
              140, f"{side}m", _seed_size(name_size)),
    ]


def flying_v_doubles_preferences() -> ModePreferences:
    frames, characters, tags, text = _header_regions(DOUBLES_HEADER_BOXES, DOUBLES_WATERMARK_ROW), [], [], []
    for slot, (members, scale, z_index, badge, size, width) in DOUBLES_TIERS.items():
        member_frames = [frame for frame, _x in members]
        for member, (frame, figure_x) in enumerate(members, 1):
            slot_id = f"entrant_{slot}_member_{member}"
            frames.append(FormattingAssetPlacement(slot_id, STANDING_FRAME, frame, z_index))
            characters.append(CharacterPlacement(slot_id, slot, PixelPoint(figure_x, frame.bottom),
                                                 member_slot=member, scale=scale, z_index=z_index))
            # The renderer lowers this baseline to just above the member's visible head.
            text.append(_text(slot, f"member_{slot}_{member}", "member.tag",
                              PixelPoint(figure_x, frame.top - NAME_ABOVE_HEAD_OFFSET), frame.width, "ms", size, member))
        center_x = (member_frames[0].left + member_frames[1].right) // 2
        if slot == 1:
            # The crest sits centered between the members' names, behind the
            # figures; the renderer follows those names, carrying the seed at
            # the crest's upper right.
            badge_y = member_frames[0].top - NAME_ABOVE_HEAD_OFFSET - size * 7 // 20
            tags.append(_badge(slot, PixelPoint(center_x, badge_y), badge, BETWEEN_NAMES_SUFFIX, z_index=z_index - 5))
            crest_right = center_x + round(badge * ORDINAL_ASPECTS[1]) // 2
            text.extend((
                _text(slot, "name_1", "entrant.team_name", PixelPoint(center_x, DOUBLES_LEADER_NAME_BASELINE), width, "ms", size),
                _text(slot, "seed_1", "entrant.seed", PixelPoint(crest_right + 4, badge_y - badge // 2 + 16), 140, "ls",
                      _seed_size(size)),
            ))
            continue
        badge_tag, label_text = _side_team_label(slot, center_x < DOUBLES_CANVAS.width // 2,
                                                 max(frame.bottom for frame in member_frames), badge, size, width)
        tags.append(badge_tag)
        text.extend(label_text)
    return ModePreferences(
        ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.DOUBLES, 3)), DOUBLES_CANVAS, ready=True,
        formatting_assets=tuple(frames), placement_tags=tuple(tags), character_slots=tuple(characters), text_slots=tuple(text),
    )


if __name__ == "__main__":
    folder = Path(__file__).resolve().parent / "preferences" / "flying_v"
    folder.mkdir(parents=True, exist_ok=True)
    for preferences in (flying_v_singles_preferences(), flying_v_singles_preferences(vertically_reversed=True),
                        flying_v_doubles_preferences()):
        target = folder / f"{preferences.selection.submode_id}.json"
        target.write_text(json.dumps(preferences.to_dict(), indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {target}")

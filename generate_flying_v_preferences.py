"""Generate the reviewed Flying V Singles Top 8 and Doubles Top 3 preferences."""

from __future__ import annotations

import json
from dataclasses import replace
from functools import cache
from pathlib import Path

from PIL import Image

from background_builder import PixelRect, PixelSize
from constants import PODIUM_BOX_COLORS_BY_SLOT
from creation_modes import CreationMode, ModeOptions, ModeSelection, flying_v_singles_variant
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
DOUBLES_CANVAS = PixelSize(2360, 1080)
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
    "top_middle": PixelRect(420, 1716, 1020, 1872),
    "top_right": PixelRect(1044, 16, 1424, 308),
}
DOUBLES_HEADER_BOXES = {
    "top_left": PixelRect(16, 800, 456, 1064),
    "top_middle": PixelRect(880, 48, 1480, 230),
    "top_right": PixelRect(1904, 800, 2344, 1064),
}
# The attribution owns a slim row in the right half of the top edge, or of the
# bottom edge when the layout is vertically reversed.
SINGLES_WATERMARK_ROW = PixelRect(720, 0, 1424, 44)
REVERSED_SINGLES_WATERMARK_ROW = PixelRect(720, 1876, 1424, 1920)
DOUBLES_WATERMARK_ROW = PixelRect(1180, 0, 2344, 44)
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


def _name_above_number(slot: int, center_x: int, top: int, badge_height: int, name_size: int, name_width: int,
                       name_field: str) -> tuple[PlacementTagPlacement, list[TextPlacement]]:
    """Hang the name from ``top`` with the placement row (sponsor, art, seed) directly below it."""
    badge_y = top + round(name_size * 1.25) + 4 + badge_height // 2
    return _badge(slot, PixelPoint(center_x, badge_y), badge_height), [
        _text(slot, f"name_{slot}", name_field, PixelPoint(center_x, top), name_width, "ma", name_size),
        _text(slot, f"seed_{slot}", "entrant.seed", PixelPoint(center_x + _badge_width(slot, badge_height) // 2 + 8, badge_y),
              140, "lm", _seed_size(name_size)),
    ]


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
# Second place stands behind first, so its name and placement row sit just off
# center at the top or bottom of its area instead; its frame is wide enough for
# the widest render at its tier scale.
SINGLES_TIERS = {
    1: (PixelRect(260, 720, 1180, 1830), 1.12, 50, 180, 64, 620),
    2: (PixelRect(334, 246, 1106, 1000), None, 40, 64, 54, 280),
    3: (PixelRect(0, 830, 420, 1300), .6, 30, 56, 48, 420),
    4: (PixelRect(1020, 830, 1440, 1300), .6, 30, 56, 48, 420),
    5: (PixelRect(10, 380, 330, 760), .45, 20, 48, 42, 320),
    6: (PixelRect(1110, 380, 1430, 760), .45, 20, 48, 42, 320),
    7: (PixelRect(0, 50, 270, 320), .3, 10, 40, 36, 270),
    8: (PixelRect(1170, 50, 1440, 320), .3, 10, 40, 36, 270),
}
# Second place's label column sits this far beside its figures' center, just
# clear of the center line: top center-right just below the title when upright,
# or bottom center-left just above the title when reversed. Flipping second
# place mirrors it.
SECOND_LABEL_OFFSET = 180
SECOND_LABEL_TOP = SINGLES_HEADER_BOXES["top_middle"].bottom + 10
# Upright second place stands this far above the line its tier scale fills, so
# more of it shows over first place's head; the renderer shrinks only the very
# tallest poses to keep them below the title.
UPRIGHT_SECOND_RISE = 60

# Flipped top to bottom: first place leads from the top, second stands beneath
# its name (its tallest render reaching up to that name) on the line where its
# own name ends, just above the title, and the flanking tiers fly downward
# toward the bottom corners. Each back-row name still ends above the frames of
# the figures below it.
REVERSED_SINGLES_TIERS = {
    1: (PixelRect(260, 56, 1180, 1040), 1.12, 50, 180, 64, 620),
    2: (PixelRect(400, 1130, 1040, REVERSED_SINGLES_HEADER_BOXES["top_middle"].top), None, 40, 64, 54, 280),
    3: (PixelRect(0, 570, 420, 1040), .6, 30, 56, 48, 420),
    4: (PixelRect(1020, 570, 1440, 1040), .6, 30, 56, 48, 420),
    5: (PixelRect(10, 1108, 330, 1488), .45, 20, 48, 42, 320),
    6: (PixelRect(1110, 1108, 1430, 1488), .45, 20, 48, 42, 320),
    7: (PixelRect(0, 1550, 270, 1820), .3, 10, 40, 36, 270),
    8: (PixelRect(1170, 1550, 1440, 1820), .3, 10, 40, 36, 270),
}

# team slot: (member frame, figure center x) pairs, tier scale (None fills the
# frame with only the tallest render), z, badge height, name size, name width.
# Upper frames start low enough that a sponsored name above the tallest head
# stays out of the watermark's top row. The 2nd and 3rd frames hold the largest
# render (Bowser's victory pose) at their tier scale, so no member shrinks;
# figures keep their spacing by centering on their own x and slide inward only
# when a wide pose would leave the frame. The winning team's frames reach the
# corner header boxes so wide poses rarely shrink it, and the renderer shrinks
# both members equally when one is too large.
DOUBLES_TIERS = {
    1: (((PixelRect(460, 320, 1340, 1040), 900), (PixelRect(1020, 320, 1900, 1040), 1460)), .8, 20, 175, 56, 900),
    2: (((PixelRect(0, 146, 560, 631), 160), (PixelRect(160, 146, 720, 631), 440)), None, 10, 50, 44, 900),
    3: (((PixelRect(1640, 146, 2200, 631), 1920), (PixelRect(1800, 146, 2360, 631), 2200)), None, 10, 50, 44, 900),
}
DOUBLES_MEMBER_NAME_WIDTH = 560
# The winning team stands a little above its name, which sits on the canvas bottom.
DOUBLES_LEADER_NAME_BASELINE = 1066
# Back team placement art sits this far below their feet, with the name beneath it.
DOUBLES_SIDE_LABEL_GAP = 4
# Back team names hug their outer canvas edge and sit behind the winning team,
# so a name running toward the center disappears under its figures.
DOUBLES_SIDE_MARGIN = 16
DOUBLES_SIDE_NAME_Z = DOUBLES_TIERS[1][2] - 5


def _second_place_label(center_x: int, frame: PixelRect, vertically_reversed: bool, second_place_flipped: bool,
                        badge: int, size: int, width: int) -> tuple[PlacementTagPlacement, list[TextPlacement]]:
    """Put second place's label beside its figures' center, at the edge of its area nearest the title."""
    side = -1 if vertically_reversed != second_place_flipped else 1
    label_x = center_x + side * SECOND_LABEL_OFFSET
    if vertically_reversed:
        # The placement row sits above the name, whose bottom meets the figures' feet.
        return _number_above_name(2, label_x, frame.bottom - round(size * 1.25) - 6, badge, size, width, "entrant.player_tag")
    return _name_above_number(2, label_x, SECOND_LABEL_TOP, badge, size, width, "entrant.player_tag")


def flying_v_singles_preferences(vertically_reversed: bool = False, second_place_flipped: bool = False) -> ModePreferences:
    tiers = REVERSED_SINGLES_TIERS if vertically_reversed else SINGLES_TIERS
    frames = _header_regions(REVERSED_SINGLES_HEADER_BOXES if vertically_reversed else SINGLES_HEADER_BOXES,
                             REVERSED_SINGLES_WATERMARK_ROW if vertically_reversed else SINGLES_WATERMARK_ROW)
    characters, tags, text = [], [], []
    for slot, (frame, scale, z_index, badge, size, width) in tiers.items():
        center_x = (frame.left + frame.right) // 2
        scale = _fill_scale(frame) if scale is None else scale
        if slot == 2 and not vertically_reversed:
            frame = replace(frame, bottom=frame.bottom - UPRIGHT_SECOND_RISE)
        frames.append(FormattingAssetPlacement(f"entrant_{slot}", STANDING_FRAME, frame, z_index))
        characters.append(CharacterPlacement(f"entrant_{slot}", slot, PixelPoint(center_x, frame.bottom),
                                             scale=scale, z_index=z_index))
        # Names show only the player tag; any sponsor moves to the placement row.
        if slot == 2:
            badge_tag, label_text = _second_place_label(center_x, frame, vertically_reversed, second_place_flipped,
                                                        badge, size, width)
        else:
            badge_tag, label_text = _number_above_name(slot, center_x, frame.bottom, badge, size, width, "entrant.player_tag")
        tags.append(badge_tag)
        text.extend(label_text)
        text.append(_sponsor(slot, badge_tag.anchor.x, badge_tag.anchor.y, badge, size, width))
    variant = flying_v_singles_variant(vertically_reversed, second_place_flipped)
    return ModePreferences(
        ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.SINGLES, 8, variant)), SINGLES_CANVAS, ready=True,
        formatting_assets=tuple(frames), placement_tags=tuple(tags), character_slots=tuple(characters), text_slots=tuple(text),
    )


def _side_team_label(slot: int, left_side: bool, line: int, badge_height: int, name_size: int,
                     name_width: int) -> tuple[PlacementTagPlacement, list[TextPlacement]]:
    """Align a back team's placement art and name to its outer edge.

    The art hangs from ``line`` with the seed on its inner side, and the name
    sits beneath it, wrapping early and stacking extra lines downward.
    """
    side = "l" if left_side else "r"
    direction = 1 if left_side else -1
    edge = DOUBLES_SIDE_MARGIN if left_side else DOUBLES_CANVAS.width - DOUBLES_SIDE_MARGIN
    badge_width = _badge_width(slot, badge_height)
    badge_x = edge + direction * (badge_width // 2)
    badge_y = line + badge_height // 2
    name = _text(slot, f"name_{slot}", "entrant.team_name", PixelPoint(edge, line + badge_height + 4), name_width,
                 f"{side}a", name_size)
    return _badge(slot, PixelPoint(badge_x, badge_y), badge_height), [
        replace(name, wrap=True, z_index=DOUBLES_SIDE_NAME_Z),
        _text(slot, f"seed_{slot}", "entrant.seed", PixelPoint(badge_x + direction * (badge_width // 2 + 8), badge_y),
              140, f"{side}m", _seed_size(name_size)),
    ]


def flying_v_doubles_preferences() -> ModePreferences:
    frames, characters, tags, text = _header_regions(DOUBLES_HEADER_BOXES, DOUBLES_WATERMARK_ROW), [], [], []
    for slot, (members, scale, z_index, badge, size, width) in DOUBLES_TIERS.items():
        member_frames = [frame for frame, _x in members]
        scale = _fill_scale(member_frames[0]) if scale is None else scale
        for member, (frame, figure_x) in enumerate(members, 1):
            slot_id = f"entrant_{slot}_member_{member}"
            frames.append(FormattingAssetPlacement(slot_id, STANDING_FRAME, frame, z_index))
            characters.append(CharacterPlacement(slot_id, slot, PixelPoint(figure_x, frame.bottom),
                                                 member_slot=member, scale=scale, z_index=z_index))
            # The renderer lowers this baseline to just above the member's visible head.
            text.append(_text(slot, f"member_{slot}_{member}", "member.tag",
                              PixelPoint(figure_x, frame.top - NAME_ABOVE_HEAD_OFFSET),
                              min(frame.width, DOUBLES_MEMBER_NAME_WIDTH), "ms", size, member))
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
                                                 max(frame.bottom for frame in member_frames) + DOUBLES_SIDE_LABEL_GAP,
                                                 badge, size, width)
        tags.append(badge_tag)
        text.extend(label_text)
    return ModePreferences(
        ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.DOUBLES, 3)), DOUBLES_CANVAS, ready=True,
        formatting_assets=tuple(frames), placement_tags=tuple(tags), character_slots=tuple(characters), text_slots=tuple(text),
    )


if __name__ == "__main__":
    folder = Path(__file__).resolve().parent / "preferences" / "flying_v"
    folder.mkdir(parents=True, exist_ok=True)
    singles = (flying_v_singles_preferences(reversed_, flipped) for reversed_ in (False, True) for flipped in (False, True))
    for preferences in (*singles, flying_v_doubles_preferences()):
        target = folder / f"{preferences.selection.submode_id}.json"
        target.write_text(json.dumps(preferences.to_dict(), indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {target}")

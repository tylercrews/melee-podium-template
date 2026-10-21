"""Generate the reviewed Flying V Singles Top 8 and Doubles Top 3 preferences."""

from __future__ import annotations

import json
from pathlib import Path

from background_builder import PixelRect, PixelSize
from constants import PODIUM_BOX_COLORS_BY_SLOT
from creation_modes import CreationMode, ModeOptions, ModeSelection
from flying_v_content_renderer import BETWEEN_NAMES_SUFFIX
from flying_v_lineup import HANGING_FRAME, STANDING_FRAME
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
DOUBLES_HEADER_BOXES = {
    "top_left": PixelRect(16, 800, 456, 1064),
    "top_middle": PixelRect(660, 48, 1260, 230),
    "top_right": PixelRect(1464, 800, 1904, 1064),
}
# Width-to-height ratios of the canonical ordinal artwork, keyed by rank.
ORDINAL_ASPECTS = {1: .95, 2: 1.15, 3: 1.26, 4: 1.26, 5: 1.36, 7: 1.1}
NAME_ABOVE_HEAD_OFFSET = 15


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}FF".format(*rgb)


def _slot_color(slot: int) -> str:
    # Entrant text defaults to the Smash Player Colors used by legacy podiums.
    return _hex(PODIUM_BOX_COLORS_BY_SLOT[slot - 1].exterior_line)


def _header_regions(boxes: dict[str, PixelRect]) -> list[FormattingAssetPlacement]:
    return [FormattingAssetPlacement(f"header_{position}", HEADER_REGION, box) for position, box in boxes.items()]


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
    return _text(slot, f"sponsor_{slot}", "entrant.sponsor", PixelPoint(right, badge_y),
                 max(60, min(name_width // 2, right - 8)), "rm", max(20, name_size * 3 // 5))


def _number_above_name(slot: int, center_x: int, line: int, badge_height: int, name_size: int, name_width: int,
                       name_field: str) -> tuple[PlacementTagPlacement, list[TextPlacement]]:
    """Cover the feet with the placement art and put the name just below the line."""
    badge_y = line + 2 - badge_height // 2
    return _badge(slot, PixelPoint(center_x, badge_y), badge_height), [
        _text(slot, f"name_{slot}", name_field, PixelPoint(center_x, line + 6), name_width, "ma", name_size),
        _text(slot, f"seed_{slot}", "entrant.seed", PixelPoint(center_x + _badge_width(slot, badge_height) // 2 + 8, badge_y),
              140, "lm", _seed_size(name_size)),
    ]


def _name_above_number(slot: int, center_x: int, line: int, badge_height: int, name_size: int, name_width: int,
                       name_field: str) -> tuple[PlacementTagPlacement, list[TextPlacement]]:
    """Rest the name over the feet with the placement art just below the line."""
    badge_y = line + 10 + badge_height // 2
    return _badge(slot, PixelPoint(center_x, badge_y), badge_height), [
        _text(slot, f"name_{slot}", name_field, PixelPoint(center_x, line - 2), name_width, "ms", name_size),
        _text(slot, f"seed_{slot}", "entrant.seed", PixelPoint(center_x + _badge_width(slot, badge_height) // 2 + 8, badge_y),
              140, "lm", _seed_size(name_size)),
    ]


# slot: frame, hanging, tier scale, z, badge height, name size, name width, label line.
# Labels rest on the frame bottom (the feet) unless a fixed label line is given:
# second place keeps one label position while its hanging figure grows past it,
# rising only when it would otherwise cover first place's head.
SINGLES_TIERS = {
    1: (PixelRect(260, 680, 1180, 1920), False, 1.16, 50, 180, 64, 620, None),
    2: (PixelRect(420, 254, 1020, 1150), True, .86, 40, 64, 54, 520, 860),
    3: (PixelRect(0, 830, 420, 1300), False, .6, 30, 56, 48, 420, None),
    4: (PixelRect(1020, 830, 1440, 1300), False, .6, 30, 56, 48, 420, None),
    5: (PixelRect(10, 380, 330, 760), False, .45, 20, 48, 42, 320, None),
    6: (PixelRect(1110, 380, 1430, 760), False, .45, 20, 48, 42, 320, None),
    7: (PixelRect(0, 50, 270, 320), False, .3, 10, 40, 36, 270, None),
    8: (PixelRect(1170, 50, 1440, 320), False, .3, 10, 40, 36, 270, None),
}
# First place's name sits on the canvas bottom with its crest right above it.
SINGLES_LEADER_NAME_BASELINE = 1900

# team slot: two member frames, tier scale, z, badge height, name size, name width.
# Upper frames start low enough that a sponsored name above the tallest head
# stays out of the watermark's top row.
DOUBLES_TIERS = {
    1: ((PixelRect(520, 320, 1040, 1080), PixelRect(880, 320, 1400, 1080)), .8, 20, 175, 56, 900),
    2: ((PixelRect(20, 146, 320, 510), PixelRect(280, 146, 580, 510)), .46, 10, 50, 44, 540),
    3: ((PixelRect(1340, 146, 1640, 510), PixelRect(1600, 146, 1900, 510)), .46, 10, 50, 44, 540),
}
# The winning team's name sits on the canvas bottom.
DOUBLES_LEADER_NAME_BASELINE = 1066


def flying_v_singles_preferences() -> ModePreferences:
    frames, characters, tags, text = _header_regions(SINGLES_HEADER_BOXES), [], [], []
    for slot, (frame, hanging, scale, z_index, badge, size, width, line) in SINGLES_TIERS.items():
        center_x = (frame.left + frame.right) // 2
        frames.append(FormattingAssetPlacement(f"entrant_{slot}", HANGING_FRAME if hanging else STANDING_FRAME, frame, z_index))
        characters.append(CharacterPlacement(f"entrant_{slot}", slot, PixelPoint(center_x, frame.top if hanging else frame.bottom),
                                             scale=scale, z_index=z_index))
        # Names show only the player tag; any sponsor moves to the placement row.
        if slot == 1:
            badge_y = SINGLES_LEADER_NAME_BASELINE - size - 4 - badge // 2
            badge_tag = _badge(slot, PixelPoint(center_x, badge_y), badge)
            label_text = [
                _text(slot, "name_1", "entrant.player_tag", PixelPoint(center_x, SINGLES_LEADER_NAME_BASELINE), width, "ms", size),
                _text(slot, "seed_1", "entrant.seed", PixelPoint(center_x + _badge_width(slot, badge) // 2 + 8, badge_y),
                      140, "lm", _seed_size(size)),
            ]
        else:
            badge_tag, label_text = _number_above_name(slot, center_x, frame.bottom if line is None else line,
                                                       badge, size, width, "entrant.player_tag")
        tags.append(badge_tag)
        text.extend(label_text)
        text.append(_sponsor(slot, center_x, badge_tag.anchor.y, badge, size, width))
    return ModePreferences(
        ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.SINGLES, 8)), SINGLES_CANVAS, ready=True,
        formatting_assets=tuple(frames), placement_tags=tuple(tags), character_slots=tuple(characters), text_slots=tuple(text),
    )


def flying_v_doubles_preferences() -> ModePreferences:
    frames, characters, tags, text = _header_regions(DOUBLES_HEADER_BOXES), [], [], []
    for slot, (member_frames, scale, z_index, badge, size, width) in DOUBLES_TIERS.items():
        for member, frame in enumerate(member_frames, 1):
            slot_id = f"entrant_{slot}_member_{member}"
            center_x = (frame.left + frame.right) // 2
            frames.append(FormattingAssetPlacement(slot_id, STANDING_FRAME, frame, z_index))
            characters.append(CharacterPlacement(slot_id, slot, PixelPoint(center_x, frame.bottom),
                                                 member_slot=member, scale=scale, z_index=z_index))
            # The renderer lowers this baseline to just above the member's visible head.
            text.append(_text(slot, f"member_{slot}_{member}", "member.tag",
                              PixelPoint(center_x, frame.top - NAME_ABOVE_HEAD_OFFSET), frame.width, "ms", size, member))
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
        badge_tag, label_text = _name_above_number(slot, center_x, max(frame.bottom for frame in member_frames),
                                                   badge, size, width, "entrant.team_name")
        tags.append(badge_tag)
        text.extend(label_text)
    return ModePreferences(
        ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.DOUBLES, 3)), DOUBLES_CANVAS, ready=True,
        formatting_assets=tuple(frames), placement_tags=tuple(tags), character_slots=tuple(characters), text_slots=tuple(text),
    )


if __name__ == "__main__":
    folder = Path(__file__).resolve().parent / "preferences" / "flying_v"
    folder.mkdir(parents=True, exist_ok=True)
    for preferences in (flying_v_singles_preferences(), flying_v_doubles_preferences()):
        target = folder / f"{preferences.selection.submode_id}.json"
        target.write_text(json.dumps(preferences.to_dict(), indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {target}")

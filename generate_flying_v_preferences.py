"""Generate the reviewed Flying V Singles Top 8 and Doubles Top 3 preferences."""

from __future__ import annotations

import json
from pathlib import Path

from background_builder import PixelRect, PixelSize
from constants import PODIUM_BOX_COLORS_BY_SLOT
from creation_modes import CreationMode, ModeOptions, ModeSelection
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
SINGLES_CANVAS = PixelSize(1280, 1920)
DOUBLES_CANVAS = PixelSize(1920, 1080)
# Shared assignment keys: top_left is the bottom-left corner, top_middle is the
# top center, and top_right is the bottom-right corner.
SINGLES_HEADER_BOXES = {
    "top_left": PixelRect(16, 1612, 356, 1904),
    "top_middle": PixelRect(340, 48, 940, 246),
    "top_right": PixelRect(924, 1612, 1264, 1904),
}
DOUBLES_HEADER_BOXES = {
    "top_left": PixelRect(16, 800, 456, 1064),
    "top_middle": PixelRect(660, 48, 1260, 230),
    "top_right": PixelRect(1464, 800, 1904, 1064),
}
# Width-to-height ratios of the canonical ordinal artwork, keyed by rank.
ORDINAL_ASPECTS = {1: .95, 2: 1.15, 3: 1.26, 4: 1.26, 5: 1.36, 7: 1.1}
# Names rest on the label line, over the figure's feet; the placement artwork
# hangs just below that line.
BADGE_GAP = 10
NAME_BASELINE_OFFSET = -2


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}FF".format(*rgb)


def _slot_color(slot: int) -> str:
    # Entrant text defaults to the Smash Player Colors used by legacy podiums.
    return _hex(PODIUM_BOX_COLORS_BY_SLOT[slot - 1].exterior_line)


def _header_regions(boxes: dict[str, PixelRect]) -> list[FormattingAssetPlacement]:
    return [FormattingAssetPlacement(f"header_{position}", HEADER_REGION, box) for position, box in boxes.items()]


def _label(slot: int, center_x: int, line: int, badge_height: int, name_size: int, name_width: int,
           name_field: str) -> tuple[PlacementTagPlacement, list[TextPlacement]]:
    """Put the name directly above the placement artwork, with the seed beside the art."""
    rank = placement_rank(slot)
    badge_width = round(badge_height * ORDINAL_ASPECTS[rank] * 1.1)
    badge_center_y = line + BADGE_GAP + badge_height // 2
    badge = PlacementTagPlacement(
        f"number_{slot}", ordinal_asset_id(rank),
        PixelPoint(center_x, badge_center_y), PixelSize(badge_width, badge_height), z_index=60,
    )
    color = _slot_color(slot)
    text = [
        TextPlacement(f"name_{slot}", name_field, PixelPoint(center_x, line + NAME_BASELINE_OFFSET), name_width,
                      entrant_slot=slot, pillow_anchor="ms", preferred_size=name_size, z_index=60, color=color),
        TextPlacement(f"seed_{slot}", "entrant.seed", PixelPoint(center_x + badge_width // 2 + 8, badge_center_y),
                      140, entrant_slot=slot, pillow_anchor="lm", preferred_size=max(20, min(36, name_size * 11 // 20)),
                      z_index=60, color=color),
    ]
    return badge, text


# slot: frame, hanging, tier scale, z, badge height, name size, name width, label line.
# A label line of None rests the name on the frame's bottom (the figure's feet).
# First place stands on the canvas bottom with its name and enlarged crest over its legs.
SINGLES_TIERS = {
    1: (PixelRect(200, 680, 1080, 1920), False, 1.16, 50, 180, 64, 560, 1718),
    2: (PixelRect(380, 254, 900, 980), True, .77, 40, 60, 52, 480, None),
    3: (PixelRect(20, 840, 380, 1330), False, .5, 30, 50, 44, 360, None),
    4: (PixelRect(900, 840, 1260, 1330), False, .5, 30, 50, 44, 360, None),
    5: (PixelRect(4, 430, 304, 800), False, .37, 20, 44, 40, 300, None),
    6: (PixelRect(976, 430, 1276, 800), False, .37, 20, 44, 40, 300, None),
    7: (PixelRect(0, 52, 250, 360), False, .3, 10, 40, 36, 250, None),
    8: (PixelRect(1030, 52, 1280, 360), False, .3, 10, 40, 36, 250, None),
}

# team slot: two member frames, tier scale, z, badge height, name size, name width, label line.
DOUBLES_TIERS = {
    1: ((PixelRect(460, 320, 1060, 1080), PixelRect(860, 320, 1460, 1080)), .88, 20, 150, 56, 900, 904),
    2: ((PixelRect(40, 150, 340, 700), PixelRect(260, 150, 560, 700)), .55, 10, 50, 44, 500, None),
    3: ((PixelRect(1360, 150, 1660, 700), PixelRect(1580, 150, 1880, 700)), .55, 10, 50, 44, 500, None),
}


def flying_v_singles_preferences() -> ModePreferences:
    frames, characters, tags, text = _header_regions(SINGLES_HEADER_BOXES), [], [], []
    for slot, (frame, hanging, scale, z_index, badge, size, width, line) in SINGLES_TIERS.items():
        center_x = (frame.left + frame.right) // 2
        frames.append(FormattingAssetPlacement(f"entrant_{slot}", HANGING_FRAME if hanging else STANDING_FRAME, frame, z_index))
        characters.append(CharacterPlacement(f"entrant_{slot}", slot, PixelPoint(center_x, frame.top if hanging else frame.bottom),
                                             scale=scale, z_index=z_index))
        badge_tag, label_text = _label(slot, center_x, frame.bottom if line is None else line, badge, size, width, "entrant.tag")
        tags.append(badge_tag)
        text.extend(label_text)
    return ModePreferences(
        ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.SINGLES, 8)), SINGLES_CANVAS, ready=True,
        formatting_assets=tuple(frames), placement_tags=tuple(tags), character_slots=tuple(characters), text_slots=tuple(text),
    )


def flying_v_doubles_preferences() -> ModePreferences:
    frames, characters, tags, text = _header_regions(DOUBLES_HEADER_BOXES), [], [], []
    for slot, (member_frames, scale, z_index, badge, size, width, line) in DOUBLES_TIERS.items():
        for member, frame in enumerate(member_frames, 1):
            slot_id = f"entrant_{slot}_member_{member}"
            center_x = (frame.left + frame.right) // 2
            frames.append(FormattingAssetPlacement(slot_id, STANDING_FRAME, frame, z_index))
            characters.append(CharacterPlacement(slot_id, slot, PixelPoint(center_x, frame.bottom),
                                                 member_slot=member, scale=scale, z_index=z_index))
            # The renderer lowers this baseline to just above the member's visible head.
            text.append(TextPlacement(f"member_{slot}_{member}", "member.tag", PixelPoint(center_x, frame.top - 15), frame.width,
                                      entrant_slot=slot, member_slot=member, pillow_anchor="ms", preferred_size=size,
                                      z_index=60, color=_slot_color(slot)))
        center_x = (member_frames[0].left + member_frames[1].right) // 2
        bottom = max(frame.bottom for frame in member_frames)
        badge_tag, label_text = _label(slot, center_x, bottom if line is None else line, badge, size, width, "entrant.team_name")
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

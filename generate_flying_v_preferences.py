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


CANVAS = PixelSize(1080, 1920)
HEADER_REGION = "flying_v_header_region"
# Shared assignment keys: top_left is the bottom-left corner, top_middle is the
# top center, and top_right is the bottom-right corner.
HEADER_BOXES = {
    "top_left": PixelRect(16, 1612, 316, 1904),
    "top_middle": PixelRect(270, 48, 810, 246),
    "top_right": PixelRect(764, 1612, 1064, 1904),
}
# Width-to-height ratios of the canonical ordinal artwork, keyed by rank.
ORDINAL_ASPECTS = {1: .95, 2: 1.15, 3: 1.26, 4: 1.26, 5: 1.36, 7: 1.1}
LABEL_GAP = 6


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}FF".format(*rgb)


def _slot_color(slot: int) -> str:
    # Entrant text defaults to the Smash Player Colors used by legacy podiums.
    return _hex(PODIUM_BOX_COLORS_BY_SLOT[slot - 1].exterior_line)


def _header_regions() -> list[FormattingAssetPlacement]:
    return [FormattingAssetPlacement(f"header_{position}", HEADER_REGION, box) for position, box in HEADER_BOXES.items()]


def _label(slot: int, center_x: int, top: int, badge_height: int, name_size: int, name_width: int,
           name_field: str) -> tuple[PlacementTagPlacement, list[TextPlacement]]:
    """Stack the placement artwork above the name, with the seed beside the art."""
    rank = placement_rank(slot)
    badge_width = round(badge_height * ORDINAL_ASPECTS[rank] * 1.1)
    badge = PlacementTagPlacement(
        f"number_{slot}", ordinal_asset_id(rank),
        PixelPoint(center_x, top + badge_height // 2), PixelSize(badge_width, badge_height), z_index=60,
    )
    color = _slot_color(slot)
    text = [
        TextPlacement(f"name_{slot}", name_field, PixelPoint(center_x, top + badge_height + 2), name_width,
                      entrant_slot=slot, pillow_anchor="ma", preferred_size=name_size, z_index=60, color=color),
        TextPlacement(f"seed_{slot}", "entrant.seed", PixelPoint(center_x + badge_width // 2 + 8, top + badge_height // 2),
                      140, entrant_slot=slot, pillow_anchor="lm", preferred_size=max(20, name_size * 11 // 20),
                      z_index=60, color=color),
    ]
    return badge, text


# slot: frame, hanging, tier scale, z, badge height, name size, name width.
SINGLES_TIERS = {
    1: (PixelRect(150, 712, 930, 1740), False, 1.08, 50, 92, 60, 440),
    2: (PixelRect(290, 254, 790, 960), True, .74, 40, 58, 52, 440),
    3: (PixelRect(20, 1000, 380, 1460), False, .5, 30, 50, 44, 330),
    4: (PixelRect(700, 1000, 1060, 1460), False, .5, 30, 50, 44, 330),
    5: (PixelRect(10, 520, 330, 880), False, .37, 20, 44, 40, 300),
    6: (PixelRect(750, 520, 1070, 880), False, .37, 20, 44, 40, 300),
    7: (PixelRect(0, 52, 262, 352), False, .3, 10, 40, 36, 262),
    8: (PixelRect(818, 52, 1080, 352), False, .3, 10, 40, 36, 262),
}

# team slot: two member frames, tier scale, z, badge height, name size, name width.
DOUBLES_TIERS = {
    1: ((PixelRect(140, 1060, 600, 1756), PixelRect(480, 1060, 940, 1756)), .8, 20, 76, 52, 440),
    2: ((PixelRect(0, 300, 290, 846), PixelRect(220, 300, 510, 846)), .54, 10, 50, 44, 440),
    3: ((PixelRect(570, 300, 860, 846), PixelRect(790, 300, 1080, 846)), .54, 10, 50, 44, 440),
}


def flying_v_singles_preferences() -> ModePreferences:
    frames, characters, tags, text = _header_regions(), [], [], []
    for slot, (frame, hanging, scale, z_index, badge, size, width) in SINGLES_TIERS.items():
        center_x = (frame.left + frame.right) // 2
        frames.append(FormattingAssetPlacement(f"entrant_{slot}", HANGING_FRAME if hanging else STANDING_FRAME, frame, z_index))
        characters.append(CharacterPlacement(f"entrant_{slot}", slot, PixelPoint(center_x, frame.top if hanging else frame.bottom),
                                             scale=scale, z_index=z_index))
        badge_tag, label_text = _label(slot, center_x, frame.bottom + LABEL_GAP, badge, size, width, "entrant.tag")
        tags.append(badge_tag)
        text.extend(label_text)
    return ModePreferences(
        ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.SINGLES, 8)), CANVAS, ready=True,
        formatting_assets=tuple(frames), placement_tags=tuple(tags), character_slots=tuple(characters), text_slots=tuple(text),
    )


def flying_v_doubles_preferences() -> ModePreferences:
    frames, characters, tags, text = _header_regions(), [], [], []
    for slot, (member_frames, scale, z_index, badge, size, width) in DOUBLES_TIERS.items():
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
        badge_tag, label_text = _label(slot, center_x, bottom + LABEL_GAP, badge, size, width, "entrant.team_name")
        tags.append(badge_tag)
        text.extend(label_text)
    return ModePreferences(
        ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.DOUBLES, 3)), CANVAS, ready=True,
        formatting_assets=tuple(frames), placement_tags=tuple(tags), character_slots=tuple(characters), text_slots=tuple(text),
    )


if __name__ == "__main__":
    folder = Path(__file__).resolve().parent / "preferences" / "flying_v"
    folder.mkdir(parents=True, exist_ok=True)
    for preferences in (flying_v_singles_preferences(), flying_v_doubles_preferences()):
        target = folder / f"{preferences.selection.submode_id}.json"
        target.write_text(json.dumps(preferences.to_dict(), indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {target}")

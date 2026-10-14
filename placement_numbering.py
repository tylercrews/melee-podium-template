"""Resolve placement-number artwork without changing retained bracket results."""

from dataclasses import replace
import re

from background_builder import PixelPoint, PixelSize
from creation_modes import CreationMode, PodiumStyle
from mode_preferences import PlacementTagPlacement


def default_tournament_placing(selection):
    return not (selection.mode is CreationMode.EYES
                and selection.options.entrant_count in {10, 15, 20, 25})


def placement_rank(slot, use_tournament_placing=True):
    if isinstance(slot, bool) or not isinstance(slot, int) or slot < 1:
        raise ValueError("placement slot must be a positive integer")
    if not use_tournament_placing or slot <= 4:
        return slot
    base = 1 << ((slot - 1).bit_length() - 1)
    group = base // 2
    return base + 1 + ((slot - 1 - base) // group) * group


def ordinal_asset_id(rank):
    suffix = "th" if 10 <= rank % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
    return f"{rank:02d}{suffix}.png"


def number_placement_tags(tags, use_tournament_placing):
    result = []
    for tag in tags:
        match = re.search(r"(?:podium|entrant|number)_(\d+)", tag.slot_id)
        if match is None:
            raise ValueError(f"Placement tag does not identify an entrant slot: {tag.slot_id}")
        result.append(replace(tag, asset_id=ordinal_asset_id(placement_rank(int(match[1]), use_tournament_placing))))
    return tuple(result)


def numbered_preferences(preferences, use_tournament_placing):
    tags = list(preferences.placement_tags)
    # The older Customizable Top 8 file calibrates only the first three badges.
    # Give the remaining small faces the same reviewed fit as Top 16's podiums.
    if (preferences.selection.mode is CreationMode.PODIUM
            and preferences.selection.options.podium_style is PodiumStyle.CUSTOMIZABLE
            and preferences.selection.submode_id == "singles_top_8"):
        existing = {tag.slot_id for tag in tags}
        for index, body in enumerate(preferences.formatting_assets, start=1):
            slot_id = f"podium_{index}_placement_tag"
            if slot_id in existing:
                continue
            box = body.destination
            height = max(14, round(box.height * .42))
            tags.append(PlacementTagPlacement(slot_id, ordinal_asset_id(index),
                        PixelPoint((box.left + box.right) // 2 - 5, box.bottom - box.height // 3),
                        PixelSize(round(height * 1.5), height), index - 1))
    return replace(preferences, placement_tags=number_placement_tags(tags, use_tournament_placing))

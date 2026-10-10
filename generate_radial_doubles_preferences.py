"""Merge Radial Singles wedges into four team blocks without moving portraits."""

from dataclasses import replace
import json
from pathlib import Path

from background_builder import PixelRect
from creation_modes import CreationMode, ModeOptions, ModeSelection
from generate_radial_preferences import radial_preferences
from mode_preferences import FormattingAssetPlacement, ModePreferences, PixelPoint, TextPlacement
from models import TournamentFormat


RADIAL_TEAM_MEMBERS = ((1, 2), (3, 5), (4, 6), (7, 8))


def radial_doubles_preferences() -> ModePreferences:
    singles = radial_preferences()
    center = (960, 540)
    polygons = (
        ((0, 0), (1920, 0), center),
        ((0, 0), center, (0, 1080)),
        ((1920, 0), (1920, 1080), center),
        ((0, 1080), center, (1920, 1080)),
    )
    assets = [p for p in singles.formatting_assets if p.asset_id == "radial_header_region"]
    for team, vertices in enumerate(polygons, 1):
        left, top = min(x for x, y in vertices), min(y for x, y in vertices)
        right, bottom = max(x for x, y in vertices), max(y for x, y in vertices)
        assets.append(FormattingAssetPlacement(
            f"slice_{team}", "radial_slice", PixelRect(left, top, right, bottom),
            polygon=tuple(PixelPoint(x - left, y - top) for x, y in vertices),
        ))
    # Member masks preserve the original portrait cuts; only the team boundary
    # polygons above receive colored borders.
    assets.extend(replace(p, slot_id=p.slot_id.replace("slice_", "portrait_"), asset_id="radial_portrait_slice") for p in singles.formatting_assets if p.asset_id == "radial_slice")
    characters, text, numbers = [], [], []
    # Doubles owns its label/art positions independently of Singles refinements.
    member_names = ((460, 105, "ma"), (1460, 105, "ma"), (145, 195, "la"), (1775, 195, "ra"), (145, 885, "ls"), (1775, 885, "rs"), (460, 975, "ms"), (1460, 975, "ms"))
    number_anchors = ((325, 96), (68, 165), (1852, 165), (200, 1028))
    seed_anchors = ((96, 8, "la"), (14, 70, "la"), (1906, 70, "ra"), (96, 1062, "ls"))
    team_labels = ((960, 18, "ma", 900), (30, 510, "la", 600), (1890, 510, "ra", 600), (960, 1054, "ms", 1050))
    for team, members in enumerate(RADIAL_TEAM_MEMBERS, 1):
        x, y, anchor, width = team_labels[team - 1]
        text.append(TextPlacement(f"team_{team}", "entrant.team_name", PixelPoint(x, y), width, entrant_slot=team, pillow_anchor=anchor, preferred_size=48, z_index=30))
        ordinal = f"{team:02}{ {1: 'st', 2: 'nd', 3: 'rd', 4: 'th'}[team]}.png"
        numbers.append(replace(singles.placement_tags[members[0] - 1], slot_id=f"number_{team}", asset_id=ordinal, anchor=PixelPoint(*number_anchors[team - 1])))
        for member, old_slot in enumerate(members, 1):
            characters.append(replace(singles.character_slots[old_slot - 1], entrant_slot=team, member_slot=member))
            label = next(p for p in singles.text_slots if p.entrant_slot == old_slot and p.field == "entrant.tag")
            name_x, name_y, name_anchor = member_names[old_slot - 1]
            label = replace(label, anchor=PixelPoint(name_x, name_y), pillow_anchor=name_anchor)
            text.append(replace(label, field="member.tag", entrant_slot=team, member_slot=member))
        seed = next(p for p in singles.text_slots if p.entrant_slot == members[0] and p.field == "entrant.seed")
        seed_x, seed_y, seed_anchor = seed_anchors[team - 1]
        seed = replace(seed, anchor=PixelPoint(seed_x, seed_y), pillow_anchor=seed_anchor)
        text.append(replace(seed, slot_id=f"seed_team_{team}", entrant_slot=team))
    return ModePreferences(
        ModeSelection(CreationMode.RADIAL, ModeOptions(TournamentFormat.DOUBLES, 4)),
        singles.canvas_size, ready=True, formatting_assets=tuple(assets),
        placement_tags=tuple(numbers), character_slots=tuple(characters), text_slots=tuple(text),
    )


if __name__ == "__main__":
    path = Path(__file__).resolve().parent / "preferences" / "radial" / "doubles_top_4.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(radial_doubles_preferences().to_dict(), indent=2) + "\n", encoding="utf-8")

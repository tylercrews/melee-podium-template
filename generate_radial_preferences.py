"""Extract the eight Radial sections and anchors from the 1280x720 reference."""

import json
from pathlib import Path

from background_builder import PixelRect, PixelSize
from creation_modes import CreationMode, ModeOptions, ModeSelection
from mode_preferences import CharacterPlacement, FormattingAssetPlacement, ModePreferences, PixelPoint, PlacementTagPlacement, TextPlacement
from models import TournamentFormat


def radial_preferences() -> ModePreferences:
    def point(x, y):
        return PixelPoint(round(x * 1.5), round(y * 1.5))

    triangles = (
        ((0, 0), (640, 0), (640, 360)),
        ((640, 0), (1280, 0), (640, 360)),
        ((0, 0), (640, 360), (0, 360)),
        ((1280, 0), (1280, 360), (640, 360)),
        ((0, 360), (640, 360), (0, 720)),
        ((640, 360), (1280, 360), (1280, 720)),
        ((0, 720), (640, 360), (640, 720)),
        ((640, 360), (1280, 720), (640, 720)),
    )
    portraits = ((490, 100), (875, 135), (220, 235), (1035, 225), (235, 465), (1035, 480), (465, 560), (850, 565))
    numbers = ((210, 48), (1710, 48), (68, 165), (1852, 165), (68, 610), (1852, 610), (200, 1028), (1720, 1028))
    names = ((450, 36), (1470, 36), (145, 195), (1775, 195), (145, 585), (1775, 585), (460, 1059), (1460, 1059))
    assets = []
    characters = []
    text = []
    placement_tags = []
    for slot, vertices in enumerate(triangles, 1):
        left = min(x for x, y in vertices)
        top = min(y for x, y in vertices)
        right = max(x for x, y in vertices)
        bottom = max(y for x, y in vertices)
        assets.append(FormattingAssetPlacement(
            f"slice_{slot}", "radial_slice", PixelRect(round(left * 1.5), round(top * 1.5), round(right * 1.5), round(bottom * 1.5)),
            polygon=tuple(point(x - left, y - top) for x, y in vertices),
        ))
        characters.append(CharacterPlacement(f"portrait_{slot}", slot, point(*portraits[slot - 1]), z_index=10))
        name_x, name_y = names[slot - 1]
        anchor = "la" if slot in (3, 5) else "ra" if slot in (4, 6) else "ms" if slot in (7, 8) else "ma"
        rank = (1, 2, 3, 4, 5, 5, 7, 7)[slot - 1]
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank, "th")
        placement_tags.append(PlacementTagPlacement(
            f"number_{slot}", f"{rank:02}{suffix}.png", PixelPoint(*numbers[slot - 1]), PixelSize(120, 80 if slot in (7, 8) else 90), z_index=20,
        ))
        text.extend((
            TextPlacement(f"tag_{slot}", "entrant.tag", PixelPoint(name_x, name_y), 330, entrant_slot=slot, pillow_anchor=anchor, preferred_size=40, z_index=30),
            TextPlacement(f"seed_{slot}", "entrant.seed", PixelPoint(name_x, name_y - 55 if slot in (7, 8) else name_y + 55), 250, entrant_slot=slot, pillow_anchor=anchor, preferred_size=22, z_index=30),
        ))
    for position, bounds in (
        ("top_left", (460, 355, 820, 445)),
        ("top_middle", (490, 230, 790, 500)),
        ("top_right", (470, 450, 810, 600)),
    ):
        assets.append(FormattingAssetPlacement(f"header_{position}", "radial_header_region", PixelRect(*(round(v * 1.5) for v in bounds))))
    return ModePreferences(
        ModeSelection(CreationMode.RADIAL, ModeOptions(TournamentFormat.SINGLES, 8)),
        PixelSize(1920, 1080), ready=True,
        formatting_assets=tuple(assets), placement_tags=tuple(placement_tags), character_slots=tuple(characters), text_slots=tuple(text),
    )


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "preferences" / "radial" / "singles_top_8.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(radial_preferences().to_dict(), indent=2) + "\n", encoding="utf-8")

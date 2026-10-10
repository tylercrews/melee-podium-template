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
    numbers = ((365, 96), (1710, 48), (68, 165), (1852, 165), (68, 915), (1852, 915), (200, 1028), (1720, 1028))
    names = ((936, 14), (984, 14), (18, 518), (1902, 518), (18, 554), (1902, 554), (936, 1054), (984, 1054))
    name_anchors = ("ra", "la", "ls", "rs", "la", "ra", "rs", "ls")
    seeds = ((96, 8, "la"), (1824, 8, "ra"), (14, 70, "la"), (1906, 70, "ra"), (14, 990, "ls"), (1906, 990, "rs"), (96, 1062, "ls"), (1824, 1062, "rs"))
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
        anchor = name_anchors[slot - 1]
        seed_x, seed_y, seed_anchor = seeds[slot - 1]
        rank = (1, 2, 3, 4, 5, 5, 7, 7)[slot - 1]
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank, "th")
        placement_tags.append(PlacementTagPlacement(
            f"number_{slot}", f"{rank:02}{suffix}.png", PixelPoint(*numbers[slot - 1]), PixelSize(200, 180) if slot == 1 else PixelSize(120, 80 if slot in (7, 8) else 90), z_index=20,
        ))
        text.extend((
            TextPlacement(f"tag_{slot}", "entrant.tag", PixelPoint(name_x, name_y), 330, entrant_slot=slot, pillow_anchor=anchor, preferred_size=40, z_index=30),
            TextPlacement(f"seed_{slot}", "entrant.seed", PixelPoint(seed_x, seed_y), 100, entrant_slot=slot, pillow_anchor=seed_anchor, preferred_size=22, z_index=30),
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

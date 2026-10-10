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
    labels = ((175, 4), (1120, 4), (38, 116), (1238, 116), (60, 376), (1228, 376), (135, 656), (1128, 656))
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
        x, y = labels[slot - 1]
        # The side labels sit near the canvas edge; fit long identities inward.
        anchor = "la" if slot in (3, 5) else "ra" if slot in (4, 6) else "ma"
        label_x = 8 if slot in (3, 5) else 1272 if slot in (4, 6) else x
        rank = (1, 2, 3, 4, 5, 5, 7, 7)[slot - 1]
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank, "th")
        placement_tags.append(PlacementTagPlacement(
            f"number_{slot}", f"{rank:02}{suffix}.png", point(x, y + 14), PixelSize(70, 44), z_index=20,
        ))
        text.extend((
            TextPlacement(f"tag_{slot}", "entrant.tag", point(label_x, 706 if slot in (7, 8) else y + 20), 360, entrant_slot=slot, pillow_anchor="ms" if slot in (7, 8) else anchor, preferred_size=40, z_index=30),
            TextPlacement(f"seed_{slot}", "entrant.seed", point(label_x, y - 23 if slot in (7, 8) else y + 49), 250, entrant_slot=slot, pillow_anchor=anchor, preferred_size=22, z_index=30),
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

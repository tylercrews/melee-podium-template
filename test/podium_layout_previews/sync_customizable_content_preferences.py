"""Project legacy content slots onto the independently-sized custom podiums."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_ROOT = PROJECT_ROOT / "preferences" / "podium" / "legacy"
CUSTOM_ROOT = PROJECT_ROOT / "preferences" / "podium" / "customizable"
ASSET_ROOT = PROJECT_ROOT / "formatting_assets" / "podium" / "customizable"


def _project_x(x: int, source: dict, destination: dict) -> int:
    proportion = (x - source["left"]) / (source["right"] - source["left"])
    return round(
        destination["left"]
        + proportion * (destination["right"] - destination["left"])
    )


def _semantic_face_bands(asset_id: str) -> tuple[int, tuple[tuple[int, int], ...]]:
    """Return mask height and inclusive cyan-band bounds."""
    with Image.open(ASSET_ROOT / asset_id) as source:
        rgba = source.convert("RGBA")
        cyan_rows = sorted(
            {
                y
                for y in range(rgba.height)
                for x in range(rgba.width)
                if rgba.getpixel((x, y))[:3] == (0, 255, 255)
            }
        )
        bands: list[tuple[int, int]] = []
        band_start = band_end = cyan_rows[0]
        for previous, current in zip(cyan_rows, cyan_rows[1:]):
            if current != previous + 1:
                bands.append((band_start, band_end))
                band_start = current
            band_end = current
        bands.append((band_start, band_end))
        return rgba.height, tuple(bands)


def _top_surface_bottom(asset_id: str, destination: dict) -> int:
    """Map the bottom of the mask's first cyan face band into its destination."""

    source_height, bands = _semantic_face_bands(asset_id)
    first_band_end = bands[0][1]
    return destination["top"] + round(
        (first_band_end + 1)
        * (destination["bottom"] - destination["top"])
        / source_height
    )


def _position_seed(entry: dict, podium: dict) -> None:
    """Keep a seed's glyphs inside the front face above its lower trim."""

    destination = podium["destination"]
    source_height, bands = _semantic_face_bands(podium["asset_id"])
    face_start, face_end = bands[1] if len(bands) > 1 else bands[0]
    height = destination["bottom"] - destination["top"]
    face_top = destination["top"] + round(face_start * height / source_height)
    face_bottom = destination["top"] + round((face_end + 1) * height / source_height)
    preferred_size = min(24, max(11, face_bottom - face_top - 4))
    entry["preferred_size"] = preferred_size
    # Tyrowo's glyph bottom sits roughly 7/6 of the font size below an
    # ascender anchor. Leave one more pixel before the lower face trim.
    entry["anchor"]["y"] = face_bottom - round(preferred_size * 7 / 6) - 1


def _podium_slot(entry: dict, four_podium: bool) -> int:
    entrant_slot = entry["entrant_slot"]
    if four_podium and entry.get("field") == "entrant.summary":
        return entrant_slot - 4
    return entrant_slot


def synchronize() -> None:
    """Populate custom content slots while retaining their style-specific geometry."""

    for custom_path in sorted(CUSTOM_ROOT.glob("*.json")):
        legacy = json.loads((LEGACY_ROOT / custom_path.name).read_text())
        custom = json.loads(custom_path.read_text())
        legacy_podiums = {
            index: item["destination"]
            for index, item in enumerate(legacy["formatting_assets"], start=1)
        }
        custom_podiums = {
            index: item
            for index, item in enumerate(custom["formatting_assets"], start=1)
        }
        four_podium = custom["selection"]["options"]["variant"] == "four_podium"

        custom["character_slots"] = []
        for source_entry in legacy["character_slots"]:
            entry = deepcopy(source_entry)
            slot = _podium_slot(entry, four_podium)
            destination = custom_podiums[slot]["destination"]
            entry["anchor"]["x"] = _project_x(
                source_entry["anchor"]["x"], legacy_podiums[slot], destination
            )
            entry["anchor"]["y"] = _top_surface_bottom(
                custom_podiums[slot]["asset_id"], destination
            )
            custom["character_slots"].append(entry)

        custom["text_slots"] = []
        for source_entry in legacy["text_slots"]:
            entry = deepcopy(source_entry)
            slot = _podium_slot(entry, four_podium)
            entry["anchor"]["x"] = _project_x(
                source_entry["anchor"]["x"],
                legacy_podiums[slot],
                custom_podiums[slot]["destination"],
            )
            if entry["field"] == "entrant.seed":
                _position_seed(entry, custom_podiums[slot])
            custom["text_slots"].append(entry)

        if custom_path.name == "doubles_top_4.json":
            second_member = next(
                entry
                for entry in custom["character_slots"]
                if entry["slot_id"] == "entrant_1_member_2_character"
            )
            second_member["anchor"]["x"] += 10

        custom_path.write_text(json.dumps(custom, indent=2) + "\n")


if __name__ == "__main__":
    synchronize()

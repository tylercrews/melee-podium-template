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


def _top_surface_bottom(asset_id: str, destination: dict) -> int:
    """Map the bottom of the mask's first cyan face band into its destination."""

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
        first_band_end = cyan_rows[0]
        for previous, current in zip(cyan_rows, cyan_rows[1:]):
            if current != previous + 1:
                break
            first_band_end = current
        source_height = rgba.height
    return destination["top"] + round(
        (first_band_end + 1)
        * (destination["bottom"] - destination["top"])
        / source_height
    )


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
            custom["text_slots"].append(entry)

        custom_path.write_text(json.dumps(custom, indent=2) + "\n")


if __name__ == "__main__":
    synchronize()

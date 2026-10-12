"""Fit Customizable four-podium numerals inside the thick outer front outlines."""

from collections import deque
from dataclasses import replace
import json
import math
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from background_builder import PixelSize
from creation_modes import PodiumStyle
from mode_preferences import ModePreferences, PixelPoint

PREFERENCES = ROOT / "preferences/podium/customizable/singles_top_8_four_podium.json"


def _runs(rows):
    runs = []
    for row in rows:
        if not runs or row != runs[-1][1] + 1:
            runs.append([row, row])
        else:
            runs[-1][1] = row
    return runs


def front_panel_bounds(body, anchor_x):
    with Image.open(ROOT / "formatting_assets/podium/customizable" / body.asset_id) as source:
        image = source.convert("RGBA")
    x = round((anchor_x - body.destination.left) / body.destination.width * image.width)
    red, cyan = [], []
    for y in range(image.height):
        r, g, b, a = image.getpixel((x, y))
        if a >= 128 and r > 200 and g < 30 and b < 30:
            red.append(y)
        if a >= 128 and r < 30 and g > 200 and b > 200:
            cyan.append(y)
    face = _runs(cyan)[-1]
    before = [run for run in _runs(red) if run[1] < face[0]]
    after = [run for run in _runs(red) if run[0] > face[1]]
    # The nearest red bands are the inner stripes. The next ones are outer rims.
    # Use the INNER edges of the thick outer rims, leaving the rims uncovered.
    top, bottom = before[-2][1] + 1, after[1][0]
    return (
        body.destination.top + round(top * body.destination.height / image.height),
        body.destination.top + round(bottom * body.destination.height / image.height),
    )


def first_numeral_vertical_bounds(image):
    """Find the largest gold component (the 1), excluding suffix, wreath, and bow."""

    width, height = image.size
    mask = bytearray(1 if a >= 128 and r >= g * .95 and g >= b * 1.25 and r >= 80 else 0
                     for r, g, b, a in image.convert("RGBA").getdata())
    best = (0, 0, 0)
    for index in range(len(mask)):
        if not mask[index]:
            continue
        mask[index] = 0
        queue = deque([index])
        count, top, bottom = 0, height, 0
        while queue:
            current = queue.popleft()
            x, y = current % width, current // width
            count += 1
            top, bottom = min(top, y), max(bottom, y + 1)
            for neighbor in (current - width if y else -1,
                             current + width if y + 1 < height else -1,
                             current - 1 if x else -1,
                             current + 1 if x + 1 < width else -1):
                if neighbor >= 0 and mask[neighbor]:
                    mask[neighbor] = 0
                    queue.append(neighbor)
        if count > best[0]:
            best = count, top, bottom
    if not best[0]:
        raise ValueError("First-place artwork must contain a gold numeral")
    # Include the numeral's dark outline beyond the gold fill.
    return max(0, best[1] - 8), min(height, best[2] + 8)


def fit_tags(preferences):
    if preferences.selection.options.podium_style is not PodiumStyle.CUSTOMIZABLE:
        raise ValueError("Outer-front calibration requires Customizable podium masks")
    if len(preferences.formatting_assets) != 4 or len(preferences.placement_tags) != 4:
        raise ValueError("This review calibrates exactly four podium numbers")
    bodies = sorted(preferences.formatting_assets, key=lambda body: body.destination.left)
    fitted, measurements = [], {}
    for body, tag in zip(bodies, preferences.placement_tags):
        top, bottom = front_panel_bounds(body, tag.anchor.x)
        with Image.open(ROOT / "formatting_assets/placement_numbers" / tag.asset_id) as source:
            source = source.convert("RGBA")
        if tag.asset_id == "01st.png":
            glyph_top, glyph_bottom = first_numeral_vertical_bounds(source)
        else:
            # Include faint antialiased edges so no part of the ordinal crosses the rim.
            glyph_top, glyph_bottom = 0, source.height
        height = math.floor((bottom - top) * source.height / (glyph_bottom - glyph_top))
        width = math.ceil(source.width * height / source.height)
        layer = source.copy()
        layer.thumbnail((width, height), Image.Resampling.LANCZOS)
        layer_top = bottom - round(glyph_bottom * layer.height / source.height)
        fitted.append(replace(tag, anchor=PixelPoint(tag.anchor.x, layer_top + layer.height // 2),
                              max_size=PixelSize(width, height)))
        measurements[tag.slot_id] = {
            "front_panel_top": top, "front_panel_bottom": bottom,
            "numeral_top": layer_top + round(glyph_top * layer.height / source.height),
            "numeral_bottom": bottom, "artwork_bottom": layer_top + layer.height,
        }
    return tuple(fitted), measurements


if __name__ == "__main__":
    raw = json.loads(PREFERENCES.read_text(encoding="utf-8"))
    tags, measurements = fit_tags(ModePreferences.from_dict(raw))
    raw["placement_tags"] = [tag.to_dict() for tag in tags]
    PREFERENCES.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(measurements, indent=2))

"""Quick-pick swatches shown in every RGBA color picker."""

from __future__ import annotations

from itertools import combinations
import json
import math
from pathlib import Path
import unittest

from color_values import format_rgba_hex
from constants import BRONZE_PODIUM, GOLD_PODIUM, MEDAL_GRAY_PODIUM, PODIUM_BOX_COLORS_BY_SLOT, SILVER_PODIUM
from preview_layers import RAINBOW_MAIN_COLORS


SAVED_COLORS = Path(__file__).resolve().parents[1] / "frontend" / "src" / "savedColors.json"
# Swatches closer than this CIEDE2000 difference read as the same color side by side.
MINIMUM_DIFFERENCE = 12
# Deliberate near pairs: signature palette colors and the requested light neutrals.
ALLOWED_NEAR_PAIRS = {
    frozenset({"Smash Player Colors Yellow", "Olympic Medals Gold"}),
    frozenset({"Smash Player Colors Gray", "Olympic Medals Gray"}),
    frozenset({"Olympic Medals Silver", "Neutrals Very Light Gray"}),
    frozenset({"Neutrals White", "Neutrals Very Light Gray"}),
}


def _swatches() -> dict[str, str]:
    return {f"{palette['name']} {entry['name']}": entry["color"]
            for palette in json.loads(SAVED_COLORS.read_text(encoding="utf-8")) for entry in palette["colors"]}


def _lab(color: str) -> tuple[float, float, float]:
    linear = [channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4
              for channel in (int(color[index:index + 2], 16) / 255 for index in (1, 3, 5))]
    x, y, z = (sum(weight * channel for weight, channel in zip(row, linear)) / white for row, white in (
        ((.4124, .3576, .1805), .95047), ((.2126, .7152, .0722), 1), ((.0193, .1192, .9505), 1.08883)))
    f = lambda value: value ** (1 / 3) if value > .008856 else 7.787 * value + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def _ciede2000(first: str, second: str) -> float:
    return _ciede2000_lab(_lab(first), _lab(second))


def _ciede2000_lab(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    (l1, a1, b1), (l2, a2, b2) = first, second
    mean_chroma = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = .5 * (1 - math.sqrt(mean_chroma ** 7 / (mean_chroma ** 7 + 25 ** 7)))
    a1, a2 = (1 + g) * a1, (1 + g) * a2
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    h1, h2 = math.degrees(math.atan2(b1, a1)) % 360, math.degrees(math.atan2(b2, a2)) % 360
    hue_delta = 0 if c1 * c2 == 0 else (h2 - h1 + 180) % 360 - 180
    hue_difference = 2 * math.sqrt(c1 * c2) * math.sin(math.radians(hue_delta / 2))
    mean_lightness, mean_chroma = (l1 + l2) / 2, (c1 + c2) / 2
    mean_hue = h1 + h2 if c1 * c2 == 0 else ((h1 + h2) / 2 + (180 if abs(h1 - h2) > 180 else 0)) % 360
    t = (1 - .17 * math.cos(math.radians(mean_hue - 30)) + .24 * math.cos(math.radians(2 * mean_hue))
         + .32 * math.cos(math.radians(3 * mean_hue + 6)) - .2 * math.cos(math.radians(4 * mean_hue - 63)))
    rotation = -2 * math.sqrt(mean_chroma ** 7 / (mean_chroma ** 7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-((mean_hue - 275) / 25) ** 2)))
    lightness = (l2 - l1) / (1 + .015 * (mean_lightness - 50) ** 2 / math.sqrt(20 + (mean_lightness - 50) ** 2))
    chroma = (c2 - c1) / (1 + .045 * mean_chroma)
    hue = hue_difference / (1 + .015 * mean_chroma * t)
    return math.sqrt(lightness ** 2 + chroma ** 2 + hue ** 2 + rotation * chroma * hue)


class SavedColorSwatchTests(unittest.TestCase):
    def test_renderer_backed_swatches_match_their_palettes(self) -> None:
        palettes = {palette["name"]: [entry["color"] for entry in palette["colors"]]
                    for palette in json.loads(SAVED_COLORS.read_text(encoding="utf-8"))}
        self.assertEqual(palettes["Smash Player Colors"], [format_rgba_hex(*box.exterior_line, 255) for box in PODIUM_BOX_COLORS_BY_SLOT])
        self.assertEqual(palettes["Olympic Medals"], [format_rgba_hex(*box.exterior_line, 255)
                                                      for box in (GOLD_PODIUM, SILVER_PODIUM, BRONZE_PODIUM, MEDAL_GRAY_PODIUM)])
        # Rainbow keeps only the colors no other palette already offers.
        self.assertEqual(palettes["Rainbow"], ["#A84BE0FF"])
        self.assertTrue(set(palettes["Rainbow"]) <= set(RAINBOW_MAIN_COLORS))

    def test_color_difference_matches_published_ciede2000_pairs(self) -> None:
        # Pairs 1, 7, 13, and 17 of Sharma, Wu, and Dalal's CIEDE2000 test data.
        for first, second, expected in (
            ((50, 2.6772, -79.7751), (50, 0, -82.7485), 2.0425),
            ((50, 0, 0), (50, -1, 2), 2.3669),
            ((50, 2.49, -.001), (50, -2.49, .0009), 7.1792),
            ((50, 2.5, 0), (73, 25, -18), 27.1492),
        ):
            self.assertAlmostEqual(_ciede2000_lab(first, second), expected, places=4)
        self.assertEqual(_ciede2000("#5B59F8FF", "#5B59F8FF"), 0)

    def test_swatches_are_distinct(self) -> None:
        swatches = _swatches()
        self.assertEqual(len(set(swatches.values())), len(swatches), "Duplicate swatch colors")
        close = sorted((round(_ciede2000(swatches[first], swatches[second]), 1), first, second)
                       for first, second in combinations(swatches, 2)
                       if frozenset({first, second}) not in ALLOWED_NEAR_PAIRS and _ciede2000(swatches[first], swatches[second]) < MINIMUM_DIFFERENCE)
        self.assertEqual(close, [])


if __name__ == "__main__":
    unittest.main()

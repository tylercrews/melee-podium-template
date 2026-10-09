"""Integrity checks for browser-composited Format preview layers."""

from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image

from preview_layers import (
    HEADER_CONTENTS,
    HEADER_POSITIONS,
    EYE_LAYOUTS,
    LAYOUTS,
    SQUARE_HEADER_LAYOUTS,
    SQUARE_LAYOUTS,
    _customizable_colors,
    header_permutation_id,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAYER_ROOT = PROJECT_ROOT / "frontend" / "public" / "format_preview_layers"


class PreviewLayerTests(unittest.TestCase):
    def test_generated_layer_inventory_is_complete(self) -> None:
        files = tuple(LAYER_ROOT.rglob("*.png"))
        self.assertEqual(len(files), 288)
        self.assertEqual(len(tuple((LAYER_ROOT / "radial_headers").rglob("*.png"))), 18)
        self.assertEqual(len(tuple((LAYER_ROOT / "radial_logos").rglob("*.png"))), 3)
        self.assertEqual(len(tuple((LAYER_ROOT / "radial").rglob("*.png"))), 4)
        self.assertEqual(len(tuple((LAYER_ROOT / "headers").rglob("*.png"))), 18)
        self.assertEqual(len(tuple((LAYER_ROOT / "square_headers").rglob("*.png"))), 36)
        self.assertEqual(len(tuple((LAYER_ROOT / "podiums" / "legacy").rglob("*.png"))), 4)
        self.assertEqual(len(tuple((LAYER_ROOT / "podiums" / "customizable").rglob("*.png"))), 16)
        self.assertEqual(len(tuple((LAYER_ROOT / "squares").rglob("*.png"))), 12)
        self.assertEqual(len(tuple((LAYER_ROOT / "eye_headers").rglob("*.png"))), 144)
        self.assertEqual(len(tuple((LAYER_ROOT / "eyes").rglob("*.png"))), 32)

    def test_layers_are_nonempty_rgba_images_with_expected_dimensions(self) -> None:
        for path in LAYER_ROOT.rglob("*.png"):
            with self.subTest(path=path), Image.open(path) as image:
                self.assertEqual(image.mode, "RGBA")
                self.assertIn(
                    image.size,
                    {
                        (1672, 941),
                        (1920, 941),
                        (1920, 1080),
                        (1080, 1920),
                        (1920, 1542),
                        (1920, 2114),
                        (2400, 1828),
                        (1920, 2686),
                        (2400, 2400),
                    },
                )
                self.assertIsNotNone(image.getbbox())

    def test_header_permutation_identifier_uses_position_order(self) -> None:
        layout = dict(zip(HEADER_POSITIONS, HEADER_CONTENTS, strict=True))
        self.assertEqual(header_permutation_id(layout), "logo-title-metadata")
        self.assertEqual(set(LAYOUTS), {"top_3", "top_4", "top_8", "top_8_four_podiums"})
        self.assertEqual(
            set(SQUARE_LAYOUTS),
            {"singles_top_8", "doubles_top_3", "doubles_top_4"},
        )
        self.assertEqual(set(SQUARE_HEADER_LAYOUTS), {"singles", "doubles"})
        self.assertEqual(
            set(EYE_LAYOUTS),
            {
                "singles_top_8",
                "singles_top_10",
                "singles_top_15",
                "singles_top_16",
                "singles_top_20",
                "singles_top_25",
                "doubles_top_3",
                "doubles_top_4",
            },
        )

    def test_square_layers_combine_border_and_background(self) -> None:
        root = LAYER_ROOT / "squares" / "singles_top_8"
        with Image.open(root / "smash_player_colors.png") as layer:
            self.assertIsNotNone(layer.getbbox())
            self.assertGreater(layer.getpixel((300, 300))[3], 0)

    def test_mode_selector_thumbnails_are_small_webp_images(self) -> None:
        thumbnail_root = PROJECT_ROOT / "frontend" / "public" / "format_mode_thumbnails"
        for name in ("podium", "eyes", "squares"):
            with self.subTest(name=name), Image.open(thumbnail_root / f"{name}.webp") as image:
                self.assertEqual(image.format, "WEBP")
                self.assertLessEqual(image.width, 360)
                self.assertLessEqual(image.height, 240)
                self.assertIsNotNone(image.getbbox())

    def test_large_cached_presets_repeat_or_keep_later_medals_gray(self) -> None:
        for preset in ("smash_player_colors", "rainbow"):
            with self.subTest(preset=preset):
                colors = _customizable_colors(preset, 25)
                self.assertEqual(
                    colors.color_for_slot(1).resolve().main_color,
                    colors.color_for_slot(9).resolve().main_color,
                )
                self.assertEqual(
                    colors.color_for_slot(2).resolve().main_color,
                    colors.color_for_slot(10).resolve().main_color,
                )
        medals = _customizable_colors("olympic_medals", 25)
        self.assertNotEqual(
            medals.color_for_slot(1).resolve().main_color,
            medals.color_for_slot(4).resolve().main_color,
        )
        self.assertEqual(
            medals.color_for_slot(4).resolve().main_color,
            medals.color_for_slot(25).resolve().main_color,
        )


if __name__ == "__main__":
    unittest.main()

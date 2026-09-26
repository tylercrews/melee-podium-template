"""Integrity checks for browser-composited Format preview layers."""

from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image

from preview_layers import HEADER_CONTENTS, HEADER_POSITIONS, LAYOUTS, header_permutation_id


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAYER_ROOT = PROJECT_ROOT / "frontend" / "public" / "format_preview_layers"


class PreviewLayerTests(unittest.TestCase):
    def test_generated_layer_inventory_is_complete(self) -> None:
        files = tuple(LAYER_ROOT.rglob("*.png"))
        self.assertEqual(len(files), 38)
        self.assertEqual(len(tuple((LAYER_ROOT / "headers").rglob("*.png"))), 18)
        self.assertEqual(len(tuple((LAYER_ROOT / "podiums" / "legacy").rglob("*.png"))), 4)
        self.assertEqual(len(tuple((LAYER_ROOT / "podiums" / "customizable").rglob("*.png"))), 16)

    def test_layers_are_nonempty_rgba_images_with_expected_dimensions(self) -> None:
        for path in LAYER_ROOT.rglob("*.png"):
            with self.subTest(path=path), Image.open(path) as image:
                self.assertEqual(image.mode, "RGBA")
                self.assertIn(image.size, {(1672, 941), (1920, 941)})
                self.assertIsNotNone(image.getbbox())

    def test_header_permutation_identifier_uses_position_order(self) -> None:
        layout = dict(zip(HEADER_POSITIONS, HEADER_CONTENTS, strict=True))
        self.assertEqual(header_permutation_id(layout), "logo-title-metadata")
        self.assertEqual(set(LAYOUTS), {"top_3", "top_4", "top_8", "top_8_four_podiums"})


if __name__ == "__main__":
    unittest.main()

"""Integrity checks for bundled full-color website icons."""

from pathlib import Path
import unittest

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ICON_FOLDER = PROJECT_ROOT / "formatting_assets" / "website_icons"
EXPECTED_ICONS = {
    "bluesky.png",
    "challonge.png",
    "parrygg.png",
    "startgg.png",
    "twitch.png",
    "x.png",
    "youtube.png",
}


class WebsiteIconTests(unittest.TestCase):
    def test_full_color_icons_are_normalized_rgba_images(self):
        actual = {path.name for path in ICON_FOLDER.glob("*.png")}
        self.assertEqual(actual, EXPECTED_ICONS)

        for filename in EXPECTED_ICONS:
            with self.subTest(filename=filename), Image.open(ICON_FOLDER / filename) as icon:
                self.assertEqual(icon.size, (512, 512))
                self.assertEqual(icon.mode, "RGBA")


if __name__ == "__main__":
    unittest.main()

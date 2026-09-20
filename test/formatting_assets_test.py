"""Tests for the mode formatting-asset composition stage."""

import unittest

from PIL import Image

from background_builder import PixelRect, PixelSize
from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from formatting_assets import FormattingAssetRenderer
from mode_preferences import FormattingAssetPlacement, ModePreferences
from models import TournamentFormat


class MemoryFormattingAssets:
    def __init__(self, images: dict[str, Image.Image]) -> None:
        self.images = images

    def open(self, selection: ModeSelection, asset_id: str) -> Image.Image:
        self.last_selection = selection
        return self.images[asset_id].copy()


class FormattingAssetsTest(unittest.TestCase):
    def test_assets_are_drawn_over_the_background_in_z_order(self) -> None:
        selection = ModeSelection(
            CreationMode.PODIUM,
            ModeOptions(
                TournamentFormat.SINGLES,
                3,
                podium_style=PodiumStyle.CUSTOMIZABLE,
            ),
        )
        preferences = ModePreferences(
            selection=selection,
            canvas_size=PixelSize(4, 4),
            ready=True,
            formatting_assets=(
                FormattingAssetPlacement(
                    "upper", "red.png", PixelRect(1, 1, 3, 3), z_index=2
                ),
                FormattingAssetPlacement(
                    "lower", "green.png", PixelRect(1, 1, 3, 3), z_index=1
                ),
            ),
        )
        assets = MemoryFormattingAssets(
            {
                "red.png": Image.new("RGBA", (1, 1), (255, 0, 0, 255)),
                "green.png": Image.new("RGBA", (1, 1), (0, 255, 0, 255)),
            }
        )
        background = Image.new("RGBA", (4, 4), (0, 0, 255, 255))

        result = FormattingAssetRenderer(assets).draw(background, preferences)

        self.assertEqual(assets.last_selection, selection)
        self.assertEqual(result.getpixel((0, 0)), (0, 0, 255, 255))
        self.assertEqual(result.getpixel((1, 1)), (255, 0, 0, 255))
        self.assertEqual(background.getpixel((1, 1)), (0, 0, 255, 255))


if __name__ == "__main__":
    unittest.main()

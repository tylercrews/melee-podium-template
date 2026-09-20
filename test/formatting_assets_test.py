"""Tests for the mode formatting-asset composition stage."""

import unittest

from PIL import Image

from background_builder import PixelRect, PixelSize
from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from formatting_assets import FormattingAssetRenderer
from mode_preferences import (
    FormattingAssetPlacement,
    ModePreferences,
    PixelPoint,
    PlacementTagPlacement,
)
from models import TournamentFormat
from podium_colors import PodiumColorSelection


class MemoryFormattingAssets:
    def __init__(self, images: dict[str, Image.Image]) -> None:
        self.images = images

    def open(self, selection: ModeSelection, asset_id: str) -> Image.Image:
        self.last_selection = selection
        return self.images[asset_id].copy()


class MemoryPlacementTagAssets:
    def __init__(self, images: dict[str, Image.Image]) -> None:
        self.images = images

    def open(self, asset_id: str) -> Image.Image:
        self.last_asset_id = asset_id
        return self.images[asset_id].copy()


class FormattingAssetsTest(unittest.TestCase):
    def test_assets_are_drawn_over_the_background_in_z_order(self) -> None:
        selection = ModeSelection(
            CreationMode.PODIUM,
            ModeOptions(
                TournamentFormat.SINGLES,
                3,
                podium_style=PodiumStyle.LEGACY,
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

    def test_customizable_assets_receive_the_selected_semantic_colors(self) -> None:
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
            canvas_size=PixelSize(3, 1),
            ready=True,
            formatting_assets=(
                FormattingAssetPlacement(
                    "podium",
                    "mask.png",
                    PixelRect(0, 0, 3, 1),
                ),
            ),
        )
        mask = Image.new("RGBA", (3, 1))
        mask.putdata(
            [
                (255, 0, 0, 255),
                (0, 255, 255, 255),
                (0, 0, 255, 255),
            ]
        )

        result = FormattingAssetRenderer(
            MemoryFormattingAssets({"mask.png": mask})
        ).draw(
            Image.new("RGBA", (3, 1)),
            preferences,
            PodiumColorSelection(
                main_color="#102030FF",
                face_color="#405060FF",
                base_color="#708090FF",
            ),
        )

        self.assertEqual(
            list(result.getdata()),
            [
                (16, 32, 48, 255),
                (64, 80, 96, 255),
                (112, 128, 144, 255),
            ],
        )

    def test_placement_tags_are_centered_and_aspect_fitted_after_podiums(self) -> None:
        selection = ModeSelection(
            CreationMode.PODIUM,
            ModeOptions(
                TournamentFormat.SINGLES,
                3,
                podium_style=PodiumStyle.LEGACY,
            ),
        )
        preferences = ModePreferences(
            selection=selection,
            canvas_size=PixelSize(7, 5),
            ready=True,
            formatting_assets=(
                FormattingAssetPlacement(
                    "podium", "green.png", PixelRect(0, 0, 7, 5)
                ),
            ),
            placement_tags=(
                PlacementTagPlacement(
                    "first_place",
                    "01st.png",
                    anchor=PixelPoint(3, 2),
                    max_size=PixelSize(4, 4),
                ),
            ),
        )
        tags = MemoryPlacementTagAssets(
            {"01st.png": Image.new("RGBA", (8, 4), (255, 0, 0, 255))}
        )
        renderer = FormattingAssetRenderer(
            assets=MemoryFormattingAssets(
                {"green.png": Image.new("RGBA", (1, 1), (0, 255, 0, 255))}
            ),
            placement_tag_assets=tags,
        )

        result = renderer.draw(Image.new("RGBA", (7, 5)), preferences)

        self.assertEqual(tags.last_asset_id, "01st.png")
        self.assertEqual(result.getpixel((0, 0)), (0, 255, 0, 255))
        self.assertEqual(result.getpixel((1, 1)), (255, 0, 0, 255))
        self.assertEqual(result.getpixel((4, 2)), (255, 0, 0, 255))
        self.assertEqual(result.getpixel((5, 2)), (0, 255, 0, 255))


if __name__ == "__main__":
    unittest.main()

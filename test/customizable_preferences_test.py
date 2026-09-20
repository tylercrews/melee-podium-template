"""Regression checks for the initial customizable podium formatting layouts."""

import unittest
from pathlib import Path

from PIL import Image

from background_builder import PixelSize
from creation_modes import CreationMode, PodiumStyle
from mode_preferences import ModePreferenceRepository


EXPECTED_ASSETS = {
    "doubles_top_3": ("tall.png", "medium.png", "short.png"),
    "singles_top_3": ("tall.png", "medium.png", "short.png"),
    "doubles_top_4": ("tall.png", "medium.png", "short.png", "x_short.png"),
    "singles_top_4": ("tall.png", "medium.png", "short.png", "x_short.png"),
    "singles_top_8_four_podium": (
        "tall.png",
        "medium.png",
        "short.png",
        "x_short.png",
    ),
    "singles_top_8": (
        "x_tall.png",
        "tall.png",
        "medium.png",
        "short.png",
        "x_short.png",
        "x_short.png",
        "flat.png",
        "flat.png",
    ),
}


class CustomizablePreferencesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        all_preferences = ModePreferenceRepository().list_preferences(
            CreationMode.PODIUM
        )
        cls.customizable = {
            item.selection.submode_id: item
            for item in all_preferences
            if item.selection.options.podium_style is PodiumStyle.CUSTOMIZABLE
        }
        cls.legacy = {
            item.selection.submode_id: item
            for item in all_preferences
            if item.selection.options.podium_style is PodiumStyle.LEGACY
        }
        cls.asset_folder = (
            Path(__file__).resolve().parents[1]
            / "formatting_assets"
            / "podium"
            / "customizable"
        )

    def test_all_six_layouts_use_the_wider_review_canvas(self) -> None:
        self.assertEqual(set(self.customizable), set(EXPECTED_ASSETS))
        for preferences in self.customizable.values():
            self.assertEqual(preferences.canvas_size, PixelSize(1736, 941))
            self.assertFalse(preferences.ready)

    def test_rank_height_assets_match_the_requested_order(self) -> None:
        for submode_id, expected in EXPECTED_ASSETS.items():
            actual = tuple(
                placement.asset_id
                for placement in self.customizable[submode_id].formatting_assets
            )
            self.assertEqual(actual, expected, submode_id)

    def test_customizable_podiums_match_legacy_widths_and_baselines(self) -> None:
        for submode_id, customizable in self.customizable.items():
            legacy = self.legacy[submode_id]
            self.assertEqual(
                len(customizable.formatting_assets),
                len(legacy.formatting_assets),
            )
            for custom_placement, legacy_placement in zip(
                customizable.formatting_assets,
                legacy.formatting_assets,
                strict=True,
            ):
                self.assertEqual(
                    custom_placement.destination.width,
                    legacy_placement.destination.width,
                    submode_id,
                )
                self.assertEqual(
                    custom_placement.destination.bottom,
                    legacy_placement.destination.bottom,
                    submode_id,
                )

    def test_destination_heights_preserve_each_asset_aspect_ratio(self) -> None:
        for submode_id, preferences in self.customizable.items():
            for placement in preferences.formatting_assets:
                with Image.open(self.asset_folder / placement.asset_id) as source:
                    expected_height = round(
                        placement.destination.width * source.height / source.width
                    )
                self.assertEqual(
                    placement.destination.height,
                    expected_height,
                    f"{submode_id}/{placement.slot_id}",
                )

    def test_each_podium_group_is_centered_on_the_wider_canvas(self) -> None:
        for submode_id, preferences in self.customizable.items():
            left_margin = min(
                placement.destination.left
                for placement in preferences.formatting_assets
            )
            right_margin = preferences.canvas_size.width - max(
                placement.destination.right
                for placement in preferences.formatting_assets
            )
            self.assertLessEqual(
                abs(left_margin - right_margin),
                1,
                submode_id,
            )

    def test_active_masks_exist_and_are_tightly_cropped(self) -> None:
        self.assertEqual(
            {path.name for path in self.asset_folder.glob("*.png")},
            {asset for assets in EXPECTED_ASSETS.values() for asset in assets},
        )
        for path in self.asset_folder.glob("*.png"):
            with Image.open(path) as source:
                alpha = source.convert("RGBA").getchannel("A")
                self.assertEqual(alpha.getbbox(), (0, 0, source.width, source.height))

    def test_placement_tag_anchors_land_inside_their_podiums(self) -> None:
        for submode_id, preferences in self.customizable.items():
            for podium, tag in zip(
                preferences.formatting_assets,
                preferences.placement_tags,
                strict=True,
            ):
                destination = podium.destination
                self.assertLessEqual(destination.left, tag.anchor.x, submode_id)
                self.assertLess(tag.anchor.x, destination.right, submode_id)
                self.assertLessEqual(destination.top, tag.anchor.y, submode_id)
                self.assertLess(tag.anchor.y, destination.bottom, submode_id)


if __name__ == "__main__":
    unittest.main()

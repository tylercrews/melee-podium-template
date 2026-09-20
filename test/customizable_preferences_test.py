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

EXPECTED_TAG_MAX_SIZES = {
    "doubles_top_3": ((155, 132), (100, 76), (54, 39)),
    "singles_top_3": ((155, 132), (100, 76), (54, 39)),
    "doubles_top_4": ((155, 132), (72, 56), (38, 30), (16, 12)),
    "singles_top_4": ((155, 132), (72, 56), (38, 30), (16, 12)),
    "singles_top_8_four_podium": (
        (155, 132),
        (72, 56),
        (38, 30),
        (16, 12),
    ),
    "singles_top_8": ((90, 95), (50, 43), (36, 28)),
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
            self.assertEqual(preferences.canvas_size, PixelSize(1920, 941))
            self.assertFalse(preferences.ready)

    def test_rank_height_assets_match_the_requested_order(self) -> None:
        for submode_id, expected in EXPECTED_ASSETS.items():
            actual = tuple(
                placement.asset_id
                for placement in self.customizable[submode_id].formatting_assets
            )
            self.assertEqual(actual, expected, submode_id)

    def test_customizable_podiums_keep_legacy_baselines(self) -> None:
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
                if submode_id != "singles_top_8":
                    self.assertGreater(
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

    def test_layouts_use_the_wider_canvas_to_reduce_overlap(self) -> None:
        for submode_id, preferences in self.customizable.items():
            podiums = sorted(
                preferences.formatting_assets,
                key=lambda placement: placement.destination.left,
            )
            overlaps = [
                previous.destination.right - current.destination.left
                for previous, current in zip(podiums, podiums[1:])
            ]
            self.assertTrue(
                all(overlap <= 0 for overlap in overlaps),
                submode_id,
            )

    def test_top_8_uses_small_consistent_gaps(self) -> None:
        podiums = sorted(
            self.customizable["singles_top_8"].formatting_assets,
            key=lambda placement: placement.destination.left,
        )
        self.assertEqual(
            [
                current.destination.left - previous.destination.right
                for previous, current in zip(podiums, podiums[1:])
            ],
            [5] * 7,
        )

    def test_character_anchors_fit_their_custom_podiums(self) -> None:
        for submode_id, preferences in self.customizable.items():
            podiums = {
                index: podium.destination
                for index, podium in enumerate(preferences.formatting_assets, start=1)
            }
            self.assertTrue(preferences.character_slots, submode_id)
            self.assertTrue(preferences.text_slots, submode_id)
            for placement in preferences.character_slots:
                destination = podiums[placement.entrant_slot]
                self.assertLessEqual(destination.left, placement.anchor.x, submode_id)
                self.assertLess(placement.anchor.x, destination.right, submode_id)
                self.assertLessEqual(destination.top, placement.anchor.y, submode_id)
                self.assertLess(placement.anchor.y, destination.bottom, submode_id)

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
            podiums_by_slot = {
                podium.slot_id: podium for podium in preferences.formatting_assets
            }
            for tag in preferences.placement_tags:
                podium_slot = tag.slot_id.removesuffix("_placement_tag")
                podium = podiums_by_slot[podium_slot]
                destination = podium.destination
                self.assertLessEqual(destination.left, tag.anchor.x, submode_id)
                self.assertLess(tag.anchor.x, destination.right, submode_id)
                self.assertLessEqual(destination.top, tag.anchor.y, submode_id)
                self.assertLess(tag.anchor.y, destination.bottom, submode_id)

    def test_flat_podiums_never_have_placement_tags(self) -> None:
        for submode_id, preferences in self.customizable.items():
            flat_slots = {
                placement.slot_id
                for placement in preferences.formatting_assets
                if placement.asset_id == "flat.png"
            }
            tagged_slots = {
                tag.slot_id.removesuffix("_placement_tag")
                for tag in preferences.placement_tags
            }
            self.assertTrue(flat_slots.isdisjoint(tagged_slots), submode_id)

    def test_top_8_only_displays_first_through_third_place_art(self) -> None:
        tags = self.customizable["singles_top_8"].placement_tags
        self.assertEqual(
            [tag.asset_id for tag in tags],
            ["01st.png", "02nd.png", "03rd.png"],
        )

    def test_customizable_placement_art_uses_layout_specific_bounds(self) -> None:
        for submode_id, preferences in self.customizable.items():
            actual = tuple(
                tag.max_size.as_tuple() for tag in preferences.placement_tags
            )
            self.assertEqual(
                actual,
                EXPECTED_TAG_MAX_SIZES[submode_id],
                submode_id,
            )


if __name__ == "__main__":
    unittest.main()

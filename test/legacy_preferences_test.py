"""Regression checks for values extracted from the legacy podium renderer."""

import unittest
from pathlib import Path

from PIL import Image

from background_builder import PixelSize
from creation_modes import CreationMode, PodiumStyle
from DrawPodium import DOUBLES_ANCHORS, PODIUM_TEXT_ANCHORS, SINGLES_ANCHORS
from mode_preferences import ModePreferenceRepository
from models import TournamentFormat
from portrait_scale_adjustment_for_each_mode import get_mode_portrait_scale


class LegacyPreferencesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.preferences = {
            item.selection.submode_id: item
            for item in ModePreferenceRepository().list_preferences(
                CreationMode.PODIUM
            )
            if item.selection.options.podium_style is PodiumStyle.LEGACY
        }

    def test_every_legacy_layout_keeps_the_old_output_size(self) -> None:
        self.assertEqual(len(self.preferences), 6)
        for item in self.preferences.values():
            self.assertEqual(item.canvas_size, PixelSize(1672, 941))

    def test_character_anchors_and_scales_match_draw_podium(self) -> None:
        for submode_id, preferences in self.preferences.items():
            options = preferences.selection.options
            layout_count = 4 if options.variant == "four_podium" else options.entrant_count
            expected_scale = get_mode_portrait_scale(submode_id)
            if options.event_format is TournamentFormat.SINGLES:
                expected = {
                    (entrant_slot, None): anchor
                    for entrant_slot, anchor in SINGLES_ANCHORS[layout_count].items()
                }
            else:
                expected = {
                    (entrant_slot, member_slot): anchor
                    for entrant_slot, anchors in DOUBLES_ANCHORS[layout_count].items()
                    for member_slot, anchor in enumerate(anchors, start=1)
                }

            actual = {
                (item.entrant_slot, item.member_slot): (item.anchor.x, item.anchor.y)
                for item in preferences.character_slots
            }
            self.assertEqual(actual, expected, submode_id)
            self.assertTrue(
                all(item.scale == expected_scale for item in preferences.character_slots),
                submode_id,
            )

    def test_fixed_text_anchors_match_draw_podium(self) -> None:
        for submode_id, preferences in self.preferences.items():
            options = preferences.selection.options
            layout_count = 4 if options.variant == "four_podium" else options.entrant_count
            by_slot_id = {item.slot_id: item for item in preferences.text_slots}

            for entrant_slot in range(1, layout_count + 1):
                seed = by_slot_id[f"entrant_{entrant_slot}_seed"]
                expected_seed = PODIUM_TEXT_ANCHORS[layout_count][entrant_slot]["seed"]
                self.assertEqual((seed.anchor.x, seed.anchor.y), expected_seed)

            if options.variant == "four_podium":
                for summary_slot, entrant_slot in enumerate(range(5, 9), start=1):
                    summary = by_slot_id[f"entrant_{entrant_slot}_summary"]
                    expected = PODIUM_TEXT_ANCHORS[4][summary_slot]["label"]
                    self.assertEqual((summary.anchor.x, summary.anchor.y), expected)
                continue

            label_offset = -22 if layout_count == 8 else -30
            label_kind = (
                "team_name"
                if options.event_format is TournamentFormat.DOUBLES
                else "character_name"
            )
            for entrant_slot in range(1, layout_count + 1):
                label = by_slot_id[f"entrant_{entrant_slot}_{label_kind}"]
                source = PODIUM_TEXT_ANCHORS[layout_count][entrant_slot]["label"]
                self.assertEqual(
                    (label.anchor.x, label.anchor.y),
                    (source[0], source[1] + label_offset),
                )

    def test_active_legacy_assets_exist_and_are_tightly_cropped(self) -> None:
        folder = (
            Path(__file__).resolve().parents[1]
            / "formatting_assets"
            / "podium"
            / "legacy"
        )

        asset_ids = {
            placement.asset_id
            for preferences in self.preferences.values()
            for placement in preferences.formatting_assets
        }
        self.assertEqual(len(asset_ids), 15)
        for asset_id in asset_ids:
            path = folder / asset_id
            self.assertTrue(path.is_file(), asset_id)
            with Image.open(path) as source:
                alpha = source.convert("RGBA").getchannel("A")
                self.assertEqual(alpha.getbbox(), (0, 0, source.width, source.height))

    def test_top_8_placement_tags_preserve_tied_bracket_results(self) -> None:
        tags = self.preferences["singles_top_8"].placement_tags

        self.assertEqual(
            [item.asset_id for item in tags],
            [
                "01st.png",
                "02nd.png",
                "03rd.png",
                "04th.png",
                "05th.png",
                "05th.png",
                "07th.png",
                "07th.png",
            ],
        )


if __name__ == "__main__":
    unittest.main()

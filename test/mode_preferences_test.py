"""Tests for mode selection and serialized per-sub-mode preferences."""

from collections import Counter
import unittest

from background_builder import PixelRect, PixelSize
from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from mode_preferences import (
    CharacterPlacement,
    FormattingAssetPlacement,
    ModePreferenceRepository,
    ModePreferences,
    PixelPoint,
    PlacementTagPlacement,
    TextPlacement,
)
from models import TournamentFormat


class ModePreferencesTest(unittest.TestCase):
    def test_the_three_initial_modes_are_explicit(self) -> None:
        self.assertEqual(
            tuple(CreationMode),
            (CreationMode.PODIUM, CreationMode.EYES, CreationMode.SQUARES),
        )

    def test_mode_options_are_part_of_the_serialized_selection(self) -> None:
        selection = ModeSelection(
            CreationMode.PODIUM,
            ModeOptions(
                TournamentFormat.SINGLES,
                8,
                "four_podium",
                PodiumStyle.CUSTOMIZABLE,
            ),
        )

        restored = ModeSelection.from_dict(selection.to_dict())

        self.assertEqual(restored, selection)
        self.assertEqual(restored.submode_id, "singles_top_8_four_podium")
        self.assertEqual(restored.options.podium_style, PodiumStyle.CUSTOMIZABLE)

    def test_podium_style_is_required_only_for_podium_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires"):
            ModeSelection(
                CreationMode.PODIUM,
                ModeOptions(TournamentFormat.SINGLES, 3),
            )
        with self.assertRaisesRegex(ValueError, "only valid"):
            ModeSelection(
                CreationMode.EYES,
                ModeOptions(
                    TournamentFormat.SINGLES,
                    3,
                    podium_style=PodiumStyle.LEGACY,
                ),
            )

    def test_podium_styles_resolve_to_independent_preference_paths(self) -> None:
        repository = ModePreferenceRepository()
        legacy = ModeSelection(
            CreationMode.PODIUM,
            ModeOptions(
                TournamentFormat.SINGLES,
                3,
                podium_style=PodiumStyle.LEGACY,
            ),
        )
        customizable = ModeSelection(
            CreationMode.PODIUM,
            ModeOptions(
                TournamentFormat.SINGLES,
                3,
                podium_style=PodiumStyle.CUSTOMIZABLE,
            ),
        )

        self.assertNotEqual(
            repository.path_for(legacy),
            repository.path_for(customizable),
        )
        self.assertEqual(repository.path_for(legacy).parent.name, "legacy")
        self.assertEqual(repository.path_for(customizable).parent.name, "customizable")

    def test_preferences_round_trip_all_placement_types(self) -> None:
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
            canvas_size=PixelSize(100, 50),
            ready=True,
            formatting_assets=(
                FormattingAssetPlacement(
                    "first_podium",
                    "podium.png",
                    PixelRect(5, 10, 45, 50),
                    2,
                ),
            ),
            placement_tags=(
                PlacementTagPlacement(
                    "first_place",
                    "01st.png",
                    anchor=PixelPoint(25, 30),
                    max_size=PixelSize(30, 25),
                    z_index=3,
                ),
            ),
            character_slots=(
                CharacterPlacement(
                    "first_character",
                    entrant_slot=1,
                    anchor=PixelPoint(20, 30),
                    scale=1.25,
                    z_index=3,
                ),
            ),
            text_slots=(
                TextPlacement(
                    "first_tag",
                    field="entrant.tag",
                    entrant_slot=1,
                    anchor=PixelPoint(20, 35),
                    max_width=40,
                    pillow_anchor="ms",
                    preferred_size=24,
                    z_index=4,
                ),
            ),
        )

        restored = ModePreferences.from_dict(preferences.to_dict())

        self.assertEqual(restored, preferences)

    def test_every_initialized_preference_file_is_valid(self) -> None:
        preferences = ModePreferenceRepository().list_preferences()
        counts = Counter(item.selection.mode for item in preferences)

        self.assertEqual(
            counts,
            {
                CreationMode.PODIUM: 12,
                CreationMode.EYES: 5,
                CreationMode.SQUARES: 5,
            },
        )
        podium_styles = Counter(
            item.selection.options.podium_style
            for item in preferences
            if item.selection.mode is CreationMode.PODIUM
        )
        self.assertEqual(
            podium_styles,
            {PodiumStyle.LEGACY: 6, PodiumStyle.CUSTOMIZABLE: 6},
        )
        for item in preferences:
            reviewed_legacy_top_8 = (
                item.selection.mode is CreationMode.PODIUM
                and item.selection.options.podium_style is PodiumStyle.LEGACY
                and item.selection.submode_id == "singles_top_8"
            )
            self.assertEqual(item.ready, reviewed_legacy_top_8)
            expected_canvas = (
                PixelSize(1920, 941)
                if item.selection.mode is CreationMode.PODIUM
                and item.selection.options.podium_style is PodiumStyle.CUSTOMIZABLE
                else PixelSize(1672, 941)
            )
            self.assertEqual(item.canvas_size, expected_canvas)
            extracted_legacy = (
                item.selection.mode is CreationMode.PODIUM
                and item.selection.options.podium_style is PodiumStyle.LEGACY
            )
            extracted_podium_formatting = item.selection.mode is CreationMode.PODIUM
            if extracted_podium_formatting:
                self.assertTrue(item.formatting_assets)
            else:
                self.assertFalse(item.formatting_assets)
            if extracted_legacy:
                self.assertTrue(item.character_slots)
                self.assertTrue(item.text_slots)
            else:
                self.assertFalse(item.character_slots)
                self.assertFalse(item.text_slots)
            if item.selection.mode is CreationMode.PODIUM:
                expected_tag_count = (
                    3
                    if item.selection.options.podium_style
                    is PodiumStyle.CUSTOMIZABLE
                    and item.selection.submode_id == "singles_top_8"
                    else (
                        4
                        if item.selection.options.variant == "four_podium"
                        else item.selection.options.entrant_count
                    )
                )
                self.assertEqual(len(item.placement_tags), expected_tag_count)
            else:
                self.assertFalse(item.placement_tags)
            self.assertEqual(
                ModePreferenceRepository().load(item.selection),
                item,
            )


if __name__ == "__main__":
    unittest.main()

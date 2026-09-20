"""Tests for mode selection and serialized per-sub-mode preferences."""

from collections import Counter
import unittest

from background_builder import PixelRect, PixelSize
from creation_modes import CreationMode, ModeOptions, ModeSelection
from mode_preferences import (
    CharacterPlacement,
    FormattingAssetPlacement,
    ModePreferenceRepository,
    ModePreferences,
    PixelPoint,
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
            ModeOptions(TournamentFormat.SINGLES, 8, "four_podium"),
        )

        restored = ModeSelection.from_dict(selection.to_dict())

        self.assertEqual(restored, selection)
        self.assertEqual(restored.submode_id, "singles_top_8_four_podium")

    def test_preferences_round_trip_all_placement_types(self) -> None:
        selection = ModeSelection(
            CreationMode.PODIUM,
            ModeOptions(TournamentFormat.SINGLES, 3),
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
                    z_index=4,
                ),
            ),
        )

        restored = ModePreferences.from_dict(preferences.to_dict())

        self.assertEqual(restored, preferences)

    def test_every_initialized_preference_file_is_valid_and_unfinished(self) -> None:
        preferences = ModePreferenceRepository().list_preferences()
        counts = Counter(item.selection.mode for item in preferences)

        self.assertEqual(
            counts,
            {
                CreationMode.PODIUM: 6,
                CreationMode.EYES: 5,
                CreationMode.SQUARES: 5,
            },
        )
        for item in preferences:
            self.assertFalse(item.ready)
            self.assertEqual(item.canvas_size, PixelSize(1672, 941))
            self.assertFalse(item.formatting_assets)
            self.assertFalse(item.character_slots)
            self.assertFalse(item.text_slots)
            self.assertEqual(
                ModePreferenceRepository().load(item.selection),
                item,
            )


if __name__ == "__main__":
    unittest.main()

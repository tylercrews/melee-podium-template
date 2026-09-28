"""Focused integration tests for the Eyes and Squares public renderers."""

import random
import unittest

from PIL import Image

from background_builder import PixelRect, PixelSize
from creation_modes import CreationMode, ModeOptions, ModeSelection
from DrawEyes import draw_doubles_top_3 as draw_eyes_doubles_top_3
from DrawEyes import draw_doubles_top_4 as draw_eyes_doubles_top_4
from DrawEyes import draw_singles_top_8 as draw_eyes_singles_top_8
from DrawSquares import draw_doubles_top_3 as draw_squares_doubles_top_3
from DrawSquares import draw_doubles_top_4 as draw_squares_doubles_top_4
from DrawSquares import draw_singles_top_8 as draw_squares_singles_top_8
from formatting_assets import FormattingAssetRenderer
from geometric_content_renderer import _squares_header_boxes
from geometric_formatting_colors import GeometricFormattingColors
from mode_preferences import FormattingAssetPlacement, ModePreferenceRepository, ModePreferences
from models import TournamentFormat
from portrait_scale_adjustment_for_each_mode import get_mode_portrait_scale
from sample_creation_data import (
    sample_top_4_teams,
    sample_top_8_entrants,
    sample_tournament,
)


class GeometricModesTest(unittest.TestCase):
    def test_reviewed_preferences_have_mode_specific_canvas_geometry(self) -> None:
        repository = ModePreferenceRepository()
        expected = {
            CreationMode.EYES: PixelSize(1080, 1920),
            CreationMode.SQUARES: PixelSize(1920, 1080),
        }
        for mode, size in expected.items():
            for event_format, count in (
                (TournamentFormat.SINGLES, 8),
                (TournamentFormat.DOUBLES, 3),
                (TournamentFormat.DOUBLES, 4),
            ):
                preferences = repository.load(
                    ModeSelection(mode, ModeOptions(event_format, count))
                )
                self.assertTrue(preferences.ready)
                self.assertEqual(preferences.canvas_size, size)
                self.assertEqual(
                    len(
                        [
                            item
                            for item in preferences.formatting_assets
                            if item.asset_id != "eyes_header_bar"
                        ]
                    ),
                    count,
                )
                expected_characters = count * (
                    2 if event_format is TournamentFormat.DOUBLES else 1
                )
                self.assertEqual(len(preferences.character_slots), expected_characters)
                self.assertEqual(len(preferences.placement_tags), count)
                self.assertFalse(
                    any(item.field == "entrant.placement" for item in preferences.text_slots)
                )
                self.assertEqual(
                    [item.asset_id for item in preferences.placement_tags],
                    [
                        "01st.png",
                        "02nd.png",
                        "03rd.png",
                        *(["04th.png"] if count >= 4 else []),
                        *(
                            ["05th.png", "05th.png", "07th.png", "07th.png"]
                            if count == 8
                            else []
                        ),
                    ],
                )

    def test_squares_doubles_emphasizes_first_and_places_headers_below_other_cards(self) -> None:
        repository = ModePreferenceRepository()
        for count in (3, 4):
            preferences = repository.load(
                ModeSelection(
                    CreationMode.SQUARES,
                    ModeOptions(TournamentFormat.DOUBLES, count),
                )
            )
            cards = {
                int(item.slot_id.rsplit("_", 1)[1]): item.destination
                for item in preferences.formatting_assets
            }
            first = cards[1]
            smaller = [cards[slot] for slot in range(2, count + 1)]
            self.assertGreater(first.width * first.height, max(card.width * card.height for card in smaller))
            self.assertGreater(first.width, max(card.width for card in smaller))
            self.assertEqual(
                [card.left for card in smaller],
                [smaller[0].left] * len(smaller),
            )
            self.assertTrue(
                all(
                    upper.bottom < lower.top
                    for upper, lower in zip(smaller, smaller[1:])
                )
            )
            boxes = _squares_header_boxes(
                Image.new("RGBA", preferences.canvas_size.as_tuple()),
                preferences,
            )
            self.assertGreaterEqual(
                min(box.top for box, _anchor in boxes.values()),
                max(card.bottom for card in smaller),
            )
            self.assertEqual(
                len({box.top for box, _anchor in boxes.values()}),
                1,
            )
            self.assertLess(
                boxes["top_left"][0].left,
                boxes["bottom_right"][0].left,
            )

    def test_squares_doubles_first_place_has_the_same_effective_scale(self) -> None:
        repository = ModePreferenceRepository()
        effective_scales = []
        for count in (3, 4):
            preferences = repository.load(
                ModeSelection(
                    CreationMode.SQUARES,
                    ModeOptions(TournamentFormat.DOUBLES, count),
                )
            )
            first_member = next(
                item
                for item in preferences.character_slots
                if item.entrant_slot == 1 and item.member_slot == 1
            )
            effective_scales.append(
                first_member.scale
                * get_mode_portrait_scale(f"squares_doubles_top_{count}")
            )
        self.assertAlmostEqual(effective_scales[0], effective_scales[1])

    def test_public_singles_renderers_use_reviewed_canvas_sizes(self) -> None:
        entrants = sample_top_8_entrants(random.Random(11))
        tournament = sample_tournament(TournamentFormat.SINGLES)

        eyes = draw_eyes_singles_top_8(entrants, tournament=tournament)
        squares = draw_squares_singles_top_8(entrants, tournament=tournament)

        self.assertEqual(eyes.size, (1080, 1920))
        self.assertEqual(squares.size, (1920, 1080))
        self.assertEqual(eyes.mode, "RGBA")
        self.assertEqual(squares.mode, "RGBA")

    def test_both_doubles_layouts_render_two_members_per_team(self) -> None:
        teams = sample_top_4_teams(random.Random(22))
        tournament = sample_tournament(TournamentFormat.DOUBLES)
        renders = (
            draw_eyes_doubles_top_3(teams[:3], tournament=tournament),
            draw_eyes_doubles_top_4(teams, tournament=tournament),
            draw_squares_doubles_top_3(teams[:3], tournament=tournament),
            draw_squares_doubles_top_4(teams, tournament=tournament),
        )

        self.assertEqual(
            [image.size for image in renders],
            [(1080, 1920), (1080, 1920), (1920, 1080), (1920, 1080)],
        )
        self.assertTrue(all(image.getbbox() is not None for image in renders))

    def test_geometric_colors_are_rgba_and_repeat_by_slot(self) -> None:
        colors = GeometricFormattingColors.one("#12345678", "#ABCDEF01")

        self.assertEqual(colors.for_slot(1).background_color, "#12345678")
        self.assertEqual(colors.for_slot(8).trim_color, "#ABCDEF01")
        self.assertEqual(
            GeometricFormattingColors.from_dict(colors.to_dict()),
            colors,
        )
        with self.assertRaisesRegex(ValueError, "8-digit"):
            GeometricFormattingColors.one("#123456")

    def test_eye_rectangle_respects_half_open_destination_bounds(self) -> None:
        selection = ModeSelection(
            CreationMode.EYES,
            ModeOptions(TournamentFormat.SINGLES, 1),
        )
        preferences = ModePreferences(
            selection=selection,
            canvas_size=PixelSize(20, 20),
            ready=True,
            formatting_assets=(
                FormattingAssetPlacement(
                    "entrant_1",
                    "eyes_rectangle",
                    PixelRect(2, 3, 12, 13),
                ),
            ),
        )

        result = FormattingAssetRenderer().draw(
            Image.new("RGBA", (20, 20), "#00000000"),
            preferences,
            GeometricFormattingColors.one("#11223344"),
        )

        self.assertEqual(result.getpixel((7, 8)), (17, 34, 51, 68))
        self.assertEqual(result.getpixel((1, 8)), (0, 0, 0, 0))
        self.assertEqual(result.getpixel((12, 8)), (0, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()

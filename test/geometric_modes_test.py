"""Focused integration tests for the Eyes and Squares public renderers."""

import random
import unittest
from unittest.mock import patch

from PIL import Image

from background_builder import BackgroundRequest, PixelRect, PixelSize
from creation import CreationRequest, TextSettings
from creation_modes import CreationMode, ModeOptions, ModeSelection
from DrawEyes import EyesMode, draw_doubles_top_3 as draw_eyes_doubles_top_3
from DrawEyes import draw_doubles_top_4 as draw_eyes_doubles_top_4
from DrawEyes import draw_eyes
from DrawEyes import draw_singles_top_8 as draw_eyes_singles_top_8
from DrawSquares import draw_doubles_top_3 as draw_squares_doubles_top_3
from DrawSquares import draw_doubles_top_4 as draw_squares_doubles_top_4
from DrawSquares import draw_singles_top_8 as draw_squares_singles_top_8
from formatting_assets import FormattingAssetRenderer
from geometric_content_renderer import (
    WATERMARK_BLACK,
    WATERMARK_WHITE,
    _metadata_lines,
    _squares_header_boxes,
    _watermark_color,
)
from geometric_formatting_colors import GeometricFormattingColors
from mode_preferences import FormattingAssetPlacement, ModePreferenceRepository, ModePreferences
from models import Character, TournamentFormat
from portrait_scale_adjustment_for_each_mode import get_mode_portrait_scale
from sample_creation_data import (
    sample_singles_entrants,
    sample_top_4_teams,
    sample_top_8_entrants,
    sample_tournament,
)
from square_portrait_renderer import (
    _staggered_x_offsets,
    render_square_portrait_group,
    square_portrait_scale_key,
)


class GeometricModesTest(unittest.TestCase):
    def test_grouped_metadata_uses_bullet_separators_and_one_line_per_row(self) -> None:
        selection = ModeSelection(
            CreationMode.EYES,
            ModeOptions(TournamentFormat.SINGLES, 8),
        )
        request = CreationRequest(
            selection=selection,
            background=BackgroundRequest(PixelSize(1080, 1920)),
            entrants=sample_top_8_entrants(random.Random(4)),
            tournament=sample_tournament(TournamentFormat.SINGLES),
            formatting_colors=GeometricFormattingColors.one("#E53935FF"),
            text_settings=TextSettings(
                metadata_rows=(("event", "date"), ("entrants_count",)),
            ),
        )

        lines = _metadata_lines(request)

        self.assertEqual(len(lines), 2)
        self.assertIn(" • ", lines[0])
        self.assertNotIn(" • ", lines[1])

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

    def test_extended_eyes_layouts_use_full_width_first_and_reviewed_grids(self) -> None:
        repository = ModePreferenceRepository()
        expected_placements = {
            10: list(range(1, 11)),
            15: list(range(1, 16)),
            16: [1, 2, 3, 4, 5, 5, 7, 7, 9, 9, 9, 9, 13, 13, 13, 13],
            20: list(range(1, 21)),
            25: list(range(1, 26)),
        }
        for count, placements in expected_placements.items():
            preferences = repository.load(
                ModeSelection(
                    CreationMode.EYES,
                    ModeOptions(TournamentFormat.SINGLES, count),
                )
            )
            cards = [
                item.destination
                for item in preferences.formatting_assets
                if item.asset_id == "eyes_rectangle"
            ]
            header = next(
                item.destination
                for item in preferences.formatting_assets
                if item.asset_id == "eyes_header_bar"
            )
            expected_columns = 4 if count in {16, 25} else 3
            self.assertEqual(
                preferences.canvas_size.width,
                2400 if expected_columns == 4 else 1920,
            )
            self.assertLess(preferences.canvas_size.height, 5000)
            self.assertGreater(header.width, header.height)
            self.assertEqual(len(cards), count)
            self.assertGreater(cards[0].width, cards[1].width * 2)
            rows: dict[int, int] = {}
            for card in cards[1:]:
                rows[card.top] = rows.get(card.top, 0) + 1
            self.assertLessEqual(max(rows.values()), expected_columns)
            if count == 16:
                self.assertEqual(list(rows.values()), [3, 4, 4, 4])
            elif count == 25:
                self.assertEqual(list(rows.values()), [4, 4, 4, 4, 4, 4])
            self.assertEqual(
                [int(item.asset_id[:2]) for item in preferences.placement_tags],
                placements,
            )
            self.assertTrue(
                all(
                    tag.anchor.y < card.top + card.height // 2
                    for tag, card in zip(preferences.placement_tags, cards, strict=True)
                )
            )

    def test_eyes_names_stay_inside_their_associated_colored_bars(self) -> None:
        repository = ModePreferenceRepository()
        singles = repository.load(
            ModeSelection(
                CreationMode.EYES,
                ModeOptions(TournamentFormat.SINGLES, 8),
            )
        )
        singles_cards = {
            int(item.slot_id.rsplit("_", 1)[1]): item.destination
            for item in singles.formatting_assets
            if item.asset_id == "eyes_rectangle"
        }
        for label in singles.text_slots:
            card = singles_cards[label.entrant_slot or 0]
            self.assertLess(label.anchor.y, card.bottom)
            self.assertGreater(label.anchor.y, card.top)
            self.assertGreater(label.anchor.x, card.left + card.width * 3 // 4)
            self.assertEqual(label.pillow_anchor, "rs")

        for count in (3, 4):
            doubles = repository.load(
                ModeSelection(
                    CreationMode.EYES,
                    ModeOptions(TournamentFormat.DOUBLES, count),
                )
            )
            cards = {
                int(item.slot_id.rsplit("_", 1)[1]): item.destination
                for item in doubles.formatting_assets
                if item.asset_id == "eyes_rectangle"
            }
            for slot in range(1, count + 1):
                card = cards[slot]
                text = [item for item in doubles.text_slots if item.entrant_slot == slot]
                team = next(item for item in text if item.field == "entrant.team_name")
                members = [item for item in text if item.field == "member.player_tag"]
                sponsors = [item for item in text if item.field == "member.sponsor"]
                self.assertEqual(len(members), 2)
                self.assertEqual(len(sponsors), 2)
                self.assertLess(team.anchor.y, card.top + card.height // 3)
                self.assertTrue(
                    all(item.anchor.y > card.top + card.height * 2 // 3 for item in members)
                )
                self.assertTrue(
                    all(
                        sponsor.anchor.y < member.anchor.y
                        for sponsor, member in zip(sponsors, members, strict=True)
                    )
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
            self.assertEqual(
                set(boxes),
                {"top_left", "top_middle", "top_right"},
            )
            self.assertLess(
                boxes["top_left"][0].left,
                boxes["top_right"][0].left,
            )

    def test_squares_doubles_layers_team_name_above_and_member_names_in_footer(self) -> None:
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
            character_z = min(item.z_index for item in preferences.character_slots)
            for slot in range(1, count + 1):
                card = cards[slot]
                slot_text = [
                    item
                    for item in preferences.text_slots
                    if item.entrant_slot == slot
                ]
                team_name = next(
                    item for item in slot_text if item.field == "entrant.team_name"
                )
                member_names = [
                    item for item in slot_text if item.field == "member.tag"
                ]
                seed = next(item for item in slot_text if item.field == "entrant.seed")

                self.assertEqual(len(member_names), 2)
                self.assertLess(team_name.z_index, character_z)
                self.assertTrue(all(item.z_index > character_z for item in member_names))
                self.assertGreater(seed.z_index, character_z)
                self.assertLess(team_name.anchor.y, card.top + card.height // 3)
                self.assertGreater(seed.anchor.y, card.top + card.height // 2)
                self.assertLess(seed.anchor.y, member_names[0].anchor.y)
                self.assertEqual(seed.pillow_anchor, "rs")
                self.assertGreaterEqual(seed.preferred_size or 0, 34)
                self.assertGreaterEqual(
                    min(item.preferred_size or 0 for item in member_names),
                    46,
                )

    def test_squares_singles_uses_the_same_three_section_bottom_header(self) -> None:
        preferences = ModePreferenceRepository().load(
            ModeSelection(
                CreationMode.SQUARES,
                ModeOptions(TournamentFormat.SINGLES, 8),
            )
        )
        cards = [item.destination for item in preferences.formatting_assets]
        boxes = _squares_header_boxes(
            Image.new("RGBA", preferences.canvas_size.as_tuple()),
            preferences,
        )

        self.assertEqual(set(boxes), {"top_left", "top_middle", "top_right"})
        self.assertGreaterEqual(
            min(box.top for box, _anchor in boxes.values()),
            max(card.bottom for card in cards),
        )
        self.assertEqual(min(card.top for card in cards), 50)

    def test_squares_reserves_the_top_right_strip_for_attribution(self) -> None:
        image = draw_squares_singles_top_8(
            sample_top_8_entrants(random.Random(31)),
            tournament=sample_tournament(TournamentFormat.SINGLES),
        )
        top_strip = image.crop((0, 0, image.width, 50))

        self.assertIsNone(top_strip.crop((0, 0, image.width // 2, 50)).getbbox())
        self.assertIsNotNone(
            top_strip.crop((image.width // 2, 0, image.width, 50)).getbbox()
        )

    def test_watermark_color_uses_local_background_brightness(self) -> None:
        sample_box = PixelRect(10, 10, 90, 40)

        self.assertEqual(
            _watermark_color(Image.new("RGBA", (100, 50), "#FFFFFFFF"), sample_box),
            WATERMARK_BLACK,
        )
        self.assertEqual(
            _watermark_color(Image.new("RGBA", (100, 50), "#000000FF"), sample_box),
            WATERMARK_WHITE,
        )
        self.assertEqual(WATERMARK_BLACK[-2:], "40")
        self.assertEqual(WATERMARK_WHITE[-2:], "40")

    def test_black_watermark_is_blended_into_an_opaque_light_background(self) -> None:
        image = draw_squares_singles_top_8(
            sample_top_8_entrants(random.Random(41)),
            tournament=sample_tournament(TournamentFormat.SINGLES),
            fill_color="#FFFFFFFF",
        )
        pixels = list(image.crop((image.width // 2, 0, image.width, 50)).getdata())
        watermark_pixels = [pixel for pixel in pixels if pixel != (255, 255, 255, 255)]

        self.assertTrue(watermark_pixels)
        self.assertTrue(all(pixel[3] == 255 for pixel in watermark_pixels))
        self.assertGreaterEqual(min(pixel[0] for pixel in watermark_pixels), 190)

    def test_eyes_places_its_attribution_in_the_bottom_left(self) -> None:
        image = draw_eyes_singles_top_8(
            sample_top_8_entrants(random.Random(37)),
            tournament=sample_tournament(TournamentFormat.SINGLES),
        )
        bottom_strip = image.crop((0, image.height - 45, image.width, image.height))

        self.assertIsNotNone(
            bottom_strip.crop((0, 0, image.width * 2 // 3, 45)).getbbox()
        )

    def test_eyes_header_rail_is_frameless(self) -> None:
        preferences = ModePreferenceRepository().load(
            ModeSelection(
                CreationMode.EYES,
                ModeOptions(TournamentFormat.SINGLES, 8),
            )
        )
        transparent = Image.new("RGBA", preferences.canvas_size.as_tuple())
        formatting = FormattingAssetRenderer().draw(
            transparent,
            preferences,
            GeometricFormattingColors.one("#E53935FF"),
        )

        self.assertEqual(formatting.getpixel((900, 100))[3], 0)

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
            scale_key = square_portrait_scale_key(
                TournamentFormat.DOUBLES,
                count,
                1,
            )
            effective_scales.append(
                first_member.scale
                * get_mode_portrait_scale(scale_key)
            )
        self.assertAlmostEqual(effective_scales[0], effective_scales[1])

    def test_squares_uses_a_distinct_scale_for_every_card_size_tier(self) -> None:
        expected = {
            (TournamentFormat.SINGLES, 8, 1): "squares_singles_top_8_first",
            (TournamentFormat.SINGLES, 8, 2): "squares_singles_top_8_second_through_fourth",
            (TournamentFormat.SINGLES, 8, 4): "squares_singles_top_8_second_through_fourth",
            (TournamentFormat.SINGLES, 8, 5): "squares_singles_top_8_fifth_and_seventh",
            (TournamentFormat.SINGLES, 8, 8): "squares_singles_top_8_fifth_and_seventh",
            (TournamentFormat.DOUBLES, 3, 1): "squares_doubles_first",
            (TournamentFormat.DOUBLES, 4, 1): "squares_doubles_first",
            (TournamentFormat.DOUBLES, 3, 2): "squares_doubles_top_3_second_through_third",
            (TournamentFormat.DOUBLES, 4, 2): "squares_doubles_top_4_second_through_fourth",
        }

        for arguments, scale_key in expected.items():
            with self.subTest(arguments=arguments):
                self.assertEqual(square_portrait_scale_key(*arguments), scale_key)
                self.assertGreater(get_mode_portrait_scale(scale_key), 0)

    def test_tallest_square_portrait_fills_each_card_tier_vertically(self) -> None:
        tiers = {
            "squares_singles_top_8_first": (560, 666),
            "squares_singles_top_8_second_through_fourth": (360, 329),
            "squares_singles_top_8_fifth_and_seventh": (264, 307),
            "squares_doubles_first": (570, 661),
            "squares_doubles_top_3_second_through_third": (300, 318),
            "squares_doubles_top_4_second_through_fourth": (300, 190),
        }
        tallest_pose = Character("Bowser", pose="c")

        for scale_key, viewport_size in tiers.items():
            with self.subTest(scale_key=scale_key):
                result = render_square_portrait_group(
                    [tallest_pose],
                    viewport_size,
                    scale_key=scale_key,
                )
                bounds = result.getbbox()
                self.assertIsNotNone(bounds)
                assert bounds is not None
                self.assertEqual(bounds[1], 0)
                self.assertEqual(bounds[3], viewport_size[1])

    def test_square_multi_character_stagger_matches_podium_order(self) -> None:
        self.assertEqual(_staggered_x_offsets(1, (500, 400)), (0,))
        self.assertEqual(_staggered_x_offsets(2, (500, 400)), (-72, 72))
        self.assertEqual(_staggered_x_offsets(3, (500, 400)), (0, -72, 72))
        self.assertEqual(
            _staggered_x_offsets(6, (500, 400)),
            (0, -72, 72, 0, -72, 72),
        )

    def test_squares_loads_every_character_for_singles_and_doubles(self) -> None:
        singles = sample_top_8_entrants(random.Random(51))
        teams = sample_top_4_teams(random.Random(52))
        expected_singles = sum(len(entrant.characters) for entrant in singles)
        expected_doubles = sum(
            len(team.entrant_1.characters) + len(team.entrant_2.characters)
            for team in teams
        )
        first_team_character_count = (
            len(teams[0].entrant_1.characters) + len(teams[0].entrant_2.characters)
        )
        fake_portrait = Image.new("RGBA", (40, 80), "#FFFFFFFF")

        with patch(
            "square_portrait_renderer.load_scaled_portrait",
            return_value=fake_portrait,
        ) as load_portrait:
            draw_squares_singles_top_8(
                singles,
                tournament=sample_tournament(TournamentFormat.SINGLES),
            )
            self.assertEqual(load_portrait.call_count, expected_singles)

        with patch(
            "square_portrait_renderer.load_scaled_portrait",
            return_value=fake_portrait,
        ) as load_portrait:
            draw_squares_doubles_top_4(
                teams,
                tournament=sample_tournament(TournamentFormat.DOUBLES),
            )
            self.assertEqual(load_portrait.call_count, expected_doubles)
            self.assertTrue(
                all(
                    call.args[0].color == teams[0].team_color
                    for call in load_portrait.call_args_list[:first_team_character_count]
                )
            )

    def test_public_singles_renderers_use_reviewed_canvas_sizes(self) -> None:
        entrants = sample_top_8_entrants(random.Random(11))
        tournament = sample_tournament(TournamentFormat.SINGLES)

        eyes = draw_eyes_singles_top_8(entrants, tournament=tournament)
        squares = draw_squares_singles_top_8(entrants, tournament=tournament)

        self.assertEqual(eyes.size, (1080, 1920))
        self.assertEqual(squares.size, (1920, 1080))
        self.assertEqual(eyes.mode, "RGBA")
        self.assertEqual(squares.mode, "RGBA")

    def test_extended_eyes_public_renderer_uses_variable_height_canvas(self) -> None:
        entrants = sample_singles_entrants(10, random.Random(61))
        image = draw_eyes(
            EyesMode.SINGLES_TOP_10,
            entrants,
            tournament=sample_tournament(TournamentFormat.SINGLES),
        )

        self.assertEqual(image.width, 1920)
        self.assertGreater(image.height, 1080)
        self.assertLess(image.height, 5000)
        self.assertIsNotNone(image.getbbox())

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

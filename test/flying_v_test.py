"""Flying V geometry, serialization, figure placement, labels, and rendering."""

from dataclasses import replace
from io import BytesIO
from itertools import permutations
import json
from pathlib import Path
import random
import unittest

from PIL import Image, ImageDraw

from app import app
from background_builder import BackgroundRequest, PixelRect
from creation import CreationPipeline, CreationRequest, TextSettings
from creation_modes import CreationMode, ModeOptions, ModeSelection
from DrawFlyingV import draw_doubles_top_3, draw_singles_top_8
from DrawPodium import CharacterTag, PodiumFont, _character_tag_bounds
from entrant_visibility import slot_from_id, visible_preferences
from flying_v_content_renderer import (
    BETWEEN_NAMES_SUFFIX,
    FlyingVContentRenderer,
    WATERMARK_ROW_HEIGHT,
    flying_v_header_boxes,
    _clear_of,
    labelled_preferences,
    place_figures,
    text_vertical_extent,
)
from flying_v_lineup import HANGING_FRAME, STANDING_FRAME, place_lineup
from flying_v_preview_layers import render_flying_v_header_layer, render_placeholder_layer
from generate_flying_v_preferences import (
    DOUBLES_HEADER_BOXES,
    SINGLES_HEADER_BOXES,
    flying_v_doubles_preferences,
    flying_v_singles_preferences,
)
from geometric_formatting_colors import GeometricFormattingColors
from legacy_podium_content_renderer import LegacyPodiumContentRenderer
from mode_preferences import ModePreferenceRepository, ModePreferences
from models import Character, DoublesTeam, Entrant, SinglesEntrant, TournamentFormat
from placement_numbering import numbered_preferences
from preview_layers import HEADER_CONTENTS, HEADER_POSITIONS
from sample_creation_data import sample_top_4_teams, sample_top_8_entrants, sample_tournament


SINGLES = ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.SINGLES, 8))
DOUBLES = ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.DOUBLES, 3))


def _frames(preferences):
    return {item.slot_id: item for item in preferences.formatting_assets if item.asset_id in {STANDING_FRAME, HANGING_FRAME}}


def _overlaps(a: PixelRect, b: PixelRect) -> bool:
    return a.left < b.right and b.left < a.right and a.top < b.bottom and b.top < a.bottom


def _singles(characters_by_slot):
    return [SinglesEntrant(tag=f"Player {slot}", characters=[characters_by_slot.get(slot, Character("Fox", color="default", pose="a"))],
                           seed=slot, placement=(1, 2, 3, 4, 5, 5, 7, 7)[slot - 1]) for slot in range(1, 9)]


def _request(selection, entrants, **kwargs):
    preferences = ModePreferenceRepository().load(selection)
    return CreationRequest(selection, BackgroundRequest(preferences.canvas_size), entrants,
                           sample_tournament(selection.options.event_format), **kwargs), preferences


class FlyingVPreferenceTests(unittest.TestCase):
    def test_singles_is_wide_portrait_doubles_is_landscape_and_both_round_trip(self):
        for selection, generated, size, boxes in ((SINGLES, flying_v_singles_preferences(), (1440, 1920), SINGLES_HEADER_BOXES),
                                                  (DOUBLES, flying_v_doubles_preferences(), (1920, 1080), DOUBLES_HEADER_BOXES)):
            with self.subTest(selection=selection.submode_id):
                preferences = ModePreferenceRepository().load(selection)
                self.assertTrue(preferences.ready)
                self.assertEqual(preferences.canvas_size.as_tuple(), size)
                self.assertEqual(preferences, generated)
                self.assertEqual(ModePreferences.from_dict(json.loads(json.dumps(preferences.to_dict()))), preferences)
                self.assertEqual(flying_v_header_boxes(preferences), boxes)

    def test_only_singles_top_8_and_doubles_top_3_are_valid(self):
        for event_format, count, variant in ((TournamentFormat.SINGLES, 3, None), (TournamentFormat.DOUBLES, 4, None),
                                             (TournamentFormat.SINGLES, 8, "four_podium")):
            with self.assertRaisesRegex(ValueError, "Flying V supports"):
                ModeSelection(CreationMode.FLYING_V, ModeOptions(event_format, count, variant))

    def test_singles_tiers_shrink_from_the_leader_back_through_the_v(self):
        preferences = ModePreferenceRepository().load(SINGLES)
        scales = {item.entrant_slot: item.scale for item in preferences.character_slots}
        depth = {item.entrant_slot: item.z_index for item in preferences.character_slots}
        self.assertTrue(scales[1] > scales[2] > scales[3] == scales[4] > scales[5] == scales[6] > scales[7] == scales[8])
        self.assertTrue(.65 <= scales[2] / scales[1] <= .8)
        self.assertTrue(.45 <= scales[3] / scales[1] <= .55)
        # Larger, nearer figures are drawn over the smaller ones behind them.
        self.assertTrue(depth[1] > depth[2] > depth[3] == depth[4] > depth[5] == depth[6] > depth[7] == depth[8])

    def test_figures_flank_the_center_and_fly_outward_toward_the_top(self):
        frames = _frames(ModePreferenceRepository().load(SINGLES))
        center = {slot: (frames[f"entrant_{slot}"].destination.left + frames[f"entrant_{slot}"].destination.right) / 2 for slot in range(1, 9)}
        self.assertEqual(center[1], 720)
        self.assertEqual(center[2], 720)
        for left, right in ((3, 4), (5, 6), (7, 8)):
            self.assertLess(center[left], 720)
            self.assertGreater(center[right], 720)
            self.assertEqual(center[left] + center[right], 1440)
        self.assertLess(center[5], center[3])
        self.assertLess(center[7], center[5])
        bottoms = {slot: frames[f"entrant_{slot}"].destination.bottom for slot in range(1, 9)}
        self.assertLess(bottoms[7], bottoms[5])
        self.assertLess(bottoms[5], bottoms[3])
        self.assertLess(bottoms[3], bottoms[1])

    def test_first_place_stands_on_the_canvas_bottom_under_its_name_and_large_crest(self):
        for selection in (SINGLES, DOUBLES):
            with self.subTest(selection=selection.submode_id):
                preferences = ModePreferenceRepository().load(selection)
                canvas = preferences.canvas_size
                leader_frames = [frame for slot_id, frame in _frames(preferences).items() if slot_from_id(slot_id) == 1]
                self.assertTrue(all(frame.destination.bottom == canvas.height for frame in leader_frames))
                badges = {slot_from_id(tag.slot_id): tag for tag in preferences.placement_tags}
                self.assertGreaterEqual(badges[1].max_size.height, 2.5 * max(tag.max_size.height for slot, tag in badges.items() if slot != 1))
                self.assertLessEqual(badges[1].anchor.y + badges[1].max_size.height // 2, canvas.height)
                # The leader's name sits on the canvas bottom, over its feet.
                name = next(item for item in preferences.text_slots if item.slot_id == "name_1")
                self.assertEqual(name.pillow_anchor, "ms")
                self.assertGreaterEqual(name.anchor.y, canvas.height - 20)

    def test_singles_placement_numbers_sit_directly_above_each_name(self):
        preferences = ModePreferenceRepository().load(SINGLES)
        frames = _frames(preferences)
        badges = {slot_from_id(tag.slot_id): tag for tag in preferences.placement_tags}
        for name in (item for item in preferences.text_slots if item.slot_id.startswith("name_")):
            with self.subTest(slot=name.entrant_slot):
                badge = badges[name.entrant_slot]
                badge_bottom = badge.anchor.y + badge.max_size.height // 2
                self.assertEqual(name.anchor.x, badge.anchor.x)
                self.assertEqual(text_vertical_extent(name)[0] - badge_bottom, 4)
                if name.entrant_slot not in {1, 2}:
                    # The placement art covers the feet and the name sits just below them.
                    self.assertEqual(badge_bottom, frames[f"entrant_{name.entrant_slot}"].destination.bottom + 2)
        # Second place keeps a fixed label while its hanging figure extends past it.
        self.assertLess(badges[2].anchor.y + badges[2].max_size.height // 2, frames["entrant_2"].destination.bottom)

    def test_singles_sponsors_share_the_placement_row_in_a_smaller_font(self):
        preferences = ModePreferenceRepository().load(SINGLES)
        badges = {slot_from_id(tag.slot_id): tag for tag in preferences.placement_tags}
        text = {item.slot_id: item for item in preferences.text_slots}
        for slot in range(1, 9):
            with self.subTest(slot=slot):
                sponsor, name, seed, badge = text[f"sponsor_{slot}"], text[f"name_{slot}"], text[f"seed_{slot}"], badges[slot]
                self.assertEqual((sponsor.field, name.field), ("entrant.sponsor", "entrant.player_tag"))
                self.assertEqual((sponsor.pillow_anchor, sponsor.anchor.y), ("rm", badge.anchor.y))
                self.assertEqual(sponsor.anchor.y, seed.anchor.y)
                self.assertLess(sponsor.anchor.x, badge.anchor.x - badge.max_size.width // 2)
                self.assertLess(sponsor.preferred_size, name.preferred_size)
                self.assertGreaterEqual(sponsor.anchor.x - sponsor.max_width, 0)

    def test_sponsored_tags_split_between_the_placement_row_and_the_name_line(self):
        entrants = sample_top_8_entrants(random.Random(4))
        sponsored = next(slot for slot, entrant in enumerate(entrants, 1) if "|" in entrant.tag)
        plain = next(slot for slot, entrant in enumerate(entrants, 1) if "|" not in entrant.tag)
        request, preferences = _request(SINGLES, entrants)
        text = {item.slot_id: item for item in preferences.text_slots}
        draw_text = Image.new("RGBA", (1440, 1920), "#00000000")
        from geometric_content_renderer import _draw_result_text
        _draw_result_text(draw_text, request, preferences, PodiumFont.TYROWO, [text[f"sponsor_{sponsored}"], text[f"sponsor_{plain}"]])
        sponsor = text[f"sponsor_{sponsored}"]
        self.assertIsNotNone(draw_text.crop((sponsor.anchor.x - sponsor.max_width, sponsor.anchor.y - 30, sponsor.anchor.x, sponsor.anchor.y + 30)).getbbox())
        empty = text[f"sponsor_{plain}"]
        self.assertIsNone(draw_text.crop((empty.anchor.x - empty.max_width, empty.anchor.y - 30, empty.anchor.x, empty.anchor.y + 30)).getbbox())

    def test_back_row_names_never_reach_the_figures_flying_below_them(self):
        preferences = ModePreferenceRepository().load(SINGLES)
        frames = _frames(preferences)
        names = {item.entrant_slot: item for item in preferences.text_slots if item.slot_id.startswith("name_")}
        # 7ths sit above the 5ths, which sit above 3rd and 4th, on each side.
        for upper, lower in ((7, 5), (8, 6), (5, 3), (6, 4)):
            with self.subTest(upper=upper, lower=lower):
                self.assertLess(text_vertical_extent(names[upper])[1], frames[f"entrant_{lower}"].destination.top)

    def test_doubles_team_names_rest_on_the_feet_and_the_winning_crest_sits_between_names(self):
        preferences = ModePreferenceRepository().load(DOUBLES)
        frames = _frames(preferences)
        badges = {slot_from_id(tag.slot_id): tag for tag in preferences.placement_tags}
        for slot in (2, 3):
            name = next(item for item in preferences.text_slots if item.slot_id == f"name_{slot}")
            feet = frames[f"entrant_{slot}_member_1"].destination.bottom
            self.assertEqual((name.pillow_anchor, name.anchor.y), ("ms", feet - 2))
            self.assertEqual(badges[slot].anchor.y - badges[slot].max_size.height // 2, feet + 10)
        crest = badges[1]
        self.assertTrue(crest.slot_id.endswith(BETWEEN_NAMES_SUFFIX))
        self.assertEqual(crest.anchor.x, 960)
        self.assertGreater(crest.max_size.height, 150)
        # The crest is layered behind the winning team's figures.
        self.assertLess(crest.z_index, min(item.z_index for item in preferences.character_slots if item.entrant_slot == 1))
        seed = next(item for item in preferences.text_slots if item.slot_id == "seed_1")
        self.assertEqual(seed.pillow_anchor, "ls")
        self.assertGreater(seed.anchor.x, crest.anchor.x + crest.max_size.height * 9 // 20)
        self.assertLess(seed.anchor.y, crest.anchor.y - crest.max_size.height // 4)

    def test_second_place_hangs_below_the_reserved_top_center(self):
        preferences = ModePreferenceRepository().load(SINGLES)
        frames = _frames(preferences)
        self.assertEqual([slot for slot, frame in frames.items() if frame.asset_id == HANGING_FRAME], ["entrant_2"])
        header = SINGLES_HEADER_BOXES["top_middle"]
        self.assertGreaterEqual(frames["entrant_2"].destination.top, header.bottom)
        anchors = {item.slot_id: item.anchor for item in preferences.character_slots}
        for slot_id, frame in frames.items():
            box = frame.destination
            expected_y = box.top if frame.asset_id == HANGING_FRAME else box.bottom
            self.assertEqual((anchors[slot_id].x, anchors[slot_id].y), ((box.left + box.right) // 2, expected_y))

    def test_reserved_header_spaces_and_watermark_row_stay_clear_of_back_figures(self):
        for selection, boxes in ((SINGLES, SINGLES_HEADER_BOXES), (DOUBLES, DOUBLES_HEADER_BOXES)):
            preferences = ModePreferenceRepository().load(selection)
            for slot_id, frame in _frames(preferences).items():
                with self.subTest(selection=selection.submode_id, slot=slot_id):
                    self.assertGreaterEqual(frame.destination.top, WATERMARK_ROW_HEIGHT)
                    self.assertFalse(_overlaps(frame.destination, boxes["top_middle"]))
                    if slot_from_id(slot_id) != 1:
                        self.assertFalse(_overlaps(frame.destination, boxes["top_left"]))
                        self.assertFalse(_overlaps(frame.destination, boxes["top_right"]))
            # Every result label sits above the bottom corners, or between them for the leader.
            for item in preferences.text_slots:
                if item.field == "member.tag":
                    continue
                _top, bottom = text_vertical_extent(item)
                if item.entrant_slot == 1:
                    self.assertLessEqual(bottom, preferences.canvas_size.height)
                    if item.field != "entrant.seed":
                        self.assertGreaterEqual(item.anchor.x - item.max_width // 2, boxes["top_left"].right)
                        self.assertLessEqual(item.anchor.x + item.max_width // 2, boxes["top_right"].left)
                else:
                    self.assertLess(bottom, boxes["top_left"].top, item.slot_id)
            for tag in preferences.placement_tags:
                if slot_from_id(tag.slot_id) != 1:
                    self.assertLess(tag.anchor.y + tag.max_size.height // 2, boxes["top_left"].top, tag.slot_id)

    def test_labels_use_canonical_ordinals_and_smash_player_colors(self):
        singles = ModePreferenceRepository().load(SINGLES)
        self.assertEqual([tag.asset_id for tag in singles.placement_tags],
                         ["01st.png", "02nd.png", "03rd.png", "04th.png", "05th.png", "05th.png", "07th.png", "07th.png"])
        self.assertEqual([tag.asset_id for tag in numbered_preferences(singles, False).placement_tags],
                         [f"0{rank}{suffix}.png" for rank, suffix in zip(range(1, 9), ("st", "nd", "rd", "th", "th", "th", "th", "th"))])
        self.assertFalse(any(item.field == "entrant.placement" for item in singles.text_slots))
        names = [item for item in singles.text_slots if item.field == "entrant.player_tag"]
        self.assertEqual([item.color for item in names[:4]], ["#D90300FF", "#5B59F8FF", "#FFD805FF", "#00F042FF"])
        doubles = ModePreferenceRepository().load(DOUBLES)
        self.assertEqual([tag.asset_id for tag in doubles.placement_tags], ["01st.png", "02nd.png", "03rd.png"])
        self.assertEqual(sorted((item.entrant_slot, item.member_slot) for item in doubles.text_slots if item.field == "member.tag"),
                         [(team, member) for team in (1, 2, 3) for member in (1, 2)])
        self.assertEqual(len([item for item in doubles.text_slots if item.field == "entrant.team_name"]), 3)


class FlyingVPlacementTests(unittest.TestCase):
    def test_oversized_characters_shrink_to_fit_their_frame(self):
        giant = [Character("Bowser", color="default", pose="c"), Character("Donkey Kong", color="default", pose="a")]
        frame = PixelRect(100, 200, 300, 500)
        standing = place_lineup(giant, 1.0, frame)
        hanging = place_lineup(giant, 1.0, frame, hanging=True)
        for placed in (standing, hanging):
            self.assertLessEqual(placed.bounds.height, frame.height)
            # A lineup wider than its frame stays centered on it.
            self.assertLessEqual(abs((placed.bounds.left + placed.bounds.right) - (frame.left + frame.right)), 1)
        self.assertEqual(standing.bounds.bottom, frame.bottom)
        self.assertEqual(hanging.bounds.top, frame.top)
        alone = place_lineup(giant[:1], 1.0, PixelRect(0, 0, 200, 300))
        self.assertLessEqual(alone.bounds.width, 200)
        self.assertLessEqual(alone.bounds.height, 300)

    def test_extra_characters_never_shrink_an_entrant_below_its_tier_size(self):
        marth, fox = Character("Marth", color="default", pose="a"), Character("Fox", color="default", pose="a")
        frame = PixelRect(0, 0, 400, 900)
        single = place_lineup([marth], .8, frame)
        lineup = place_lineup([marth, fox, fox], .8, frame)
        self.assertGreater(lineup.bounds.width, frame.width)
        self.assertEqual(lineup.bounds.height, single.bounds.height)
        # Characters that fit keep their relativity scale; only overflow shrinks.
        pichu, fox = Character("Pichu", color="default", pose="a"), Character("Fox", color="default", pose="a")
        roomy = PixelRect(0, 0, 1000, 1000)
        ratio = place_lineup([pichu], .3, roomy).bounds.height / place_lineup([fox], .3, roomy).bounds.height
        self.assertAlmostEqual(ratio, 434.6 / 796, delta=.02)

    def test_second_place_label_stays_put_while_its_figure_grows(self):
        pichu, bowser = Character("Pichu", color="default", pose="a"), Character("Bowser", color="default", pose="c")
        for second in (pichu, bowser):
            with self.subTest(second=second.melee_fighter_name):
                request, preferences = _request(SINGLES, _singles({1: pichu, 2: second}))
                figures = place_figures(request, preferences)
                self.assertEqual(figures["entrant_2"].lineup.bounds.top, _frames(preferences)["entrant_2"].destination.top)
                labelled = labelled_preferences(preferences, figures)
                self.assertEqual(labelled.placement_tags, preferences.placement_tags)
                self.assertEqual(labelled.text_slots, preferences.text_slots)
        badge = next(tag for tag in preferences.placement_tags if tag.slot_id == "number_2")
        self.assertGreater(figures["entrant_2"].lineup.bounds.bottom, badge.anchor.y)

    def test_second_place_label_rises_only_to_clear_first_places_head(self):
        request, preferences = _request(SINGLES, _singles({1: Character("Ganondorf", color="default", pose="c"),
                                                            2: Character("Bowser", color="default", pose="c")}))
        figures = place_figures(request, preferences)
        first = figures["entrant_1"].lineup.bounds
        labelled = labelled_preferences(preferences, figures)
        name = next(item for item in labelled.text_slots if item.slot_id == "name_2")
        self.assertLessEqual(text_vertical_extent(name)[1], first.top - 6)
        unchanged = {item.slot_id: item for item in preferences.text_slots}
        self.assertLess(name.anchor.y, unchanged["name_2"].anchor.y)
        self.assertEqual(next(item for item in labelled.text_slots if item.slot_id == "name_4"), unchanged["name_4"])

    def test_winning_crest_follows_the_member_names_and_pushes_them_clear(self):
        request, preferences = _request(DOUBLES, sample_top_4_teams(random.Random(2))[:3])
        figures = place_figures(request, preferences)
        labelled = labelled_preferences(preferences, figures)
        names = [item for item in labelled.text_slots if item.field == "member.tag" and item.entrant_slot == 1]
        crest = next(tag for tag in labelled.placement_tags if tag.slot_id.endswith(BETWEEN_NAMES_SUFFIX))
        self.assertEqual(crest.anchor.y, round(sum(item.anchor.y - item.preferred_size * 7 // 20 for item in names) / 2))
        seed = next(item for item in labelled.text_slots if item.slot_id == "seed_1")
        original = {item.slot_id: item for item in preferences.text_slots}
        original_crest = next(tag for tag in preferences.placement_tags if tag.slot_id == crest.slot_id)
        self.assertEqual(seed.anchor.y - original["seed_1"].anchor.y, crest.anchor.y - original_crest.anchor.y)
        draw = ImageDraw.Draw(Image.new("RGBA", (1920, 1080)))
        box = (crest.anchor.x - 80, crest.anchor.y - 75, crest.anchor.x + 80, crest.anchor.y + 75)
        for x in (crest.anchor.x - 60, crest.anchor.x + 60):
            tag = _clear_of(draw, CharacterTag((x, crest.anchor.y + 20), "AVeryLongPlayerTag", "#FFFFFFFF", 600), box, PodiumFont.TYROWO)
            left, _top, right, _bottom = _character_tag_bounds(draw, tag, PodiumFont.TYROWO)
            self.assertTrue(right <= box[0] or left >= box[2])

    def test_doubles_member_names_sit_above_each_visible_head(self):
        request, preferences = _request(DOUBLES, sample_top_4_teams(random.Random(5))[:3])
        figures = place_figures(request, preferences)
        labelled = labelled_preferences(preferences, figures)
        for item in labelled.text_slots:
            if item.field == "member.tag":
                head = figures[f"entrant_{item.entrant_slot}_member_{item.member_slot}"].lineup.bounds.top
                self.assertEqual(item.anchor.y, head - 15)

    def test_omitted_entrants_leave_their_slot_blank_without_moving_others(self):
        entrants = sample_top_8_entrants(random.Random(3))
        entrants[2] = replace(entrants[2], omit_entrant=True)
        entrants[4] = replace(entrants[4], omit_placement=True)
        request, preferences = _request(SINGLES, entrants)
        visible = visible_preferences(preferences, request.entrants)
        figures = place_figures(request, visible)
        self.assertNotIn("entrant_3", figures)
        self.assertNotIn("number_3", {tag.slot_id for tag in visible.placement_tags})
        self.assertNotIn("number_5", {tag.slot_id for tag in visible.placement_tags})
        self.assertIn("name_5", {item.slot_id for item in visible.text_slots})
        self.assertEqual(figures["entrant_4"].lineup.bounds.bottom, _frames(preferences)["entrant_4"].destination.bottom)


class FlyingVRenderingTests(unittest.TestCase):
    def test_public_api_renders_both_layouts_with_header_and_top_row_watermark(self):
        singles = draw_singles_top_8(sample_top_8_entrants(random.Random(1)), tournament=sample_tournament(TournamentFormat.SINGLES))
        doubles = draw_doubles_top_3(sample_top_4_teams(random.Random(1))[:3], tournament=sample_tournament(TournamentFormat.DOUBLES))
        for image, size, boxes in ((singles, (1440, 1920), SINGLES_HEADER_BOXES), (doubles, (1920, 1080), DOUBLES_HEADER_BOXES)):
            self.assertEqual((image.mode, image.size), ("RGBA", size))
            self.assertIsNotNone(image.crop(boxes["top_middle"].as_tuple()).getbbox())
            self.assertIsNotNone(image.crop((size[0] // 2, 0, size[0], WATERMARK_ROW_HEIGHT)).getbbox())
            self.assertIsNone(image.crop((0, 0, 400, WATERMARK_ROW_HEIGHT)).getchannel("A").point(lambda value: 255 if value > 70 else 0).getbbox())

    def test_flying_v_rejects_formatting_colors(self):
        with self.assertRaisesRegex(ValueError, "formatting_colors"):
            _request(SINGLES, sample_top_8_entrants(random.Random(1)), formatting_colors=GeometricFormattingColors.one("#FFFFFFFF"))

    def test_corner_header_blocks_hug_the_bottom_and_every_assignment_renders(self):
        request, preferences = _request(SINGLES, sample_top_8_entrants(random.Random(2)))
        renderer = FlyingVContentRenderer()
        for contents in permutations(HEADER_CONTENTS):
            layout = dict(zip(HEADER_POSITIONS, contents, strict=True))
            canvas = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
            renderer._draw_header(canvas, replace(request, header_layout=layout), preferences)
            for position, content in layout.items():
                if content == "tournament_logo":
                    continue
                box = SINGLES_HEADER_BOXES[position]
                visible = canvas.crop(box.as_tuple()).getbbox()
                self.assertIsNotNone(visible, (position, content))
                if position == "top_middle":
                    self.assertLess(visible[1], 20)
                else:
                    self.assertGreater(visible[3], box.height - 12)

    def test_metadata_rows_align_to_their_box_edges_in_every_provided_font(self):
        request, preferences = _request(SINGLES, sample_top_8_entrants(random.Random(2)),
                                        header_layout={"top_left": "tournament_title", "top_middle": "metadata", "top_right": "tournament_logo"})
        box = SINGLES_HEADER_BOXES["top_middle"]
        for font in PodiumFont:
            with self.subTest(font=font.value):
                left, _top, right, _bottom = FlyingVContentRenderer(font=font).header_text_layer(request, "metadata", box, "ma").getbbox()
                self.assertLessEqual(abs(left - (box.width - right)), 6)
                # A wide layer reveals any overshoot that a box-sized layer would clip.
                layer = Image.new("RGBA", (1600, 120), "#00000000")
                LegacyPodiumContentRenderer(font=font)._draw_joined_metadata_row(
                    layer, request, [("2026-10-20", 28)], x=1000, y=10, anchor="ra", max_width=box.width, exact_size=True)
                self.assertIn(layer.getbbox()[2], (1000, 1001))

    def test_explicit_entrant_text_colors_override_the_default_palette(self):
        entrants = sample_top_8_entrants(random.Random(4))
        request, preferences = _request(SINGLES, entrants, text_settings=TextSettings(
            entrant_text_color_mode="pick_1", entrant_text_colors=("#00FF00FF",), include_seeding=False))
        result = CreationPipeline({CreationMode.FLYING_V: FlyingVContentRenderer()}).create(request)
        name = next(item for item in preferences.text_slots if item.slot_id == "name_4")
        region = result.crop((name.anchor.x - 100, name.anchor.y, name.anchor.x + 100, name.anchor.y + 44)).convert("RGBA")
        self.assertIn((0, 255, 0, 255), set(region.getdata()))
        self.assertNotIn((0, 240, 66, 255), set(region.getdata()))

    def test_format_preview_route_renders_both_layouts_and_rejects_other_counts(self):
        client = app.test_client()
        for event_format, count, size in (("singles", 8, (1440, 1920)), ("doubles", 3, (1920, 1080))):
            response = client.post("/api/format-preview", json={"mode": "flying_v", "event_format": event_format, "entrant_count": count})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(Image.open(BytesIO(response.data)).size, size)
        response = client.post("/api/format-preview", json={"mode": "flying_v", "event_format": "doubles", "entrant_count": 4})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Flying V supports", response.get_json()["error"])

    def test_browser_logo_boxes_match_the_serialized_header_regions(self):
        source = (Path(__file__).resolve().parents[1] / "frontend" / "src" / "LayeredFormatPreview.tsx").read_text(encoding="utf-8")
        block = source[source.index('format.selection.mode === "flying_v"'):]
        for boxes in (SINGLES_HEADER_BOXES, DOUBLES_HEADER_BOXES):
            for position, box in boxes.items():
                self.assertIn(f"{position}: {{ left: {box.left}, top: {box.top}, right: {box.right}, bottom: {box.bottom} }}", block[:1000])

    def test_preview_layers_match_the_placeholder_figures_and_header_boxes(self):
        for layout_id, size in (("singles_top_8", (1440, 1920)), ("doubles_top_3", (1920, 1080))):
            layer = render_placeholder_layer(layout_id)
            self.assertEqual(layer.size, size)
            self.assertIsNotNone(layer.getbbox())
        header = render_flying_v_header_layer(PodiumFont.UBUNTU, TournamentFormat.SINGLES,
                                              {"top_left": "tournament_logo", "top_middle": "tournament_title", "top_right": "metadata"})
        # The boxed logo placeholder marks the bottom-left reserved corner.
        self.assertIsNotNone(header.crop(SINGLES_HEADER_BOXES["top_left"].as_tuple()).getbbox())


if __name__ == "__main__":
    unittest.main()

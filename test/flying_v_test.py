"""Flying V geometry, serialization, figure placement, labels, and rendering."""

from dataclasses import replace
from io import BytesIO
from itertools import permutations
import json
from pathlib import Path
import random
import unittest

from PIL import Image

from app import app
from background_builder import BackgroundRequest, PixelRect
from creation import CreationPipeline, CreationRequest, TextSettings
from creation_modes import CreationMode, ModeOptions, ModeSelection
from DrawFlyingV import draw_doubles_top_3, draw_singles_top_8
from DrawPodium import PodiumFont
from entrant_visibility import slot_from_id, visible_preferences
from flying_v_content_renderer import (
    FlyingVContentRenderer,
    WATERMARK_ROW_HEIGHT,
    flying_v_header_boxes,
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
        for selection, generated, size, boxes in ((SINGLES, flying_v_singles_preferences(), (1280, 1920), SINGLES_HEADER_BOXES),
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
        self.assertAlmostEqual(scales[2] / scales[1], 2 / 3, delta=.05)
        self.assertTrue(.4 <= scales[3] / scales[1] <= .5)
        # Larger, nearer figures are drawn over the smaller ones behind them.
        self.assertTrue(depth[1] > depth[2] > depth[3] == depth[4] > depth[5] == depth[6] > depth[7] == depth[8])

    def test_figures_flank_the_center_and_fly_outward_toward_the_top(self):
        frames = _frames(ModePreferenceRepository().load(SINGLES))
        center = {slot: (frames[f"entrant_{slot}"].destination.left + frames[f"entrant_{slot}"].destination.right) / 2 for slot in range(1, 9)}
        self.assertEqual(center[1], 640)
        self.assertEqual(center[2], 640)
        for left, right in ((3, 4), (5, 6), (7, 8)):
            self.assertLess(center[left], 640)
            self.assertGreater(center[right], 640)
            self.assertEqual(center[left] + center[right], 1280)
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
                # The name and crest are drawn over the leader's legs.
                name = next(item for item in preferences.text_slots if item.slot_id == "name_1")
                self.assertGreater(name.anchor.y - name.preferred_size, min(frame.destination.top for frame in leader_frames))

    def test_names_rest_on_the_feet_directly_above_each_placement_number(self):
        for selection in (SINGLES, DOUBLES):
            preferences = ModePreferenceRepository().load(selection)
            badges = {slot_from_id(tag.slot_id): tag for tag in preferences.placement_tags}
            feet = {}
            for slot_id, frame in _frames(preferences).items():
                feet[slot_from_id(slot_id)] = max(feet.get(slot_from_id(slot_id), 0), frame.destination.bottom)
            for name in (item for item in preferences.text_slots if item.slot_id.startswith("name_")):
                with self.subTest(selection=selection.submode_id, slot=name.entrant_slot):
                    badge = badges[name.entrant_slot]
                    self.assertEqual(name.pillow_anchor, "ms")
                    self.assertEqual(name.anchor.x, badge.anchor.x)
                    self.assertEqual(badge.anchor.y - badge.max_size.height // 2 - name.anchor.y, 12)
                    if name.entrant_slot != 1:
                        self.assertEqual(name.anchor.y, feet[name.entrant_slot] - 2)

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
        names = [item for item in singles.text_slots if item.field == "entrant.tag"]
        self.assertEqual([item.color for item in names[:4]], ["#D90300FF", "#5B59F8FF", "#FFD805FF", "#00F042FF"])
        doubles = ModePreferenceRepository().load(DOUBLES)
        self.assertEqual([tag.asset_id for tag in doubles.placement_tags], ["01st.png", "02nd.png", "03rd.png"])
        self.assertEqual(sorted((item.entrant_slot, item.member_slot) for item in doubles.text_slots if item.field == "member.tag"),
                         [(team, member) for team in (1, 2, 3) for member in (1, 2)])
        self.assertEqual(len([item for item in doubles.text_slots if item.field == "entrant.team_name"]), 3)


class FlyingVPlacementTests(unittest.TestCase):
    def test_lineups_shrink_only_when_they_overflow_their_frame(self):
        giant = [Character("Bowser", color="default", pose="c"), Character("Donkey Kong", color="default", pose="a")]
        frame = PixelRect(100, 200, 300, 500)
        standing = place_lineup(giant, 1.0, frame)
        hanging = place_lineup(giant, 1.0, frame, hanging=True)
        for placed in (standing, hanging):
            self.assertLessEqual(placed.bounds.width, frame.width)
            self.assertLessEqual(placed.bounds.height, frame.height)
            self.assertGreaterEqual(placed.bounds.left, frame.left)
            self.assertLessEqual(placed.bounds.right, frame.right)
        self.assertEqual(standing.bounds.bottom, frame.bottom)
        self.assertEqual(hanging.bounds.top, frame.top)
        # Characters that fit keep their relativity scale; only overflow shrinks.
        pichu, fox = Character("Pichu", color="default", pose="a"), Character("Fox", color="default", pose="a")
        roomy = PixelRect(0, 0, 1000, 1000)
        ratio = place_lineup([pichu], .3, roomy).bounds.height / place_lineup([fox], .3, roomy).bounds.height
        self.assertAlmostEqual(ratio, 434.6 / 796, delta=.02)

    def test_short_second_place_label_rises_to_its_feet(self):
        pichu = Character("Pichu", color="default", pose="a")
        request, preferences = _request(SINGLES, _singles({1: pichu, 2: pichu}))
        figures = place_figures(request, preferences)
        second = figures["entrant_2"].lineup.bounds
        self.assertEqual(second.top, _frames(preferences)["entrant_2"].destination.top)
        labelled = labelled_preferences(preferences, figures)
        badge = next(tag for tag in labelled.placement_tags if tag.slot_id == "number_2")
        name = next(item for item in labelled.text_slots if item.slot_id == "name_2")
        self.assertEqual(name.anchor.y, second.bottom - 2)
        self.assertEqual(badge.anchor.y - badge.max_size.height // 2, second.bottom + 10)

    def test_covered_second_place_label_stays_above_first_place(self):
        request, preferences = _request(SINGLES, _singles({1: Character("Ganondorf", color="default", pose="c"),
                                                            2: Character("Bowser", color="default", pose="c")}))
        figures = place_figures(request, preferences)
        first = figures["entrant_1"].lineup.bounds
        self.assertLess(first.top, figures["entrant_2"].lineup.bounds.bottom)
        labelled = labelled_preferences(preferences, figures)
        badge = next(tag for tag in labelled.placement_tags if tag.slot_id == "number_2")
        self.assertLessEqual(badge.anchor.y + badge.max_size.height // 2, first.top - 6)
        unchanged = {item.slot_id: item for item in preferences.text_slots}
        self.assertEqual(next(item for item in labelled.text_slots if item.slot_id == "name_4"), unchanged["name_4"])

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
        for image, size, boxes in ((singles, (1280, 1920), SINGLES_HEADER_BOXES), (doubles, (1920, 1080), DOUBLES_HEADER_BOXES)):
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
        region = result.crop((name.anchor.x - 100, name.anchor.y - 40, name.anchor.x + 100, name.anchor.y + 4)).convert("RGBA")
        self.assertIn((0, 255, 0, 255), set(region.getdata()))
        self.assertNotIn((0, 240, 66, 255), set(region.getdata()))

    def test_format_preview_route_renders_both_layouts_and_rejects_other_counts(self):
        client = app.test_client()
        for event_format, count, size in (("singles", 8, (1280, 1920)), ("doubles", 3, (1920, 1080))):
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
        for layout_id, size in (("singles_top_8", (1280, 1920)), ("doubles_top_3", (1920, 1080))):
            layer = render_placeholder_layer(layout_id)
            self.assertEqual(layer.size, size)
            self.assertIsNotNone(layer.getbbox())
        header = render_flying_v_header_layer(PodiumFont.UBUNTU, TournamentFormat.SINGLES,
                                              {"top_left": "tournament_logo", "top_middle": "tournament_title", "top_right": "metadata"})
        # The boxed logo placeholder marks the bottom-left reserved corner.
        self.assertIsNotNone(header.crop(SINGLES_HEADER_BOXES["top_left"].as_tuple()).getbbox())


if __name__ == "__main__":
    unittest.main()

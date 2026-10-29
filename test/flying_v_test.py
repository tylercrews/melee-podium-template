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
from creation_modes import (
    FLYING_V_SECOND_PLACE_FLIPPED,
    FLYING_V_VERTICALLY_REVERSED,
    CreationMode,
    ModeOptions,
    ModeSelection,
    flying_v_singles_variant,
)
from DrawFlyingV import draw_doubles_top_3, draw_singles_top_8
from DrawPodium import CharacterTag, PodiumFont, _character_tag_bounds, _draw_text
from entrant_visibility import slot_from_id, visible_preferences
from flying_v_content_renderer import (
    BETWEEN_NAMES_SUFFIX,
    composite_outlined_names,
    draw_outlined_placement_tags,
    FlyingVContentRenderer,
    WATERMARK_ROW_HEIGHT,
    flying_v_header_boxes,
    flying_v_watermark_row,
    _clear_of,
    labelled_preferences,
    place_figures,
    text_vertical_extent,
)
from flying_v_lineup import STANDING_FRAME, LineupSlot, place_lineup, place_team
from flying_v_preview_layers import render_flying_v_header_layer, render_placeholder_layer
from generate_flying_v_preferences import (
    DOUBLES_HEADER_BOXES,
    DOUBLES_SIDE_LABEL_GAP,
    REVERSED_SINGLES_HEADER_BOXES,
    SECOND_LABEL_OFFSET,
    SINGLES_HEADER_BOXES,
    UPRIGHT_SECOND_RISE,
    tallest_render_height,
    flying_v_doubles_preferences,
    flying_v_singles_preferences,
)
from formatting_assets import draw_placement_tags
from geometric_formatting_colors import GeometricFormattingColors
from legacy_podium_content_renderer import LegacyPodiumContentRenderer
from mode_preferences import ModePreferenceRepository, ModePreferences
from models import Character, DoublesTeam, Entrant, SinglesEntrant, TournamentFormat
from placement_numbering import numbered_preferences
from preview_layers import HEADER_CONTENTS, HEADER_POSITIONS
from sample_creation_data import sample_top_4_teams, sample_top_8_entrants, sample_tournament


SINGLES = ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.SINGLES, 8))
DOUBLES = ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.DOUBLES, 3))
REVERSED = ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.SINGLES, 8, FLYING_V_VERTICALLY_REVERSED))
FLIPPED = ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.SINGLES, 8, FLYING_V_SECOND_PLACE_FLIPPED))
REVERSED_FLIPPED = ModeSelection(CreationMode.FLYING_V, ModeOptions(TournamentFormat.SINGLES, 8, flying_v_singles_variant(True, True)))
ALL_SINGLES = (SINGLES, FLIPPED, REVERSED, REVERSED_FLIPPED)
SINGLES_BOXES = {SINGLES: SINGLES_HEADER_BOXES, FLIPPED: SINGLES_HEADER_BOXES,
                 REVERSED: REVERSED_SINGLES_HEADER_BOXES, REVERSED_FLIPPED: REVERSED_SINGLES_HEADER_BOXES}


def _is_reversed(selection) -> bool:
    return (selection.options.variant or "").startswith(FLYING_V_VERTICALLY_REVERSED)


def _frames(preferences):
    return {item.slot_id: item for item in preferences.formatting_assets if item.asset_id == STANDING_FRAME}


def _label_rect(item) -> PixelRect:
    top, bottom = text_vertical_extent(item)
    left = {"l": item.anchor.x, "r": item.anchor.x - item.max_width}.get(item.pillow_anchor[0], item.anchor.x - item.max_width // 2)
    return PixelRect(left, top, left + item.max_width, bottom)


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
        singles = [(selection, flying_v_singles_preferences(_is_reversed(selection), selection in (FLIPPED, REVERSED_FLIPPED)),
                    (1440, 1920), SINGLES_BOXES[selection]) for selection in ALL_SINGLES]
        for selection, generated, size, boxes in (*singles,
                                                  (DOUBLES, flying_v_doubles_preferences(), (2160, 1080), DOUBLES_HEADER_BOXES)):
            with self.subTest(selection=selection.submode_id):
                preferences = ModePreferenceRepository().load(selection)
                self.assertTrue(preferences.ready)
                self.assertEqual(preferences.canvas_size.as_tuple(), size)
                self.assertEqual(preferences, generated)
                self.assertEqual(ModePreferences.from_dict(json.loads(json.dumps(preferences.to_dict()))), preferences)
                self.assertEqual(flying_v_header_boxes(preferences), boxes)

    def test_only_singles_top_8_and_doubles_top_3_are_valid(self):
        for event_format, count, variant in ((TournamentFormat.SINGLES, 3, None), (TournamentFormat.DOUBLES, 4, None),
                                             (TournamentFormat.SINGLES, 8, "four_podium"),
                                             (TournamentFormat.DOUBLES, 3, FLYING_V_VERTICALLY_REVERSED),
                                             (TournamentFormat.DOUBLES, 3, FLYING_V_SECOND_PLACE_FLIPPED),
                                             (TournamentFormat.SINGLES, 8, "second_place_flipped_vertically_reversed")):
            with self.assertRaisesRegex(ValueError, "Flying V supports"):
                ModeSelection(CreationMode.FLYING_V, ModeOptions(event_format, count, variant))
        self.assertEqual([selection.submode_id for selection in ALL_SINGLES],
                         ["singles_top_8", "singles_top_8_second_place_flipped", "singles_top_8_vertically_reversed",
                          "singles_top_8_vertically_reversed_second_place_flipped"])

    def test_flipping_second_place_moves_only_its_label_to_the_other_side(self):
        for unflipped, flipped, shift in ((SINGLES, FLIPPED, -2 * SECOND_LABEL_OFFSET),
                                          (REVERSED, REVERSED_FLIPPED, 2 * SECOND_LABEL_OFFSET)):
            with self.subTest(selection=flipped.submode_id):
                original, moved = (ModePreferenceRepository().load(selection) for selection in (unflipped, flipped))
                self.assertEqual(moved.formatting_assets, original.formatting_assets)
                self.assertEqual(moved.character_slots, original.character_slots)
                for before, after in ((original.text_slots, moved.text_slots), (original.placement_tags, moved.placement_tags)):
                    for item, mirrored in zip(before, after, strict=True):
                        if getattr(item, "entrant_slot", None) == 2 or item.slot_id == "number_2":
                            self.assertEqual(mirrored, replace(item, anchor=replace(item.anchor, x=item.anchor.x + shift)))
                        else:
                            self.assertEqual(mirrored, item)

    def test_singles_tiers_shrink_from_the_leader_back_through_the_v(self):
        for selection in ALL_SINGLES:
            with self.subTest(selection=selection.submode_id):
                preferences = ModePreferenceRepository().load(selection)
                scales = {item.entrant_slot: item.scale for item in preferences.character_slots}
                depth = {item.entrant_slot: item.z_index for item in preferences.character_slots}
                self.assertTrue(scales[1] > scales[3] == scales[4] > scales[5] == scales[6] > scales[7] == scales[8])
                self.assertTrue(.45 <= scales[3] / scales[1] <= .55)
                self.assertLess(scales[2], scales[1])
                if not _is_reversed(selection):
                    # Standing behind first place, upright second outranks third and fourth.
                    self.assertGreater(scales[2], scales[3])
                # Larger, nearer figures are drawn over the smaller ones behind them.
                self.assertTrue(depth[1] > depth[2] > depth[3] == depth[4] > depth[5] == depth[6] > depth[7] == depth[8])

    def test_figures_flank_the_center_and_fly_outward_toward_the_top(self):
        self._assert_flying_v(_frames(ModePreferenceRepository().load(SINGLES)), reversed_order=False)

    def test_reversed_figures_fly_outward_toward_the_bottom_beneath_the_leader(self):
        frames = _frames(ModePreferenceRepository().load(REVERSED))
        self._assert_flying_v(frames, reversed_order=True)
        # Second place stands beneath first, not behind it.
        self.assertGreater(frames["entrant_2"].destination.top, frames["entrant_1"].destination.bottom)

    def _assert_flying_v(self, frames, *, reversed_order):
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
        order = (1, 3, 5, 7) if reversed_order else (7, 5, 3, 1)
        for upper, lower in zip(order, order[1:]):
            self.assertLessEqual(bottoms[upper], bottoms[lower])

    def test_doubles_first_place_stands_a_little_above_its_bottom_edge_name(self):
        preferences = ModePreferenceRepository().load(DOUBLES)
        canvas = preferences.canvas_size
        leader_frames = [frame for slot_id, frame in _frames(preferences).items() if slot_from_id(slot_id) == 1]
        badges = {slot_from_id(tag.slot_id): tag for tag in preferences.placement_tags}
        self.assertGreaterEqual(badges[1].max_size.height, 2.5 * max(tag.max_size.height for slot, tag in badges.items() if slot != 1))
        name = next(item for item in preferences.text_slots if item.slot_id == "name_1")
        self.assertEqual(name.pillow_anchor, "ms")
        self.assertGreaterEqual(name.anchor.y, canvas.height - 20)
        for frame in leader_frames:
            self.assertEqual(frame.destination.bottom, canvas.height - 40)
            self.assertLess(frame.destination.bottom, name.anchor.y)

    def test_every_singles_figure_stands_on_its_placement_number_above_its_name(self):
        for selection in ALL_SINGLES:
            preferences = ModePreferenceRepository().load(selection)
            frames = _frames(preferences)
            badges = {slot_from_id(tag.slot_id): tag for tag in preferences.placement_tags}
            for name in (item for item in preferences.text_slots if item.slot_id.startswith("name_")):
                if name.entrant_slot == 2:
                    continue  # Second place's label sits in a corner of its area instead.
                with self.subTest(selection=selection.submode_id, slot=name.entrant_slot):
                    badge = badges[name.entrant_slot]
                    badge_bottom = badge.anchor.y + badge.max_size.height // 2
                    self.assertEqual(name.anchor.x, badge.anchor.x)
                    self.assertEqual(text_vertical_extent(name)[0] - badge_bottom, 4)
                    # The placement art covers the feet and the name sits just below them.
                    self.assertEqual(badge_bottom, frames[f"entrant_{name.entrant_slot}"].destination.bottom + 2)
            first_crest = badges[1].max_size.height
            self.assertGreaterEqual(first_crest, 2.5 * max(tag.max_size.height for slot, tag in badges.items() if slot != 1))
            self.assertLessEqual(text_vertical_extent(next(item for item in preferences.text_slots if item.slot_id == "name_1"))[1],
                                 preferences.canvas_size.height)

    def test_second_place_label_sits_in_the_corner_of_its_area_nearest_the_title(self):
        for selection, side in ((SINGLES, 1), (FLIPPED, -1), (REVERSED, -1), (REVERSED_FLIPPED, 1)):
            with self.subTest(selection=selection.submode_id):
                preferences = ModePreferenceRepository().load(selection)
                frame = _frames(preferences)["entrant_2"].destination
                text = {item.slot_id: item for item in preferences.text_slots}
                badge = next(tag for tag in preferences.placement_tags if tag.slot_id == "number_2")
                name, seed, sponsor = text["name_2"], text["seed_2"], text["sponsor_2"]
                # The label column sits entirely to one side of the figures' center...
                center = (frame.left + frame.right) // 2
                self.assertEqual(name.anchor.x, center + side * SECOND_LABEL_OFFSET)
                self.assertGreater(side * (name.anchor.x - center), name.max_width // 2)
                # ...with the placement row (sponsor, art, seed) sharing one line.
                self.assertEqual(name.anchor.x, badge.anchor.x)
                self.assertEqual(sponsor.anchor.y, badge.anchor.y)
                self.assertEqual(seed.anchor.y, badge.anchor.y)
                self.assertEqual(name.pillow_anchor, "ma")
                name_top, name_bottom = text_vertical_extent(name)
                if _is_reversed(selection):
                    # The number row sits above the name, which ends where the figures stand, just above the title.
                    self.assertEqual(name_top - (badge.anchor.y + badge.max_size.height // 2), 4)
                    self.assertEqual(name_bottom, frame.bottom)
                    self.assertEqual(frame.bottom, REVERSED_SINGLES_HEADER_BOXES["top_middle"].top)
                else:
                    # The name hangs just below the title with the number row directly beneath it.
                    self.assertGreater(name.anchor.y, SINGLES_HEADER_BOXES["top_middle"].bottom)
                    self.assertLess(name.anchor.y, frame.top + frame.height // 4)
                    self.assertEqual(badge.anchor.y - badge.max_size.height // 2 - name_bottom, 4)

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
        # 7ths sit above the 5ths, which sit above 3rd and 4th, on each side;
        # reversed, 1st sits above 2nd and the flanking tiers fly downward.
        for selection in ALL_SINGLES:
            pairs = ((1, 2), (3, 5), (4, 6), (5, 7), (6, 8)) if _is_reversed(selection) else ((7, 5), (8, 6), (5, 3), (6, 4))
            preferences = ModePreferenceRepository().load(selection)
            frames = _frames(preferences)
            names = {item.entrant_slot: item for item in preferences.text_slots if item.slot_id.startswith("name_")}
            for upper, lower in pairs:
                with self.subTest(selection=selection.submode_id, upper=upper, lower=lower):
                    self.assertLess(text_vertical_extent(names[upper])[1], frames[f"entrant_{lower}"].destination.top)

    def test_doubles_back_teams_hang_their_art_then_name_below_the_feet_and_the_crest_sits_between_names(self):
        preferences = ModePreferenceRepository().load(DOUBLES)
        frames = _frames(preferences)
        badges = {slot_from_id(tag.slot_id): tag for tag in preferences.placement_tags}
        self.assertGreater(DOUBLES_SIDE_LABEL_GAP, 0)
        for slot, side, edge in ((2, "l", 16), (3, "r", 2144)):
            name = next(item for item in preferences.text_slots if item.slot_id == f"name_{slot}")
            feet = frames[f"entrant_{slot}_member_1"].destination.bottom
            # The placement art hangs just below the feet, and the name beneath it
            # hugs the outer edge, wrapping downward.
            art_top = feet + DOUBLES_SIDE_LABEL_GAP
            self.assertEqual(badges[slot].anchor.y - badges[slot].max_size.height // 2, art_top)
            self.assertEqual((name.pillow_anchor, name.anchor.x, name.anchor.y, name.wrap),
                             (f"{side}a", edge, art_top + badges[slot].max_size.height + 4, True))
            # Two wrapped lines still end above the corner header boxes.
            self.assertLessEqual(name.anchor.y + 2 * round(name.preferred_size * 1.25), DOUBLES_HEADER_BOXES["top_left"].top)
            badge_edge = badges[slot].anchor.x + (-1 if side == "l" else 1) * (badges[slot].max_size.width // 2)
            self.assertLessEqual(abs(badge_edge - edge), 1)
            seed = next(item for item in preferences.text_slots if item.slot_id == f"seed_{slot}")
            self.assertEqual(seed.pillow_anchor, f"{side}m")
            # Names that run toward the center pass behind the winning team.
            self.assertLess(name.z_index, min(item.z_index for item in preferences.character_slots if item.entrant_slot == 1))
            self.assertGreater(name.z_index, max(item.z_index for item in preferences.character_slots if item.entrant_slot == slot))
        crest = badges[1]
        self.assertTrue(crest.slot_id.endswith(BETWEEN_NAMES_SUFFIX))
        self.assertEqual(crest.anchor.x, preferences.canvas_size.width // 2)
        self.assertGreater(crest.max_size.height, 150)
        # The crest is layered behind the winning team's figures.
        self.assertLess(crest.z_index, min(item.z_index for item in preferences.character_slots if item.entrant_slot == 1))
        seed = next(item for item in preferences.text_slots if item.slot_id == "seed_1")
        self.assertEqual(seed.pillow_anchor, "ls")
        self.assertGreater(seed.anchor.x, crest.anchor.x + crest.max_size.height * 9 // 20)
        self.assertLess(seed.anchor.y, crest.anchor.y - crest.max_size.height // 4)

    def test_second_place_is_standardized_so_only_the_tallest_render_fills_its_frame(self):
        tallest = tallest_render_height()
        for selection, ceiling, rise in ((SINGLES, SINGLES_HEADER_BOXES["top_middle"].bottom, UPRIGHT_SECOND_RISE),
                                         (REVERSED, None, 0)):
            with self.subTest(selection=selection.submode_id):
                preferences = ModePreferenceRepository().load(selection)
                frame = _frames(preferences)["entrant_2"].destination
                second = next(item for item in preferences.character_slots if item.entrant_slot == 2)
                # The tier scale fills the frame with the tallest character exactly; upright
                # second place then stands a little higher, so only the very tallest
                # poses shrink to stay below the title.
                self.assertLessEqual(tallest * second.scale, frame.height + rise)
                self.assertGreaterEqual(tallest * second.scale, frame.height + rise - 1)
                self.assertEqual((second.anchor.x, second.anchor.y), ((frame.left + frame.right) // 2, frame.bottom))
                if ceiling is not None:
                    self.assertEqual(frame.top, ceiling)
                else:
                    first_name = next(item for item in preferences.text_slots if item.slot_id == "name_1")
                    self.assertGreater(frame.top, text_vertical_extent(first_name)[1])
        bowser = Character("Bowser", color="default", pose="c")
        for selection in (SINGLES, REVERSED):
            with self.subTest(selection=selection.submode_id):
                preferences = ModePreferenceRepository().load(selection)
                frame = _frames(preferences)["entrant_2"].destination
                scale = next(item.scale for item in preferences.character_slots if item.entrant_slot == 2)
                placed = place_lineup([bowser], scale, frame)
                roomy = place_lineup([bowser], scale, PixelRect(0, 0, 4000, 4000))
                # Only height ever limits the tallest render, which reaches the frame top.
                self.assertLessEqual(abs(placed.bounds.top - frame.top), 1)
                self.assertAlmostEqual(placed.image.width / placed.image.height, roomy.image.width / roomy.image.height, delta=.01)

    def test_reserved_header_spaces_and_watermark_row_stay_clear(self):
        for selection, boxes in (*SINGLES_BOXES.items(), (DOUBLES, DOUBLES_HEADER_BOXES)):
            preferences = ModePreferenceRepository().load(selection)
            reserved = [*boxes.values(), flying_v_watermark_row(preferences)]
            for slot_id, frame in _frames(preferences).items():
                with self.subTest(selection=selection.submode_id, slot=slot_id):
                    self.assertFalse(_overlaps(frame.destination, flying_v_watermark_row(preferences)))
                    self.assertFalse(_overlaps(frame.destination, boxes["top_middle"]))
                    if slot_from_id(slot_id) != 1:
                        self.assertFalse(_overlaps(frame.destination, boxes["top_left"]))
                        self.assertFalse(_overlaps(frame.destination, boxes["top_right"]))
            # Result names, seeds, and sponsors never enter the header boxes or the
            # watermark row; the leader's crest and seed follow its names.
            for item in preferences.text_slots:
                if item.field == "member.tag" or (item.entrant_slot == 1 and item.field == "entrant.seed"):
                    continue
                with self.subTest(selection=selection.submode_id, text=item.slot_id):
                    self.assertFalse(any(_overlaps(_label_rect(item), box) for box in reserved))
            for tag in preferences.placement_tags:
                if slot_from_id(tag.slot_id) != 1:
                    rect = PixelRect(tag.anchor.x - tag.max_size.width // 2, tag.anchor.y - tag.max_size.height // 2,
                                     tag.anchor.x + tag.max_size.width // 2, tag.anchor.y + tag.max_size.height // 2)
                    self.assertFalse(any(_overlaps(rect, box) for box in reserved), tag.slot_id)

    def test_reversed_header_puts_logo_and_metadata_on_top_and_the_title_at_the_bottom(self):
        preferences = ModePreferenceRepository().load(REVERSED)
        boxes = flying_v_header_boxes(preferences)
        height = preferences.canvas_size.height
        self.assertLess(boxes["top_left"].bottom, height // 4)
        self.assertLess(boxes["top_right"].bottom, height // 4)
        self.assertGreater(boxes["top_middle"].top, height * 3 // 4)
        self.assertGreater(flying_v_watermark_row(preferences).top, boxes["top_middle"].bottom)

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
        self.assertLessEqual(standing.bounds.height, frame.height)
        # A lineup wider than its frame stays centered on it.
        self.assertLessEqual(abs((standing.bounds.left + standing.bounds.right) - (frame.left + frame.right)), 1)
        self.assertEqual(standing.bounds.bottom, frame.bottom)
        alone = place_lineup(giant[:1], 1.0, PixelRect(0, 0, 200, 300))
        self.assertLessEqual(alone.bounds.width, 200)
        self.assertLessEqual(alone.bounds.height, 300)

    def test_extra_characters_never_shrink_an_entrant_below_its_tier_size(self):
        marth, fox = Character("Marth", color="default", pose="b"), Character("Fox", color="default", pose="a")
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

    def test_every_render_fits_the_doubles_back_tiers_at_full_tier_size(self):
        preferences = ModePreferenceRepository().load(DOUBLES)
        frames = _frames(preferences)
        # Second and third place mirror each other at one shared tier size.
        back = {(item.entrant_slot, item.member_slot): item for item in preferences.character_slots if item.entrant_slot != 1}
        for member, mirror in ((1, 2), (2, 1)):
            second, third = back[(2, member)], back[(3, mirror)]
            self.assertEqual(second.scale, third.scale)
            self.assertEqual(second.anchor.x, preferences.canvas_size.width - third.anchor.x)
            second_frame, third_frame = frames[second.slot_id].destination, frames[third.slot_id].destination
            self.assertEqual((second_frame.width, second_frame.height), (third_frame.width, third_frame.height))
            self.assertEqual(second_frame.left, preferences.canvas_size.width - third_frame.right)
        largest = [Character("Bowser", color="default", pose="c"), Character("Ice Climbers", color="default", pose="a"),
                   Character("Marth", color="default", pose="e")]
        for placement in preferences.character_slots:
            if placement.entrant_slot == 1:
                continue
            frame = frames[placement.slot_id].destination
            for character in largest:
                with self.subTest(slot=placement.slot_id, character=character.melee_fighter_name):
                    placed = place_lineup([character], placement.scale, frame, anchor_x=placement.anchor.x)
                    roomy = place_lineup([character], placement.scale, PixelRect(0, 0, 4000, 4000))
                    self.assertEqual(placed.image.size, roomy.image.size)
                    self.assertGreaterEqual(placed.bounds.left, max(0, frame.left))
                    self.assertLessEqual(placed.bounds.right, min(preferences.canvas_size.width, frame.right))

    def test_teammates_shrink_together_and_keep_their_relative_sizes(self):
        marth, puff = Character("Marth", color="default", pose="a"), Character("Jigglypuff", color="default", pose="a")
        frame, roomy = PixelRect(0, 0, 900, 500), PixelRect(0, 0, 4000, 4000)
        tall, short = place_team([LineupSlot([marth], .8, frame), LineupSlot([puff], .8, frame)])
        # Marth is too tall for the frame, so both partners shrink by his factor.
        self.assertEqual(tall.bounds.height, frame.height)
        self.assertLess(short.bounds.height, place_lineup([puff], .8, frame).bounds.height)
        natural = place_lineup([puff], .8, roomy).bounds.height / place_lineup([marth], .8, roomy).bounds.height
        self.assertAlmostEqual(short.bounds.height / tall.bounds.height, natural, delta=.01)

    def test_winning_doubles_partners_keep_their_relative_sizes(self):
        marth, puff = Character("Marth", color="default", pose="a"), Character("Jigglypuff", color="default", pose="a")
        leaders = DoublesTeam(seed=1, placement=1, entrant_1=Entrant(tag="Puff", characters=[puff]),
                              entrant_2=Entrant(tag="Marth", characters=[marth]), team_name="Leaders")
        request, preferences = _request(DOUBLES, [leaders, *sample_top_4_teams(random.Random(1))[1:3]])
        figures = place_figures(request, preferences)
        roomy = PixelRect(0, 0, 4000, 4000)
        natural = place_lineup([puff], .8, roomy).bounds.height / place_lineup([marth], .8, roomy).bounds.height
        ratio = figures["entrant_1_member_1"].lineup.bounds.height / figures["entrant_1_member_2"].lineup.bounds.height
        self.assertAlmostEqual(ratio, natural, delta=.01)

    def test_figures_center_on_their_anchor_and_slide_only_to_stay_in_frame(self):
        fox, bowser = Character("Fox", color="default", pose="a"), Character("Bowser", color="default", pose="c")
        frame = PixelRect(0, 0, 560, 600)
        placed = place_lineup([fox], .46, frame, anchor_x=170)
        self.assertLessEqual(abs((placed.bounds.left + placed.bounds.right) / 2 - 170), 1)
        wide = place_lineup([bowser], .46, frame, anchor_x=170)
        self.assertEqual(wide.bounds.left, 0)

    def test_back_team_names_wrap_early_and_pass_behind_the_winning_team(self):
        # Fixed poses keep the measured figures identical to the rendered ones.
        member = Entrant(tag="Player", characters=[Character("Fox", color="default", pose="a")])
        teams = [DoublesTeam(seed=slot, placement=slot, entrant_1=member, entrant_2=member, team_name=name)
                 for slot, name in enumerate(("Leaders", "TheseTeamNamesHaveNoSpacesAndRunOnForever",
                                              "A Very Long Team Name That Keeps Going"), 1)]
        request, preferences = _request(DOUBLES, teams, text_settings=TextSettings(include_seeding=False))
        names = {item.entrant_slot: item for item in preferences.text_slots if item.field == "entrant.team_name"}
        renderer = FlyingVContentRenderer(font=PodiumFont.UBUNTU)
        image = renderer.draw(Image.new("RGBA", (2160, 1080), "#00000000"), request, preferences)
        without_leader = renderer.draw(Image.new("RGBA", (2160, 1080), "#00000000"),
                                       replace(request, entrants=[replace(teams[0], omit_entrant=True), *teams[1:]]),
                                       visible_preferences(preferences, [replace(teams[0], omit_entrant=True), *teams[1:]]))
        # The unbroken name runs on into the first-place figures, which cover it
        # wherever they are opaque.
        row = names[2].anchor.y + 20
        topmost = {}
        leaders = [figure for figure in place_figures(request, preferences).values() if figure.entrant_slot == 1]
        for figure in sorted(leaders, key=lambda item: (item.z_index, item.slot_id)):
            bounds = figure.lineup.bounds
            if bounds.top <= row < bounds.bottom:
                for x in range(max(0, bounds.left), min(2160, bounds.right)):
                    pixel = figure.lineup.image.getpixel((x - bounds.left, row - bounds.top))
                    if pixel[3] == 255:
                        topmost[x] = pixel
        covered = [x for x in topmost if without_leader.getpixel((x, row))[3]]
        self.assertGreater(len(covered), 20)
        for x in covered:
            self.assertEqual(image.getpixel((x, row)), topmost[x])
        # The spaced name breaks into right-aligned lines stacked downward from
        # beneath its placement art, with nothing above its first line.
        header_top = DOUBLES_HEADER_BOXES["top_right"].top
        third = without_leader.crop((1540, names[3].anchor.y - 2, 2160, header_top))
        self.assertGreater(third.getbbox()[3] - third.getbbox()[1], 44 * 3 // 2)
        art_left = 2144 - next(tag for tag in preferences.placement_tags if tag.slot_id == "number_3").max_size.width
        self.assertIsNone(without_leader.crop((1540, names[3].anchor.y - 50, art_left - 80, names[3].anchor.y - 4)).getbbox())

    def test_second_place_stands_on_its_number_whatever_its_height(self):
        pichu, bowser = Character("Pichu", color="default", pose="a"), Character("Bowser", color="default", pose="c")
        for second in (pichu, bowser):
            with self.subTest(second=second.melee_fighter_name):
                request, preferences = _request(SINGLES, _singles({1: pichu, 2: second}))
                figures = place_figures(request, preferences)
                frame = _frames(preferences)["entrant_2"].destination
                self.assertEqual(figures["entrant_2"].lineup.bounds.bottom, frame.bottom)
                labelled = labelled_preferences(preferences, figures)
                self.assertEqual(labelled.placement_tags, preferences.placement_tags)
                self.assertEqual(labelled.text_slots, preferences.text_slots)
        # The tallest render reaches the title; shorter characters keep their relative size.
        self.assertLessEqual(abs(figures["entrant_2"].lineup.bounds.top - frame.top), 1)

    def test_reversed_second_place_label_never_rises_under_the_leader(self):
        request, preferences = _request(REVERSED, _singles({1: Character("Ganondorf", color="default", pose="c"),
                                                             2: Character("Bowser", color="default", pose="c")}))
        figures = place_figures(request, preferences)
        self.assertLess(figures["entrant_1"].lineup.bounds.bottom, figures["entrant_2"].lineup.bounds.top)
        labelled = labelled_preferences(preferences, figures)
        self.assertEqual(labelled.text_slots, preferences.text_slots)

    def test_result_labels_keep_their_positions_even_under_a_towering_leader(self):
        request, preferences = _request(SINGLES, _singles({1: Character("Ganondorf", color="default", pose="c"),
                                                            2: Character("Bowser", color="default", pose="c")}))
        figures = place_figures(request, preferences)
        labelled = labelled_preferences(preferences, figures)
        self.assertEqual(labelled.text_slots, preferences.text_slots)
        self.assertEqual(labelled.placement_tags, preferences.placement_tags)
        # Second place's top-right label stays clear of first place's head.
        badge = next(tag for tag in preferences.placement_tags if tag.slot_id == "number_2")
        self.assertLess(badge.anchor.y + badge.max_size.height // 2, figures["entrant_1"].lineup.bounds.top)

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

    def test_placement_art_is_outlined_in_black_except_the_first_place_crest(self):
        preferences = ModePreferenceRepository().load(SINGLES)
        for slot_id, outlined in (("number_1", False), ("number_2", True), ("number_5", True), ("number_7", True)):
            with self.subTest(slot=slot_id):
                tag = next(item for item in preferences.placement_tags if item.slot_id == slot_id)
                plain = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
                draw_placement_tags(plain, replace(preferences, placement_tags=(tag,)))
                layer = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
                draw_outlined_placement_tags(layer, replace(preferences, placement_tags=(tag,)))
                if not outlined:
                    self.assertEqual(layer.tobytes(), plain.tobytes())
                    continue
                left, top, right, bottom = plain.getbbox()
                # The outline widens the art and is opaque black where the art was clear.
                grown = layer.getbbox()
                self.assertLess(grown[0], left)
                self.assertGreater(grown[2], right)
                box = grown
                outline = [pixel for pixel, original in zip(layer.crop(box).getdata(), plain.crop(box).getdata())
                           if original[3] == 0 and pixel == (0, 0, 0, 255)]
                self.assertGreater(len(outline), 100)

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
        for image, size, boxes in ((singles, (1440, 1920), SINGLES_HEADER_BOXES), (doubles, (2160, 1080), DOUBLES_HEADER_BOXES)):
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

    def test_name_outlines_share_each_names_alpha(self):
        for alpha, expected_inside, expected_ring in (("FF", (255, 0, 0), (0, 0, 0)), ("80", (255, 127, 127), (127, 127, 127)),
                                                      ("40", (255, 191, 191), (191, 191, 191))):
            with self.subTest(alpha=alpha):
                layer = Image.new("RGBA", (400, 120), "#00000000")
                _draw_text(ImageDraw.Draw(layer), (20, 20), "Mang0", anchor="la", max_width=360, preferred_size=64,
                           font=PodiumFont.UBUNTU, fill=f"#FF0000{alpha}")
                canvas = Image.new("RGBA", layer.size, "#FFFFFFFF")
                composite_outlined_names(canvas, layer)
                coverage = layer.getchannel("A")
                full = max(coverage.getdata())
                inside = {canvas.getpixel((x, y))[:3] for x in range(400) for y in range(120) if coverage.getpixel((x, y)) == full}
                ring = [canvas.getpixel((x, y))[:3] for x in range(400) for y in range(120)
                        if coverage.getpixel((x, y)) == 0 and canvas.getpixel((x, y))[:3] != (255, 255, 255)]
                # Letters show the background at the name's own transparency, never a black underlay.
                self.assertEqual(inside, {expected_inside})
                self.assertEqual(min(ring, key=sum), expected_ring)

    def test_translucent_entrant_names_render_without_a_darkened_outline_underlay(self):
        request, preferences = _request(SINGLES, sample_top_8_entrants(random.Random(4)), text_settings=TextSettings(
            entrant_text_color_mode="pick_1", entrant_text_colors=("#FF000080",), include_seeding=False))
        request = replace(request, background=BackgroundRequest(preferences.canvas_size, fill_color="#FFFFFFFF"))
        result = CreationPipeline({CreationMode.FLYING_V: FlyingVContentRenderer()}).create(request)
        name = next(item for item in preferences.text_slots if item.slot_id == "name_7")
        region = set(result.crop((name.anchor.x - 120, name.anchor.y, name.anchor.x + 120, name.anchor.y + 44)).getdata())
        self.assertTrue(any(abs(red - 255) <= 1 and abs(green - 127) <= 1 and abs(blue - 127) <= 1 for red, green, blue, _ in region))
        self.assertFalse(any(red > 150 and green < 90 for red, green, _blue, _ in region))

    def test_format_preview_route_renders_both_layouts_and_rejects_other_counts(self):
        client = app.test_client()
        for event_format, count, size in (("singles", 8, (1440, 1920)), ("doubles", 3, (2160, 1080))):
            response = client.post("/api/format-preview", json={"mode": "flying_v", "event_format": event_format, "entrant_count": count})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(Image.open(BytesIO(response.data)).size, size)
        response = client.post("/api/format-preview", json={"mode": "flying_v", "event_format": "doubles", "entrant_count": 4})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Flying V supports", response.get_json()["error"])

    def test_browser_logo_boxes_match_the_serialized_header_regions(self):
        source = (Path(__file__).resolve().parents[1] / "frontend" / "src" / "LayeredFormatPreview.tsx").read_text(encoding="utf-8")
        block = source[source.index('format.selection.mode === "flying_v"'):]
        for boxes in (REVERSED_SINGLES_HEADER_BOXES, SINGLES_HEADER_BOXES, DOUBLES_HEADER_BOXES):
            for position, box in boxes.items():
                self.assertIn(f"{position}: {{ left: {box.left}, top: {box.top}, right: {box.right}, bottom: {box.bottom} }}", block[:1600])

    def test_preview_layers_match_the_placeholder_figures_and_header_boxes(self):
        for layout_id, size in (("singles_top_8", (1440, 1920)), ("doubles_top_3", (2160, 1080))):
            layer = render_placeholder_layer(layout_id)
            self.assertEqual(layer.size, size)
            self.assertIsNotNone(layer.getbbox())
        header = render_flying_v_header_layer(PodiumFont.UBUNTU, "singles_top_8",
                                              {"top_left": "tournament_logo", "top_middle": "tournament_title", "top_right": "metadata"})
        # The boxed logo placeholder marks the bottom-left reserved corner.
        self.assertIsNotNone(header.crop(SINGLES_HEADER_BOXES["top_left"].as_tuple()).getbbox())


if __name__ == "__main__":
    unittest.main()

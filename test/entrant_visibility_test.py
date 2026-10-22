"""Omitted slots and honorable mentions stay separate from ranking and favorites."""

from io import BytesIO
import unittest
from unittest.mock import patch

from PIL import Image

from app import app, _preview_entrants
from creation_modes import CreationMode, PodiumStyle
from DrawPodium import PodiumFont
from entrant_visibility import visible_preferences, apply_visibility
from format_preview import prepare_format_preview
from geometric_formatting_colors import GeometricFormattingColors
from mode_preferences import ModePreferenceRepository
from models import TournamentFormat
from placement_preview_layers import preview_selections
from podiums_clapping_renderer import ClappingLayout
from sample_creation_data import sample_singles_entrants, sample_top_4_teams


class EntrantVisibilityTest(unittest.TestCase):
    def test_all_supported_layouts_render_with_every_slot_intentionally_blank(self):
        for selection in preview_selections():
            with self.subTest(selection=selection):
                options = selection.options
                result = prepare_format_preview(options.podium_style or PodiumStyle.LEGACY,
                    options.event_format, options.entrant_count, options.variant, transparent=True,
                    creation_mode=selection.mode, font=PodiumFont.UBUNTU,
                    formatting_colors=GeometricFormattingColors.from_dict({"mode": "pick_1", "colors": [
                        {"background_color": "#112233FF", "trim_color": "#445566FF"}]} ) if selection.mode not in {CreationMode.PODIUM, CreationMode.FLYING_V} else None,
                    entrant_visibility=[{"omit_entrant": True}] * options.entrant_count)
                image = result.frame() if isinstance(result, ClappingLayout) else result
                self.assertIsInstance(image, Image.Image)
                self.assertEqual(image.size, ModePreferenceRepository().load(selection).canvas_size.as_tuple())
                if isinstance(result, ClappingLayout):
                    self.assertEqual(result.tracks, ())
                    self.assertEqual(result.badges, ())
                    self.assertEqual(result.frame(0).tobytes(), result.frame().tobytes())

    def test_omitting_all_content_removes_assets_while_HM_only_removes_badges(self):
        for selection in preview_selections():
            options = selection.options
            entrants = sample_singles_entrants(options.entrant_count) if options.event_format is TournamentFormat.SINGLES else sample_top_4_teams()
            if len(entrants) < options.entrant_count:
                from sample_creation_data import sample_top_8_teams
                entrants = sample_top_8_teams()
            omitted = apply_visibility(entrants, [{"omit_entrant": True}] * len(entrants))
            original = ModePreferenceRepository().load(selection)
            hidden = visible_preferences(original, omitted)
            self.assertEqual(hidden.character_slots, ())
            self.assertEqual(hidden.placement_tags, ())
            self.assertFalse(any(row.entrant_slot is not None for row in hidden.text_slots))
            hm = visible_preferences(original, apply_visibility(entrants, [{"omit_placement": True}] * len(entrants)))
            self.assertEqual(hm.formatting_assets, original.formatting_assets)
            self.assertEqual(hm.character_slots, original.character_slots)
            self.assertEqual(hm.placement_tags, ())
            self.assertEqual(original, ModePreferenceRepository().load(selection))

    def test_blank_omitted_API_slots_require_no_tags_characters_or_seeds(self):
        for event in TournamentFormat.SINGLES, TournamentFormat.DOUBLES:
            entrants = _preview_entrants([{"omit_entrant": True}] * 8, event)
            self.assertTrue(all(entrant.omit_entrant for entrant in entrants))
        for key in ("omit_entrant", "omit_placement"):
            for invalid in (None, "true", 1):
                response = app.test_client().post("/api/format-preview", json={
                    "entrant_visibility": [{key: invalid}]})
                self.assertEqual(response.status_code, 400)
                with self.assertRaisesRegex(ValueError, "booleans"):
                    _preview_entrants([{key: invalid}], TournamentFormat.SINGLES)

    def test_blank_omitted_legacy_podium_slots_skip_footer_measurement(self):
        character = {"melee_fighter_name": "Fox", "color": "default", "pose": "a"}
        member = lambda tag: {"tag": tag, "characters": [character]}
        for event_format, count, variant in (("singles", 8, None), ("singles", 8, "four_podium"), ("doubles", 3, None)):
            with self.subTest(event_format=event_format, count=count, variant=variant):
                entrants = [{"team_name": f"Team {slot}", "seed": slot, "placement": slot, "team_color": "red",
                             "entrant_1": member(f"A{slot}"), "entrant_2": member(f"B{slot}")}
                            if event_format == "doubles" else {**member(f"P{slot}"), "seed": slot, "placement": slot}
                            for slot in range(1, count + 1)]
                entrants[0] = {"omit_entrant": True, "tag": "", "team_name": "", "characters": [{"melee_fighter_name": ""}]}
                entrants[-1] = {"omit_entrant": True}
                response = app.test_client().post("/api/format-preview", json={
                    "style": "legacy", "event_format": event_format, "entrant_count": count, "variant": variant,
                    "animated": False, "transparent": True, "entrants": entrants,
                    "tournament": {"title": "Omitted", "date": "2026-10-20", "event_format": event_format}})
                self.assertEqual(response.status_code, 200, response.data[:200])

    def test_mixed_radial_teams_remove_both_member_regions_and_keep_header_geometry(self):
        from creation_modes import ModeOptions, ModeSelection
        selection = ModeSelection(CreationMode.RADIAL, ModeOptions(TournamentFormat.DOUBLES, 4))
        original = ModePreferenceRepository().load(selection)
        teams = sample_top_4_teams()
        visible = apply_visibility(teams, [{}, {"omit_entrant": True}, {}, {"omit_placement": True}])
        preferences = visible_preferences(original, visible)
        self.assertEqual(len(preferences.character_slots), 6)
        self.assertEqual(len([row for row in preferences.formatting_assets if row.asset_id == "radial_portrait_slice"]), 6)
        self.assertEqual(len(preferences.placement_tags), 2)
        image = prepare_format_preview(PodiumStyle.LEGACY, TournamentFormat.DOUBLES, 4,
            creation_mode=CreationMode.RADIAL, transparent=True, entrants=visible,
            formatting_colors=GeometricFormattingColors.one("#112233FF", "#556677FF"))
        self.assertEqual(image.size, (1920, 1080))

    def test_mixed_slots_and_HMs_persist_in_every_clapping_gif_frame(self):
        from app import prepare_format_preview as real_prepare
        captured = []
        def capture(*args, **kwargs):
            result = real_prepare(*args, **kwargs)
            captured.append(result)
            return result
        visibility = [{"omit_entrant": True}, {"omit_placement": True}] + [{}] * 2 + [
            {"omit_entrant": True}, {"omit_placement": True}, {}, {}]
        with patch("app.prepare_format_preview", side_effect=capture):
            response = app.test_client().post("/api/format-preview", json={
                "style": "customizable", "event_format": "singles", "entrant_count": 8,
                "variant": "four_podium", "animated": True, "transparent": True,
                "formatting_asset_colors": {"mode": "premade", "preset": "smash_player_colors", "colors": []},
                "entrant_visibility": visibility})
        self.assertEqual(response.status_code, 200, response.data[:200])
        layout = captured[0]
        self.assertEqual([track.panel.entrant_slot for track in layout.tracks], [6, 7, 8])
        self.assertEqual([badge.slot_id for badge in layout.badges], ["lower_pair_2_entrant_7_placement_tag", "lower_pair_2_entrant_8_placement_tag"])
        self.assertEqual([row.slot_id for row in layout.preferences.formatting_assets], ["podium_2", "podium_3", "podium_4"])
        self.assertEqual([row.slot_id for row in layout.preferences.placement_tags], ["podium_3_placement_tag", "podium_4_placement_tag"])
        omitted_rect = (110, 815, 211, 941)
        # No animated track is present for slot 5; its lower region remains still.
        frames = [layout.frame(index).crop(omitted_rect).tobytes() for index in (0, 18, 41)]
        self.assertEqual(frames[0], frames[1])
        self.assertEqual(frames[1], frames[2])
        with Image.open(BytesIO(response.data)) as gif:
            self.assertEqual(gif.n_frames, 42)
            self.assertEqual(gif.info["loop"], 0)

    def test_all_omitted_clapping_gif_encodes_a_valid_still_cycle(self):
        response = app.test_client().post("/api/format-preview", json={
            "style": "customizable", "event_format": "singles", "entrant_count": 7,
            "variant": "clapping_grid_4", "animated": True, "transparent": True,
            "formatting_asset_colors": {"mode": "premade", "preset": "smash_player_colors", "colors": []},
            "entrants": [{"omit_entrant": True}] * 7})
        self.assertEqual(response.status_code, 200, response.data[:200])
        with Image.open(BytesIO(response.data)) as image:
            self.assertEqual(image.size, (1920, 1150))
            self.assertEqual(image.n_frames, 1)

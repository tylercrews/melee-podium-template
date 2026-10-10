"""Checks for independent typography controls, API validation, and rendering."""

from dataclasses import replace
import random
import unittest
from unittest.mock import patch

from PIL import Image

from app import app
from creation import TextSettings
from creation_modes import PodiumStyle
from format_preview import render_format_preview
from models import TournamentFormat
from sample_creation_data import sample_singles_entrants, sample_top_4_teams, sample_tournament


class FontSizeAdjustmentTests(unittest.TestCase):
    def test_validates_each_adjustment_and_metadata_row_count(self):
        for field in ("title_font_size_adjustment", "subtitle_font_size_adjustment", "seed_font_size_adjustment"):
            for value in (-21, 21, True, 1.5, "2"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    TextSettings(**{field: value})
        with self.assertRaises(ValueError):
            TextSettings(metadata_rows=(("event",),), metadata_row_font_size_adjustments=(0, 1))
        with self.assertRaises(ValueError):
            TextSettings(metadata_rows=(("event",),), metadata_row_font_size_adjustments=(True,))
        self.assertEqual(TextSettings().metadata_row_font_size_adjustments, (0, 0, 0, 0))

    def test_preview_api_retains_format_and_individual_doubles_sizes(self):
        teams = sample_top_4_teams(random.Random(0))[:3]
        payload = {
            "style": "legacy", "event_format": "doubles", "entrant_count": 3,
            "text_settings": {"title_font_size_adjustment": 10, "subtitle_font_size_adjustment": -7,
                              "seed_font_size_adjustment": 6, "metadata_rows": [["event"], ["date"]],
                              "metadata_row_font_size_adjustments": [3, -4]},
            "entrants": [{"team_name": team.team_name, "team_name_font_size_adjustment": 8,
                          "placement": team.placement, "seed": team.seed,
                          "entrant_1": {"tag": team.entrant_1.tag, "name_font_size_adjustment": -5,
                                        "characters": [{"melee_fighter_name": "Fox"}]},
                          "entrant_2": {"tag": team.entrant_2.tag, "name_font_size_adjustment": 12,
                                        "characters": [{"melee_fighter_name": "Marth"}]}} for team in teams],
        }
        with patch("app.render_format_preview", return_value=Image.new("RGBA", (10, 10))) as render:
            response = app.test_client().post("/api/format-preview", json=payload)
        self.assertEqual(response.status_code, 200)
        settings = render.call_args.kwargs["text_settings"]
        self.assertEqual((settings.title_font_size_adjustment, settings.subtitle_font_size_adjustment, settings.seed_font_size_adjustment), (10, -7, 6))
        self.assertEqual(settings.metadata_row_font_size_adjustments, (3, -4))
        team = render.call_args.kwargs["entrants"][0]
        self.assertEqual((team.team_name_font_size_adjustment, team.entrant_1.name_font_size_adjustment, team.entrant_2.name_font_size_adjustment), (8, -5, 12))
        payload["entrants"][0]["entrant_1"]["name_font_size_adjustment"] = True
        self.assertEqual(app.test_client().post("/api/format-preview", json=payload).status_code, 400)

    def test_singles_name_sizes_cross_api_boundary(self):
        with patch("app.render_format_preview", return_value=Image.new("RGBA", (10, 10))) as render:
            response = app.test_client().post("/api/format-preview", json={
                "entrant_count": 3, "entrants": [{"tag": "Player", "placement": index, "seed": index,
                    "name_font_size_adjustment": index, "characters": [{"melee_fighter_name": "Fox"}]} for index in range(1, 4)]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([entrant.name_font_size_adjustment for entrant in render.call_args.kwargs["entrants"]], [1, 2, 3])

    def test_metadata_offsets_do_not_shift_when_a_row_is_empty(self):
        from legacy_podium_content_renderer import LegacyPodiumContentRenderer
        from types import SimpleNamespace
        tournament = replace(sample_tournament(), event=None)
        settings = TextSettings(metadata_rows=(("event",), ("date",)), metadata_row_font_size_adjustments=(20, -3))
        rows = LegacyPodiumContentRenderer._metadata_items(SimpleNamespace(tournament=tournament, text_settings=settings))
        self.assertEqual(rows, [[(str(tournament.date), 25)]])

    def test_geometric_layouts_apply_per_member_and_team_offsets_independently(self):
        from types import SimpleNamespace
        from creation_modes import CreationMode, ModeOptions, ModeSelection
        from DrawPodium import PodiumFont
        from geometric_content_renderer import _draw_result_text, _header_text_lines
        from mode_preferences import ModePreferenceRepository
        teams = sample_top_4_teams(random.Random(0))
        teams = [replace(team, team_name_font_size_adjustment=8,
                         entrant_1=replace(team.entrant_1, name_font_size_adjustment=-4),
                         entrant_2=replace(team.entrant_2, name_font_size_adjustment=12)) for team in teams]
        settings = TextSettings(seed_font_size_adjustment=3, title_font_size_adjustment=9,
                                subtitle_font_size_adjustment=-8,
                                metadata_rows=(("event", "date"), ("entrants_count",)),
                                metadata_row_font_size_adjustments=(-5, 10))
        request = SimpleNamespace(entrants=teams, text_settings=settings, tournament=sample_tournament(TournamentFormat.DOUBLES))
        for mode in (CreationMode.EYES, CreationMode.SQUARES, CreationMode.RADIAL):
            preferences = ModePreferenceRepository().load(ModeSelection(mode, ModeOptions(event_format=TournamentFormat.DOUBLES, entrant_count=4)))
            with patch("geometric_content_renderer._draw_text") as draw:
                _draw_result_text(Image.new("RGBA", preferences.canvas_size.as_tuple()), request, preferences, PodiumFont.TYROWO)
            for call in draw.call_args_list:
                placement = next(slot for slot in preferences.text_slots
                                 if (slot.anchor.x, slot.anchor.y) == call.args[1])
                offset = (3 if placement.field == "entrant.seed" else 8 if placement.field == "entrant.team_name"
                          else -4 if placement.member_slot == 1 else 12)
                self.assertEqual(call.kwargs["preferred_size"], max(11, (placement.preferred_size or 42) + offset))
        self.assertEqual([size for _text, size in _header_text_lines(request, "tournament_title", 58, 26)], [67, 50])
        self.assertEqual([size for _text, size in _header_text_lines(request, "metadata", 58, 26)], [21, 36])

    def test_render_changes_only_the_selected_header_text_region(self):
        from DrawPodium import _POSE_FILENAME, _resolve_character_path
        def fixed_pose(character):
            selected = _POSE_FILENAME.match(_resolve_character_path(character).name)
            return replace(character, pose=selected.group("pose"))
        entrants = [replace(entrant, characters=[fixed_pose(character) for character in entrant.characters])
                    for entrant in sample_singles_entrants(3, random.Random(0))]
        tournament = replace(sample_tournament(), title="Local", subtitle="Finals", event="Melee")
        layout = {"top_left": "tournament_title", "top_middle": "tournament_logo", "top_right": "metadata"}
        def render(settings):
            return render_format_preview(PodiumStyle.LEGACY, TournamentFormat.SINGLES, 3,
                header_layout=layout, text_settings=settings, entrants=entrants, tournament=tournament)
        settings = TextSettings(metadata_rows=(("event",), ("date",)))
        baseline = render(settings)
        changed = render(replace(settings, title_font_size_adjustment=-20))
        self.assertNotEqual(baseline.crop((0, 0, 550, 100)).tobytes(), changed.crop((0, 0, 550, 100)).tobytes())
        self.assertEqual(baseline.crop((0, 110, 550, 190)).tobytes(), changed.crop((0, 110, 550, 190)).tobytes())
        self.assertEqual(baseline.crop((1120, 0, 1672, 190)).tobytes(), changed.crop((1120, 0, 1672, 190)).tobytes())
        # A following default render must retain its original calibration.
        self.assertEqual(baseline.tobytes(), render(settings).tobytes())


if __name__ == "__main__":
    unittest.main()

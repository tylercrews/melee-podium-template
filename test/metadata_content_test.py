"""Date ranges, literal metadata, PR defaults, and renderer/API compatibility."""

from dataclasses import replace
from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image

from app import app
from creation import TextSettings
from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from geometric_content_renderer import _metadata_lines
from legacy_podium_content_renderer import LegacyPodiumContentRenderer
from layout_text_defaults import layout_text_defaults
from metadata_content import metadata_values, validate_date_range
from sample_creation_data import sample_tournament


FIELDS = (("date_range",), ("free_text_1",), ("free_text_2",), ("free_text_3",), ("free_text_4",))


class MetadataContentTest(unittest.TestCase):
    def test_range_dates_validate_and_join_with_to(self):
        for start, end in (("2026-01-01", "2026-06-30"), (date(2026, 1, 1), date(2026, 6, 30))):
            tournament = replace(sample_tournament(), date_range_start=start, date_range_end=end)
            self.assertEqual(metadata_values(tournament)["date_range"], "2026-01-01 to 2026-06-30")
        validate_date_range(None, None)
        for start, end in ((None, "2026-06-30"), ("2026-01-01", None), ("2026-02-30", "2026-06-30"),
                           ("20260101", "20260630"), ("2026-07-01", "2026-06-30")):
            with self.assertRaises(ValueError):
                validate_date_range(start, end)

    def test_all_metadata_renderers_preserve_free_text_and_grouping(self):
        tournament = replace(sample_tournament(), date_range_start="2026-01-01", date_range_end="2026-06-30",
                             free_text_1="North Carolina PR", free_text_2="Season 1", free_text_3="HM: Example", free_text_4="Thanks, everyone!")
        settings = TextSettings(metadata_rows=FIELDS, metadata_row_font_size_adjustments=(0, 1, 2, 3, 4))
        request = SimpleNamespace(tournament=tournament, text_settings=settings)
        lines = ["2026-01-01 to 2026-06-30", "North Carolina PR", "Season 1", "HM: Example", "Thanks, everyone!"]
        self.assertEqual(_metadata_lines(request), lines)
        self.assertEqual(LegacyPodiumContentRenderer._metadata_items(request),
                         [[(text, 28 + index)] for index, text in enumerate(lines)])
        request.text_settings = TextSettings(metadata_rows=(("date_range", "free_text_1"), ("free_text_4",)))
        self.assertEqual(_metadata_lines(request), [lines[0] + " • " + lines[1], lines[4]])
        empty = replace(tournament, free_text_1=None, date_range_start=None, date_range_end=None)
        request.tournament = empty
        self.assertEqual(_metadata_lines(request), [lines[4]])

    def test_preview_API_retains_dates_text_and_rejects_invalid_ranges(self):
        payload = {"entrant_count": 3, "text_settings": {"metadata_rows": [list(row) for row in FIELDS]},
                   "tournament": {"title": "Spring PR", "date_range_start": "2026-01-01", "date_range_end": "2026-06-30",
                                  **{f"free_text_{index}": f"My text {index}" for index in range(1, 5)}}}
        with patch("app.render_format_preview", return_value=Image.new("RGBA", (10, 10))) as render:
            response = app.test_client().post("/api/format-preview", json=payload)
        self.assertEqual(response.status_code, 200, response.data)
        tournament = render.call_args.kwargs["tournament"]
        self.assertEqual(metadata_values(tournament)["date_range"], "2026-01-01 to 2026-06-30")
        self.assertEqual([getattr(tournament, f"free_text_{index}") for index in range(1, 5)], [f"My text {index}" for index in range(1, 5)])
        self.assertEqual(render.call_args.kwargs["text_settings"].metadata_rows, FIELDS)
        for end in (None, "2025-01-01", "invalid"):
            invalid = {**payload, "tournament": {**payload["tournament"], "date_range_end": end}}
            response = app.test_client().post("/api/format-preview", json=invalid)
            self.assertEqual(response.status_code, 400)

    def test_PR_defaults_apply_to_API_and_allow_explicit_saved_overrides(self):
        for mode, count, variant in (("eyes", 15, None), ("podium", 11, "clapping_grid_4")):
            payload = dict(mode=mode, entrant_count=count, variant=variant, animated=False, style="customizable",
                           formatting_asset_colors=dict(mode="premade", preset="smash_player_colors", colors=[]))
            renderer = "app.prepare_format_preview" if mode == "podium" else "app.render_format_preview"
            with patch(renderer, return_value=Image.new("RGBA", (10, 10))) as render:
                response = app.test_client().post("/api/format-preview", json=payload)
            self.assertEqual(response.status_code, 200, response.data)
            settings = render.call_args.kwargs["text_settings"]
            self.assertFalse(settings.include_seeding)
            self.assertFalse(settings.use_tournament_placing)
            self.assertEqual(settings.metadata_rows, (("event",), ("date_range",), ("entrants_count",)))
            payload["text_settings"] = dict(include_seeding=True, use_tournament_placing=True, metadata_rows=[["tournament_link", "date"]])
            with patch(renderer, return_value=Image.new("RGBA", (10, 10))) as render:
                response = app.test_client().post("/api/format-preview", json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(render.call_args.kwargs["text_settings"].include_seeding)
            self.assertEqual(render.call_args.kwargs["text_settings"].metadata_rows, (("tournament_link", "date"),))

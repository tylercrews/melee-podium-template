"""API-boundary checks for customized Format-step previews."""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image

from app import app


class FormatPreviewRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = app.test_client()

    def test_renders_an_uncached_rainbow_preview(self) -> None:
        response = self.client.post(
            "/api/format-preview",
            json={
                "style": "customizable",
                "event_format": "singles",
                "entrant_count": 3,
                "variant": None,
                "transparent": True,
                "formatting_asset_colors": {
                    "mode": "premade",
                    "preset": "rainbow",
                    "preset_transparency": 40,
                    "colors": [],
                },
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertTrue(response.data.startswith(b"\x89PNG"))

    def test_rejects_a_pick_two_mode_without_two_palettes(self) -> None:
        response = self.client.post(
            "/api/format-preview",
            json={
                "style": "customizable",
                "event_format": "singles",
                "entrant_count": 3,
                "formatting_asset_colors": {
                    "mode": "pick_2",
                    "preset": None,
                    "colors": [
                        {
                            "main_color": "#FF0000FF",
                            "face_color": "#880000FF",
                            "base_color": "#000000FF",
                            "metallic": False,
                        }
                    ],
                },
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_applies_transparency_to_premade_palette_colors(self) -> None:
        with patch("app.render_format_preview", return_value=Image.new("RGBA", (16, 16))) as render_preview:
            response = self.client.post(
                "/api/format-preview",
                json={
                    "style": "customizable",
                    "event_format": "singles",
                    "entrant_count": 3,
                    "formatting_asset_colors": {
                        "mode": "premade",
                        "preset": "smash_player_colors",
                        "preset_transparency": 50,
                        "colors": [],
                    },
                },
            )

        self.assertEqual(response.status_code, 200)
        colors = render_preview.call_args.kwargs["podium_colors"]
        first = colors.color_for_slot(1)
        self.assertEqual(first.main_color[-2:], "80")
        self.assertEqual(first.face_color[-2:], "80")
        self.assertEqual(first.base_color[-2:], "80")

    def test_applies_independent_transparency_to_each_preset_part(self) -> None:
        with patch("app.render_format_preview", return_value=Image.new("RGBA", (16, 16))) as render_preview:
            response = self.client.post(
                "/api/format-preview",
                json={
                    "style": "customizable",
                    "event_format": "singles",
                    "entrant_count": 3,
                    "formatting_asset_colors": {
                        "mode": "premade",
                        "preset": "smash_player_colors",
                        "preset_transparency": {
                            "main_color": 10,
                            "face_color": 20,
                            "base_color": 75,
                        },
                        "colors": [],
                    },
                },
            )

        self.assertEqual(response.status_code, 200)
        first = render_preview.call_args.kwargs["podium_colors"].color_for_slot(1)
        self.assertEqual(first.main_color[-2:], "E6")
        self.assertEqual(first.face_color[-2:], "CC")
        self.assertEqual(first.base_color[-2:], "40")

    def test_squares_maps_main_to_border_and_sides_to_background(self) -> None:
        with patch("app.render_format_preview", return_value=Image.new("RGBA", (16, 16))) as render_preview:
            response = self.client.post(
                "/api/format-preview",
                json={
                    "mode": "squares",
                    "style": "legacy",
                    "event_format": "doubles",
                    "entrant_count": 4,
                    "formatting_asset_colors": {
                        "mode": "pick_1",
                        "preset": None,
                        "preset_transparency": {
                            "main_color": 0,
                            "face_color": 0,
                            "base_color": 0,
                        },
                        "colors": [{
                            "main_color": "#AABBCCDD",
                            "face_color": "#11223344",
                            "base_color": "#20304080",
                            "metallic": False,
                        }],
                    },
                },
            )

        self.assertEqual(response.status_code, 200)
        colors = render_preview.call_args.kwargs["formatting_colors"]
        self.assertEqual(colors.for_slot(1).trim_color, "#AABBCCDD")
        self.assertEqual(colors.for_slot(1).background_color, "#20304080")

    def test_eyes_maps_main_to_rectangle_background(self) -> None:
        with patch("app.render_format_preview", return_value=Image.new("RGBA", (16, 16))) as render_preview:
            response = self.client.post(
                "/api/format-preview",
                json={
                    "mode": "eyes",
                    "event_format": "singles",
                    "entrant_count": 8,
                    "formatting_asset_colors": {
                        "mode": "pick_1",
                        "preset": None,
                        "preset_transparency": {
                            "main_color": 0,
                            "face_color": 0,
                            "base_color": 0,
                        },
                        "colors": [{
                            "main_color": "#AABBCCDD",
                            "face_color": "#11223344",
                            "base_color": "#20304080",
                            "metallic": False,
                        }],
                    },
                },
            )

        self.assertEqual(response.status_code, 200)
        colors = render_preview.call_args.kwargs["formatting_colors"]
        self.assertEqual(colors.for_slot(1).background_color, "#AABBCCDD")
        self.assertIsNone(colors.for_slot(1).trim_color)

    def test_large_eyes_presets_repeat_or_extend_as_reviewed(self) -> None:
        for preset in ("smash_player_colors", "rainbow", "olympic_medals"):
            with self.subTest(preset=preset), patch(
                "app.render_format_preview",
                return_value=Image.new("RGBA", (16, 16)),
            ) as render_preview:
                response = self.client.post(
                    "/api/format-preview",
                    json={
                        "mode": "eyes",
                        "event_format": "singles",
                        "entrant_count": 25,
                        "formatting_asset_colors": {
                            "mode": "premade",
                            "preset": preset,
                            "preset_transparency": {
                                "main_color": 0,
                                "face_color": 0,
                                "base_color": 0,
                            },
                            "colors": [],
                        },
                    },
                )

                self.assertEqual(response.status_code, 200)
                colors = render_preview.call_args.kwargs["formatting_colors"]
                if preset == "olympic_medals":
                    self.assertNotEqual(
                        colors.for_slot(1).background_color,
                        colors.for_slot(4).background_color,
                    )
                    self.assertEqual(
                        colors.for_slot(4).background_color,
                        colors.for_slot(25).background_color,
                    )
                else:
                    self.assertEqual(
                        colors.for_slot(1).background_color,
                        colors.for_slot(9).background_color,
                    )
                    self.assertEqual(
                        colors.for_slot(2).background_color,
                        colors.for_slot(10).background_color,
                    )

    def test_accepts_grouped_metadata_rows_and_legacy_flat_fields(self) -> None:
        for text_settings, expected in (
            (
                {"metadata_rows": [["event", "date"], ["entrants_count"]]},
                (("event", "date"), ("entrants_count",)),
            ),
            (
                {"metadata_fields": ["event", "date"]},
                (("event",), ("date",)),
            ),
        ):
            with self.subTest(text_settings=text_settings), patch(
                "app.render_format_preview",
                return_value=Image.new("RGBA", (16, 16)),
            ) as render_preview:
                response = self.client.post(
                    "/api/format-preview",
                    json={
                        "event_format": "singles",
                        "entrant_count": 3,
                        "text_settings": text_settings,
                    },
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    render_preview.call_args.kwargs["text_settings"].metadata_rows,
                    expected,
                )

    def test_lists_provided_fonts_and_renders_uploaded_font_bytes(self) -> None:
        fonts_response = self.client.get("/api/fonts")
        self.assertEqual(fonts_response.status_code, 200)
        self.assertEqual(
            {item["asset_id"] for item in fonts_response.get_json()["items"]},
            {"tyrowo", "impact", "ubuntu"},
        )
        font_bytes = (Path(__file__).resolve().parents[1] / "fonts" / "Ubuntu-Regular.ttf").read_bytes()
        config = {
            "style": "legacy",
            "event_format": "singles",
            "entrant_count": 3,
            "transparent": True,
            "header_layout": {
                "top_left": "metadata",
                "top_middle": "tournament_logo",
                "top_right": "tournament_title",
            },
            "text_settings": {
                "font_asset_id": "user:test-font",
                "font_size_adjustment": 4,
                "replace_base_urls_with_icons": True,
                "metadata_fields": ["stream_link", "vod_link"],
            },
        }
        preview_response = self.client.post(
            "/api/format-preview",
            data={
                "config": json.dumps(config),
                "font_file": (BytesIO(font_bytes), "custom.ttf"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(preview_response.status_code, 200)
        self.assertTrue(preview_response.data.startswith(b"\x89PNG"))

    def test_passes_completed_tournament_and_entrants_to_preview_renderer(self) -> None:
        with patch("app.render_format_preview", return_value=Image.new("RGBA", (16, 16))) as render_preview:
            response = self.client.post(
                "/api/format-preview",
                json={
                    "style": "legacy",
                    "event_format": "singles",
                    "entrant_count": 3,
                    "transparent": True,
                    "tournament": {
                        "title": "My Local",
                        "subtitle": "Week 12",
                        "event": "Melee Singles",
                        "date": "2026-09-26",
                        "entrants_count": 48,
                        "link": "start.gg/my-local",
                        "location": "Local Venue, Philadelphia, PA",
                        "stream_link": "twitch.tv/my-local",
                    },
                    "entrants": [
                        {
                            "tag": tag,
                            "seed": index,
                            "placement": index,
                            "characters": [{"melee_fighter_name": fighter}],
                        }
                        for index, (tag, fighter) in enumerate(
                            (("Alpha", "Fox"), ("Bravo", "Marth"), ("Charlie", "Falco")),
                            start=1,
                        )
                    ],
                },
            )

        self.assertEqual(response.status_code, 200)
        tournament = render_preview.call_args.kwargs["tournament"]
        entrants = render_preview.call_args.kwargs["entrants"]
        self.assertEqual(tournament.title, "My Local")
        self.assertEqual(tournament.stream_link, "twitch.tv/my-local")
        self.assertEqual(tournament.location, "Local Venue, Philadelphia, PA")
        self.assertEqual([entrant.tag for entrant in entrants], ["Alpha", "Bravo", "Charlie"])

    def test_passes_heading_and_entrant_text_colors_to_preview_renderer(self) -> None:
        with patch("app.render_format_preview", return_value=Image.new("RGBA", (16, 16))) as render_preview:
            response = self.client.post(
                "/api/format-preview",
                json={
                    "style": "legacy",
                    "event_format": "singles",
                    "entrant_count": 3,
                    "text_settings": {"heading_color": "#10203080", "heading_metallic": True},
                    "entrant_text_colors": {
                        "mode": "pick_2",
                        "colors": ["#FF0000FF", "#00FF00AA"],
                        "metallic": [True, False],
                    },
                },
            )

        self.assertEqual(response.status_code, 200)
        settings = render_preview.call_args.kwargs["text_settings"]
        self.assertEqual(settings.heading_color, "#10203080")
        self.assertTrue(settings.heading_metallic)
        self.assertEqual(settings.entrant_text_color_mode, "pick_2")
        self.assertEqual(settings.entrant_text_colors, ("#FF0000FF", "#00FF00AA"))
        self.assertEqual(settings.entrant_text_metallic, (True, False))


if __name__ == "__main__":
    unittest.main()

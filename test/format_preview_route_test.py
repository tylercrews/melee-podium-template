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
        self.assertEqual([entrant.tag for entrant in entrants], ["Alpha", "Bravo", "Charlie"])


if __name__ == "__main__":
    unittest.main()

"""API-boundary checks for customized Format-step previews."""

from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()

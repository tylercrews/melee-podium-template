"""API integration for animated/still downloads and browser-supplied composition."""

from io import BytesIO
import json
import unittest

from PIL import Image

from app import app


class PodiumsClappingRouteTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_default_animated_and_explicit_still_for_both_styles(self):
        for style, width in (("legacy", 1672), ("customizable", 1920)):
            for animated in (None, False):
                payload = {"style": style, "event_format": "singles", "entrant_count": 8,
                           "variant": "four_podium", "transparent": True,
                           "formatting_asset_colors": {"mode": "premade", "preset": "rainbow", "colors": []}}
                if animated is not None:
                    payload["animated"] = animated
                response = self.client.post("/api/format-preview", json=payload)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, "image/gif" if animated is None else "image/png")
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                with Image.open(BytesIO(response.data)) as image:
                    self.assertEqual(image.format, "GIF" if animated is None else "PNG")
                    self.assertEqual(image.size, (width, 941))
                    self.assertEqual(image.n_frames, 42 if animated is None else 1)
                    if animated is None:
                        self.assertEqual(image.info["loop"], 0)

    def test_composited_background_and_logo_remain_in_every_frame(self):
        def image_file(image):
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer
        background = Image.new("RGBA", (1672, 941), "#123456FF")
        overlay = Image.new("RGBA", background.size, "#00000000")
        overlay.paste("#CC6633FF", (150, 25, 170, 45))
        response = self.client.post("/api/format-preview", data={
            "config": json.dumps({"style": "legacy", "event_format": "singles", "entrant_count": 8,
                                  "variant": "four_podium", "animated": True, "transparent": True}),
            "composite_background": (image_file(background), "background.png"),
            "composite_overlay": (image_file(overlay), "overlay.png"),
        })
        self.assertEqual(response.status_code, 200)
        with Image.open(BytesIO(response.data)) as image:
            for index in (0, 18, 41):
                image.seek(index)
                frame = image.convert("RGBA")
                background_pixel = frame.getpixel((10, 900))
                logo_pixel = frame.getpixel((155, 30))
                self.assertEqual(background_pixel[3], 255)
                self.assertEqual(logo_pixel[3], 255)
                self.assertLess(max(abs(a - b) for a, b in zip(background_pixel[:3], (18, 52, 86))), 16)
                self.assertLess(max(abs(a - b) for a, b in zip(logo_pixel[:3], (204, 102, 51))), 32)

    def test_rejects_non_boolean_and_unsupported_animation(self):
        for animated in (None, "false", 1):
            response = self.client.post("/api/format-preview", json={"variant": "four_podium", "animated": animated})
            self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/format-preview", json={"entrant_count": 4, "animated": True})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()

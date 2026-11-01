"""Layered exact previews: header layers change without re-rendering content."""

from __future__ import annotations

import base64
from dataclasses import replace
from io import BytesIO
import random
import unittest

from PIL import Image

from app import app
from creation import TextSettings
from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from format_preview import prepare_format_preview, prepare_format_preview_layers, render_format_preview_header
from geometric_formatting_colors import GeometricFormattingColors
from layout_text_defaults import layout_text_defaults
from models import TournamentFormat
from render_layers import flatten_layers, header_images
from sample_creation_data import sample_tournament


HEADER = {"top_left": "tournament_logo", "top_middle": "tournament_title", "top_right": "metadata"}
COLORS = GeometricFormattingColors.one("#000000FF", "#E53935FF")
CASES = {
    "legacy podium": (PodiumStyle.LEGACY, TournamentFormat.SINGLES, 4, None, CreationMode.PODIUM, {}),
    "customizable doubles": (PodiumStyle.CUSTOMIZABLE, TournamentFormat.DOUBLES, 3, None, CreationMode.PODIUM, {}),
    "podiums+clapping still": (PodiumStyle.LEGACY, TournamentFormat.SINGLES, 8, "four_podium", CreationMode.PODIUM, {"animated": False}),
    "squares": (PodiumStyle.LEGACY, TournamentFormat.SINGLES, 8, None, CreationMode.SQUARES, {"formatting_colors": COLORS}),
    "eyes": (PodiumStyle.LEGACY, TournamentFormat.DOUBLES, 3, None, CreationMode.EYES, {"formatting_colors": COLORS}),
    "radial": (PodiumStyle.LEGACY, TournamentFormat.SINGLES, 8, None, CreationMode.RADIAL, {"formatting_colors": COLORS}),
    "flying v reversed": (PodiumStyle.LEGACY, TournamentFormat.SINGLES, 8, "vertically_reversed", CreationMode.FLYING_V, {}),
}


def _arguments(case: str, *, enlarged: bool = False) -> tuple[tuple, dict]:
    style, event_format, count, variant, mode, extra = CASES[case]
    selection = ModeSelection(mode, ModeOptions(event_format, count, variant,
                                                style if mode is CreationMode.PODIUM else None))
    text_settings = TextSettings(**layout_text_defaults(selection))
    tournament = sample_tournament(event_format)
    if enlarged:
        # Every header-only input the browser refreshes without re-rendering content.
        text_settings = replace(
            text_settings,
            heading_color="#FFD700C0",
            heading_metallic=True,
            title_font_size_adjustment=14,
            subtitle_font_size_adjustment=-6,
            metadata_row_font_size_adjustments=tuple(4 for _row in text_settings.metadata_rows),
        )
        tournament = replace(tournament, title="A Much Longer Tournament Title For Wrapping", subtitle="Grand Finals Weekend")
    return (style, event_format, count, variant), {
        "transparent": True, "header_layout": HEADER, "creation_mode": mode,
        "text_settings": text_settings, "tournament": tournament, **extra,
    }


def _seeded(render, *args, **kwargs):
    # Unposed sample characters pick a random pose; compare like with like.
    random.seed(2026)
    return render(*args, **kwargs)


def _decoded(layer: dict) -> Image.Image | None:
    if layer["image"] is None:
        return None
    return Image.open(BytesIO(base64.b64decode(layer["image"].split(",", 1)[1]))).convert("RGBA")


class PreviewRenderLayerTests(unittest.TestCase):
    def test_header_only_render_matches_the_layered_header(self) -> None:
        for case in CASES:
            with self.subTest(case=case):
                args, kwargs = _arguments(case, enlarged=True)
                layered = header_images(_seeded(prepare_format_preview_layers, *args, **kwargs).layers)
                header_only = _seeded(render_format_preview_header, *args, **kwargs)
                self.assertEqual(len(header_only), len(layered))
                self.assertGreater(len(header_only), 0)
                for expected, actual in zip(layered, header_only, strict=True):
                    self.assertEqual(actual.tobytes(), expected.tobytes())

    def test_header_settings_leave_every_content_layer_unchanged(self) -> None:
        for case in CASES:
            with self.subTest(case=case):
                args, kwargs = _arguments(case)
                default = _seeded(prepare_format_preview_layers, *args, **kwargs).layers
                args, kwargs = _arguments(case, enlarged=True)
                enlarged = _seeded(prepare_format_preview_layers, *args, **kwargs).layers
                self.assertEqual([layer.kind for layer in default], [layer.kind for layer in enlarged])
                for before, after in zip(default, enlarged, strict=True):
                    if before.kind == "content":
                        self.assertEqual(before.image.tobytes(), after.image.tobytes())
                self.assertNotEqual(
                    [image.tobytes() for image in header_images(default)],
                    [image.tobytes() for image in header_images(enlarged)],
                )

    def test_flattened_layers_match_the_complete_render(self) -> None:
        for case in CASES:
            with self.subTest(case=case):
                args, kwargs = _arguments(case, enlarged=True)
                complete = _seeded(prepare_format_preview, *args, **kwargs)
                if not isinstance(complete, Image.Image):
                    complete = complete.frame()
                layers = _seeded(prepare_format_preview_layers, *args, **kwargs).layers
                self.assertEqual(flatten_layers(layers).tobytes(), complete.tobytes())

    def test_podium_subtitle_stays_beneath_the_portraits(self) -> None:
        args, kwargs = _arguments("legacy podium")
        layers = prepare_format_preview_layers(*args, **kwargs).layers
        self.assertEqual([layer.kind for layer in layers], ["content", "header", "content", "header"])


class PreviewRenderLayerRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = app.test_client()

    def _config(self, **overrides) -> dict:
        return {
            "mode": "squares", "event_format": "singles", "entrant_count": 8, "transparent": True,
            "header_layout": HEADER,
            "formatting_asset_colors": {"mode": "premade", "preset": "rainbow", "preset_transparency": 0, "colors": []},
            "text_settings": {"title_font_size_adjustment": 10, "heading_color": "#80C0FFFF"},
            **overrides,
        }

    def test_layers_route_places_cropped_layers_and_header_route_matches(self) -> None:
        layered = _seeded(self.client.post, "/api/format-preview/layers", json=self._config())
        header = _seeded(self.client.post, "/api/format-preview/header", json=self._config())
        self.assertEqual((layered.status_code, header.status_code), (200, 200))
        self.assertEqual(layered.headers["Cache-Control"], "no-store")
        body = layered.get_json()
        self.assertEqual((body["width"], body["height"]), (1920, 1080))
        self.assertEqual([layer["kind"] for layer in body["layers"]], ["content", "header", "content"])
        self.assertEqual(body["logo_index"], 3)
        self.assertIsNone(body["animation"])
        layered_headers = [layer for layer in body["layers"] if layer["kind"] == "header"]
        header_layers = header.get_json()["layers"]
        self.assertEqual(len(header_layers), len(layered_headers))
        for expected, actual in zip(layered_headers, header_layers, strict=True):
            self.assertEqual((actual["left"], actual["top"]), (expected["left"], expected["top"]))
            self.assertEqual(_decoded(actual).tobytes(), _decoded(expected).tobytes())

    def test_animated_layers_include_the_gif_and_draw_the_logo_beneath_the_panels(self) -> None:
        response = self.client.post("/api/format-preview/layers", json={
            "style": "legacy", "event_format": "singles", "entrant_count": 8, "variant": "four_podium",
            "animated": True, "transparent": True, "header_layout": HEADER,
        })
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual([layer["kind"] for layer in body["layers"]], ["content", "header", "content", "header", "content"])
        self.assertEqual(body["logo_index"], 4)
        self.assertTrue(base64.b64decode(body["animation"].split(",", 1)[1]).startswith(b"GIF89a"))

    def test_header_route_rejects_a_non_object_body(self) -> None:
        response = self.client.post("/api/format-preview/header", json=[1, 2])
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()

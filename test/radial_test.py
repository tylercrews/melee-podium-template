"""Radial reference geometry, clipping, serialization, and logo layering."""

from dataclasses import replace
from io import BytesIO
from itertools import permutations
import json
import random
import unittest
from unittest.mock import patch

from PIL import Image

from app import app
from background_builder import BackgroundRequest, PixelRect
from creation import CreationRequest, TextSettings
from creation_modes import CreationMode, ModeOptions, ModeSelection
from DrawPodium import PodiumFont
from DrawRadial import draw_singles_top_8
from geometric_formatting_colors import GeometricFormattingColors
from mode_preferences import FormattingAssetPlacement, ModePreferenceRepository, ModePreferences, PixelPoint
from models import TournamentFormat
from radial_content_renderer import RadialContentRenderer
from radial_geometry import clip_to_section, radial_sections
from radial_palette import radial_palette_color
from podium_colors import PodiumColorSelection
from sample_creation_data import sample_top_8_entrants, sample_tournament


class RadialTests(unittest.TestCase):
    def setUp(self):
        self.selection = ModeSelection(CreationMode.RADIAL, ModeOptions(TournamentFormat.SINGLES, 8))
        self.preferences = ModePreferenceRepository().load(self.selection)
        self.entrants = sample_top_8_entrants(random.Random(4))
        self.request = CreationRequest(self.selection, BackgroundRequest(self.preferences.canvas_size), self.entrants, sample_tournament(TournamentFormat.SINGLES), formatting_colors=GeometricFormattingColors.one("#00000000"), text_settings=TextSettings(include_seeding=False))

    def test_reference_geometry_and_preferences_round_trip(self):
        self.assertTrue(self.preferences.ready)
        self.assertEqual(ModePreferences.from_dict(json.loads(json.dumps(self.preferences.to_dict()))), self.preferences)
        center = (960, 540)
        for section in radial_sections(self.preferences).values():
            self.assertEqual(len(section.polygon), 3)
            self.assertIn(center, [(section.destination.left + p.x, section.destination.top + p.y) for p in section.polygon])
        self.assertFalse(any(p.field == "entrant.placement" for p in self.preferences.text_slots))
        self.assertEqual([p.anchor for p in self.preferences.placement_tags], [PixelPoint(x, y) for x, y in ((210, 48), (1710, 48), (68, 165), (1852, 165), (68, 610), (1852, 610), (200, 1028), (1720, 1028))])
        self.assertEqual([p.asset_id for p in self.preferences.placement_tags], ["01st.png", "02nd.png", "03rd.png", "04th.png", "05th.png", "05th.png", "07th.png", "07th.png"])

    def test_enlarged_numbers_have_a_separate_horizontal_region_from_names(self):
        names = [p for p in self.preferences.text_slots if p.field == "entrant.tag"]
        for slot, (number, name) in enumerate(zip(self.preferences.placement_tags, names), 1):
            self.assertGreaterEqual(number.max_size.height, 80)
            left = name.anchor.x if name.pillow_anchor.startswith("l") else name.anchor.x - name.max_width if name.pillow_anchor.startswith("r") else name.anchor.x - name.max_width / 2
            right = left + name.max_width
            number_left = number.anchor.x - number.max_size.width / 2
            number_right = number.anchor.x + number.max_size.width / 2
            self.assertTrue(number_right + 15 <= left or right + 15 <= number_left, slot)

    def test_radial_primary_background_and_box_border_keep_independent_alpha(self):
        selection = PodiumColorSelection("#12345680", "#010203FF", "#65432140")
        self.assertEqual(radial_palette_color(selection).to_dict(), {"background_color": "#12345680", "trim_color": "#65432140"})

    def test_border_colors_survive_portraits_and_are_composited_only_once(self):
        request = replace(self.request, formatting_colors=GeometricFormattingColors.one("#00000000", "#00FF0080"))
        with patch("radial_content_renderer.render_eye_portrait", side_effect=lambda _character, size, **_settings: Image.new("RGBA", size)):
            image = RadialContentRenderer().draw(Image.new("RGBA", (1920, 1080)), request, self.preferences)
        self.assertEqual(image.getpixel((957, 120)), (0, 255, 0, 128))

    def test_api_maps_radial_custom_background_and_border_colors(self):
        config = {"mode": "radial", "event_format": "singles", "entrant_count": 8, "formatting_asset_colors": {"mode": "pick_1", "preset": None, "colors": [{"main_color": "#11223380", "base_color": "#44556640", "face_color": "#000000FF", "metallic": False}]}}
        with patch("app.render_format_preview", return_value=Image.new("RGBA", (8, 8))) as renderer:
            response = app.test_client().post("/api/format-preview", json=config)
        self.assertEqual(response.status_code, 200)
        color = renderer.call_args.kwargs["formatting_colors"].for_slot(8)
        self.assertEqual(color.background_color, "#11223380")
        self.assertEqual(color.trim_color, "#44556640")

    def test_renders_canonical_tied_placement_art_above_an_overlapping_logo(self):
        with patch("formatting_assets.LocalPlacementTagAssets.open", autospec=True, side_effect=lambda _provider, _asset_id: Image.new("RGBA", (14, 14), "#00CCCCFF")) as assets:
            image = RadialContentRenderer(tournament_logo=Image.new("RGBA", (200, 200), "#FF0000FF"), logo_scale=10).draw(Image.new("RGBA", (1920, 1080)), self.request, self.preferences)
        self.assertEqual([call.args[1] for call in assets.call_args_list], ["01st.png", "02nd.png", "03rd.png", "04th.png", "05th.png", "05th.png", "07th.png", "07th.png"])
        for placement in self.preferences.placement_tags:
            self.assertEqual(image.getpixel((placement.anchor.x, placement.anchor.y)), (0, 204, 204, 255))

    def test_polygon_clipping_preserves_existing_alpha_and_rejects_bad_bounds(self):
        section = FormattingAssetPlacement("slice_1", "radial_slice", PixelRect(0, 0, 20, 20), polygon=(PixelPoint(0, 0), PixelPoint(20, 0), PixelPoint(0, 20)))
        result = clip_to_section(Image.new("RGBA", (20, 20), "#FF000080"), section)
        self.assertEqual(result.getpixel((3, 3)), (255, 0, 0, 128))
        self.assertEqual(result.getpixel((18, 18))[3], 0)
        self.assertTrue(any(0 < a < 128 for a in result.getchannel("A").getdata()))
        with self.assertRaisesRegex(ValueError, "dimensions"):
            clip_to_section(Image.new("RGBA", (21, 20)), section)
        with self.assertRaisesRegex(ValueError, "within"):
            replace(section, polygon=(PixelPoint(0, 0), PixelPoint(21, 0), PixelPoint(0, 20)))
        with self.assertRaisesRegex(ValueError, "nonzero"):
            replace(section, polygon=(PixelPoint(0, 0), PixelPoint(2, 2), PixelPoint(4, 4)))

    def test_each_portrait_is_confined_to_its_own_slice_and_uses_doubles_zoom(self):
        colors = ("#FF0000FF", "#00FF00FF", "#0000FFFF", "#FFFF00FF", "#FF00FFFF", "#00FFFFFF", "#777777FF", "#333333FF")
        def portrait(character, size, **kwargs):
            return Image.new("RGBA", size, colors[self.entrants.index(next(e for e in self.entrants if e.characters[0] is character))])
        with patch("radial_content_renderer.render_eye_portrait", side_effect=portrait) as renderer:
            image = RadialContentRenderer().draw(Image.new("RGBA", (1920, 1080)), self.request, replace(self.preferences, text_slots=()))
        for index, placement in enumerate(self.preferences.character_slots):
            self.assertEqual(image.getpixel((placement.anchor.x, placement.anchor.y)), Image.new("RGBA", (1, 1), colors[index]).getpixel((0, 0)))
        self.assertTrue(all(call.kwargs["doubles"] for call in renderer.call_args_list))
        self.assertEqual(image.getpixel((960, 100)), (255, 255, 255, 255))

    def test_header_text_is_above_logo_in_every_assignment(self):
        renderer = RadialContentRenderer(font=PodiumFont.UBUNTU)
        logo_renderer = replace(renderer, tournament_logo=Image.new("RGBA", (200, 200), "#FF0000FF"), logo_scale=5)
        for items in permutations(("tournament_logo", "tournament_title", "metadata")):
            request = replace(self.request, header_layout=dict(zip(("top_left", "top_middle", "top_right"), items)))
            bare = Image.new("RGBA", (1920, 1080))
            with_logo = bare.copy()
            renderer._draw_header(bare, request, self.preferences)
            logo_renderer._draw_header(with_logo, request, self.preferences)
            white_pixels = [i for i, pixel in enumerate(bare.getdata()) if pixel == (255, 255, 255, 255)]
            actual = list(with_logo.getdata())
            self.assertGreater(len(white_pixels), 500)
            self.assertTrue(all(actual[i] == (255, 255, 255, 255) for i in white_pixels))

    def test_public_renderer_preserves_canvas_and_validates_selection(self):
        image = draw_singles_top_8(self.entrants, tournament=self.request.tournament)
        self.assertEqual((image.mode, image.size), ("RGBA", (1920, 1080)))
        for options in (ModeOptions(TournamentFormat.DOUBLES, 8), ModeOptions(TournamentFormat.SINGLES, 4), ModeOptions(TournamentFormat.SINGLES, 8, "four_podium")):
            with self.assertRaisesRegex(ValueError, "Singles Top 8"):
                ModeSelection(CreationMode.RADIAL, options)

    def test_exact_route_accepts_and_validates_logo_upload_and_scale(self):
        config = {"mode": "radial", "event_format": "singles", "entrant_count": 8, "transparent": True, "logo_size": 2, "formatting_asset_colors": {"mode": "premade", "preset": "rainbow", "colors": []}}
        upload = BytesIO()
        Image.new("RGBA", (80, 80), "#FF0000FF").save(upload, format="PNG")
        response = app.test_client().post("/api/format-preview", data={"config": json.dumps(config), "logo_file": (BytesIO(upload.getvalue()), "logo.png")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        with Image.open(BytesIO(response.data)) as image:
            self.assertEqual(image.size, (1920, 1080))
        invalid = app.test_client().post("/api/format-preview", data={"config": json.dumps(config), "logo_file": (BytesIO(b"not an image"), "logo.png")})
        self.assertEqual(invalid.status_code, 400)
        for scale in (-1, 101, True, "large"):
            self.assertEqual(app.test_client().post("/api/format-preview", json={**config, "logo_size": scale}).status_code, 400)


if __name__ == "__main__":
    unittest.main()

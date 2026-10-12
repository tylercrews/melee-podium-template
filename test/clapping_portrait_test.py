"""Clapping costume resolution, serialized crops, and clipped image composition."""

from pathlib import Path
import json
import sys
import unittest

from PIL import Image, ImageDraw
from dataclasses import replace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clapping_assets import CLAPPING_FOLDER, load_clapping_frame, resolve_clapping_path
from clapping_frame_compositor import compose_clapping_member_layers
from clapping_portrait_renderer import render_clapping_portrait, render_clapping_portrait_frame
from color_values import parse_rgba_hex
from models import Character, MELEE_FIGHTERS
from portrait_crop_adjustment_for_clapping import (
    CALIBRATION_PATH, ClappingPortraitAdjustment, ClappingPortraitLayer,
    get_clapping_portrait_adjustment,
)


class ClappingPortraitTests(unittest.TestCase):
    def test_every_costume_resolves_to_its_manifest_asset_and_renders(self):
        assets = json.loads((CLAPPING_FOLDER / "manifest.json").read_text())["assets"]
        self.assertEqual(len(assets), 134)
        for asset in assets:
            with self.subTest(fighter=asset["character"], color=asset["color"]):
                character = Character(asset["character"], color=asset["color"], pose="a")
                self.assertEqual(resolve_clapping_path(character), CLAPPING_FOLDER / asset["path"])
                portrait = render_clapping_portrait(character, (64, 96), background_color="#FB8B00FF")
                self.assertEqual(portrait.size, (64, 96))
                self.assertEqual(portrait.mode, "RGBA")

    def test_costume_codes_and_static_poses_do_not_change_animation_selection(self):
        selected = resolve_clapping_path(Character("Fox", color="blue", pose="a"))
        for color in ("03", "03_blue"):
            self.assertEqual(resolve_clapping_path(Character("Fox", color=color, pose="f")), selected)
        with self.assertRaises(ValueError):
            resolve_clapping_path(Character("Fox", color="purple"))

    def test_all_characters_have_round_trippable_fixed_windows(self):
        profiles = json.loads(CALIBRATION_PATH.read_text())["characters"]
        self.assertEqual(set(profiles), set(MELEE_FIGHTERS))
        for fighter in MELEE_FIGHTERS:
            crop = get_clapping_portrait_adjustment(fighter)
            restored = ClappingPortraitAdjustment.from_dict(json.loads(json.dumps(crop.to_dict())))
            self.assertEqual(crop, restored)

    def test_invalid_crops_are_rejected(self):
        for size, crop in [((0, 512), (0, 0, 20, 30)), ((512, 512), (20, 0, 0, 30)),
                           ((512, 512), (0, 0, float("nan"), 30)), ((True, 512), (0, 0, 20, 30))]:
            with self.subTest(size=size, crop=crop), self.assertRaises(ValueError):
                ClappingPortraitAdjustment(size, crop)

    def test_background_alpha_and_border_are_independent(self):
        image = render_clapping_portrait_frame(
            Image.new("RGBA", (32, 32), "#00000000"),
            ClappingPortraitAdjustment((32, 32), (0, 0, 32, 32)),
            (40, 40), background_color="#00CDC380", border_color="#FF000040",
        )
        self.assertEqual(image.getpixel((20, 20)), parse_rgba_hex("#00CDC380"))
        self.assertEqual(image.getpixel((0, 0)), parse_rgba_hex("#FF000040"))

    def test_out_of_source_window_stays_background_and_content_cannot_cover_border(self):
        image = render_clapping_portrait_frame(
            Image.new("RGBA", (20, 20), "#FF0000FF"),
            ClappingPortraitAdjustment((20, 20), (-10, -10, 30, 30)),
            (52, 52), background_color="#00FF00FF", border_color="#0000FFFF",
        )
        self.assertEqual(image.getpixel((6, 6)), parse_rgba_hex("#00FF00FF"))
        self.assertEqual(image.getpixel((26, 26)), parse_rgba_hex("#FF0000FF"))
        self.assertEqual(image.getpixel((0, 26)), parse_rgba_hex("#0000FFFF"))

    def test_square_window_keeps_vertical_zoom_and_mirroring(self):
        source = Image.new("RGBA", (80, 80), "#00000000")
        ImageDraw.Draw(source).rectangle((29, 20, 32, 59), fill="#FF0000FF")
        crop = ClappingPortraitAdjustment((80, 80), (20, 10, 60, 70))
        tall = render_clapping_portrait_frame(source, crop, (40, 60), background_color="#00000000", border_width=0)
        square = render_clapping_portrait_frame(source, crop, (60, 60), background_color="#00000000", border_width=0)
        self.assertEqual(tall.getbbox()[1::2], square.getbbox()[1::2])
        self.assertEqual(tall.getbbox()[2] - tall.getbbox()[0], square.getbbox()[2] - square.getbbox()[0])
        mirrored = render_clapping_portrait_frame(source, crop, (60, 60), background_color="#00000000", border_width=0, mirror_horizontally=True)
        self.assertEqual(mirrored.tobytes(), square.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes())

    def test_crop_does_not_follow_animation_bounds(self):
        a = Image.new("RGBA", (80, 80), "#00000000")
        b = a.copy()
        ImageDraw.Draw(a).rectangle((35, 20, 44, 49), fill="#FF0000FF")
        ImageDraw.Draw(b).rectangle((35, 25, 44, 54), fill="#FF0000FF")
        crop = ClappingPortraitAdjustment((80, 80), (20, 10, 60, 70))
        renders = [render_clapping_portrait_frame(im, crop, (40, 60), background_color="#00000000", border_width=0) for im in (a, b)]
        self.assertEqual(renders[1].getbbox()[1] - renders[0].getbbox()[1], 5)

    def test_frame_selection_preserves_animation_and_rejects_bad_indices(self):
        a = load_clapping_frame(Character("Donkey Kong"), 0)
        b = load_clapping_frame(Character("Donkey Kong"), 20)
        self.assertNotEqual(a.tobytes(), b.tobytes())
        for index in (-1, True, 999999):
            with self.subTest(index=index), self.assertRaises(ValueError):
                load_clapping_frame(Character("Fox"), index)

    def test_member_layers_preserve_foreground_occlusion_and_scale_offsets(self):
        source = Image.new("RGBA", (20, 20), "#00000000")
        draw = ImageDraw.Draw(source)
        draw.rectangle((2, 2, 7, 12), fill="#FF0000FF")
        draw.rectangle((12, 2, 17, 12), fill="#0000FFFF")
        adjustment = ClappingPortraitAdjustment((20, 20), (0, 0, 20, 20), (
            ClappingPortraitLayer((0, 0, 10, 20), (0, 0), 1),
            ClappingPortraitLayer((10, 0, 20, 20), (-7, -1), 0),
        ))
        result = compose_clapping_member_layers(source, adjustment)
        self.assertEqual(result.getpixel((5, 5)), parse_rgba_hex("#FF0000FF"))
        self.assertEqual(result.getpixel((9, 5)), parse_rgba_hex("#0000FFFF"))
        self.assertEqual(result.getpixel((15, 5)), parse_rgba_hex("#00000000"))
        scaled_source = source.resize((40, 40), Image.Resampling.NEAREST)
        scaled = compose_clapping_member_layers(scaled_source, adjustment)
        self.assertEqual(scaled.tobytes(), result.resize((40, 40), Image.Resampling.NEAREST).tobytes())

    def test_ice_climbers_rear_member_is_visible_in_every_costume(self):
        adjustment = get_clapping_portrait_adjustment("Ice Climbers")
        self.assertEqual(len(adjustment.member_layers), 2)
        original_adjustment = replace(adjustment, member_layers=())
        for color in ("default", "red", "green", "blue", "cyan"):
            with self.subTest(color=color):
                source = load_clapping_frame(Character("Ice Climbers", color=color), 18)
                rear = render_clapping_portrait_frame(source, adjustment, background_color="#666666FF")
                original = render_clapping_portrait_frame(source, original_adjustment, background_color="#666666FF")
                self.assertNotEqual(rear.tobytes(), original.tobytes())

    def test_member_layer_validation(self):
        for crop, offset, order in [((0, 0, 0, 10), (0, 0), 0),
                                    ((0, 0, 10, 10), (float("inf"), 0), 0),
                                    ((0, 0, 10, 10), (0, 0), True)]:
            with self.subTest(crop=crop, offset=offset, order=order), self.assertRaises(ValueError):
                ClappingPortraitLayer(crop, offset, order)
        layer = ClappingPortraitLayer((0, 0, 10, 10), (0, 0), 0)
        with self.assertRaises(ValueError):
            ClappingPortraitAdjustment((20, 20), (0, 0, 20, 20), (layer, layer))

    def test_invalid_output_settings_are_rejected(self):
        source = Image.new("RGBA", (20, 20), "#00000000")
        crop = ClappingPortraitAdjustment((20, 20), (0, 0, 20, 20))
        for settings in [dict(size=(0, 20)), dict(size=(10, 10)), dict(border_width=-1),
                         dict(background_color="#FF0000"), dict(mirror_horizontally=1)]:
            kwargs = dict(background_color="#00000000")
            kwargs.update(settings)
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                render_clapping_portrait_frame(source, crop, **kwargs)


if __name__ == "__main__":
    unittest.main()

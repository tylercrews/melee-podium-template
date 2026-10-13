"""Sandbag selection, asset previews, and singles/doubles API rendering."""

from io import BytesIO
from hashlib import sha256
import json
from pathlib import Path
import unittest

from PIL import Image

from app import app
from clapping_assets import resolve_clapping_path
from DrawPodium import _character_with_team_color
from models import Character
from portrait_assets import load_scaled_portrait, resolve_character_path, with_team_color
from portrait_crop_adjustment_for_clapping import get_clapping_portrait_adjustment


class SandbagEntrantTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_native_art_is_cropped_losslessly_and_keeps_reviewed_render_height(self):
        root = Path(__file__).resolve().parents[1]
        with Image.open(root / "docs/archive/sandbag/sandbag-standing-frame-0001-native-2048-yaw-plus43.png") as source:
            expected = source.convert("RGBA").crop((0, 184, 2048, 1864))
        with Image.open(resolve_character_path(Character("Sandbag"))) as portrait:
            self.assertEqual(portrait.size, expected.size)
            self.assertEqual(portrait.tobytes(), expected.tobytes())
        # Top 4 keeps its reviewed ~264px visible height despite the 4x source.
        scaled = load_scaled_portrait(Character("Sandbag"), 0.26)
        self.assertAlmostEqual(scaled.getbbox()[3] - scaled.getbbox()[1], 264, delta=2)

    def test_standing_gif_manifest_and_all_three_crops_use_native_dimensions(self):
        root = Path(__file__).resolve().parents[1]
        folder = root / "char_assets/animated_renders/clapping"
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        for asset in (row for row in manifest["assets"] if row["character"] == "Sandbag"):
            path = folder / asset["path"]
            self.assertTrue(path.name.endswith("_standing.gif"))
            self.assertEqual(sha256(path.read_bytes()).hexdigest(), asset["sha256"])
            with Image.open(path) as gif:
                self.assertEqual(gif.size, (2048, 1680))
                self.assertEqual(gif.size, (asset["width"], asset["height"]))
                self.assertEqual(gif.n_frames, 1)
                self.assertEqual(gif.info["duration"], 20)
                self.assertEqual(gif.info["loop"], 0)
                self.assertEqual(gif.convert("RGBA").getpixel((0, 0))[3], 0)
        self.assertFalse(list((folder / "Sandbag").glob("*_clapping.gif")))
        for placement in (2, 3, 4):
            self.assertEqual(get_clapping_portrait_adjustment("Sandbag", placement).source_size, (2048, 1680))

    def test_team_costumes_are_exact_copies_with_matching_stock_icons(self):
        default = Character("Sandbag")
        static_bytes = resolve_character_path(default).read_bytes()
        clapping_bytes = resolve_clapping_path(default).read_bytes()
        root = Path(__file__).resolve().parents[1]
        for code, color in (("01", "red"), ("02", "green"), ("03", "blue")):
            with self.subTest(color=color):
                character = Character("Sandbag", color=color)
                self.assertEqual(resolve_character_path(character).read_bytes(), static_bytes)
                self.assertEqual(resolve_clapping_path(character).read_bytes(), clapping_bytes)
                filename = f"{code}_{color}_sandbag_stock.png"
                for folder in ("char_assets/stock_icons/sandbag", "frontend/public/char_assets/stock_icons/sandbag"):
                    self.assertEqual((root / folder / filename).read_bytes(),
                                     (root / folder / "00_default_sandbag_stock.png").read_bytes())

    def test_picker_options_include_standing_sandbag_and_a_served_portrait(self):
        response = self.client.get("/api/options")
        self.assertEqual(response.status_code, 200)
        sandbag = next(row for row in response.get_json()["fighters"] if row["name"] == "Sandbag")
        self.assertEqual([option["color"] for option in sandbag["options"]], ["default", "red", "green", "blue"])
        option = sandbag["options"][0]
        self.assertEqual((option["color"], option["pose"], option["pose_label"]), ("default", "a", "Standing"))
        portrait = self.client.get(f"/char_assets/renders/Sandbag/{option['portrait']}")
        self.assertEqual(portrait.status_code, 200)
        with Image.open(BytesIO(portrait.data)) as image:
            self.assertEqual(image.size, (2048, 1680))
            self.assertEqual(image.mode, "RGBA")
            bounds = image.getchannel("A").getbbox()
            self.assertEqual((bounds[1], bounds[3]), (0, image.height))
        portrait.close()

    def test_doubles_applies_team_colors_without_losing_sandbags_other_settings(self):
        sandbag = Character("Sandbag", mirror_horizontally=True)
        for override in (with_team_color, _character_with_team_color):
            self.assertIs(override(sandbag, None), sandbag)
            for color in ("red", "green", "blue"):
                selected = override(sandbag, color)
                self.assertEqual(selected.color, color)
                self.assertTrue(selected.mirror_horizontally)
            self.assertEqual(override(Character("Fox"), "red").color, "red")

    def test_selected_sandbag_renders_in_every_mode_for_singles_and_doubles(self):
        member = {"tag": "Sandbag player", "characters": [
            {"melee_fighter_name": "Sandbag", "color": "default", "pose": "a"},
        ]}
        for mode in ("podium", "eyes", "squares", "radial"):
            for event_format in ("singles", "doubles"):
                with self.subTest(mode=mode, event_format=event_format):
                    count = 4 if event_format == "doubles" or mode == "podium" else 8
                    placements = [1, 2, 3, 4] if count == 4 else [1, 2, 3, 4, 5, 5, 7, 7]
                    if event_format == "singles":
                        entrants = [{**member, "placement": rank} for rank in placements]
                    else:
                        entrants = [{"team_name": f"Sandbag team {rank}", "placement": rank,
                            "team_color": ["red", "green", "blue", "red"][rank - 1], "entrant_1": member, "entrant_2": member}
                            for rank in placements]
                    response = self.client.post("/api/format-preview", json={
                        "mode": mode, "style": "legacy", "event_format": event_format,
                        "entrant_count": count, "font": "ubuntu", "transparent": True,
                        "entrants": entrants,
                        "formatting_asset_colors": {"mode": "premade", "preset": "rainbow", "colors": []},
                    })
                    self.assertEqual(response.status_code, 200, response.data[:500])
                    self.assertEqual(response.mimetype, "image/png")
                    with Image.open(BytesIO(response.data)) as image:
                        self.assertIsNotNone(image.getbbox())


if __name__ == "__main__":
    unittest.main()

"""Matched entrant text colors that seed explicit Pick 1/2/all selections."""

from __future__ import annotations

import unittest

from app import app
from clapping_colors import TOP16_PLAYER_COLOR_SLOTS
from color_values import format_rgba_hex
from constants import PODIUM_BOX_COLORS_BY_SLOT


SMASH_PLAYER_COLORS = [format_rgba_hex(*box.exterior_line, 255) for box in PODIUM_BOX_COLORS_BY_SLOT]


def _premade(preset: str, **transparency: int) -> dict:
    return {"mode": "premade", "preset": preset, "colors": [],
            "preset_transparency": {"main_color": 0, "face_color": 0, "base_color": 0, **transparency}}


class MatchedEntrantTextColorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = app.test_client()

    def matched(self, **payload) -> dict:
        response = self.client.post("/api/entrant-text-colors/matched", json=payload)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        return response.get_json()

    def test_customizable_podiums_return_their_colors_and_metallic_finishes(self) -> None:
        medals = self.matched(mode="podium", style="customizable", event_format="singles", entrant_count=3,
                              formatting_asset_colors=_premade("olympic_medals"))
        self.assertEqual(medals, {"colors": ["#D4AF37FF", "#BEC6D2FF", "#B87333FF"], "metallic": [True, True, True]})
        translucent = self.matched(mode="podium", style="customizable", event_format="doubles", entrant_count=4,
                                   formatting_asset_colors=_premade("smash_player_colors", main_color=50))
        self.assertEqual(translucent["colors"], [f"{color[:7]}80" for color in SMASH_PLAYER_COLORS[:4]])
        picked = [{"main_color": color, "face_color": "#000000FF", "base_color": "#000000FF", "metallic": index == 1}
                  for index, color in enumerate(("#123456FF", "#ABCDEFFF", "#FEDCBAFF"))]
        custom = self.matched(mode="podium", style="customizable", event_format="singles", entrant_count=3,
                              formatting_asset_colors={"mode": "pick_all", "preset": None, "colors": picked})
        self.assertEqual(custom, {"colors": ["#123456FF", "#ABCDEFFF", "#FEDCBAFF"], "metallic": [False, True, False]})

    def test_layout_specific_slots_follow_the_renderer(self) -> None:
        top16 = self.matched(mode="podium", style="customizable", event_format="singles", entrant_count=16,
                             variant="clapping", formatting_asset_colors=_premade("smash_player_colors"))
        self.assertEqual(top16["colors"], [SMASH_PLAYER_COLORS[slot - 1] for slot in TOP16_PLAYER_COLOR_SLOTS])
        lower = self.matched(mode="podium", style="customizable", event_format="singles", entrant_count=8,
                             variant="four_podium", formatting_asset_colors=_premade("rainbow"))
        self.assertEqual(lower["colors"][4:], lower["colors"][:4])
        legacy = self.matched(mode="podium", style="legacy", event_format="singles", entrant_count=16, variant="clapping")
        self.assertEqual(legacy["colors"], SMASH_PLAYER_COLORS + SMASH_PLAYER_COLORS[::-1])
        self.assertEqual(legacy["metallic"], [False] * 16)

    def test_other_modes_return_their_placement_text_colors(self) -> None:
        eyes = self.matched(mode="eyes", event_format="singles", entrant_count=8, formatting_asset_colors=_premade("rainbow"))
        self.assertEqual(eyes, {"colors": ["#FFFFFFFF"] * 8, "metallic": [False] * 8})
        flying_v = self.matched(mode="flying_v", event_format="singles", entrant_count=8)
        self.assertEqual(flying_v["colors"], SMASH_PLAYER_COLORS)

    def test_unsupported_layouts_are_rejected(self) -> None:
        response = self.client.post("/api/entrant-text-colors/matched", json={"mode": "squares", "event_format": "singles", "entrant_count": 5,
                                                                              "formatting_asset_colors": _premade("rainbow")})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()

"""Radial team grouping, fixed portrait anchors, and merged border behavior."""

from dataclasses import replace
from io import BytesIO
import json
import random
import unittest
from unittest.mock import patch

from PIL import Image

from app import app
from background_builder import BackgroundRequest
from creation import CreationRequest
from creation_modes import CreationMode, ModeOptions, ModeSelection
from DrawRadial import draw_doubles_top_4
from formatting_assets import FormattingAssetRenderer
from geometric_formatting_colors import GeometricFormattingColor, GeometricFormattingColors
from mode_preferences import ModePreferenceRepository, ModePreferences, PixelPoint
from models import TournamentFormat
from radial_content_renderer import RadialContentRenderer
from radial_geometry import radial_sections
from sample_creation_data import sample_top_4_teams, sample_tournament


class RadialDoublesTests(unittest.TestCase):
    def setUp(self):
        self.repository = ModePreferenceRepository()
        self.selection = ModeSelection(CreationMode.RADIAL, ModeOptions(TournamentFormat.DOUBLES, 4))
        self.preferences = self.repository.load(self.selection)
        self.teams = sample_top_4_teams(random.Random(4))
        self.colors = GeometricFormattingColors(tuple(GeometricFormattingColor(color, "#FFFFFFFF") for color in ("#FF0000FF", "#0000FFFF", "#FFFF00FF", "#00FF00FF")))
        self.request = CreationRequest(self.selection, BackgroundRequest(self.preferences.canvas_size), self.teams, sample_tournament(TournamentFormat.DOUBLES), formatting_colors=self.colors)

    def test_serialized_team_mapping_keeps_all_eight_singles_portrait_positions(self):
        self.assertTrue(self.preferences.ready)
        self.assertEqual(ModePreferences.from_dict(json.loads(json.dumps(self.preferences.to_dict()))), self.preferences)
        singles = self.repository.load(ModeSelection(CreationMode.RADIAL, ModeOptions(TournamentFormat.SINGLES, 8)))
        by_id = {p.slot_id: p for p in self.preferences.character_slots}
        expected = ((1, 1), (1, 2), (2, 1), (3, 1), (2, 2), (3, 2), (4, 1), (4, 2))
        for old, (team, member) in zip(singles.character_slots, expected):
            current = by_id[old.slot_id]
            self.assertEqual((current.anchor, current.scale), (old.anchor, old.scale))
            self.assertEqual((current.entrant_slot, current.member_slot), (team, member))
        self.assertEqual(len(radial_sections(self.preferences)), 4)
        self.assertEqual(len([p for p in self.preferences.formatting_assets if p.asset_id == "radial_portrait_slice"]), 8)
        self.assertEqual([p.asset_id for p in self.preferences.placement_tags], ["01st.png", "02nd.png", "03rd.png", "04th.png"])

    def test_team_names_are_top_left_middle_right_middle_and_bottom(self):
        names = [p for p in self.preferences.text_slots if p.field == "entrant.team_name"]
        self.assertEqual([(p.entrant_slot, p.anchor, p.pillow_anchor) for p in names], [(1, PixelPoint(960, 18), "ma"), (2, PixelPoint(30, 510), "la"), (3, PixelPoint(1890, 510), "ra"), (4, PixelPoint(960, 1054), "ms")])
        identities = [p for p in self.preferences.text_slots if p.field == "member.tag"]
        self.assertEqual(len(identities), 8)
        for team in range(1, 5):
            self.assertEqual({p.member_slot for p in identities if p.entrant_slot == team}, {1, 2})

    def test_member_names_mirror_and_seeds_use_the_outer_placement_corners(self):
        names = {(p.entrant_slot, p.member_slot): p for p in self.preferences.text_slots if p.field == "member.tag"}
        for member in (1, 2):
            top, bottom = names[(1, member)], names[(4, member)]
            self.assertEqual(top.anchor.x, bottom.anchor.x)
            self.assertEqual(top.anchor.y + bottom.anchor.y, 1080)
        for team in (2, 3):
            top, bottom = names[(team, 1)], names[(team, 2)]
            self.assertEqual(top.anchor.x, bottom.anchor.x)
            self.assertEqual(top.anchor.y + bottom.anchor.y, 1080)
        seeds = [p for p in self.preferences.text_slots if p.field == "entrant.seed"]
        for number, seed in zip(self.preferences.placement_tags, seeds):
            corner = (1920, 0) if number.anchor.x > 960 else (0, 1080) if number.anchor.y > 540 else (0, 0)
            distance = lambda point: (point.x - corner[0]) ** 2 + (point.y - corner[1]) ** 2
            self.assertLess(distance(seed.anchor), distance(number.anchor))

    def test_internal_teammate_seams_have_no_border_and_share_one_palette(self):
        preferences = replace(self.preferences, text_slots=(), placement_tags=())
        formatted = FormattingAssetRenderer().draw(Image.new("RGBA", (1920, 1080)), preferences, self.colors)
        with patch("radial_content_renderer.render_eye_portrait", side_effect=lambda _character, size, **_settings: Image.new("RGBA", size)):
            image = RadialContentRenderer().draw(formatted, self.request, preferences)
        for point, color in (((960, 100), (255, 0, 0, 255)), ((50, 540), (0, 0, 255, 255)), ((1870, 540), (255, 255, 0, 255)), ((960, 1020), (0, 255, 0, 255))):
            self.assertEqual(image.getpixel(point), color)

    def test_both_members_are_rendered_with_doubles_profiles_and_their_original_foci(self):
        with patch("radial_content_renderer.render_eye_portrait", side_effect=lambda _character, size, **_settings: Image.new("RGBA", size)) as portraits:
            RadialContentRenderer().draw(Image.new("RGBA", (1920, 1080)), self.request, self.preferences)
        self.assertEqual(len(portraits.call_args_list), 8)
        clips = {p.slot_id: p for p in self.preferences.formatting_assets if p.asset_id == "radial_portrait_slice"}
        for placement, call in zip(sorted(self.preferences.character_slots, key=lambda p: (p.z_index, p.slot_id)), portraits.call_args_list):
            team = self.teams[placement.entrant_slot - 1]
            member = team.entrant_1 if placement.member_slot == 1 else team.entrant_2
            self.assertEqual(call.args[0].melee_fighter_name, member.characters[0].melee_fighter_name)
            self.assertEqual(call.args[0].color, team.team_color)
            self.assertTrue(call.kwargs["doubles"])
            clip = clips[placement.slot_id].destination
            self.assertEqual(call.kwargs["focal_destination"], (placement.anchor.x - clip.left, placement.anchor.y - clip.top))

    def test_public_and_uncached_api_renderers_accept_doubles_top_four(self):
        image = draw_doubles_top_4(self.teams, tournament=self.request.tournament)
        self.assertEqual((image.mode, image.size), ("RGBA", (1920, 1080)))
        response = app.test_client().post("/api/format-preview", json={"mode": "radial", "event_format": "doubles", "entrant_count": 4, "transparent": True, "formatting_asset_colors": {"mode": "premade", "preset": "rainbow", "colors": []}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        with Image.open(BytesIO(response.data)) as rendered:
            self.assertEqual(rendered.size, (1920, 1080))


if __name__ == "__main__":
    unittest.main()

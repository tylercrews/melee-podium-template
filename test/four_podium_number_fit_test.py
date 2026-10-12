"""Front-panel number fitting, crest overhang, and preference serialization."""

from pathlib import Path
import sys
import unittest
from dataclasses import replace

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "test/podium_layout_previews"))

from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from mode_preferences import ModePreferenceRepository, PlacementTagPlacement
from models import TournamentFormat
from preview_layers import render_podium_layer
from formatting_assets import draw_placement_tags
from fit_four_podium_numbers import fit_tags


class FourPodiumNumberFitTests(unittest.TestCase):
    def setUp(self):
        self.selection = ModeSelection(CreationMode.PODIUM, ModeOptions(
            event_format=TournamentFormat.SINGLES, entrant_count=8,
            variant="four_podium", podium_style=PodiumStyle.CUSTOMIZABLE,
        ))
        self.preferences = ModePreferenceRepository().load(self.selection)

    def test_number_edges_fit_inside_the_thick_outer_front_outline(self):
        tags, measured = fit_tags(self.preferences)
        expected_spans = [(681, 789), (724, 796), (755, 799), (784, 807)]
        for tag, expected in zip(tags, expected_spans):
            row = measured[tag.slot_id]
            self.assertEqual((row['front_panel_top'], row['front_panel_bottom']), expected)
            self.assertGreaterEqual(row['numeral_top'], expected[0])
            self.assertEqual(row['numeral_bottom'], expected[1])

    def test_crest_ribbon_hangs_below_podium_without_scaling_to_full_crest_height(self):
        tags, measured = fit_tags(self.preferences)
        first = measured[tags[0].slot_id]
        self.assertGreater(first['artwork_bottom'], self.preferences.formatting_assets[0].destination.bottom)
        self.assertEqual(first['numeral_bottom'], first['front_panel_bottom'])

    def test_saved_placements_match_fit_and_round_trip(self):
        tags, _ = fit_tags(self.preferences)
        self.assertEqual(tags, self.preferences.placement_tags)
        for tag in tags:
            self.assertEqual(PlacementTagPlacement.from_dict(tag.to_dict()), tag)
        self.assertFalse(self.preferences.ready)

    def test_browser_preview_guide_does_not_cover_the_hanging_ribbon(self):
        layer = render_podium_layer(PodiumStyle.CUSTOMIZABLE, "top_8_four_podiums", "smash_player_colors")
        crest = Image.new('RGBA', layer.size, '#00000000')
        draw_placement_tags(crest, replace(self.preferences, placement_tags=self.preferences.placement_tags[:1]))
        visible_bow_pixels = 0
        for y in range(self.preferences.formatting_assets[0].destination.bottom, 860):
            for x in range(150, 330):
                red, green, blue, alpha = crest.getpixel((x, y))
                if alpha == 255 and red > green * 2 and red > blue * 2:
                    visible_bow_pixels += 1
                    self.assertEqual(layer.getpixel((x, y)), crest.getpixel((x, y)))
        self.assertGreater(visible_bow_pixels, 0)


if __name__ == '__main__':
    unittest.main()

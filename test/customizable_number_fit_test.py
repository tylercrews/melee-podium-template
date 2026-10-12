"""All-layout fitting, semantic body mapping, raster bounds, and omitted ranks."""

from pathlib import Path
import sys
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'test/podium_layout_previews'))

from mode_preferences import ModePreferences, PlacementTagPlacement
from fit_customizable_podium_numbers import PREFERENCE_ROOT, fit_tags

import json


class CustomizableNumberFitTests(unittest.TestCase):
    def test_all_six_layouts_are_fitted_and_existing_number_choices_preserved(self):
        expected_counts = {'singles_top_3': 3, 'doubles_top_3': 3,
                           'singles_top_4': 4, 'doubles_top_4': 4,
                           'singles_top_8': 3, 'singles_top_8_four_podium': 4}
        paths = list(PREFERENCE_ROOT.glob('*.json'))
        self.assertEqual(len(paths), 6)
        for path in paths:
            with self.subTest(layout=path.stem):
                preferences = ModePreferences.from_dict(json.loads(path.read_text()))
                fitted, measurements = fit_tags(preferences)
                self.assertEqual(len(fitted), expected_counts[path.stem])
                self.assertEqual(fitted, preferences.placement_tags)
                self.assertEqual([tag.asset_id for tag in fitted],
                                 ['01st.png', '02nd.png', '03rd.png'] + (['04th.png'] if len(fitted) == 4 else []))
                for tag in fitted:
                    self.assertEqual(tag, PlacementTagPlacement.from_dict(tag.to_dict()))
                    bounds = measurements[tag.slot_id]
                    self.assertGreaterEqual(bounds['numeral_top'], bounds['front_panel_top'])
                    self.assertEqual(bounds['numeral_bottom'], bounds['front_panel_bottom'])
                    if tag.asset_id == '01st.png':
                        continue
                    with Image.open(ROOT / 'formatting_assets/placement_numbers' / tag.asset_id) as image:
                        image.thumbnail(tag.max_size.as_tuple(), Image.Resampling.LANCZOS)
                        visible = image.getchannel('A').getbbox()
                        top = tag.anchor.y - image.height // 2
                        self.assertGreaterEqual(top + visible[1], bounds['front_panel_top'])
                        self.assertLessEqual(top + visible[3], bounds['front_panel_bottom'])
                        self.assertGreaterEqual(image.height, bounds['front_panel_bottom'] - bounds['front_panel_top'] - 1)

    def test_centered_top_three_maps_numbers_by_slot_not_left_to_right_body_order(self):
        preferences = ModePreferences.from_dict(json.loads((PREFERENCE_ROOT / 'singles_top_3.json').read_text()))
        _, measured = fit_tags(preferences)
        self.assertEqual(measured['podium_1_placement_tag']['front_panel_top'], 635)
        self.assertEqual(measured['podium_2_placement_tag']['front_panel_top'], 672)
        self.assertEqual(measured['podium_3_placement_tag']['front_panel_top'], 719)

    def test_all_first_place_ribbons_extend_below_their_own_podium(self):
        for path in PREFERENCE_ROOT.glob('*.json'):
            with self.subTest(layout=path.stem):
                preferences = ModePreferences.from_dict(json.loads(path.read_text()))
                _, measured = fit_tags(preferences)
                body = next(body for body in preferences.formatting_assets if body.slot_id == 'podium_1')
                self.assertGreater(measured['podium_1_placement_tag']['artwork_bottom'], body.destination.bottom)


if __name__ == '__main__':
    unittest.main()

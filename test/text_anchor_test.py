"""Single-line seed anchors remain supported in ordinary and metallic text."""

import unittest
from PIL import Image, ImageDraw

from DrawPodium import PodiumFont, _draw_text


class TextAnchorTests(unittest.TestCase):
    def test_bottom_anchored_single_line_seed_draws_without_multiline_anchor_error(self):
        for metallic in (False, True):
            with self.subTest(metallic=metallic):
                image = Image.new('RGBA', (150, 80), '#00000000')
                _draw_text(ImageDraw.Draw(image), (20, 60), '[8s]', anchor='lb',
                           max_width=120, preferred_size=20, font=PodiumFont.UBUNTU,
                           fill='#FFFFFFFF', metallic=metallic)
                bounds = image.getbbox()
                self.assertIsNotNone(bounds)
                self.assertLess(bounds[1], 60)
                self.assertLessEqual(bounds[3], 62)


if __name__ == '__main__':
    unittest.main()

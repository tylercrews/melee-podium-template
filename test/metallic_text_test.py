"""Tests for the optional directional metallic finish on rendered text."""

from pathlib import Path
import sys
import unittest

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import PodiumFont, _draw_text


class MetallicTextTests(unittest.TestCase):
    def test_metallic_text_adds_a_highlight_inside_the_glyphs(self) -> None:
        flat = Image.new("RGBA", (240, 90))
        metallic = Image.new("RGBA", flat.size)
        arguments = {
            "position": (12, 8),
            "text": "METALLIC",
            "anchor": "la",
            "max_width": 220,
            "preferred_size": 52,
            "font": PodiumFont.IMPACT,
            "fill": "#806020FF",
        }

        _draw_text(ImageDraw.Draw(flat), **arguments)
        _draw_text(ImageDraw.Draw(metallic), **arguments, metallic=True)

        self.assertNotEqual(list(flat.getdata()), list(metallic.getdata()))
        self.assertGreater(
            max(red for red, _green, _blue, alpha in metallic.getdata() if alpha),
            128,
        )


if __name__ == "__main__":
    unittest.main()

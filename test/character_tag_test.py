"""Regression tests for entrant tag rendering."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import (
    CharacterTag,
    PodiumFont,
    _character_tag_bounds,
    _draw_character_tag,
)


class StubFont:
    def getbbox(self, text: str) -> tuple[int, int, int, int]:
        return (0, 0, len(text) * 10, 20)


class RecordingDraw:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def multiline_textbbox(self, position, text, **kwargs):
        self.texts.append(text)
        return (position[0], position[1], position[0] + len(text) * 10, position[1] + 20)


class CharacterTagTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tag = CharacterTag(
            position=(100, 200),
            text="Sponsor | Player",
            glow_fill=(255, 255, 255),
            max_width=300,
        )

    @patch("DrawPodium._font_to_fit", return_value=StubFont())
    @patch("DrawPodium._draw_text")
    def test_sponsor_line_does_not_include_separator(self, draw_text, _font_to_fit) -> None:
        _draw_character_tag(RecordingDraw(), self.tag, PodiumFont.IMPACT)

        rendered_text = [call.args[2] for call in draw_text.call_args_list]
        self.assertEqual(rendered_text, ["Player", "Sponsor"])

    @patch("DrawPodium._font_to_fit", return_value=StubFont())
    def test_sponsor_bounds_do_not_measure_separator(self, _font_to_fit) -> None:
        draw = RecordingDraw()

        _character_tag_bounds(draw, self.tag, PodiumFont.IMPACT)

        self.assertEqual(draw.texts, ["Player", "Sponsor"])


if __name__ == "__main__":
    unittest.main()

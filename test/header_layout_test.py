"""Regression tests for tournament header collision handling."""

from pathlib import Path
import sys
import unittest

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import PodiumFont, _centered_header_fields, _wrap_url
from models import Tournament


class HeaderLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.canvas = Image.new("RGBA", (1672, 941))

    def test_short_title_and_subtitle_are_centered(self) -> None:
        tournament = Tournament(
            title="Melee Weekly",
            subtitle="Top 8",
            date="August 6, 2026",
            entrants_count=64,
            link="https://start.gg/test",
        )

        self.assertEqual(
            _centered_header_fields(
                self.canvas,
                tournament,
                font=PodiumFont.IMPACT,
                is_doubles=False,
            ),
            (True, True),
        )

    def test_long_title_and_subtitle_remain_side_aligned(self) -> None:
        tournament = Tournament(
            title="Very Very Long Podium Rendering Test",
            subtitle="Very Very Very Long Subtitle Rendering Test",
            date="July 12, 2026",
            entrants_count=64,
            link=(
                "https://www.start.gg/tournament/moon-dog-melee-11-"
                "med1cinal-s-birthday-bash/events/melee-singles-secondaries-"
                "only/brackets/2343959/3386903/overview"
            ),
        )

        self.assertEqual(
            _centered_header_fields(
                self.canvas,
                tournament,
                font=PodiumFont.IMPACT,
                is_doubles=False,
            ),
            (False, False),
        )

    def test_url_prefers_a_slash_break_just_past_its_target_width(self) -> None:
        url = "start.gg/tournament/moon-dog-melee/events/melee-singles"
        target_width = 100
        max_width = 300
        wrapped = _wrap_url(url, target_width, max_width, 14, PodiumFont.IMPACT)

        self.assertEqual(wrapped.splitlines()[0], "start.gg/tournament/")

    def test_url_never_exceeds_its_safe_width(self) -> None:
        url = "start.gg/tournament/moon-dog-melee/events/melee-singles"
        wrapped = _wrap_url(url, 100, 300, 14, PodiumFont.IMPACT)
        from DrawPodium import _font_settings
        from PIL import ImageFont

        font_path, _ = _font_settings(PodiumFont.IMPACT)
        loaded_font = ImageFont.truetype(font_path, 22)
        self.assertTrue(
            all(loaded_font.getlength(line) <= 300 for line in wrapped.splitlines())
        )


if __name__ == "__main__":
    unittest.main()

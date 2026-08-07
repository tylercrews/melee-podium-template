"""Regression tests for tournament header collision handling."""

from pathlib import Path
import sys
import unittest

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import PodiumFont, _centered_header_fields
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


if __name__ == "__main__":
    unittest.main()

"""Regression tests for adaptive attribution placement."""

from pathlib import Path
import sys
import unittest

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import PodiumFont, PodiumMode, _attribution_layout
from models import Character, DoublesTeam, Entrant, SinglesEntrant


class FooterLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.canvas = Image.new("RGBA", (1672, 941))

    @staticmethod
    def doubles_team(placement: int, name: str) -> DoublesTeam:
        def member(tag: str) -> Entrant:
            return Entrant(characters=[Character("Fox")], tag=tag)

        return DoublesTeam(
            placement,
            placement,
            member("Player one"),
            member("Player two"),
            name,
        )

    @staticmethod
    def singles_entrant(index: int, tag: str) -> SinglesEntrant:
        placements = (1, 2, 3, 4, 5, 5, 7, 7)
        return SinglesEntrant(
            characters=[Character("Fox")],
            tag=tag,
            seed=index + 1,
            placement=placements[index],
        )

    def test_attribution_stays_right_when_both_sides_are_clear(self) -> None:
        entrants = [self.doubles_team(index, "Short") for index in range(1, 5)]

        self.assertEqual(
            _attribution_layout(
                self.canvas,
                entrants,
                font=PodiumFont.IMPACT,
                mode=PodiumMode.DOUBLES_TOP_4,
            ),
            ((1662, 911), "ra"),
        )

    def test_attribution_moves_away_from_a_long_right_team_name(self) -> None:
        names = [
            "Short",
            "Short",
            "Short",
            "one two three four five six seven eight nine ten eleven twelve",
        ]
        entrants = [
            self.doubles_team(index, name)
            for index, name in enumerate(names, start=1)
        ]

        self.assertEqual(
            _attribution_layout(
                self.canvas,
                entrants,
                font=PodiumFont.IMPACT,
                mode=PodiumMode.DOUBLES_TOP_4,
            ),
            ((10, 911), "la"),
        )

    def test_attribution_moves_away_from_a_low_right_entrant_tag(self) -> None:
        tags = ["Short"] * 7 + [
            "Very Long Sponsor Name | Very Long Player Tag Here"
        ]
        entrants = [
            self.singles_entrant(index, tag) for index, tag in enumerate(tags)
        ]

        self.assertEqual(
            _attribution_layout(
                self.canvas,
                entrants,
                font=PodiumFont.IMPACT,
                mode=PodiumMode.SINGLES_TOP_8_FOUR_PODIUM,
            ),
            ((10, 911), "la"),
        )


if __name__ == "__main__":
    unittest.main()

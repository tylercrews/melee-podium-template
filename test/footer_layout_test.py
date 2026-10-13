"""Regression tests for adaptive attribution placement."""

from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import PodiumFont, PodiumMode, _attribution_layout
from models import Character, DoublesTeam, Entrant, SinglesEntrant
from footer_attribution import choose_footer_placement
from background_builder import PixelRect
from creation import TextSettings
from podiums_clapping_renderer import ClappingPanel, PodiumsClappingContentRenderer, draw_clapping_attribution


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

    def test_attribution_prefers_left_when_both_sides_are_clear(self) -> None:
        entrants = [self.doubles_team(index, "Short") for index in range(1, 5)]

        self.assertEqual(
            _attribution_layout(
                self.canvas,
                entrants,
                font=PodiumFont.IMPACT,
                mode=PodiumMode.DOUBLES_TOP_4,
            ),
            ((10, 911), "la"),
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

        position, anchor = _attribution_layout(
            self.canvas,
            entrants,
            font=PodiumFont.IMPACT,
            mode=PodiumMode.DOUBLES_TOP_4,
        )
        self.assertEqual(anchor, "la")
        self.assertLess(position[0], self.canvas.width * 3 // 4)

    def test_measured_footer_candidates_choose_left_middle_or_right(self):
        text = (0, 900, 240, 920)
        cases = [([], 10), ([(0, 890, 300, 935)], 380),
                 ([(0, 890, 700, 935)], 750),
                 ([(0, 890, 300, 935), (700, 890, 1000, 935)], 380)]
        for obstacles, expected in cases:
            with self.subTest(obstacles=obstacles):
                self.assertEqual(choose_footer_placement(1000, text, obstacles).origin_x, expected)

    def test_equal_nonzero_overlap_prefers_the_left(self):
        placement = choose_footer_placement(1000, (0, 900, 240, 920),
            [(10, 900, 20, 920), (380, 900, 440, 920), (750, 900, 760, 920)])
        self.assertEqual(placement.origin_x, 10)

    def test_footer_ink_bounds_stay_inside_the_canvas_despite_font_bearings(self):
        placement = choose_footer_placement(1000, (-2, 900, 242, 920), [])
        self.assertEqual(placement.origin_x, 12)
        self.assertEqual(placement.bounds, (10, 900, 254, 920))

    def test_clapping_footer_uses_the_rendered_name_size_and_alignment(self):
        panel = ClappingPanel(5, PixelRect(356, 830, 424, 934), 342, 269, "right")
        entrant = SinglesEntrant(characters=[Character("Fox", color="default")],
            tag="Sponsor | A Player Name That Fills This Footer", placement=5, seed=None,
            name_font_size_adjustment=20)
        request = SimpleNamespace(text_settings=TextSettings(include_seeding=False))
        renderer = PodiumsClappingContentRenderer(font=PodiumFont.IMPACT)
        bounds = renderer._draw_identity(self.canvas, entrant, panel, request, "#FFFFFFFF", False)
        placement = draw_clapping_attribution(self.canvas, PodiumFont.IMPACT, bounds + [panel.rect.as_tuple()])
        self.assertGreater(placement.bounds[0], 10)
        for obstacle in bounds:
            overlap_width = max(0, min(placement.bounds[2], obstacle[2]) - max(placement.bounds[0], obstacle[0]))
            overlap_height = max(0, min(placement.bounds[3], obstacle[3]) - max(placement.bounds[1], obstacle[1]))
            self.assertEqual(overlap_width * overlap_height, 0)

    def test_attribution_moves_away_from_a_low_right_entrant_tag(self) -> None:
        tags = ["Short"] * 7 + [
            "Very Long Sponsor Name | Very Long Player Tag Here"
        ]
        entrants = [
            self.singles_entrant(index, tag) for index, tag in enumerate(tags)
        ]

        position, anchor = _attribution_layout(
            self.canvas,
            entrants,
            font=PodiumFont.IMPACT,
            mode=PodiumMode.SINGLES_TOP_8_FOUR_PODIUM,
        )
        self.assertEqual(anchor, "la")
        self.assertLess(position[0], self.canvas.width * 3 // 4)

    def test_attribution_can_use_middle_when_both_corners_have_text(self) -> None:
        names = [
            "one two three four five six seven eight nine ten eleven twelve",
            "Short",
            "Short",
            "one two three four five six seven eight nine ten eleven twelve",
        ]
        entrants = [
            self.doubles_team(index, name)
            for index, name in enumerate(names, start=1)
        ]

        position, anchor = _attribution_layout(
            self.canvas,
            entrants,
            font=PodiumFont.IMPACT,
            mode=PodiumMode.DOUBLES_TOP_4,
        )

        self.assertEqual(anchor, "la")
        self.assertGreater(position[0], 10)
        self.assertLess(position[0], self.canvas.width * 3 // 4)


if __name__ == "__main__":
    unittest.main()

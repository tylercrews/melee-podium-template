"""Regression tests for vertically centered under-podium labels."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import PodiumFont, PodiumMode, _draw_text
from legacy_podium_content_renderer import _under_podium_vertical_center_lines


class RecordingDraw:
    def __init__(self) -> None:
        self.positions: list[tuple[int, int]] = []

    def multiline_textbbox(self, position, text, **kwargs):
        line_count = text.count("\n") + 1
        return (0, 0, 40, 10 + (line_count - 1) * 20)

    def multiline_text(self, position, text, **kwargs) -> None:
        self.positions.append(position)


class UnderPodiumTextTests(unittest.TestCase):
    def test_one_line_label_is_centered_between_two_reserved_rows(self) -> None:
        draw = RecordingDraw()

        with (
            patch("DrawPodium._wrap_text", return_value="Fox"),
            patch("DrawPodium._font_to_fit", return_value=object()),
        ):
            _draw_text(
                draw,
                (100, 200),
                "Fox",
                anchor="ma",
                max_width=290,
                preferred_size=34,
                font=PodiumFont.IMPACT,
                wrap=True,
                vertical_center_lines=2,
            )

        self.assertEqual(draw.positions, [(100, 210)])

    def test_two_line_label_keeps_the_calibrated_first_row_anchor(self) -> None:
        draw = RecordingDraw()

        with (
            patch("DrawPodium._wrap_text", return_value="Captain\nFalcon"),
            patch("DrawPodium._font_to_fit", return_value=object()),
        ):
            _draw_text(
                draw,
                (100, 200),
                "Captain\nFalcon",
                anchor="ma",
                max_width=290,
                preferred_size=34,
                font=PodiumFont.IMPACT,
                wrap=True,
                vertical_center_lines=2,
            )

        self.assertEqual(draw.positions, [(100, 200)])

    def test_labels_without_reserved_rows_are_unchanged(self) -> None:
        draw = RecordingDraw()

        with patch("DrawPodium._font_to_fit", return_value=object()):
            _draw_text(
                draw,
                (100, 200),
                "Top 8 summary",
                anchor="ma",
                max_width=290,
                preferred_size=34,
                font=PodiumFont.IMPACT,
            )

        self.assertEqual(draw.positions, [(100, 200)])

    def test_four_podium_top_8_keeps_its_existing_text_positioning(self) -> None:
        self.assertIsNone(
            _under_podium_vertical_center_lines(
                "entrant.primary_character_name",
                PodiumMode.SINGLES_TOP_8_FOUR_PODIUM,
            )
        )
        self.assertEqual(
            _under_podium_vertical_center_lines(
                "entrant.primary_character_name",
                PodiumMode.SINGLES_TOP_8,
            ),
            2,
        )


if __name__ == "__main__":
    unittest.main()

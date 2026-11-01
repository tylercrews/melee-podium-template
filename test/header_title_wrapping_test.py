"""Checks that enlarged header titles wrap instead of shrinking back to their slot."""

from dataclasses import replace
import random
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from creation import TextSettings
from DrawPodium import PodiumFont, _draw_text, _font_to_fit, _text_bounds
from header_title_wrapping import added_title_height, wrap_enlarged_title
from sample_creation_data import sample_singles_entrants, sample_tournament

LONG_TITLE = "The Big House 12: Melee Singles Championship"
FONT = PodiumFont.UBUNTU


def bounds(call):
    kwargs = {key: call.kwargs[key] for key in ("anchor", "max_width", "preferred_size", "font", "align")}
    return _text_bounds(ImageDraw.Draw(Image.new("RGBA", (1, 1))), call.args[1], call.args[2], **kwargs)


class WrapEnlargedTitleTests(unittest.TestCase):
    def test_default_and_reduced_sizes_keep_the_single_shrinking_line(self):
        for adjustment in (0, -5, -20):
            with self.subTest(adjustment=adjustment):
                self.assertEqual(wrap_enlarged_title(LONG_TITLE, max_width=527, preferred_size=72 + adjustment,
                                                     adjustment=adjustment, font=FONT), (LONG_TITLE, 72 + adjustment))

    def test_titles_that_fit_or_cannot_split_stay_on_one_line(self):
        self.assertEqual(wrap_enlarged_title("Local", max_width=527, preferred_size=92, adjustment=20, font=FONT),
                         ("Local", 92))
        self.assertEqual(wrap_enlarged_title("Supercalifragilisticexpialidocious", max_width=200, preferred_size=92,
                                             adjustment=20, font=FONT),
                         ("Supercalifragilisticexpialidocious", 92))

    def test_enlarged_long_title_wraps_into_two_balanced_lines_at_a_larger_size(self):
        text, size = wrap_enlarged_title(LONG_TITLE, max_width=527, preferred_size=92, adjustment=20, font=FONT)
        self.assertEqual(text, "The Big House 12: Melee\nSingles Championship")
        wrapped = _font_to_fit(text, 527, size, FONT)
        self.assertGreater(wrapped.size, _font_to_fit(LONG_TITLE, 527, 92, FONT).size)
        self.assertTrue(all(wrapped.getlength(line) <= 527 for line in text.splitlines()))

    def test_wrapping_respects_the_available_height(self):
        text, size = wrap_enlarged_title(LONG_TITLE, max_width=597, preferred_size=78, adjustment=20, font=FONT,
                                         max_height=110)
        self.assertIn("\n", text)
        face = _font_to_fit(text, 597, size, FONT)
        self.assertLessEqual(ImageDraw.Draw(Image.new("L", (1, 1))).multiline_textbbox(
            (0, 0), text, font=face, anchor="la")[3], 110)
        # Too little height for two lines larger than the single line keeps it.
        self.assertEqual(wrap_enlarged_title(LONG_TITLE, max_width=597, preferred_size=78, adjustment=20, font=FONT,
                                             max_height=40), (LONG_TITLE, 78))

    def test_added_height_counts_one_line_advance_per_wrapped_line(self):
        self.assertEqual(added_title_height("Local", max_width=527, preferred_size=92, font=FONT), 0)
        text, size = wrap_enlarged_title(LONG_TITLE, max_width=527, preferred_size=92, adjustment=20, font=FONT)
        self.assertGreater(added_title_height(text, max_width=527, preferred_size=size, font=FONT), size // 2)


class HeaderTitleRenderingTests(unittest.TestCase):
    def setUp(self):
        self.tournament = replace(sample_tournament(), title=LONG_TITLE)

    def test_podium_subtitle_moves_below_a_wrapped_title(self):
        from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
        from DrawPodium import PodiumMode
        from legacy_podium_content_renderer import LegacyPodiumContentRenderer
        from models import TournamentFormat
        request = SimpleNamespace(
            tournament=self.tournament,
            entrants=sample_singles_entrants(3, random.Random(0)),
            text_settings=TextSettings(title_font_size_adjustment=20, metadata_rows=(("event",),)),
            header_layout={"top_left": "tournament_logo", "top_middle": "tournament_title", "top_right": "metadata"},
            selection=ModeSelection(CreationMode.PODIUM, ModeOptions(TournamentFormat.SINGLES, 3,
                                                                    podium_style=PodiumStyle.LEGACY)),
        )
        renderer = LegacyPodiumContentRenderer(font=FONT)
        canvas = Image.new("RGBA", (1672, 941))
        with patch("legacy_podium_content_renderer._draw_text", wraps=_draw_text) as draw:
            renderer._draw_assigned_subtitle(canvas, request)
            renderer._draw_assigned_tournament_text(canvas, request, PodiumMode.SINGLES_TOP_3)
        subtitle = next(call for call in draw.call_args_list if call.args[2] == self.tournament.subtitle)
        title = next(call for call in draw.call_args_list if "\n" in call.args[2])
        self.assertGreater(bounds(subtitle)[1], bounds(title)[3])

    def test_geometric_subtitle_follows_a_wrapped_title_inside_its_box(self):
        from geometric_content_renderer import _draw_header_lines
        from mode_preferences import PixelRect
        box = PixelRect(40, 888, 637, 1070)
        request = SimpleNamespace(tournament=self.tournament, text_settings=TextSettings(title_font_size_adjustment=20))
        with patch("geometric_content_renderer._draw_text", wraps=_draw_text) as draw:
            _draw_header_lines(Image.new("RGBA", (1920, 1080)), request, "tournament_title", box, FONT, "la",
                               title_size=58)
        title, subtitle = draw.call_args_list
        self.assertIn("\n", title.args[2])
        self.assertGreater(bounds(subtitle)[1], bounds(title)[3])
        self.assertLessEqual(bounds(subtitle)[3], box.bottom)


if __name__ == "__main__":
    unittest.main()

"""Tests for Replay Reporter's Start.gg costume-score convention."""

from pathlib import Path
import re
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import MELEE_FIGHTERS
from startgg_usb_reporting import (
    USB_COSTUMES_BY_FIGHTER,
    canonical_fighter_name,
    costume_for_usb_score,
    decode_usb_score,
)


class StartggUsbReportingTests(unittest.TestCase):
    def test_decodes_costume_index_and_real_stock_count(self):
        decoded = decode_usb_score(204)

        self.assertIsNotNone(decoded)
        self.assertEqual(decoded.costume_index, 1)
        self.assertEqual(decoded.stocks_remaining, 4)

    def test_ordinary_and_non_integer_scores_are_not_metadata(self):
        for score in (4, -1, None, "204", 204.0, True):
            with self.subTest(score=score):
                self.assertIsNone(decode_usb_score(score))

    def test_translates_slippi_indices_to_local_asset_labels(self):
        self.assertEqual(costume_for_usb_score("Captain Falcon", 204), "black")
        self.assertEqual(costume_for_usb_score("Yoshi", 604), "cyan")
        self.assertEqual(costume_for_usb_score("Ice Climbers", 304), "cyan")
        self.assertEqual(costume_for_usb_score("Jigglypuff", 504), "white")

    def test_encoded_neutral_costume_is_explicitly_default(self):
        self.assertEqual(costume_for_usb_score("Fox", 104), "default")

    def test_stock_glitch_index_outside_fighter_palette_is_ignored(self):
        self.assertIsNone(costume_for_usb_score("Fox", 504))

    def test_startgg_game_and_watch_name_is_canonicalized(self):
        self.assertEqual(canonical_fighter_name("Mr. Game & Watch"), "Mr. Game and Watch")
        self.assertEqual(costume_for_usb_score("Mr. Game & Watch", 204), "red")

    def test_every_translation_points_to_an_available_render_color(self):
        self.assertEqual(set(USB_COSTUMES_BY_FIGHTER), set(MELEE_FIGHTERS))
        renders = Path(__file__).resolve().parents[1] / "char_assets" / "renders"
        filename = re.compile(r"^\d{2}[a-z]_([^_]+)_")
        for fighter, expected_colors in USB_COSTUMES_BY_FIGHTER.items():
            available = {
                match.group(1).lower()
                for asset in (renders / fighter).glob("*.png")
                if (match := filename.match(asset.name))
            }
            with self.subTest(fighter=fighter):
                self.assertTrue(set(expected_colors).issubset(available))

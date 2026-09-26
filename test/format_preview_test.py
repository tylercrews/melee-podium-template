"""Focused checks for the Format-step sample renderer."""

from __future__ import annotations

import unittest

from creation_modes import PodiumStyle
from format_preview import render_format_preview
from models import TournamentFormat


class FormatPreviewTests(unittest.TestCase):
    def test_legacy_and_customizable_previews_use_their_layout_dimensions(self) -> None:
        legacy = render_format_preview(
            PodiumStyle.LEGACY,
            TournamentFormat.SINGLES,
            3,
        )
        customizable = render_format_preview(
            PodiumStyle.CUSTOMIZABLE,
            TournamentFormat.DOUBLES,
            4,
        )
        self.assertEqual((legacy.mode, legacy.size), ("RGBA", (1672, 941)))
        self.assertEqual((customizable.mode, customizable.size), ("RGBA", (1920, 941)))

    def test_rejects_an_unsupported_mode_combination(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported format preview layout"):
            render_format_preview(
                PodiumStyle.LEGACY,
                TournamentFormat.DOUBLES,
                8,
            )

    def test_transparent_preview_leaves_the_background_available_for_browser_composition(self) -> None:
        preview = render_format_preview(
            PodiumStyle.LEGACY,
            TournamentFormat.SINGLES,
            3,
            transparent=True,
        )
        self.assertEqual(preview.getpixel((0, 0))[3], 0)


if __name__ == "__main__":
    unittest.main()

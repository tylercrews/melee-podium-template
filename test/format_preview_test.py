"""Focused checks for the Format-step sample renderer."""

from __future__ import annotations

import unittest
from pathlib import Path

from creation import TextSettings
from creation_modes import PodiumStyle
from format_preview import render_format_preview
from models import TournamentFormat
from podium_colors import PodiumColorConfiguration, PodiumColorSelection


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

    def test_customizable_preview_uses_uncached_color_configuration(self) -> None:
        red = PodiumColorSelection("#FF0000FF", "#880000FF", "#220000FF")
        green = PodiumColorSelection("#00FF00FF", "#008800FF", "#002200FF")
        red_preview = render_format_preview(
            PodiumStyle.CUSTOMIZABLE,
            TournamentFormat.SINGLES,
            3,
            transparent=True,
            podium_colors=PodiumColorConfiguration.per_podium(red, red, red),
        )
        green_preview = render_format_preview(
            PodiumStyle.CUSTOMIZABLE,
            TournamentFormat.SINGLES,
            3,
            transparent=True,
            podium_colors=PodiumColorConfiguration.per_podium(green, green, green),
        )
        self.assertNotEqual(red_preview.tobytes(), green_preview.tobytes())

    def test_header_assignments_change_the_rendered_text_positions(self) -> None:
        left_title = render_format_preview(
            PodiumStyle.LEGACY,
            TournamentFormat.SINGLES,
            3,
            transparent=True,
            header_layout={
                "top_left": "tournament_title",
                "top_middle": "tournament_logo",
                "top_right": "metadata",
            },
        )
        right_title = render_format_preview(
            PodiumStyle.LEGACY,
            TournamentFormat.SINGLES,
            3,
            transparent=True,
            header_layout={
                "top_left": "metadata",
                "top_middle": "tournament_logo",
                "top_right": "tournament_title",
            },
        )
        self.assertNotEqual(
            left_title.crop((0, 0, left_title.width, 180)).tobytes(),
            right_title.crop((0, 0, right_title.width, 180)).tobytes(),
        )

    def test_custom_font_and_metadata_settings_change_the_preview(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        custom_font = (project_root / "fonts" / "Ubuntu-Regular.ttf").read_bytes()
        header_layout = {
            "top_left": "metadata",
            "top_middle": "tournament_logo",
            "top_right": "tournament_title",
        }
        plain = render_format_preview(
            PodiumStyle.LEGACY,
            TournamentFormat.SINGLES,
            3,
            transparent=True,
            header_layout=header_layout,
            text_settings=TextSettings(metadata_fields=frozenset({"stream_link"})),
        )
        customized = render_format_preview(
            PodiumStyle.LEGACY,
            TournamentFormat.SINGLES,
            3,
            transparent=True,
            header_layout=header_layout,
            custom_font_bytes=custom_font,
            text_settings=TextSettings(
                font_size_adjustment=5,
                replace_base_urls_with_icons=True,
                metadata_fields=frozenset({"stream_link"}),
            ),
        )
        self.assertNotEqual(
            plain.crop((0, 0, plain.width, 180)).tobytes(),
            customized.crop((0, 0, customized.width, 180)).tobytes(),
        )


if __name__ == "__main__":
    unittest.main()

"""Render the Load-step Quick Picks with their actual layout, font, and palette."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from creation_modes import CreationMode, PodiumStyle
from DrawPodium import PodiumFont
from format_preview import render_format_preview
from geometric_formatting_colors import GeometricFormattingColor, GeometricFormattingColors
from models import TournamentFormat
from podium_colors import PodiumColorConfiguration, PodiumColorPreset


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "frontend" / "public" / "quick_pick_thumbnails"


def generate_quick_pick_thumbnails() -> tuple[Path, ...]:
    catalog = json.loads((ROOT / "frontend" / "src" / "quickPicks.json").read_text())
    controller_colors = PodiumColorConfiguration.from_preset(PodiumColorPreset.LEGACY)
    paths = []
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for pick in catalog:
        mode = CreationMode(pick["mode"])
        colors = GeometricFormattingColors(tuple(
            GeometricFormattingColor(color.base_color, color.main_color)
            for slot in range(1, pick["entrant_count"] + 1)
            for color in (controller_colors.color_for_slot(slot).resolve(),)
        )) if mode is CreationMode.SQUARES else None
        image = render_format_preview(
            PodiumStyle.LEGACY,
            TournamentFormat(pick["event_format"]),
            pick["entrant_count"],
            creation_mode=mode,
            font=PodiumFont.UBUNTU,
            formatting_colors=colors,
            header_layout={"top_left": "tournament_title", "top_middle": "tournament_logo", "top_right": "metadata"},
        )
        image.thumbnail((480, 270), Image.Resampling.LANCZOS)
        path = OUTPUT / f"{pick['id']}.webp"
        image.save(path, format="WEBP", quality=86, method=6)
        paths.append(path)
    return tuple(paths)


if __name__ == "__main__":
    print(f"Generated {len(generate_quick_pick_thumbnails())} Quick Pick thumbnails in {OUTPUT}")

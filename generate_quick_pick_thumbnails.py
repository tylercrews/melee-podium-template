"""Render the Load-step Quick Picks with their actual layout, font, and palette."""

from __future__ import annotations

import json
import argparse
from pathlib import Path

from PIL import Image

from creation_modes import CreationMode, PodiumStyle
from DrawPodium import PodiumFont
from format_preview import prepare_format_preview, render_format_preview
from podiums_clapping_renderer import ClappingLayout
from geometric_formatting_colors import GeometricFormattingColor, GeometricFormattingColors
from models import TournamentFormat
from podium_colors import PodiumColorConfiguration, PodiumColorPreset


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "frontend" / "public" / "quick_pick_thumbnails"


def generate_quick_pick_thumbnails(ids: tuple[str, ...] | None = None) -> tuple[Path, ...]:
    catalog = json.loads((ROOT / "frontend" / "src" / "quickPicks.json").read_text())
    controller_colors = PodiumColorConfiguration.from_preset(PodiumColorPreset.LEGACY)
    paths = []
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for pick in catalog:
        if ids is not None and pick["id"] not in ids:
            continue
        mode = CreationMode(pick["mode"])
        colors = GeometricFormattingColors(tuple(
            GeometricFormattingColor(color.base_color, color.main_color)
            for slot in range(1, pick["entrant_count"] + 1)
            for color in (controller_colors.color_for_slot(slot).resolve(),)
        )) if mode is CreationMode.SQUARES else None
        renderer = prepare_format_preview if pick.get("animated") else render_format_preview
        result = renderer(
            PodiumStyle(pick.get("podium_style", "legacy")),
            TournamentFormat(pick["event_format"]),
            pick["entrant_count"],
            variant=pick.get("variant"),
            animated=pick.get("animated", False),
            creation_mode=mode,
            font=PodiumFont.UBUNTU,
            formatting_colors=colors,
            header_layout={"top_left": "tournament_title", "top_middle": "tournament_logo", "top_right": "metadata"},
        )
        path = OUTPUT / f"{pick['id']}.webp"
        if isinstance(result, ClappingLayout):
            frames = []
            for index in range(len(result.durations)):
                frame = result.frame(index)
                frame.thumbnail((480, 270), Image.Resampling.LANCZOS)
                frames.append(frame)
            frames[0].save(path, format="WEBP", save_all=True, append_images=frames[1:],
                           duration=result.durations, loop=0, quality=86, method=6)
        else:
            result.thumbnail((480, 270), Image.Resampling.LANCZOS)
            result.save(path, format="WEBP", quality=86, method=6)
        paths.append(path)
    return tuple(paths)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", action="append", help="Only generate selected catalog IDs.")
    args = parser.parse_args()
    print(f"Generated {len(generate_quick_pick_thumbnails(tuple(args.id) if args.id else None))} Quick Pick thumbnails in {OUTPUT}")

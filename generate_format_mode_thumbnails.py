"""Generate compact examples for the frontend's image-type selector."""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image

from DrawEyes import draw_singles_top_8 as draw_eyes_singles_top_8
from DrawRadial import draw_singles_top_8 as draw_radial_singles_top_8
from creation_modes import CreationMode, PodiumStyle
from DrawSquares import draw_singles_top_8 as draw_squares_singles_top_8
from format_preview import render_format_preview
from models import TournamentFormat
from sample_creation_data import sample_singles_entrants, sample_tournament


ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / "frontend" / "public" / "format_mode_thumbnails"
MAXIMUM_SIZE = (360, 240)


def _save_thumbnail(image: Image.Image, name: str) -> Path:
    output = image.convert("RGBA")
    output.thumbnail(MAXIMUM_SIZE, Image.Resampling.LANCZOS)
    path = OUTPUT_ROOT / f"{name}.webp"
    path.parent.mkdir(parents=True, exist_ok=True)
    output.save(path, format="WEBP", quality=86, method=6)
    return path


def generate_format_mode_thumbnails() -> tuple[Path, ...]:
    rng = random.Random(20260928)
    top_8 = sample_singles_entrants(8, rng)
    tournament = sample_tournament(TournamentFormat.SINGLES)
    images = {
        "podium": render_format_preview(
            PodiumStyle.LEGACY,
            TournamentFormat.SINGLES,
            4,
            creation_mode=CreationMode.PODIUM,
            entrants=top_8[:4],
            tournament=tournament,
        ),
        "eyes": draw_eyes_singles_top_8(
            top_8,
            tournament=tournament,
            fill_color="#080B14FF",
        ),
        "squares": draw_squares_singles_top_8(
            top_8,
            tournament=tournament,
            fill_color="#080B14FF",
        ),
        "radial": draw_radial_singles_top_8(top_8, tournament=tournament),
    }
    return tuple(_save_thumbnail(image, name) for name, image in images.items())


if __name__ == "__main__":
    generated = generate_format_mode_thumbnails()
    print(f"Generated {len(generated)} mode thumbnails in {OUTPUT_ROOT}")

"""Render example Flying V Singles Top 8 and Doubles Top 3 images plus an overview.

Usage:
    python test/generate/generate_flying_v_previews.py [--count 3] [--seed 2026]

Each example uses randomized sample entrants, so repeated runs show how the
layout handles different characters, multi-character lineups, and tag lengths.
Pass --seed to reproduce a set of examples.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import random
import sys

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from background_builder import (  # noqa: E402
    BUILTIN_BACKGROUND_SIZES,
    BackgroundRequest,
    ImagePlacement,
    PixelRect,
    PixelSize,
    cover_crop,
)
from DrawFlyingV import draw_doubles_top_3, draw_singles_top_8  # noqa: E402
from DrawPodium import PodiumFont  # noqa: E402
from models import TournamentFormat  # noqa: E402
from sample_creation_data import sample_top_4_teams, sample_top_8_entrants, sample_tournament  # noqa: E402


OUTPUT_FOLDER = PROJECT_ROOT / "test" / "flying_v_previews"
CANVAS = PixelSize(1080, 1920)
BACKGROUNDS = (
    "00_Battlefield_5000_5000_resaved.png",
    "05_FinalDestinationSpace_5000_5000_resaved.png",
)
OVERVIEW_SCALE = .35


def _background(asset_id: str) -> BackgroundRequest:
    placement = ImagePlacement(asset_id, cover_crop(BUILTIN_BACKGROUND_SIZES[asset_id], CANVAS), PixelRect(0, 0, CANVAS.width, CANVAS.height))
    return BackgroundRequest(size=CANVAS, image=placement)


def generate_examples(count: int, seed: int | None) -> list[tuple[str, Path]]:
    rng = random.Random(seed)
    fonts = tuple(PodiumFont)
    outputs = []
    for index in range(1, count + 1):
        background = _background(BACKGROUNDS[(index - 1) % len(BACKGROUNDS)])
        font = fonts[(index - 1) % len(fonts)]
        singles = OUTPUT_FOLDER / f"singles_top_8_{index}.png"
        draw_singles_top_8(sample_top_8_entrants(rng), tournament=sample_tournament(TournamentFormat.SINGLES),
                           background=background, font=font, output_path=singles)
        outputs.append((f"Singles #{index} - {font.value}", singles))
        doubles = OUTPUT_FOLDER / f"doubles_top_3_{index}.png"
        draw_doubles_top_3(sample_top_4_teams(rng)[:3], tournament=sample_tournament(TournamentFormat.DOUBLES),
                           background=background, font=font, output_path=doubles)
        outputs.append((f"Doubles #{index} - {font.value}", doubles))
    return outputs


def build_overview(examples: list[tuple[str, Path]], columns: int) -> Path:
    """Lay out every example in labeled rows: all Singles, then all Doubles."""
    width, height = round(CANVAS.width * OVERVIEW_SCALE), round(CANVAS.height * OVERVIEW_SCALE)
    label_height, gap = 34, 12
    ordered = [item for item in examples if item[0].startswith("Singles")] + [item for item in examples if item[0].startswith("Doubles")]
    rows = -(-len(ordered) // columns)
    sheet = Image.new("RGB", (columns * (width + gap) + gap, rows * (height + label_height + gap) + gap), "#17191F")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(str(PROJECT_ROOT / "fonts" / "Ubuntu-Regular.ttf"), 20)
    for index, (label, path) in enumerate(ordered):
        left = gap + (index % columns) * (width + gap)
        top = gap + (index // columns) * (height + label_height + gap)
        draw.text((left, top + 4), label, font=font, fill="#FFFFFF")
        with Image.open(path) as image:
            sheet.paste(image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS), (left, top + label_height))
    path = OUTPUT_FOLDER / "overview.jpg"
    sheet.save(path, quality=88)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--count", type=int, default=3, help="Examples to render for each layout (default 3).")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible entrants.")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be at least 1")
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    examples = generate_examples(args.count, args.seed)
    overview = build_overview(examples, columns=args.count)
    for label, path in examples:
        print(f"{label}: {path.relative_to(PROJECT_ROOT)}")
    print(f"Overview: {overview.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

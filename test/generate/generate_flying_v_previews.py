"""Render example Flying V Singles Top 8 (every layout variant) and Doubles Top 3 images plus an overview.

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
from creation_modes import CreationMode, ModeOptions, ModeSelection  # noqa: E402
from DrawFlyingV import draw_doubles_top_3, draw_singles_top_8  # noqa: E402
from DrawPodium import PodiumFont  # noqa: E402
from mode_preferences import ModePreferenceRepository  # noqa: E402
from models import TournamentFormat  # noqa: E402
from sample_creation_data import sample_top_4_teams, sample_top_8_entrants, sample_tournament  # noqa: E402


OUTPUT_FOLDER = PROJECT_ROOT / "test" / "flying_v_previews"
BACKGROUNDS = (
    "00_Battlefield_5000_5000_resaved.png",
    "05_FinalDestinationSpace_5000_5000_resaved.png",
)
OVERVIEW_HEIGHT = 560


def _canvas(event_format: TournamentFormat, count: int) -> PixelSize:
    selection = ModeSelection(CreationMode.FLYING_V, ModeOptions(event_format, count))
    return ModePreferenceRepository().load(selection).canvas_size


def _background(asset_id: str, canvas: PixelSize) -> BackgroundRequest:
    placement = ImagePlacement(asset_id, cover_crop(BUILTIN_BACKGROUND_SIZES[asset_id], canvas), PixelRect(0, 0, canvas.width, canvas.height))
    return BackgroundRequest(size=canvas, image=placement)


def generate_examples(count: int, seed: int | None) -> list[tuple[str, Path]]:
    rng = random.Random(seed)
    fonts = tuple(PodiumFont)
    singles_canvas = _canvas(TournamentFormat.SINGLES, 8)
    doubles_canvas = _canvas(TournamentFormat.DOUBLES, 3)
    outputs = []
    for index in range(1, count + 1):
        asset_id = BACKGROUNDS[(index - 1) % len(BACKGROUNDS)]
        font = fonts[(index - 1) % len(fonts)]
        singles = OUTPUT_FOLDER / f"singles_top_8_{index}.png"
        entrants = sample_top_8_entrants(rng)
        draw_singles_top_8(entrants, tournament=sample_tournament(TournamentFormat.SINGLES),
                           background=_background(asset_id, singles_canvas), font=font, output_path=singles)
        outputs.append((f"Singles #{index} - {font.value}", singles))
        # The same entrants in every other Singles layout variant, for side-by-side comparison.
        for kind, filename, reversed_, flipped in (("Flipped 2nd", "second_place_flipped", False, True),
                                                   ("Reversed", "vertically_reversed", True, False),
                                                   ("Flipped Reversed", "vertically_reversed_second_place_flipped", True, True)):
            variant = OUTPUT_FOLDER / f"singles_top_8_{filename}_{index}.png"
            draw_singles_top_8(entrants, tournament=sample_tournament(TournamentFormat.SINGLES),
                               background=_background(asset_id, singles_canvas), font=font, output_path=variant,
                               vertically_reversed=reversed_, second_place_flipped=flipped)
            outputs.append((f"{kind} #{index} - {font.value}", variant))
        doubles = OUTPUT_FOLDER / f"doubles_top_3_{index}.png"
        draw_doubles_top_3(sample_top_4_teams(rng)[:3], tournament=sample_tournament(TournamentFormat.DOUBLES),
                           background=_background(asset_id, doubles_canvas), font=font, output_path=doubles)
        outputs.append((f"Doubles #{index} - {font.value}", doubles))
    return outputs


def build_overview(examples: list[tuple[str, Path]]) -> Path:
    """Lay out labeled rows of each Singles layout variant and of Doubles examples."""
    label_height, gap = 34, 12
    kinds = ("Singles", "Flipped 2nd", "Reversed", "Flipped Reversed", "Doubles")
    rows = [[item for item in examples if item[0].startswith(kind)] for kind in kinds]
    thumbnails = []
    for row in rows:
        loaded = []
        for label, path in row:
            with Image.open(path) as image:
                width = round(image.width * OVERVIEW_HEIGHT / image.height)
                loaded.append((label, image.convert("RGB").resize((width, OVERVIEW_HEIGHT), Image.Resampling.LANCZOS)))
        thumbnails.append(loaded)
    sheet_width = max(sum(image.width + gap for _label, image in row) for row in thumbnails) + gap
    sheet = Image.new("RGB", (sheet_width, len(rows) * (OVERVIEW_HEIGHT + label_height + gap) + gap), "#17191F")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(str(PROJECT_ROOT / "fonts" / "Ubuntu-Regular.ttf"), 20)
    for row_index, row in enumerate(thumbnails):
        left = gap
        top = gap + row_index * (OVERVIEW_HEIGHT + label_height + gap)
        for label, image in row:
            draw.text((left, top + 4), label, font=font, fill="#FFFFFF")
            sheet.paste(image, (left, top + label_height))
            left += image.width + gap
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
    overview = build_overview(examples)
    for label, path in examples:
        print(f"{label}: {path.relative_to(PROJECT_ROOT)}")
    print(f"Overview: {overview.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

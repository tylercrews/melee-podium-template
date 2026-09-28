"""Regenerate entrant-filled Eyes/Squares preview images and their overview."""

from __future__ import annotations

from pathlib import Path
import random
import sys

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawEyes import (
    EyesMode,
    draw_eyes,
    draw_doubles_top_3 as draw_eyes_doubles_top_3,
    draw_doubles_top_4 as draw_eyes_doubles_top_4,
    draw_singles_top_8 as draw_eyes_singles_top_8,
)
from DrawSquares import (
    draw_doubles_top_3 as draw_squares_doubles_top_3,
    draw_doubles_top_4 as draw_squares_doubles_top_4,
    draw_singles_top_8 as draw_squares_singles_top_8,
)
from models import TournamentFormat
from sample_creation_data import (
    sample_singles_entrants,
    sample_top_4_teams,
    sample_top_8_entrants,
    sample_tournament,
)


OUTPUT_FOLDER = PROJECT_ROOT / "test" / "generated" / "template-previews"
DARK_BACKGROUND = "#17191FFF"


def _generate_eyes_previews() -> list[Path]:
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    entrants = sample_top_8_entrants(random.Random(11))
    teams = sample_top_4_teams(random.Random(22))
    singles_tournament = sample_tournament(TournamentFormat.SINGLES)
    doubles_tournament = sample_tournament(TournamentFormat.DOUBLES)
    outputs = [
        OUTPUT_FOLDER / "eyes-singles-top-8.png",
        OUTPUT_FOLDER / "eyes-doubles-top-3.png",
        OUTPUT_FOLDER / "eyes-doubles-top-4.png",
    ]
    random.seed(201)
    draw_eyes_singles_top_8(
        entrants,
        tournament=singles_tournament,
        fill_color=DARK_BACKGROUND,
        output_path=outputs[0],
    )
    random.seed(202)
    draw_eyes_doubles_top_3(
        teams[:3],
        tournament=doubles_tournament,
        fill_color=DARK_BACKGROUND,
        output_path=outputs[1],
    )
    random.seed(203)
    draw_eyes_doubles_top_4(
        teams,
        tournament=doubles_tournament,
        fill_color=DARK_BACKGROUND,
        output_path=outputs[2],
    )
    extended = (
        (EyesMode.SINGLES_TOP_10, 10, tuple(range(1, 11))),
        (EyesMode.SINGLES_TOP_15, 15, tuple(range(1, 16))),
        (
            EyesMode.SINGLES_TOP_16,
            16,
            (1, 2, 3, 4, 5, 5, 7, 7, 9, 9, 9, 9, 13, 13, 13, 13),
        ),
        (EyesMode.SINGLES_TOP_20, 20, tuple(range(1, 21))),
        (EyesMode.SINGLES_TOP_25, 25, tuple(range(1, 26))),
    )
    for index, (mode, count, placements) in enumerate(extended, start=1):
        output = OUTPUT_FOLDER / f"eyes-singles-top-{count}.png"
        random.seed(300 + index)
        draw_eyes(
            mode,
            sample_singles_entrants(
                count,
                random.Random(30 + index),
                placements=placements,
            ),
            tournament=singles_tournament,
            fill_color=DARK_BACKGROUND,
            output_path=output,
        )
        outputs.append(output)
    return outputs


def _generate_squares_previews() -> list[Path]:
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    entrants = sample_top_8_entrants(random.Random(11))
    teams = sample_top_4_teams(random.Random(22))
    singles_tournament = sample_tournament(TournamentFormat.SINGLES)
    doubles_tournament = sample_tournament(TournamentFormat.DOUBLES)

    outputs = [
        OUTPUT_FOLDER / "squares-singles-top-8.png",
        OUTPUT_FOLDER / "squares-doubles-top-3.png",
        OUTPUT_FOLDER / "squares-doubles-top-4.png",
        OUTPUT_FOLDER / "squares-singles-top-8-light-watermark.png",
    ]
    # Portraits with unspecified poses intentionally select a pose at render
    # time. Seed that selection so committed preview sheets are reproducible.
    random.seed(101)
    draw_squares_singles_top_8(
        entrants,
        tournament=singles_tournament,
        fill_color=DARK_BACKGROUND,
        output_path=outputs[0],
    )
    random.seed(102)
    draw_squares_doubles_top_3(
        teams[:3],
        tournament=doubles_tournament,
        fill_color=DARK_BACKGROUND,
        output_path=outputs[1],
    )
    random.seed(103)
    draw_squares_doubles_top_4(
        teams,
        tournament=doubles_tournament,
        fill_color=DARK_BACKGROUND,
        output_path=outputs[2],
    )
    random.seed(101)
    draw_squares_singles_top_8(
        entrants,
        tournament=singles_tournament,
        fill_color="#FFFFFFFF",
        output_path=outputs[3],
    )
    return outputs


def _fit_preview(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as source:
        preview = source.convert("RGB")
    preview.thumbnail(size, Image.Resampling.LANCZOS)
    return preview


def _regenerate_overview() -> Path:
    overview = Image.new("RGB", (1920, 1080), DARK_BACKGROUND)
    draw = ImageDraw.Draw(overview)
    title_font = ImageFont.truetype(PROJECT_ROOT / "fonts" / "Ubuntu-Regular.ttf", 30)
    label_font = ImageFont.truetype(PROJECT_ROOT / "fonts" / "Ubuntu-Regular.ttf", 23)
    draw.text(
        (50, 24),
        "Eyes and Squares — example entrant previews",
        fill="white",
        font=title_font,
    )

    columns = (70, 710, 1350)
    entries = (
        ("eyes-singles-top-8.png", "Eyes — Singles Top 8"),
        ("eyes-doubles-top-3.png", "Eyes — Doubles Top 3"),
        ("eyes-doubles-top-4.png", "Eyes — Doubles Top 4"),
        ("squares-singles-top-8.png", "Squares — Singles Top 8"),
        ("squares-doubles-top-3.png", "Squares — Doubles Top 3"),
        ("squares-doubles-top-4.png", "Squares — Doubles Top 4"),
    )
    for index, (filename, label) in enumerate(entries):
        row, column = divmod(index, 3)
        max_size = (500, 650) if row == 0 else (500, 260)
        preview = _fit_preview(OUTPUT_FOLDER / filename, max_size)
        cell_left = columns[column]
        image_top = 70 if row == 0 else 760
        x = cell_left + (500 - preview.width) // 2
        y = image_top + (max_size[1] - preview.height) // 2
        overview.paste(preview, (x, y))
        bounds = draw.textbbox((0, 0), label, font=label_font)
        label_width = bounds[2] - bounds[0]
        label_y = 730 if row == 0 else 1038
        draw.text(
            (cell_left + (500 - label_width) // 2, label_y),
            label,
            fill="white",
            font=label_font,
        )

    output = OUTPUT_FOLDER / "preview-overview.png"
    overview.save(output)
    return output


def _regenerate_extended_eyes_overview() -> Path:
    overview = Image.new("RGB", (1920, 1080), DARK_BACKGROUND)
    draw = ImageDraw.Draw(overview)
    title_font = ImageFont.truetype(PROJECT_ROOT / "fonts" / "Ubuntu-Regular.ttf", 30)
    label_font = ImageFont.truetype(PROJECT_ROOT / "fonts" / "Ubuntu-Regular.ttf", 22)
    draw.text(
        (50, 24),
        "Eyes — extended singles layout studies",
        fill="white",
        font=title_font,
    )
    entries = (
        (10, "PR Top 10"),
        (15, "PR Top 15"),
        (16, "Tournament Top 16"),
        (20, "PR Top 20"),
        (25, "PR Top 25"),
    )
    cell_width = 360
    gap = 15
    left_margin = (overview.width - (cell_width * 5 + gap * 4)) // 2
    for index, (count, label) in enumerate(entries):
        preview = _fit_preview(
            OUTPUT_FOLDER / f"eyes-singles-top-{count}.png",
            (cell_width, 900),
        )
        cell_left = left_margin + index * (cell_width + gap)
        x = cell_left + (cell_width - preview.width) // 2
        y = 80 + (900 - preview.height) // 2
        overview.paste(preview, (x, y))
        bounds = draw.textbbox((0, 0), label, font=label_font)
        draw.text(
            (cell_left + (cell_width - (bounds[2] - bounds[0])) // 2, 1010),
            label,
            fill="white",
            font=label_font,
        )
    output = OUTPUT_FOLDER / "eyes-extended-overview.png"
    overview.save(output)
    return output


def main() -> None:
    outputs = _generate_eyes_previews()
    outputs.extend(_generate_squares_previews())
    outputs.append(_regenerate_overview())
    outputs.append(_regenerate_extended_eyes_overview())
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()

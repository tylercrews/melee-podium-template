"""Generate review sheets for every portrait pose used by Eyes mode.

This is a visual calibration tool rather than a golden-image test.  Each pose
is represented once (the default costume when available) so focal points can be
reviewed without duplicating identical costume geometry.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from eyes_portrait_renderer import render_eye_portrait  # noqa: E402
from models import Character  # noqa: E402
from portrait_assets import CHARACTER_FOLDER, PORTRAIT_FILENAME  # noqa: E402


CELL_SIZE = (420, 420)
SHEET_COLUMNS = 4
POSE_AREA_TOP = 44


def _review_portraits() -> dict[str, dict[str, Path]]:
    portraits: dict[str, dict[str, list[Path]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for path in sorted(CHARACTER_FOLDER.glob("*/*.png")):
        match = PORTRAIT_FILENAME.match(path.name)
        if match is not None:
            portraits[path.parent.name][match.group("pose").casefold()].append(path)

    selected: dict[str, dict[str, Path]] = {}
    for character, poses in portraits.items():
        selected[character] = {}
        for pose, candidates in poses.items():
            selected[character][pose] = next(
                (
                    path
                    for path in candidates
                    if PORTRAIT_FILENAME.match(path.name).group("color").casefold()
                    == "default"
                ),
                candidates[0],
            )
    return selected


def render_source_sheets(output_dir: Path) -> tuple[Path, ...]:
    """Render uncropped review sheets, split into readable groups."""

    output_dir.mkdir(parents=True, exist_ok=True)
    portraits = _review_portraits()
    characters = sorted(portraits)
    output_paths: list[Path] = []
    for sheet_index, start in enumerate(range(0, len(characters), 5), start=1):
        group = characters[start : start + 5]
        entries = [
            (character, pose, path)
            for character in group
            for pose, path in sorted(portraits[character].items())
        ]
        rows = (len(entries) + SHEET_COLUMNS - 1) // SHEET_COLUMNS
        sheet = Image.new(
            "RGBA",
            (CELL_SIZE[0] * SHEET_COLUMNS, CELL_SIZE[1] * rows),
            "#20242CFF",
        )
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.load_default(size=18)
        for index, (character, pose, path) in enumerate(entries):
            column = index % SHEET_COLUMNS
            row = index // SHEET_COLUMNS
            left = column * CELL_SIZE[0]
            top = row * CELL_SIZE[1]
            draw.rectangle(
                (left, top, left + CELL_SIZE[0] - 1, top + CELL_SIZE[1] - 1),
                outline="#626A78FF",
                width=2,
            )
            draw.text(
                (left + 10, top + 10),
                f"{character} / {pose}",
                fill="#FFFFFFFF",
                font=font,
            )
            with Image.open(path) as source:
                portrait = source.convert("RGBA")
            bounds = portrait.getbbox()
            if bounds is None:
                continue
            portrait = portrait.crop(bounds)
            portrait.thumbnail(
                (CELL_SIZE[0] - 20, CELL_SIZE[1] - POSE_AREA_TOP - 10),
                Image.Resampling.LANCZOS,
            )
            x = left + (CELL_SIZE[0] - portrait.width) // 2
            y = top + POSE_AREA_TOP + (
                CELL_SIZE[1] - POSE_AREA_TOP - portrait.height
            ) // 2
            sheet.alpha_composite(portrait, (x, y))

        output_path = output_dir / f"eye-pose-sources-{sheet_index}.png"
        sheet.convert("RGB").save(output_path)
        output_paths.append(output_path)
    return tuple(output_paths)


def render_eye_crop_sheets(output_dir: Path) -> tuple[Path, ...]:
    """Render the real Eyes crop for every pose with a center crosshair."""

    output_dir.mkdir(parents=True, exist_ok=True)
    portraits = _review_portraits()
    characters = sorted(portraits)
    cell_width, cell_height = 820, 220
    viewport_size = (780, 160)
    output_paths: list[Path] = []
    for sheet_index, start in enumerate(range(0, len(characters), 5), start=1):
        group = characters[start : start + 5]
        entries = [
            (character, pose, path)
            for character in group
            for pose, path in sorted(portraits[character].items())
        ]
        columns = 2
        rows = (len(entries) + columns - 1) // columns
        sheet = Image.new(
            "RGBA",
            (cell_width * columns, cell_height * rows),
            "#20242CFF",
        )
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.load_default(size=18)
        for index, (character_name, pose, path) in enumerate(entries):
            column = index % columns
            row = index // columns
            left = column * cell_width
            top = row * cell_height
            match = PORTRAIT_FILENAME.match(path.name)
            assert match is not None
            character = Character(
                character_name,
                color=match.group("color"),
                pose=pose,
            )
            crop = Image.new("RGBA", viewport_size, "#315A62FF")
            crop.alpha_composite(render_eye_portrait(character, viewport_size))
            crop_draw = ImageDraw.Draw(crop)
            center_x, center_y = viewport_size[0] // 2, viewport_size[1] // 2
            crop_draw.line(
                (center_x - 14, center_y, center_x + 14, center_y),
                fill="#FF34D2FF",
                width=2,
            )
            crop_draw.line(
                (center_x, center_y - 14, center_x, center_y + 14),
                fill="#FF34D2FF",
                width=2,
            )
            sheet.alpha_composite(crop, (left + 20, top + 44))
            draw.text(
                (left + 20, top + 12),
                f"{character_name} / {pose} / {match.group('color')}",
                fill="#FFFFFFFF",
                font=font,
            )
        output_path = output_dir / f"eye-positioning-{sheet_index}.png"
        sheet.convert("RGB").save(output_path)
        output_paths.append(output_path)
    return tuple(output_paths)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "test" / "generated" / "eye-positioning",
    )
    args = parser.parse_args()
    for path in render_source_sheets(args.output_dir) + render_eye_crop_sheets(args.output_dir):
        print(path)


if __name__ == "__main__":
    main()

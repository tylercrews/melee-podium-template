"""Generate Eyes doubles crop sheets for every available character pose.

Adjust doubles-only scale and focus in
``portrait_scale_adjustment_for_eyes_doubles.py``, then rerun this script.
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


VIEWPORT_SIZE = (324, 310)
CELL_SIZE = (384, 382)
SHEET_COLUMNS = 4


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


def render_doubles_eye_crop_sheets(output_dir: Path) -> tuple[Path, ...]:
    """Render the real doubles crop for every pose with a center crosshair."""

    output_dir.mkdir(parents=True, exist_ok=True)
    portraits = _review_portraits()
    characters = sorted(portraits)
    output_paths: list[Path] = []
    for sheet_index, start in enumerate(range(0, len(characters), 5), start=1):
        entries = [
            (character, pose, path)
            for character in characters[start : start + 5]
            for pose, path in sorted(portraits[character].items())
        ]
        rows = (len(entries) + SHEET_COLUMNS - 1) // SHEET_COLUMNS
        sheet = Image.new(
            "RGBA",
            (CELL_SIZE[0] * SHEET_COLUMNS, CELL_SIZE[1] * rows),
            "#20242CFF",
        )
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.load_default(size=17)
        for index, (character_name, pose, path) in enumerate(entries):
            column = index % SHEET_COLUMNS
            row = index // SHEET_COLUMNS
            left = column * CELL_SIZE[0]
            top = row * CELL_SIZE[1]
            match = PORTRAIT_FILENAME.match(path.name)
            assert match is not None
            character = Character(
                character_name,
                color=match.group("color"),
                pose=pose,
            )
            crop = Image.new("RGBA", VIEWPORT_SIZE, "#315A62FF")
            crop.alpha_composite(
                render_eye_portrait(character, VIEWPORT_SIZE, doubles=True)
            )
            crop_draw = ImageDraw.Draw(crop)
            center_x, center_y = VIEWPORT_SIZE[0] // 2, VIEWPORT_SIZE[1] // 2
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
            sheet.alpha_composite(crop, (left + 30, top + 44))
            draw.text(
                (left + 30, top + 12),
                f"{character_name} / {pose} / {match.group('color')}",
                fill="#FFFFFFFF",
                font=font,
            )

        output_path = output_dir / f"eye-doubles-positioning-{sheet_index}.png"
        sheet.convert("RGB").save(output_path)
        output_paths.append(output_path)
    return tuple(output_paths)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            PROJECT_ROOT
            / "test"
            / "generated"
            / "eye-positioning-doubles"
        ),
    )
    args = parser.parse_args()
    for path in render_doubles_eye_crop_sheets(args.output_dir):
        print(path)


if __name__ == "__main__":
    main()

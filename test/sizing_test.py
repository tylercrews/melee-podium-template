"""Create a bottom-aligned comparison sheet for every default-color pose."""

from pathlib import Path
import re
import sys

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from portrait_scale_adjustment_to_character_relativity import get_pose_scale


POSES_DIR = PROJECT_ROOT / "char_assets" / "renders"
OUTPUT_PATH = Path(__file__).with_name("sizing_test_output.png")

BACKGROUND = (38, 38, 42, 255)
LABEL_COLOR = (245, 245, 245, 255)
BASELINE_COLOR = (255, 90, 90, 255)
SIDE_PADDING = 12
TOP_PADDING = 40
BOTTOM_PADDING = 12
LABEL_HEIGHT = 44
DEFAULT_POSE_FILENAME = re.compile(r"^00(?P<pose>[a-z]+)_.*\.png$", re.IGNORECASE)


def find_default_poses() -> list[tuple[str, str, Path]]:
    """Return every default-color portrait, ordered by character and pose code."""
    poses: list[tuple[str, str, Path]] = []

    for character_dir in sorted(POSES_DIR.iterdir(), key=lambda path: path.name.lower()):
        if not character_dir.is_dir():
            continue

        default_poses: dict[str, Path] = {}
        for path in sorted(character_dir.glob("00*.png")):
            match = DEFAULT_POSE_FILENAME.match(path.name)
            if match is None:
                continue
            pose_code = f"00{match.group('pose').lower()}"
            if pose_code in default_poses:
                raise RuntimeError(
                    f"Expected one {pose_code} PNG in {character_dir}, found multiple"
                )
            default_poses[pose_code] = path

        poses.extend(
            (character_dir.name, pose_code, path)
            for pose_code, path in sorted(default_poses.items())
        )

    if not poses:
        raise RuntimeError(f"No character poses found in {POSES_DIR}")

    return poses


def main() -> None:
    poses = find_default_poses()
    loaded = []
    for character, pose_code, path in poses:
        image = Image.open(path).convert("RGBA")
        scale = get_pose_scale(character, pose_code)
        if scale != 1.0:
            scaled_size = (
                max(1, round(image.width * scale)),
                max(1, round(image.height * scale)),
            )
            image = image.resize(scaled_size, Image.Resampling.LANCZOS)
        loaded.append((character, pose_code, scale, image))

    max_height = max(image.height for _, _, _, image in loaded)
    content_bottom = TOP_PADDING + max_height
    canvas_width = SIDE_PADDING + sum(
        image.width + SIDE_PADDING for _, _, _, image in loaded
    )
    canvas_height = content_bottom + BOTTOM_PADDING + LABEL_HEIGHT

    canvas = Image.new("RGBA", (canvas_width, canvas_height), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    # Pillow uses a top-left origin, so subtracting each height from the shared
    # bottom edge makes the images build upward from the same baseline.
    x = SIDE_PADDING
    for character, pose_code, scale, image in loaded:
        y = content_bottom - image.height
        canvas.alpha_composite(image, (x, y))

        label = f"{character}\n{pose_code} ({scale:.1%})"
        label_box = draw.multiline_textbbox((0, 0), label, font=font, align="center")
        label_width = label_box[2] - label_box[0]
        draw.multiline_text(
            (x + (image.width - label_width) // 2, content_bottom + BOTTOM_PADDING),
            label,
            fill=LABEL_COLOR,
            font=font,
            align="center",
            spacing=2,
        )
        x += image.width + SIDE_PADDING

    draw.line(
        (0, content_bottom, canvas_width, content_bottom),
        fill=BASELINE_COLOR,
        width=2,
    )
    canvas.convert("RGB").save(OUTPUT_PATH)

    print(f"Compared {len(loaded)} images ({len({character for character, _, _, _ in loaded})} characters).")
    print(f"Maximum adjusted height: {max_height}px")
    print(f"Output size: {canvas_width}x{canvas_height}px")
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

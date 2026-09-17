"""Create simple blue and gold podiums from a semantic segmentation mask."""

from pathlib import Path
import sys

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from constants import BLACK, GOLD_PODIUM, RGB, SECOND_PLACE_BOX


MASK_PATH = (
    PROJECT_ROOT
    / "docs"
    / "archive"
    / "old_podium_iterations"
    / "02_3d_second_attempt"
    / "03x_medium_segmentation_mask.png"
)
OUTPUT_FOLDER = Path(__file__).with_name("colorize_podium_test_outputs")

# The source mask is generated artwork, so its nominal class colors contain
# small one- or two-channel variations.  Nearest-color matching makes those
# pixels behave like their intended flat segmentation classes.
MASK_CLASSES: tuple[RGB, ...] = (
    (255, 255, 0),  # outer top shell
    (255, 0, 0),  # top and front inset panels
    (0, 0, 255),  # dark body and recessed channels
    (0, 255, 255),  # outer front trim
    (255, 0, 255),  # thin inner trim
)


def nearest_mask_class(pixel: RGB) -> RGB:
    """Return the semantic mask color closest to an imperfect source pixel."""

    red, green, blue = pixel
    return min(
        MASK_CLASSES,
        key=lambda color: (
            (red - color[0]) ** 2
            + (green - color[1]) ** 2
            + (blue - color[2]) ** 2
        ),
    )


def colorize_podium(mask: Image.Image, color: RGB, dark_color: RGB) -> Image.Image:
    """Colorize a mask with bright trim, dark inset faces, and a black body."""

    source = mask.convert("RGBA")
    output_pixels: list[tuple[int, int, int, int]] = []

    for red, green, blue, alpha in source.getdata():
        if alpha == 0:
            output_pixels.append((0, 0, 0, 0))
            continue

        mask_class = nearest_mask_class((red, green, blue))
        if mask_class == (0, 0, 255):
            replacement = BLACK
        elif mask_class == (255, 0, 0):
            replacement = dark_color
        else:
            replacement = color

        output_pixels.append((*replacement, alpha))

    result = Image.new("RGBA", source.size)
    result.putdata(output_pixels)
    return result


def main() -> None:
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    with Image.open(MASK_PATH) as mask:
        variants = {
            "03_medium_blue.png": (
                SECOND_PLACE_BOX.exterior_line,
                SECOND_PLACE_BOX.interior_line,
            ),
            "03_medium_gold.png": (
                GOLD_PODIUM.exterior_line,
                GOLD_PODIUM.interior_line,
            ),
        }

        for filename, (color, dark_color) in variants.items():
            output_path = OUTPUT_FOLDER / filename
            colorize_podium(mask, color, dark_color).save(output_path)
            print(f"Generated {output_path}")


if __name__ == "__main__":
    main()

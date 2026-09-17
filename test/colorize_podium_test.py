"""Create simple blue and gold podiums from a semantic segmentation mask."""

from math import sin
from pathlib import Path
import sys

from PIL import Image, ImageFilter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from constants import BLACK, FIRST_PLACE_BOX, GOLD_PODIUM, RGB, SECOND_PLACE_BOX


MASK_PATH = (
    PROJECT_ROOT
    / "docs"
    / "archive"
    / "old_podium_iterations"
    / "02_3d_second_attempt"
    / "03x_medium_segmentation_mask.png"
)
REFERENCE_PATH = MASK_PATH.with_name("03_medium.png")
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


def interpolate_stops(value: float, stops: tuple[tuple[float, float], ...]) -> float:
    for (start_at, start_value), (end_at, end_value) in zip(stops, stops[1:]):
        if value <= end_at:
            progress = (value - start_at) / (end_at - start_at)
            return start_value + (end_value - start_value) * progress
    return stops[-1][1]


def brightened_color(color: RGB, peak: int, white_mix: float) -> RGB:
    scale = peak / max(color)
    saturated = tuple(min(255, round(channel * scale)) for channel in color)
    return tuple(
        round(channel + (255 - channel) * white_mix) for channel in saturated
    )


def apply_reference_to_region(
    image: Image.Image,
    mask: Image.Image,
    reference: Image.Image,
    base: RGB,
    highlight: RGB,
    strength: float,
) -> None:
    """Transfer positive-only lighting detail from the original artwork."""

    bounds = mask.getbbox()
    if bounds is None:
        return
    left, top, right, bottom = bounds
    mask_pixels = mask.load()
    reference_pixels = reference.load()
    image_pixels = image.load()

    values = sorted(
        max(reference_pixels[x, y][:3])
        for x in range(left, right)
        for y in range(top, bottom)
        if mask_pixels[x, y]
    )
    low = values[len(values) * 5 // 100]
    high = values[len(values) * 95 // 100]
    span = max(1, high - low)

    for x in range(left, right):
        for y in range(top, bottom):
            if not mask_pixels[x, y]:
                continue
            reference_value = max(reference_pixels[x, y][:3])
            normalized = min(1.0, max(0.0, (reference_value - low) / span))
            blend = normalized * strength
            lit = tuple(
                round(channel + (light - channel) * blend)
                for channel, light in zip(base, highlight)
            )
            image_pixels[x, y] = (*lit, image_pixels[x, y][3])


def apply_podium_lighting(
    image: Image.Image,
    structure_mask: Image.Image,
    panel_mask: Image.Image,
    accent_mask: Image.Image,
    reference: Image.Image,
    accent_color: RGB,
    panel_color: RGB,
    *,
    shade_accents: bool,
) -> None:
    """Transfer the original podium's lighting without darkening palette colors."""

    apply_reference_to_region(
        image,
        structure_mask,
        reference,
        BLACK,
        (42, 42, 46),
        0.72,
    )
    apply_reference_to_region(
        image,
        panel_mask,
        reference,
        panel_color,
        brightened_color(panel_color, min(255, round(max(panel_color) * 1.65)), 0.05),
        0.68,
    )

    if not shade_accents:
        return
    apply_reference_to_region(
        image,
        accent_mask,
        reference,
        accent_color,
        brightened_color(accent_color, 255, 0.14),
        0.78,
    )


def apply_metallic_finish(image: Image.Image, metal_mask: Image.Image, base: RGB) -> None:
    """Shade all metal with one continuous field so reflections join cleanly."""

    image_pixels = image.load()
    mask_pixels = metal_mask.load()
    edge_pixels = metal_mask.filter(ImageFilter.MinFilter(9)).load()
    width, height = image.size
    bounds = metal_mask.getbbox()
    if bounds is None:
        return
    _, top, _, bottom = bounds
    metal_height = max(1, bottom - top - 1)
    reflection_stops = (
        (0.00, 0.70),
        (0.035, 1.34),
        (0.09, 0.88),
        (0.20, 1.06),
        (0.27, 1.40),
        (0.32, 0.84),
        (0.50, 0.96),
        (0.57, 1.30),
        (0.64, 0.82),
        (0.79, 1.08),
        (0.86, 1.38),
        (0.91, 0.84),
        (1.00, 0.68),
    )
    highlight = (255, 239, 166)

    for x in range(width):
        for y in range(height):
            if not mask_pixels[x, y]:
                continue

            position = min(1.0, max(0.0, (y - top) / metal_height))
            value = interpolate_stops(position, reflection_stops)
            # Subtle continuous horizontal variation suggests brushed metal;
            # it never restarts at a component or corner boundary.
            value += 0.012 * sin(x / 15.0) + 0.005 * sin(x / 3.8)

            if value <= 1.0:
                shaded = tuple(round(channel * value) for channel in base)
            else:
                blend = min(0.68, (value - 1.0) * 1.9)
                shaded = tuple(
                    round(channel + (light - channel) * blend)
                    for channel, light in zip(base, highlight)
                )

            # A soft inner rim supplies the bevel glint without creating a
            # separate texture coordinate system for every mask component.
            edge_amount = (255 - edge_pixels[x, y]) / 255 * 0.20
            shaded = tuple(
                round(channel + (light - channel) * edge_amount)
                for channel, light in zip(shaded, highlight)
            )

            alpha = image_pixels[x, y][3]
            image_pixels[x, y] = (*shaded, alpha)

def colorize_podium(
    mask: Image.Image,
    reference: Image.Image,
    color: RGB,
    dark_color: RGB,
    *,
    metallic: bool = False,
) -> Image.Image:
    """Colorize a mask with bright trim, dark inset faces, and a black body."""

    source = mask.convert("RGBA")
    output_pixels: list[tuple[int, int, int, int]] = []
    metal_pixels: list[int] = []
    panel_pixels: list[int] = []
    structure_pixels: list[int] = []

    for red, green, blue, alpha in source.getdata():
        if alpha == 0:
            output_pixels.append((0, 0, 0, 0))
            metal_pixels.append(0)
            panel_pixels.append(0)
            structure_pixels.append(0)
            continue

        mask_class = nearest_mask_class((red, green, blue))
        if mask_class == (0, 0, 255):
            replacement = BLACK
            is_metal = False
            is_panel = False
            is_structure = True
        elif mask_class == (255, 0, 0):
            replacement = dark_color
            is_metal = False
            is_panel = True
            is_structure = False
        else:
            replacement = color
            is_metal = True
            is_panel = False
            is_structure = False

        output_pixels.append((*replacement, alpha))
        metal_pixels.append(255 if is_metal else 0)
        panel_pixels.append(255 if is_panel else 0)
        structure_pixels.append(255 if is_structure else 0)

    result = Image.new("RGBA", source.size)
    result.putdata(output_pixels)
    accent_mask = Image.new("L", source.size)
    accent_mask.putdata(metal_pixels)
    panel_mask = Image.new("L", source.size)
    panel_mask.putdata(panel_pixels)
    structure_mask = Image.new("L", source.size)
    structure_mask.putdata(structure_pixels)
    apply_podium_lighting(
        result,
        structure_mask,
        panel_mask,
        accent_mask,
        reference,
        color,
        dark_color,
        shade_accents=not metallic,
    )
    if metallic:
        apply_metallic_finish(result, accent_mask, color)
    return result


def main() -> None:
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    with Image.open(MASK_PATH) as mask, Image.open(REFERENCE_PATH) as reference:
        reference_lighting = reference.convert("RGBA").filter(
            ImageFilter.GaussianBlur(10)
        )
        variants = {
            "03_medium_red.png": (
                FIRST_PLACE_BOX.exterior_line,
                FIRST_PLACE_BOX.interior_line,
                False,
            ),
            "03_medium_blue.png": (
                SECOND_PLACE_BOX.exterior_line,
                SECOND_PLACE_BOX.interior_line,
                False,
            ),
            "03_medium_gold.png": (
                GOLD_PODIUM.exterior_line,
                GOLD_PODIUM.interior_line,
                True,
            ),
        }

        for filename, (color, dark_color, metallic) in variants.items():
            output_path = OUTPUT_FOLDER / filename
            colorize_podium(
                mask,
                reference_lighting,
                color,
                dark_color,
                metallic=metallic,
            ).save(output_path)
            print(f"Generated {output_path}")


if __name__ == "__main__":
    main()

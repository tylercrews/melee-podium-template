"""Create colored podium previews from semantic segmentation masks."""

from math import sin
from pathlib import Path
import sys

from PIL import Image, ImageFilter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from constants import (
    BLACK,
    BRONZE_PODIUM,
    FIRST_PLACE_BOX,
    GOLD_PODIUM,
    RGB,
    SECOND_PLACE_BOX,
    SILVER_PODIUM,
)


ARTWORK_FOLDER = (
    PROJECT_ROOT
    / "docs"
    / "archive"
    / "old_podium_iterations"
    / "02_3d_second_attempt"
)
OUTPUT_FOLDER = Path(__file__).with_name("colorize_podium_test_outputs")

PODIUM_SIZES: tuple[tuple[str, str, str], ...] = (
    ("00_flat", "00x_flat_segmentation_mask.png", "00_flat.png"),
    ("01_x_short", "01x_x_short_segmentation_mask.png", "01_x_short.png"),
    ("02_short", "02x_short_segmentation_mask.png", "02_short.png"),
    ("03_medium", "03x_medium_segmentation_mask.png", "03_medium.png"),
    ("04_tall", "04x_tall_segmentation_mask.png", "04_tall.png"),
    ("05_x_tall", "05x_x_tall_segmentation_mask.png", "05_x_tall.png"),
)

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


def prepare_reference_lighting(
    reference: Image.Image,
    target_size: tuple[int, int],
) -> Image.Image:
    """Align an original image with its generated segmentation-mask canvas."""

    aligned = reference.convert("RGBA")
    if aligned.size != target_size:
        aligned = aligned.resize(target_size, Image.Resampling.LANCZOS)
    return aligned.filter(ImageFilter.GaussianBlur(10))


def premultiplied_blur(image: Image.Image, radius: float) -> Image.Image:
    """Blur RGBA without introducing black halos at transparent edges."""

    return image.convert("RGBa").filter(
        ImageFilter.GaussianBlur(radius)
    ).convert("RGBA")


def antialias_boundaries(
    image: Image.Image,
    region_masks: tuple[Image.Image, ...],
) -> Image.Image:
    """Smooth region contours while retaining crisp interior lighting."""

    class_map = Image.new("L", image.size)
    for value, mask in zip((64, 128, 192), region_masks[:3]):
        class_map.paste(value, mask=mask)
    edge = class_map.filter(ImageFilter.FIND_EDGES).point(
        lambda value: 255 if value else 0
    )
    edge = edge.filter(ImageFilter.MaxFilter(3)).filter(
        ImageFilter.GaussianBlur(0.45)
    )
    softened = premultiplied_blur(image, 0.70)
    return Image.composite(softened, image, edge)


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


def apply_metallic_finish(
    image: Image.Image,
    metal_mask: Image.Image,
    base: RGB,
    highlight: RGB,
) -> None:
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


def apply_right_side_shadow(image: Image.Image, visible_mask: Image.Image) -> None:
    """Darken the rightmost face to separate it from the podium front."""

    bounds = visible_mask.getbbox()
    if bounds is None:
        return
    _, top, _, bottom = bounds
    podium_height = max(1, bottom - top - 1)
    side_width = max(56, round(image.width * 0.058))
    image_pixels = image.load()
    mask_pixels = visible_mask.load()

    for y in range(top, bottom):
        visible_columns = [x for x in range(image.width) if mask_pixels[x, y]]
        if not visible_columns:
            continue
        right_edge = max(visible_columns)
        side_start = max(0, right_edge - side_width)
        vertical = (y - top) / podium_height
        # Keep the upper edge readable while making the side face distinctly
        # deeper toward the base.  This ranges from 31% to 54% at the rim.
        maximum_shadow = 0.31 + 0.23 * vertical

        for x in range(side_start, right_edge + 1):
            if not mask_pixels[x, y]:
                continue
            progress = (x - side_start) / side_width
            smooth_progress = progress * progress * (3.0 - 2.0 * progress)
            value = 1.0 - maximum_shadow * smooth_progress
            red, green, blue, alpha = image_pixels[x, y]
            image_pixels[x, y] = (
                round(red * value),
                round(green * value),
                round(blue * value),
                alpha,
            )

def colorize_podium(
    mask: Image.Image,
    reference: Image.Image,
    color: RGB,
    dark_color: RGB,
    *,
    metallic: bool = False,
    metal_highlight: RGB = (255, 255, 255),
) -> Image.Image:
    """Colorize a mask with bright trim, dark inset faces, and a black body."""

    source = mask.convert("RGBA")
    output_pixels: list[tuple[int, int, int, int]] = []
    metal_pixels: list[int] = []
    panel_pixels: list[int] = []
    structure_pixels: list[int] = []
    visible_pixels: list[int] = []

    for red, green, blue, alpha in source.getdata():
        if alpha == 0:
            output_pixels.append((0, 0, 0, 0))
            metal_pixels.append(0)
            panel_pixels.append(0)
            structure_pixels.append(0)
            visible_pixels.append(0)
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
        visible_pixels.append(255)

    result = Image.new("RGBA", source.size)
    result.putdata(output_pixels)
    accent_mask = Image.new("L", source.size)
    accent_mask.putdata(metal_pixels)
    panel_mask = Image.new("L", source.size)
    panel_mask.putdata(panel_pixels)
    structure_mask = Image.new("L", source.size)
    structure_mask.putdata(structure_pixels)
    visible_mask = Image.new("L", source.size)
    visible_mask.putdata(visible_pixels)
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
        apply_metallic_finish(result, accent_mask, color, metal_highlight)
    apply_right_side_shadow(result, visible_mask)
    return antialias_boundaries(
        result,
        (accent_mask, panel_mask, structure_mask, visible_mask),
    )


def main() -> None:
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    # Red is the geometry control: render it for every height to confirm the
    # mask mapping and lighting transfer work across the complete size set.
    for size_name, mask_filename, reference_filename in PODIUM_SIZES:
        with (
            Image.open(ARTWORK_FOLDER / mask_filename) as mask,
            Image.open(ARTWORK_FOLDER / reference_filename) as reference,
        ):
            reference_lighting = prepare_reference_lighting(reference, mask.size)
            output_path = OUTPUT_FOLDER / f"{size_name}_red.png"
            colorize_podium(
                mask,
                reference_lighting,
                FIRST_PLACE_BOX.exterior_line,
                FIRST_PLACE_BOX.interior_line,
            ).save(output_path)
            print(f"Generated {output_path}")

    # Keep the color/finish comparison on the medium geometry.
    medium_mask_path = ARTWORK_FOLDER / "03x_medium_segmentation_mask.png"
    medium_reference_path = ARTWORK_FOLDER / "03_medium.png"
    with (
        Image.open(medium_mask_path) as mask,
        Image.open(medium_reference_path) as reference,
    ):
        reference_lighting = prepare_reference_lighting(reference, mask.size)
        variants = {
            "03_medium_blue.png": (
                SECOND_PLACE_BOX.exterior_line,
                SECOND_PLACE_BOX.interior_line,
                False,
                (255, 255, 255),
            ),
            "03_medium_gold.png": (
                GOLD_PODIUM.exterior_line,
                GOLD_PODIUM.interior_line,
                True,
                (255, 239, 166),
            ),
            "03_medium_silver.png": (
                SILVER_PODIUM.exterior_line,
                SILVER_PODIUM.interior_line,
                True,
                (250, 253, 255),
            ),
            "03_medium_bronze.png": (
                BRONZE_PODIUM.exterior_line,
                BRONZE_PODIUM.interior_line,
                True,
                (255, 205, 132),
            ),
        }

        for filename, (color, dark_color, metallic, highlight) in variants.items():
            output_path = OUTPUT_FOLDER / filename
            colorize_podium(
                mask,
                reference_lighting,
                color,
                dark_color,
                metallic=metallic,
                metal_highlight=highlight,
            ).save(output_path)
            print(f"Generated {output_path}")


if __name__ == "__main__":
    main()

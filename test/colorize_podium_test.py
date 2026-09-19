"""Create colored podium previews from semantic segmentation masks."""

from collections import Counter, defaultdict
from math import sin
from pathlib import Path
from statistics import median
import sys

from PIL import Image, ImageChops, ImageFilter


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
    ("00_flat", "00x_flat_segmentation_mask_cleaned.png", "00_flat.png"),
    (
        "01_x_short",
        "01x_x_short_segmentation_mask_cleaned.png",
        "01_x_short.png",
    ),
    (
        "02_short",
        "02x_short_segmentation_mask_cleaned.png",
        "02_short.png",
    ),
    (
        "03_medium",
        "03x_medium_segmentation_mask_cleaned.png",
        "03_medium.png",
    ),
    ("04_tall", "04x_tall_segmentation_mask_cleaned.png", "04_tall.png"),
    (
        "05_x_tall",
        "05x_x_tall_segmentation_mask_cleaned.png",
        "05_x_tall.png",
    ),
)

# The source mask is generated artwork, so its nominal class colors contain
# small one- or two-channel variations.  Nearest-color matching makes those
# pixels behave like their intended flat segmentation classes.
MASK_CLASSES: tuple[RGB, ...] = (
    (0, 0, 0),  # outlines and recessed structure
    (255, 255, 255),  # specular highlights preserved from the mask
    (255, 255, 0),  # outer top shell
    (255, 0, 0),  # top and front inset panels
    (0, 0, 255),  # dark body and recessed channels
    (0, 255, 255),  # outer front trim
    (255, 0, 255),  # thin inner trim
    (0, 255, 0),  # outer body used by the replacement medium mask
)
MASK_ALPHA_THRESHOLD = 64
PRESERVED_COMPONENT_MINIMUMS: dict[RGB, int] = {
    (0, 0, 0): 32,
    (255, 255, 255): 8,
}


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


def remove_preserved_color_speckles(
    classes: list[RGB | None],
    source_pixels: list[tuple[int, int, int, int]],
    size: tuple[int, int],
) -> None:
    """Keep real black/white artwork while removing generated edge flecks."""

    width, height = size
    chromatic_classes = tuple(
        color for color in MASK_CLASSES if color not in PRESERVED_COMPONENT_MINIMUMS
    )

    for target, minimum_size in PRESERVED_COMPONENT_MINIMUMS.items():
        visited = bytearray(width * height)
        for start, mask_class in enumerate(classes):
            if mask_class != target or visited[start]:
                continue

            component: list[int] = []
            pending = [start]
            visited[start] = 1
            while pending:
                index = pending.pop()
                component.append(index)
                x, y = index % width, index // width
                neighbors = []
                if x:
                    neighbors.append(index - 1)
                if x + 1 < width:
                    neighbors.append(index + 1)
                if y:
                    neighbors.append(index - width)
                if y + 1 < height:
                    neighbors.append(index + width)
                for neighbor in neighbors:
                    if not visited[neighbor] and classes[neighbor] == target:
                        visited[neighbor] = 1
                        pending.append(neighbor)

            if len(component) >= minimum_size:
                continue

            for index in component:
                red, green, blue, _ = source_pixels[index]
                classes[index] = min(
                    chromatic_classes,
                    key=lambda color: (
                        (red - color[0]) ** 2
                        + (green - color[1]) ** 2
                        + (blue - color[2]) ** 2
                    ),
                )


def smooth_classification_noise(
    classes: list[RGB | None],
    size: tuple[int, int],
) -> None:
    """Remove isolated one-pixel bites without softening intentional edges."""

    class_values = {color: index + 1 for index, color in enumerate(MASK_CLASSES)}
    encoded = Image.new("L", size)
    encoded.putdata([
        0 if mask_class is None else class_values[mask_class]
        for mask_class in classes
    ])
    filtered = encoded.filter(ImageFilter.ModeFilter(5)).filter(
        ImageFilter.ModeFilter(5)
    )
    decoded = (None, *MASK_CLASSES)
    classes[:] = [
        original
        if original == (255, 255, 255)
        else decoded[value]
        for original, value in zip(classes, filtered.getdata())
    ]


def straighten_horizontal_class_boundaries(
    classes: list[RGB | None],
    size: tuple[int, int],
) -> None:
    """Level long near-horizontal class boundaries while preserving corners."""

    width, height = size
    transitions: dict[
        tuple[RGB | None, RGB | None], list[tuple[int, int]]
    ] = defaultdict(list)
    for x in range(width):
        for y in range(1, height):
            above = classes[(y - 1) * width + x]
            below = classes[y * width + x]
            if above != below and (255, 255, 255) not in (above, below):
                transitions[(above, below)].append((x, y))

    for (above, below), points in transitions.items():
        row_counts = Counter(y for _, y in points)
        dense_rows = sorted(y for y, count in row_counts.items() if count >= 80)
        if not dense_rows:
            continue

        row_groups: list[list[int]] = [[dense_rows[0]]]
        for row in dense_rows[1:]:
            if row - row_groups[-1][-1] <= 4:
                row_groups[-1].append(row)
            else:
                row_groups.append([row])

        for rows in row_groups:
            candidates = [
                (x, y)
                for x, y in points
                if rows[0] - 3 <= y <= rows[-1] + 3
            ]
            by_x: dict[int, list[int]] = defaultdict(list)
            for x, y in candidates:
                by_x[x].append(y)
            if not by_x or max(by_x) - min(by_x) < 120:
                continue

            selected = [(x, round(median(ys))) for x, ys in by_x.items()]
            target_y = round(median(y for _, y in selected))
            stable_x = sorted(x for x, y in selected if abs(y - target_y) <= 3)
            if not stable_x:
                continue

            runs: list[list[int]] = [[stable_x[0]]]
            for x in stable_x[1:]:
                if x - runs[-1][-1] <= 12:
                    runs[-1].append(x)
                else:
                    runs.append([x])

            for run in runs:
                if run[-1] - run[0] < 120:
                    continue
                for x in range(run[0] + 4, run[-1] - 3):
                    nearby = [
                        y
                        for y in range(max(1, target_y - 4), min(height, target_y + 5))
                        if classes[(y - 1) * width + x] == above
                        and classes[y * width + x] == below
                    ]
                    if nearby:
                        old_y = min(nearby, key=lambda y: abs(y - target_y))
                        if target_y > old_y:
                            for y in range(old_y, target_y):
                                classes[y * width + x] = above
                        elif target_y < old_y:
                            for y in range(target_y, old_y):
                                classes[y * width + x] = below

                    # Generated masks often contain a third-color tooth that
                    # touches the main region and therefore is not a removable
                    # speckle.  Lock a narrow band on both sides of a detected
                    # long boundary to its two intended classes.
                    for y in range(max(0, target_y - 3), target_y):
                        if classes[y * width + x] != (255, 255, 255):
                            classes[y * width + x] = above
                    for y in range(target_y, min(height, target_y + 3)):
                        if classes[y * width + x] != (255, 255, 255):
                            classes[y * width + x] = below


def straighten_vertical_class_boundaries(
    classes: list[RGB | None],
    size: tuple[int, int],
) -> None:
    """Straighten long vertical boundaries using the horizontal-pass rules."""

    width, height = size
    transposed = [
        classes[y * width + x]
        for x in range(width)
        for y in range(height)
    ]
    straighten_horizontal_class_boundaries(transposed, (height, width))
    classes[:] = [
        transposed[x * height + y]
        for y in range(height)
        for x in range(width)
    ]


def repair_medium_mask_artifacts(
    classes: list[RGB | None],
    size: tuple[int, int],
) -> None:
    """Lock the generated medium mask's long center trim to clean rows."""

    if size != (1774, 887):
        return
    width, _ = size
    # Preserve the rounded endpoints but rebuild the short lower-left trim's
    # straight center, which is too short for the general line detector.
    for y in range(661, 675):
        for x in range(64, 120):
            classes[y * width + x] = (255, 0, 0)

    # Lock the thin inner panel trim between its rounded end caps.
    for y in range(385, 630):
        for x in range(166, 176):
            classes[y * width + x] = (255, 0, 0)

    for y in range(628, 651):
        for x in range(548, 1135):
            classes[y * width + x] = (255, 0, 0)


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
    target_mask: Image.Image | None = None,
) -> Image.Image:
    """Align the visible reference podium with the target mask geometry."""

    source = reference.convert("RGBA")
    if target_mask is None or source.size == target_size:
        aligned = source.resize(target_size, Image.Resampling.LANCZOS)
    else:
        source_alpha = source.getchannel("A").point(
            lambda value: 255 if value > MASK_ALPHA_THRESHOLD else 0
        )
        target_alpha = target_mask.convert("RGBA").getchannel("A").point(
            lambda value: 255 if value > MASK_ALPHA_THRESHOLD else 0
        )
        source_bounds = source_alpha.getbbox()
        target_bounds = target_alpha.getbbox()
        aligned = Image.new("RGBA", target_size)
        if source_bounds is not None and target_bounds is not None:
            target_width = target_bounds[2] - target_bounds[0]
            target_height = target_bounds[3] - target_bounds[1]
            cropped = source.crop(source_bounds).resize(
                (target_width, target_height),
                Image.Resampling.LANCZOS,
            )
            aligned.paste(cropped, target_bounds[:2], cropped)
    return aligned.filter(ImageFilter.GaussianBlur(14))


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
    class_map.paste(32, mask=region_masks[3])
    for value, mask in zip((64, 128, 192), region_masks[:3]):
        class_map.paste(value, mask=mask)
    horizontal = ImageChops.difference(
        class_map, ImageChops.offset(class_map, 1, 0)
    ).point(
        lambda value: 255 if value else 0
    )
    vertical = ImageChops.difference(
        class_map, ImageChops.offset(class_map, 0, 1)
    ).point(
        lambda value: 255 if value else 0
    )
    edge = ImageChops.multiply(
        horizontal.filter(ImageFilter.MaxFilter(5)),
        vertical.filter(ImageFilter.MaxFilter(5)),
    ).filter(ImageFilter.MaxFilter(5)).filter(
        ImageFilter.GaussianBlur(0.7)
    )
    softened = premultiplied_blur(image, 1.0)
    return Image.composite(softened, image, edge)


def antialias_all_boundaries(
    image: Image.Image,
    semantic_classes: list[RGB | None],
) -> Image.Image:
    """Antialias every semantic edge without changing the class geometry.

    The legacy helper deliberately intersects horizontal and vertical edge
    maps, which limits smoothing mostly to corners.  A cleaned mask needs the
    union so long horizontal, vertical, curved, and diagonal edges are all
    rendered consistently.
    """

    class_values = {
        None: 0,
        (0, 0, 0): 32,
        (255, 255, 255): 64,
        (255, 0, 0): 96,
        (0, 0, 255): 128,
        (0, 255, 255): 160,
        (255, 255, 0): 192,
        (255, 0, 255): 224,
        (0, 255, 0): 255,
    }
    class_map = Image.new("L", image.size)
    class_map.putdata([class_values[mask_class] for mask_class in semantic_classes])
    horizontal = ImageChops.difference(
        class_map, ImageChops.offset(class_map, 1, 0)
    ).point(lambda value: 255 if value else 0)
    vertical = ImageChops.difference(
        class_map, ImageChops.offset(class_map, 0, 1)
    ).point(lambda value: 255 if value else 0)
    edge = ImageChops.lighter(horizontal, vertical).filter(
        ImageFilter.MaxFilter(3)
    ).filter(ImageFilter.GaussianBlur(0.6))
    softened = premultiplied_blur(image, 0.72)
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
    """Add a soft shadow confined to the podium's outer-right depth."""

    bounds = visible_mask.getbbox()
    if bounds is None:
        return
    _, top, _, bottom = bounds
    podium_height = max(1, bottom - top - 1)
    # Keep the field narrow so it follows the existing perspective edge rather
    # than crossing onto the broad horizontal top and front planes.
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
        maximum_shadow = 0.42 + 0.18 * vertical

        for x in range(side_start, right_edge + 1):
            if not mask_pixels[x, y]:
                continue
            progress = (x - side_start) / side_width
            smooth_progress = progress * progress * (3.0 - 2.0 * progress)
            shadow = maximum_shadow * smooth_progress
            value = 1.0 - shadow
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
    panel_classes: tuple[RGB, ...] = ((255, 0, 0),),
    structure_classes: tuple[RGB, ...] = ((0, 0, 255),),
    precleaned: bool = False,
) -> Image.Image:
    """Colorize a mask with bright trim, dark inset faces, and a black body."""

    source = mask.convert("RGBA")
    source_pixels = list(source.getdata())
    alpha_threshold = 127 if precleaned else MASK_ALPHA_THRESHOLD
    classified_pixels: list[RGB | None] = [
        nearest_mask_class((red, green, blue))
        if alpha > alpha_threshold
        else None
        for red, green, blue, alpha in source_pixels
    ]
    if not precleaned:
        smooth_classification_noise(classified_pixels, source.size)
        straighten_horizontal_class_boundaries(classified_pixels, source.size)
        straighten_vertical_class_boundaries(classified_pixels, source.size)
        remove_preserved_color_speckles(
            classified_pixels,
            source_pixels,
            source.size,
        )
        straighten_horizontal_class_boundaries(classified_pixels, source.size)
        straighten_vertical_class_boundaries(classified_pixels, source.size)
        if panel_classes == ((0, 255, 255),):
            repair_medium_mask_artifacts(classified_pixels, source.size)
    output_pixels: list[tuple[int, int, int, int]] = []
    metal_pixels: list[int] = []
    panel_pixels: list[int] = []
    structure_pixels: list[int] = []
    visible_pixels: list[int] = []

    for pixel_index, ((red, green, blue, alpha), mask_class) in enumerate(
        zip(source_pixels, classified_pixels)
    ):
        if mask_class is None:
            output_pixels.append((0, 0, 0, 0))
            metal_pixels.append(0)
            panel_pixels.append(0)
            structure_pixels.append(0)
            visible_pixels.append(0)
            continue

        if mask_class == (255, 255, 255):
            replacement = (
                metal_highlight
                if metallic
                else brightened_color(color, 255, 0.72)
            )
            is_metal = False
            is_panel = False
            is_structure = False
        elif mask_class == (0, 0, 0):
            replacement = BLACK
            is_metal = False
            is_panel = False
            is_structure = False
        elif mask_class in structure_classes:
            replacement = BLACK
            is_metal = False
            is_panel = False
            is_structure = True
        elif mask_class in panel_classes:
            replacement = dark_color
            is_metal = False
            is_panel = True
            is_structure = False
        else:
            replacement = color
            is_metal = True
            is_panel = False
            is_structure = False

        output_pixels.append((*replacement, 255))
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
    boundary_masks = (accent_mask, panel_mask, structure_mask, visible_mask)
    if precleaned:
        return antialias_all_boundaries(result, classified_pixels)
    return antialias_boundaries(result, boundary_masks)


def main() -> None:
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    # Red is the geometry control: render it for every height to confirm the
    # mask mapping and lighting transfer work across the complete size set.
    for size_name, mask_filename, reference_filename in PODIUM_SIZES:
        precleaned = mask_filename.endswith("_cleaned.png")
        with (
            Image.open(ARTWORK_FOLDER / mask_filename) as mask,
            Image.open(ARTWORK_FOLDER / reference_filename) as reference,
        ):
            reference_lighting = prepare_reference_lighting(
                reference, mask.size, mask
            )
            output_path = OUTPUT_FOLDER / f"{size_name}_red.png"
            colorize_podium(
                mask,
                reference_lighting,
                FIRST_PLACE_BOX.exterior_line,
                FIRST_PLACE_BOX.interior_line,
                panel_classes=((0, 255, 255),)
                if size_name
                in (
                    "00_flat",
                    "01_x_short",
                    "02_short",
                    "03_medium",
                    "04_tall",
                    "05_x_tall",
                )
                else ((255, 0, 0),),
                precleaned=precleaned,
            ).save(output_path)
            print(f"Generated {output_path}")

    # Keep the color/finish comparison on the medium geometry.
    medium_mask_path = (
        ARTWORK_FOLDER / "03x_medium_segmentation_mask_cleaned.png"
    )
    medium_reference_path = ARTWORK_FOLDER / "03_medium.png"
    with (
        Image.open(medium_mask_path) as mask,
        Image.open(medium_reference_path) as reference,
    ):
        reference_lighting = prepare_reference_lighting(reference, mask.size, mask)
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
                panel_classes=((0, 255, 255),),
                precleaned=True,
            ).save(output_path)
            print(f"Generated {output_path}")


if __name__ == "__main__":
    main()

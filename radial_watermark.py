"""A compact attribution centered on the lower-right Radial divider."""

import math

from PIL import Image, ImageChops, ImageColor, ImageDraw

from DrawPodium import ATTRIBUTION_TEXT, PodiumFont, _draw_text
from geometric_content_renderer import WATERMARK_BLACK, WATERMARK_WHITE


# Both layouts write along the divider from the canvas center to the
# bottom-right corner: between the tied sevenths in Singles and between the
# third- and fourth-place teams in Doubles. Both share one position near the
# corner, so Singles text may pass beneath the lower seventh-place art.
RADIAL_WATERMARK_RAY = ((960, 540), (1920, 1080))
RADIAL_WATERMARK_ANGLE = math.degrees(math.atan2(540, 960))
RADIAL_WATERMARK_END = 1050
RADIAL_WATERMARK_LENGTH = 270
# Lift the text perpendicular to the ray, toward the upper-right section, so
# less of it crosses into the lower section while still straddling the line.
RADIAL_WATERMARK_LIFT = 2


def _ray_point(distance: float) -> tuple[float, float]:
    (x0, y0), (x1, y1) = RADIAL_WATERMARK_RAY
    length = math.hypot(x1 - x0, y1 - y0)
    return x0 + (x1 - x0) * distance / length, y0 + (y1 - y0) * distance / length


def radial_watermark_line_samples() -> list[tuple[int, int]]:
    """Divider pixels under the text; the frontend mirrors this sampling."""
    end = RADIAL_WATERMARK_END
    left = math.floor(_ray_point(end - RADIAL_WATERMARK_LENGTH)[0])
    right = math.floor(_ray_point(end)[0])
    (x0, y0), (x1, y1) = RADIAL_WATERMARK_RAY
    return [
        (x, math.floor(y0 + (x - x0) * (y1 - y0) / (x1 - x0) + .5) + offset)
        for x in range(left, right + 1)
        for offset in (-1, 0, 1)
    ]


def radial_watermark_color(canvas: Image.Image) -> str:
    """Contrast with the divider color the text is written over."""
    rgba = canvas.convert("RGBA")
    samples = radial_watermark_line_samples()
    luminance = 0.0
    for x, y in samples:
        red, green, blue, alpha = rgba.getpixel((x, y))
        luminance += (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255 * alpha / 255
    return WATERMARK_BLACK if luminance / len(samples) >= 0.55 else WATERMARK_WHITE


def radial_watermark_mask(size: tuple[int, int]) -> Image.Image:
    end = _ray_point(RADIAL_WATERMARK_END)
    angle = math.radians(RADIAL_WATERMARK_ANGLE)
    origin = (round(end[0] + RADIAL_WATERMARK_LIFT * math.sin(angle)), round(end[1] - RADIAL_WATERMARK_LIFT * math.cos(angle)))
    layer = Image.new("RGBA", size, "#00000000")
    _draw_text(
        ImageDraw.Draw(layer),
        origin,
        ATTRIBUTION_TEXT,
        anchor="rm",
        max_width=RADIAL_WATERMARK_LENGTH,
        preferred_size=20,
        font=PodiumFont.UBUNTU,
        fill="#FFFFFFFF",
    )
    # Pillow rotates counter-clockwise; descend with the ray instead.
    return layer.getchannel("A").rotate(-RADIAL_WATERMARK_ANGLE, Image.Resampling.BICUBIC, center=origin)


def draw_radial_watermark(canvas: Image.Image, *, doubles: bool = False, fill: str | None = None) -> None:
    # Singles and Doubles share the same divider position.
    red, green, blue, alpha = ImageColor.getcolor(fill or radial_watermark_color(canvas), "RGBA")
    layer = Image.new("RGBA", canvas.size, (red, green, blue, 0))
    layer.putalpha(ImageChops.multiply(radial_watermark_mask(canvas.size), Image.new("L", canvas.size, alpha)))
    canvas.alpha_composite(layer)

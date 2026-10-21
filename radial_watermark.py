"""A compact attribution along the lower-right Radial divider."""

import math

from PIL import Image, ImageChops, ImageColor, ImageDraw

from background_builder import PixelRect
from DrawPodium import ATTRIBUTION_TEXT, PodiumFont, _draw_text
from geometric_content_renderer import _composite_watermark, _watermark_color


# Singles reads along the shared ray between the two seventh-place entrants,
# resting just above the divider that runs from the canvas center to the
# bottom-right corner. The box bounds the rotated text and is also its contrast
# sample. Doubles has a separate corner position below the member identity and
# right of the team name.
RADIAL_WATERMARK_ANGLE = math.degrees(math.atan2(540, 960))
RADIAL_WATERMARK_ORIGIN = (1564, 870)
RADIAL_WATERMARK_BOX = PixelRect(1450, 787, 1686, 933)
RADIAL_DOUBLES_WATERMARK_BOX = PixelRect(1562, 1034, 1902, 1062)


def _singles_watermark_mask(size: tuple[int, int]) -> Image.Image:
    layer = Image.new("RGBA", size, "#00000000")
    _draw_text(
        ImageDraw.Draw(layer),
        RADIAL_WATERMARK_ORIGIN,
        ATTRIBUTION_TEXT,
        anchor="md",
        max_width=340,
        preferred_size=20,
        font=PodiumFont.UBUNTU,
        fill="#FFFFFFFF",
    )
    # Pillow rotates counter-clockwise; descend with the ray instead.
    return layer.getchannel("A").rotate(-RADIAL_WATERMARK_ANGLE, Image.Resampling.BICUBIC, center=RADIAL_WATERMARK_ORIGIN)


def draw_radial_watermark(canvas: Image.Image, *, doubles: bool = False, fill: str | None = None) -> None:
    if doubles:
        box = RADIAL_DOUBLES_WATERMARK_BOX
        _composite_watermark(
            canvas,
            position=(box.right, box.bottom - 6),
            anchor="rs",
            max_width=box.width,
            font=PodiumFont.UBUNTU,
            fill=fill or _watermark_color(canvas, box),
        )
        return
    red, green, blue, alpha = ImageColor.getcolor(fill or _watermark_color(canvas, RADIAL_WATERMARK_BOX), "RGBA")
    layer = Image.new("RGBA", canvas.size, (red, green, blue, 0))
    layer.putalpha(ImageChops.multiply(_singles_watermark_mask(canvas.size), Image.new("L", canvas.size, alpha)))
    canvas.alpha_composite(layer)

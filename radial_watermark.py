"""A compact attribution between the lower-right placement art and seeds."""

from PIL import Image

from background_builder import PixelRect
from DrawPodium import PodiumFont
from geometric_content_renderer import _composite_watermark, _watermark_color


# The shared ray separates two seventh-place entrants in Singles. This gap is
# above the bottom badge and left of the right-edge seed. Doubles has a separate
# corner position below the member identity and right of the team name.
RADIAL_WATERMARK_BOX = PixelRect(1450, 962, 1790, 986)
RADIAL_DOUBLES_WATERMARK_BOX = PixelRect(1562, 1034, 1902, 1062)


def draw_radial_watermark(canvas: Image.Image, *, doubles: bool = False, fill: str | None = None) -> None:
    box = RADIAL_DOUBLES_WATERMARK_BOX if doubles else RADIAL_WATERMARK_BOX
    _composite_watermark(
        canvas,
        position=(box.right, box.bottom - 6),
        anchor="rs",
        max_width=box.width,
        font=PodiumFont.UBUNTU,
        fill=fill or _watermark_color(canvas, box),
    )

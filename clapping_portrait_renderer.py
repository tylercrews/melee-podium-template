"""Draw a bordered, color-backed portrait from a fixed clapping GIF crop."""

from __future__ import annotations

from PIL import Image, ImageDraw

from clapping_assets import load_clapping_frame
from color_values import normalize_rgba_hex
from models import Character
from portrait_crop_adjustment_for_clapping import (
    ClappingPortraitAdjustment,
    get_clapping_portrait_adjustment,
)


def render_clapping_portrait_frame(
    source: Image.Image,
    adjustment: ClappingPortraitAdjustment,
    size: tuple[int, int] = (112, 172),
    *,
    background_color: str,
    border_color: str = "#808080FF",
    border_width: int = 2,
    mirror_horizontally: bool = False,
) -> Image.Image:
    """Crop one RGBA frame with stable zoom, then composite background and border.

    The source window never follows individual frames' alpha bounds. Changing
    aspect ratio preserves vertical zoom and expands/contracts the horizontal
    window around its calibrated center, so square variants remain undistorted.
    """

    if len(size) != 2 or any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in size):
        raise ValueError("Portrait size must contain two positive integers")
    if isinstance(border_width, bool) or not isinstance(border_width, int) or border_width < 0:
        raise ValueError("border_width must be a non-negative integer")
    if not isinstance(mirror_horizontally, bool):
        raise ValueError("mirror_horizontally must be a boolean")
    background = normalize_rgba_hex(background_color, field_name="background_color")
    border = normalize_rgba_hex(border_color, field_name="border_color")
    inset = border_width * 3
    width, height = size
    inner_width, inner_height = width - inset * 2, height - inset * 2
    if min(inner_width, inner_height) <= 0:
        raise ValueError("Portrait size must leave space inside its border")

    left, top, right, bottom = adjustment.source_crop
    source_width, source_height = adjustment.source_size
    center_x = (left + right) / 2 / source_width * source.width
    top = top / source_height * source.height
    bottom = bottom / source_height * source.height
    crop_height = bottom - top
    crop_width = crop_height * inner_width / inner_height
    source_window = (
        round(center_x - crop_width / 2), round(top),
        round(center_x + crop_width / 2), round(bottom),
    )
    if source_window[2] <= source_window[0] or source_window[3] <= source_window[1]:
        raise ValueError("Source crop is too small for its source image")
    portrait = source.convert("RGBA").crop(source_window).resize(
        (inner_width, inner_height), Image.Resampling.LANCZOS,
    )
    if mirror_horizontally:
        portrait = portrait.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    image = Image.new("RGBA", size, background)
    image.alpha_composite(portrait, (inset, inset))
    if border_width:
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, width - 1, height - 1), outline=border, width=border_width)
        draw.rectangle(
            (border_width, border_width, width - border_width - 1, height - border_width - 1),
            outline="#282828FF", width=border_width,
        )
        draw.rectangle(
            (2 * border_width, 2 * border_width, width - 2 * border_width - 1, height - 2 * border_width - 1),
            outline=border, width=border_width,
        )
    return image


def render_clapping_portrait(
    character: Character,
    size: tuple[int, int] = (112, 172),
    *,
    background_color: str,
    frame_index: int = 0,
    border_color: str = "#808080FF",
    border_width: int = 2,
) -> Image.Image:
    """Draw the selected character/costume without using its static portrait pose."""

    return render_clapping_portrait_frame(
        load_clapping_frame(character, frame_index),
        get_clapping_portrait_adjustment(character.melee_fighter_name),
        size,
        background_color=background_color,
        border_color=border_color,
        border_width=border_width,
        mirror_horizontally=character.mirror_horizontally,
    )

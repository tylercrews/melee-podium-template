"""Render a character portrait as a focal-point-controlled Eyes crop."""

from __future__ import annotations

from PIL import Image

from models import Character
from portrait_assets import load_character_source
from portrait_scale_adjustment_for_eyes import get_eye_portrait_adjustment
from portrait_scale_adjustment_for_eyes_doubles import (
    get_doubles_eye_portrait_adjustment,
)


def render_eye_portrait(
    character: Character,
    size: tuple[int, int],
    *,
    zoom_multiplier: float = 1.0,
    doubles: bool = False,
    focal_destination: tuple[float, float] | None = None,
    framing_width: float | None = None,
) -> Image.Image:
    """Center one pose's reviewed eye point in a clipped RGBA viewport."""

    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError("Eye portrait viewport dimensions must be positive")
    if zoom_multiplier <= 0:
        raise ValueError("zoom_multiplier must be greater than zero")
    if framing_width is not None and framing_width <= 0:
        raise ValueError("framing_width must be greater than zero")
    source, pose = load_character_source(character)
    adjustment = (
        get_doubles_eye_portrait_adjustment(character.melee_fighter_name, pose)
        if doubles
        else get_eye_portrait_adjustment(character.melee_fighter_name, pose)
    )
    bounds = source.getbbox()
    if bounds is None:
        return Image.new("RGBA", size, "#00000000")
    scale = (framing_width if framing_width is not None else width) / (bounds[2] - bounds[0])
    scale *= adjustment.zoom * zoom_multiplier
    resized = source.resize(
        (
            max(1, round(source.width * scale)),
            max(1, round(source.height * scale)),
        ),
        Image.Resampling.LANCZOS,
    )
    focal_x = adjustment.focal_x
    if character.mirror_horizontally:
        focal_x = source.width - focal_x
    viewport = Image.new("RGBA", size, "#00000000")
    destination_x, destination_y = focal_destination or (width / 2, height / 2)
    viewport.alpha_composite(
        resized,
        (
            round(destination_x - focal_x * scale),
            round(destination_y - adjustment.focal_y * scale),
        ),
    )
    return viewport

"""Render a character portrait as a focal-point-controlled Eyes crop."""

from __future__ import annotations

from PIL import Image

from models import Character
from portrait_assets import load_character_source
from portrait_scale_adjustment_for_eyes import get_eye_portrait_adjustment


def render_eye_portrait(
    character: Character,
    size: tuple[int, int],
    *,
    zoom_multiplier: float = 1.0,
) -> Image.Image:
    """Center one pose's reviewed eye point in a clipped RGBA viewport."""

    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError("Eye portrait viewport dimensions must be positive")
    if zoom_multiplier <= 0:
        raise ValueError("zoom_multiplier must be greater than zero")
    source, pose = load_character_source(character)
    adjustment = get_eye_portrait_adjustment(character.melee_fighter_name, pose)
    bounds = source.getbbox()
    if bounds is None:
        return Image.new("RGBA", size, "#00000000")
    scale = width / (bounds[2] - bounds[0])
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
    viewport.alpha_composite(
        resized,
        (
            round(width / 2 - focal_x * scale),
            round(height / 2 - adjustment.focal_y * scale),
        ),
    )
    return viewport

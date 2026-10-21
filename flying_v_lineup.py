"""Render one Flying V entrant's full-body character lineup inside a frame."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from PIL import Image

from background_builder import PixelRect
from models import Character
from portrait_assets import load_scaled_portrait, with_team_color


# Additional characters follow the Podium center/left/right stagger at a
# spacing relative to the tallest portrait, so every tier keeps its proportions.
LINEUP_SPREAD = 0.2
STANDING_FRAME = "flying_v_standing_frame"
HANGING_FRAME = "flying_v_hanging_frame"
FRAME_ASSETS = frozenset({STANDING_FRAME, HANGING_FRAME})


@dataclass(frozen=True, slots=True)
class PlacedLineup:
    """A composited lineup and the canvas rectangle its visible pixels cover."""

    image: Image.Image
    bounds: PixelRect


def _visible_portraits(characters: Sequence[Character], scale: float, team_color: str | None) -> list[Image.Image]:
    portraits = []
    for character in characters:
        portrait = load_scaled_portrait(with_team_color(character, team_color), scale)
        visible = portrait.getbbox()
        if visible is not None:
            portraits.append(portrait.crop(visible))
    # The tallest portrait establishes the silhouette; later ones layer over it.
    return sorted(portraits, key=lambda image: image.height, reverse=True)


def render_lineup(
    characters: Sequence[Character],
    scale: float,
    *,
    team_color: str | None = None,
) -> tuple[Image.Image, int]:
    """Bottom-align a lineup and return it with its center anchor's x offset."""

    if not characters:
        raise ValueError("A Flying V entrant must have at least one character")
    portraits = _visible_portraits(characters, scale, team_color)
    if not portraits:
        return Image.new("RGBA", (1, 1), "#00000000"), 0
    spread = round(portraits[0].height * LINEUP_SPREAD)
    pattern = (-spread, spread) if len(portraits) == 2 else (0, -spread, spread)
    offsets = [pattern[index % len(pattern)] for index in range(len(portraits))]
    left = min(offset - image.width / 2 for offset, image in zip(offsets, portraits))
    right = max(offset + image.width / 2 for offset, image in zip(offsets, portraits))
    height = max(image.height for image in portraits)
    lineup = Image.new("RGBA", (round(right - left), height), "#00000000")
    for offset, image in zip(offsets, portraits):
        lineup.alpha_composite(image, (round(offset - image.width / 2 - left), height - image.height))
    return lineup, round(-left)


def place_lineup(
    characters: Sequence[Character],
    scale: float,
    frame: PixelRect,
    *,
    hanging: bool = False,
    team_color: str | None = None,
) -> PlacedLineup:
    """Scale a lineup to its tier, shrinking only when it would overflow the frame.

    Standing lineups rest on the frame's bottom center. Hanging lineups start at
    the frame's top center so they never rise into space reserved above them.
    """

    if scale <= 0:
        raise ValueError("Flying V scales must be greater than zero")
    lineup, anchor_x = render_lineup(characters, scale, team_color=team_color)
    # Per-portrait rounding can leave a refit lineup a few pixels too large.
    for _attempt in range(3):
        fit = min(1.0, frame.width / lineup.width, frame.height / lineup.height)
        if fit >= 1:
            break
        scale *= fit
        lineup, anchor_x = render_lineup(characters, scale, team_color=team_color)
    if lineup.width > frame.width or lineup.height > frame.height:
        fit = min(frame.width / lineup.width, frame.height / lineup.height)
        anchor_x = round(anchor_x * fit)
        lineup = lineup.resize((max(1, int(lineup.width * fit)), max(1, int(lineup.height * fit))), Image.Resampling.LANCZOS)
    # Center the primary character, then keep uneven lineups inside the frame.
    left = min(max((frame.left + frame.right) // 2 - anchor_x, frame.left), frame.right - lineup.width)
    top = frame.top if hanging else frame.bottom - lineup.height
    return PlacedLineup(lineup, PixelRect(left, top, left + lineup.width, top + lineup.height))

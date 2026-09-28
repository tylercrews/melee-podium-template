"""Render one entrant's complete character lineup inside a Squares card."""

from __future__ import annotations

from collections.abc import Sequence

from PIL import Image

from models import Character, TournamentFormat
from portrait_assets import load_scaled_portrait, with_team_color
from portrait_scale_adjustment_for_each_mode import get_mode_portrait_scale


def square_portrait_scale_key(
    event_format: TournamentFormat,
    entrant_count: int,
    entrant_slot: int,
) -> str:
    """Return the scale entry owned by this distinct Squares card size."""

    if entrant_slot <= 0:
        raise ValueError("entrant_slot must be greater than zero")
    if event_format is TournamentFormat.SINGLES and entrant_count == 8:
        if entrant_slot == 1:
            return "squares_singles_top_8_first"
        if entrant_slot <= 4:
            return "squares_singles_top_8_second_through_fourth"
        if entrant_slot <= 8:
            return "squares_singles_top_8_fifth_and_seventh"
    elif event_format is TournamentFormat.DOUBLES:
        if entrant_slot == 1 and entrant_count in {3, 4}:
            return "squares_doubles_first"
        if entrant_count == 3 and entrant_slot <= 3:
            return "squares_doubles_top_3_second_through_third"
        if entrant_count == 4 and entrant_slot <= 4:
            return "squares_doubles_top_4_second_through_fourth"
    raise ValueError(
        "Unsupported Squares portrait tier: "
        f"{event_format.value} Top {entrant_count}, entrant slot {entrant_slot}"
    )


def _staggered_x_offsets(
    character_count: int,
    viewport_size: tuple[int, int],
) -> tuple[int, ...]:
    """Match Podium's center/left/right order at a card-relative spacing."""

    if character_count <= 0:
        return ()
    width, height = viewport_size
    spread = max(1, round(min(width, height) * 0.18))
    center_left_right = (0, -spread, spread)
    # As on the podiums, a two-character lineup balances around center. Three
    # or more starts at center and then alternates left/right in repeating sets.
    sequence = center_left_right[1:] if character_count == 2 else center_left_right
    return tuple(sequence[index % len(sequence)] for index in range(character_count))


def render_square_portrait_group(
    characters: Sequence[Character],
    viewport_size: tuple[int, int],
    *,
    scale_key: str,
    scale_multiplier: float = 1.0,
    team_color: str | None = None,
) -> Image.Image:
    """Bottom-align every selected character in a clipped Squares viewport.

    Portraits retain the shared per-character/pose relativity scale. As in the
    Podium renderer, the tallest image establishes the outer silhouette and
    smaller images are layered over it in center/left/right order.
    """

    if not characters:
        raise ValueError("A Squares entrant must have at least one character")
    if scale_multiplier <= 0:
        raise ValueError("scale_multiplier must be greater than zero")
    width, height = viewport_size
    if width <= 0 or height <= 0:
        raise ValueError("Squares portrait viewport dimensions must be positive")

    mode_scale = get_mode_portrait_scale(scale_key) * scale_multiplier
    portraits: list[Image.Image] = []
    for character in characters:
        selected = with_team_color(character, team_color)
        portrait = load_scaled_portrait(selected, mode_scale)
        visible_bounds = portrait.getbbox()
        if visible_bounds is not None:
            portraits.append(portrait.crop(visible_bounds))

    viewport = Image.new("RGBA", viewport_size, "#00000000")
    if not portraits:
        return viewport
    portraits.sort(key=lambda image: image.height, reverse=True)
    offsets = _staggered_x_offsets(len(portraits), viewport_size)
    for portrait, offset in zip(portraits, offsets, strict=True):
        viewport.alpha_composite(
            portrait,
            (
                round(width / 2 + offset - portrait.width / 2),
                height - portrait.height,
            ),
        )
    return viewport

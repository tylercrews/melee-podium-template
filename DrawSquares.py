"""Public API for flat, thick-outlined Squares result graphics."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path

from PIL import Image

from background_builder import BackgroundRequest
from creation import TextSettings
from creation_modes import CreationMode
from DrawPodium import PodiumFont
from geometric_content_renderer import LogoInput
from geometric_creation import draw_geometric_template
from geometric_formatting_colors import (
    GeometricFormattingColor,
    GeometricFormattingColors,
)
from models import DoublesTeam, SinglesEntrant, Tournament


class SquaresMode(StrEnum):
    SINGLES_TOP_8 = "singles_top_8"
    DOUBLES_TOP_3 = "doubles_top_3"
    DOUBLES_TOP_4 = "doubles_top_4"


DEFAULT_SQUARE_COLORS = GeometricFormattingColors.one(
    "#000000E8",
    "#E5243FFF",
)


def draw_squares(
    mode: SquaresMode | str,
    entrants: Sequence[SinglesEntrant] | Sequence[DoublesTeam],
    *,
    tournament: Tournament,
    square_colors: GeometricFormattingColors = DEFAULT_SQUARE_COLORS,
    background: BackgroundRequest | None = None,
    fill_color: str = "#00000000",
    header_layout: Mapping[str, str | None] | None = None,
    tournament_logo: LogoInput = None,
    font: PodiumFont | str = PodiumFont.TYROWO,
    custom_font_bytes: bytes | None = None,
    text_settings: TextSettings | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    """Draw one reviewed Squares layout with background and trim colors."""

    try:
        mode = SquaresMode(mode)
    except ValueError as error:
        choices = ", ".join(item.value for item in SquaresMode)
        raise ValueError(f"mode must be one of: {choices}") from error
    return draw_geometric_template(
        CreationMode.SQUARES,
        mode.value,
        entrants,
        tournament=tournament,
        formatting_colors=square_colors,
        background=background,
        fill_color=fill_color,
        header_layout=header_layout,
        tournament_logo=tournament_logo,
        font=font,
        custom_font_bytes=custom_font_bytes,
        text_settings=text_settings,
        output_path=output_path,
    )


def draw_singles_top_8(
    entrants: Sequence[SinglesEntrant],
    **kwargs: object,
) -> Image.Image:
    return draw_squares(SquaresMode.SINGLES_TOP_8, entrants, **kwargs)


def draw_doubles_top_3(
    teams: Sequence[DoublesTeam],
    **kwargs: object,
) -> Image.Image:
    return draw_squares(SquaresMode.DOUBLES_TOP_3, teams, **kwargs)


def draw_doubles_top_4(
    teams: Sequence[DoublesTeam],
    **kwargs: object,
) -> Image.Image:
    return draw_squares(SquaresMode.DOUBLES_TOP_4, teams, **kwargs)

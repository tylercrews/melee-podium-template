"""Public API for portrait-strip Eyes result graphics."""

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


class EyesMode(StrEnum):
    SINGLES_TOP_8 = "singles_top_8"
    SINGLES_TOP_10 = "singles_top_10"
    SINGLES_TOP_15 = "singles_top_15"
    SINGLES_TOP_16 = "singles_top_16"
    SINGLES_TOP_20 = "singles_top_20"
    SINGLES_TOP_25 = "singles_top_25"
    DOUBLES_TOP_3 = "doubles_top_3"
    DOUBLES_TOP_4 = "doubles_top_4"


DEFAULT_EYES_COLORS = GeometricFormattingColors(
    tuple(
        GeometricFormattingColor(color)
        for color in (
            "#FF5A20FF",
            "#087B37FF",
            "#0965A8FF",
            "#6B3140FF",
            "#064634FF",
            "#00564CFF",
            "#2D2945FF",
            "#312B4AFF",
        )
    )
)


def draw_eyes(
    mode: EyesMode | str,
    entrants: Sequence[SinglesEntrant] | Sequence[DoublesTeam],
    *,
    tournament: Tournament,
    rectangle_colors: GeometricFormattingColors = DEFAULT_EYES_COLORS,
    background: BackgroundRequest | None = None,
    fill_color: str = "#00000000",
    header_layout: Mapping[str, str] | None = None,
    tournament_logo: LogoInput = None,
    font: PodiumFont | str = PodiumFont.TYROWO,
    custom_font_bytes: bytes | None = None,
    text_settings: TextSettings | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    """Draw one reviewed Eyes layout with user-selectable rectangle colors."""

    try:
        mode = EyesMode(mode)
    except ValueError as error:
        choices = ", ".join(item.value for item in EyesMode)
        raise ValueError(f"mode must be one of: {choices}") from error
    return draw_geometric_template(
        CreationMode.EYES,
        mode.value,
        entrants,
        tournament=tournament,
        formatting_colors=rectangle_colors,
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
    return draw_eyes(EyesMode.SINGLES_TOP_8, entrants, **kwargs)


def draw_singles_top_10(
    entrants: Sequence[SinglesEntrant],
    **kwargs: object,
) -> Image.Image:
    return draw_eyes(EyesMode.SINGLES_TOP_10, entrants, **kwargs)


def draw_singles_top_15(
    entrants: Sequence[SinglesEntrant],
    **kwargs: object,
) -> Image.Image:
    return draw_eyes(EyesMode.SINGLES_TOP_15, entrants, **kwargs)


def draw_singles_top_16(
    entrants: Sequence[SinglesEntrant],
    **kwargs: object,
) -> Image.Image:
    return draw_eyes(EyesMode.SINGLES_TOP_16, entrants, **kwargs)


def draw_singles_top_20(
    entrants: Sequence[SinglesEntrant],
    **kwargs: object,
) -> Image.Image:
    return draw_eyes(EyesMode.SINGLES_TOP_20, entrants, **kwargs)


def draw_singles_top_25(
    entrants: Sequence[SinglesEntrant],
    **kwargs: object,
) -> Image.Image:
    return draw_eyes(EyesMode.SINGLES_TOP_25, entrants, **kwargs)


def draw_doubles_top_3(
    teams: Sequence[DoublesTeam],
    **kwargs: object,
) -> Image.Image:
    return draw_eyes(EyesMode.DOUBLES_TOP_3, teams, **kwargs)


def draw_doubles_top_4(
    teams: Sequence[DoublesTeam],
    **kwargs: object,
) -> Image.Image:
    return draw_eyes(EyesMode.DOUBLES_TOP_4, teams, **kwargs)

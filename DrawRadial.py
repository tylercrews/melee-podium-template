"""Public API for Singles Top 8 and Doubles Top 4 Radial layouts."""

from collections.abc import Sequence
from collections.abc import Mapping
from pathlib import Path

from PIL import Image

from background_builder import BackgroundRequest
from creation import TextSettings
from creation_modes import CreationMode
from DrawPodium import PodiumFont
from geometric_content_renderer import LogoInput
from geometric_creation import draw_geometric_template
from geometric_formatting_colors import GeometricFormattingColor, GeometricFormattingColors
from models import DoublesTeam, SinglesEntrant, Tournament


DEFAULT_RADIAL_COLORS = GeometricFormattingColors(tuple(
    GeometricFormattingColor(color)
    for color in ("#7D280AFF", "#73158FFF", "#73158FFF", "#7D280AFF", "#7D280AFF", "#73158FFF", "#73158FFF", "#7D280AFF")
))


DEFAULT_RADIAL_DOUBLES_COLORS = GeometricFormattingColors(tuple(
    DEFAULT_RADIAL_COLORS.for_slot(slot) for slot in (1, 3, 4, 7)
))

def draw_singles_top_8(
    entrants: Sequence[SinglesEntrant],
    *,
    tournament: Tournament,
    slice_colors: GeometricFormattingColors = DEFAULT_RADIAL_COLORS,
    background: BackgroundRequest | None = None,
    fill_color: str = "#00000000",
    header_layout: Mapping[str, str] | None = None,
    tournament_logo: LogoInput = None,
    logo_scale: float | None = None,
    font: PodiumFont | str = PodiumFont.TYROWO,
    custom_font_bytes: bytes | None = None,
    text_settings: TextSettings | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    """Render eight clipped portraits; omitted logo_scale fits the center box."""
    return draw_geometric_template(
        CreationMode.RADIAL, "singles_top_8", entrants,
        tournament=tournament, formatting_colors=slice_colors, background=background,
        fill_color=fill_color, header_layout=header_layout, tournament_logo=tournament_logo,
        logo_scale=logo_scale, font=font, custom_font_bytes=custom_font_bytes,
        text_settings=text_settings, output_path=output_path,
    )


def draw_doubles_top_4(
    entrants: Sequence[DoublesTeam],
    *,
    tournament: Tournament,
    slice_colors: GeometricFormattingColors = DEFAULT_RADIAL_DOUBLES_COLORS,
    background: BackgroundRequest | None = None,
    fill_color: str = "#00000000",
    header_layout: Mapping[str, str] | None = None,
    tournament_logo: LogoInput = None,
    logo_scale: float | None = None,
    font: PodiumFont | str = PodiumFont.TYROWO,
    custom_font_bytes: bytes | None = None,
    text_settings: TextSettings | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    """Render four team blocks with the eight original portrait anchors."""
    return draw_geometric_template(
        CreationMode.RADIAL, "doubles_top_4", entrants,
        tournament=tournament, formatting_colors=slice_colors, background=background,
        fill_color=fill_color, header_layout=header_layout, tournament_logo=tournament_logo,
        logo_scale=logo_scale, font=font, custom_font_bytes=custom_font_bytes,
        text_settings=text_settings, output_path=output_path,
    )

"""Public API for the Singles Top 8 and Doubles Top 3 Flying V layouts."""

from collections.abc import Mapping, Sequence
from pathlib import Path

from PIL import Image

from background_builder import BackgroundRequest
from creation import CreationPipeline, CreationRequest, TextSettings
from creation_modes import CreationMode, ModeOptions, ModeSelection, flying_v_singles_variant
from DrawPodium import PodiumFont
from flying_v_content_renderer import FlyingVContentRenderer
from geometric_content_renderer import LogoInput
from mode_preferences import ModePreferenceRepository
from models import DoublesTeam, SinglesEntrant, Tournament, TournamentFormat


def _draw_flying_v(
    event_format: TournamentFormat,
    entrant_count: int,
    entrants: Sequence[SinglesEntrant] | Sequence[DoublesTeam],
    *,
    tournament: Tournament,
    background: BackgroundRequest | None,
    fill_color: str,
    header_layout: Mapping[str, str] | None,
    tournament_logo: LogoInput,
    font: PodiumFont | str,
    custom_font_bytes: bytes | None,
    text_settings: TextSettings | None,
    output_path: str | Path | None,
    variant: str | None = None,
) -> Image.Image:
    selection = ModeSelection(CreationMode.FLYING_V, ModeOptions(event_format, entrant_count, variant))
    repository = ModePreferenceRepository()
    preferences = repository.load(selection)
    request = CreationRequest(
        selection=selection,
        background=background or BackgroundRequest(size=preferences.canvas_size, fill_color=fill_color),
        entrants=entrants,
        tournament=tournament,
        header_layout=header_layout,
        text_settings=text_settings or TextSettings(),
    )
    renderer = FlyingVContentRenderer(PodiumFont(font), tournament_logo, custom_font_bytes)
    result = CreationPipeline(content_renderers={CreationMode.FLYING_V: renderer}, preferences=repository).create(request)
    if output_path is not None:
        result.save(output_path, format="PNG")
    return result


def draw_singles_top_8(
    entrants: Sequence[SinglesEntrant],
    *,
    tournament: Tournament,
    background: BackgroundRequest | None = None,
    fill_color: str = "#00000000",
    header_layout: Mapping[str, str] | None = None,
    tournament_logo: LogoInput = None,
    font: PodiumFont | str = PodiumFont.TYROWO,
    custom_font_bytes: bytes | None = None,
    text_settings: TextSettings | None = None,
    output_path: str | Path | None = None,
    vertically_reversed: bool = False,
    second_place_flipped: bool = False,
) -> Image.Image:
    """Render first place in front, second behind it, and the rest flying out.

    ``vertically_reversed`` flips the layout: first place leads from the top,
    the title moves to the bottom, and the logo and metadata take the top corners.
    ``second_place_flipped`` mirrors second place's label to the other side of
    its figures: top center-left instead of top center-right, or bottom
    center-right instead of bottom center-left when reversed.
    """
    return _draw_flying_v(
        TournamentFormat.SINGLES, 8, entrants, tournament=tournament, background=background,
        fill_color=fill_color, header_layout=header_layout, tournament_logo=tournament_logo, font=font,
        custom_font_bytes=custom_font_bytes, text_settings=text_settings, output_path=output_path,
        variant=flying_v_singles_variant(vertically_reversed, second_place_flipped),
    )


def draw_doubles_top_3(
    entrants: Sequence[DoublesTeam],
    *,
    tournament: Tournament,
    background: BackgroundRequest | None = None,
    fill_color: str = "#00000000",
    header_layout: Mapping[str, str] | None = None,
    tournament_logo: LogoInput = None,
    font: PodiumFont | str = PodiumFont.TYROWO,
    custom_font_bytes: bytes | None = None,
    text_settings: TextSettings | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    """Render the winning team in front with second and third flanking above."""
    return _draw_flying_v(
        TournamentFormat.DOUBLES, 3, entrants, tournament=tournament, background=background,
        fill_color=fill_color, header_layout=header_layout, tournament_logo=tournament_logo, font=font,
        custom_font_bytes=custom_font_bytes, text_settings=text_settings, output_path=output_path,
    )

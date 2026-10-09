"""Shared creation entry point for Eyes, Squares, and Radial APIs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from PIL import Image

from background_builder import BackgroundRequest
from creation import CreationPipeline, CreationRequest, TextSettings
from creation_modes import CreationMode, ModeOptions, ModeSelection
from DrawPodium import PodiumFont
from geometric_content_renderer import EyesContentRenderer, LogoInput, SquaresContentRenderer
from geometric_formatting_colors import GeometricFormattingColors
from mode_preferences import ModePreferenceRepository
from models import DoublesTeam, SinglesEntrant, Tournament, TournamentFormat
from radial_content_renderer import RadialContentRenderer


EntrantResult = SinglesEntrant | DoublesTeam


def draw_geometric_template(
    creation_mode: CreationMode,
    submode_id: str,
    entrants: Sequence[EntrantResult],
    *,
    tournament: Tournament,
    formatting_colors: GeometricFormattingColors,
    background: BackgroundRequest | None = None,
    fill_color: str = "#00000000",
    header_layout: Mapping[str, str | None] | None = None,
    tournament_logo: LogoInput = None,
    logo_scale: float | None = None,
    font: PodiumFont | str = PodiumFont.TYROWO,
    custom_font_bytes: bytes | None = None,
    text_settings: TextSettings | None = None,
    output_path: str | Path | None = None,
) -> Image.Image:
    """Render one reviewed non-podium layout through the creation pipeline."""

    if creation_mode not in {CreationMode.EYES, CreationMode.SQUARES, CreationMode.RADIAL}:
        raise ValueError("draw_geometric_template only supports Eyes, Squares, and Radial")
    try:
        font = PodiumFont(font)
    except ValueError as error:
        choices = ", ".join(item.value for item in PodiumFont)
        raise ValueError(f"font must be one of: {choices}") from error
    event_format = (
        TournamentFormat.DOUBLES
        if submode_id.startswith("doubles_")
        else TournamentFormat.SINGLES
    )
    try:
        entrant_count = int(submode_id.rsplit("_", 1)[1])
    except (IndexError, ValueError) as error:
        raise ValueError(f"Invalid geometric submode: {submode_id}") from error
    selection = ModeSelection(
        creation_mode,
        ModeOptions(event_format=event_format, entrant_count=entrant_count),
    )
    repository = ModePreferenceRepository()
    preferences = repository.load(selection)
    background = background or BackgroundRequest(
        size=preferences.canvas_size,
        fill_color=fill_color,
    )
    settings = text_settings or TextSettings()
    request = CreationRequest(
        selection=selection,
        background=background,
        entrants=entrants,
        tournament=tournament,
        formatting_colors=formatting_colors,
        header_layout=header_layout,
        text_settings=settings,
    )
    renderer = (
        EyesContentRenderer(font, tournament_logo, custom_font_bytes)
        if creation_mode is CreationMode.EYES
        else RadialContentRenderer(font, tournament_logo, custom_font_bytes, logo_scale)
        if creation_mode is CreationMode.RADIAL
        else SquaresContentRenderer(font, tournament_logo, custom_font_bytes)
    )
    result = CreationPipeline(
        content_renderers={creation_mode: renderer},
        preferences=repository,
    ).create(request)
    if output_path is not None:
        result.save(output_path, format="PNG")
    return result

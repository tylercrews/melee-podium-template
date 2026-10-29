"""Render deterministic example images for the frontend Format-step preview."""

from __future__ import annotations

import random
from collections.abc import Mapping

from PIL import Image

from background_builder import (
    BUILTIN_BACKGROUND_SIZES,
    BackgroundRequest,
    ImagePlacement,
    PixelRect,
    cover_crop,
    create_background,
)
from creation import CreationRequest
from creation import TextSettings
from clapping_colors import resolve_clapping_podium_colors
from placement_numbering import default_tournament_placing, numbered_preferences
from DrawPodium import PodiumFont
from creation_modes import FLYING_V_VERTICALLY_REVERSED, CreationMode, ModeOptions, ModeSelection, PodiumStyle
from formatting_assets import FormattingAssetRenderer
from geometric_content_renderer import EyesContentRenderer, SquaresContentRenderer
from geometric_formatting_colors import GeometricFormattingColors
from legacy_podium_content_renderer import LegacyPodiumContentRenderer
from podiums_clapping_renderer import ClappingLayout, PodiumsClappingContentRenderer
from extended_clapping_renderer import DoublesClappingContentRenderer, SinglesTop16ClappingContentRenderer
from clapping_grid_renderer import ClappingGridContentRenderer
from clapping_grid_layouts import GRID_LAYOUTS, GRID_VARIANTS
from entrant_visibility import apply_visibility, visible_preferences
from layout_text_defaults import layout_text_defaults
from mode_preferences import ModePreferenceRepository
from radial_content_renderer import RadialContentRenderer
from flying_v_content_renderer import FlyingVContentRenderer
from models import DoublesTeam, SinglesEntrant, Tournament, TournamentFormat
from podium_colors import PodiumColorConfiguration, PodiumColorPreset
from sample_creation_data import (
    sample_singles_entrants,
    sample_top_4_teams,
    sample_top_8_teams,
    sample_top_8_entrants,
    sample_tournament,
)


PREVIEW_BACKGROUND_ASSET_ID = "00_Battlefield_5000_5000_resaved.png"
SUPPORTED_LAYOUTS = frozenset(
    {
        (TournamentFormat.SINGLES, 3, None),
        (TournamentFormat.SINGLES, 4, None),
        (TournamentFormat.SINGLES, 8, None),
        (TournamentFormat.SINGLES, 8, "four_podium"),
        (TournamentFormat.SINGLES, 16, "clapping"),
        (TournamentFormat.DOUBLES, 3, None),
        (TournamentFormat.DOUBLES, 4, None),
        (TournamentFormat.DOUBLES, 8, "four_podium"),
        *((TournamentFormat.SINGLES, row["entrant_count"], f"clapping_grid_{row['columns']}") for row in GRID_LAYOUTS),
    }
)
SUPPORTED_SQUARE_LAYOUTS = frozenset(
    {
        (TournamentFormat.SINGLES, 8, None),
        (TournamentFormat.DOUBLES, 3, None),
        (TournamentFormat.DOUBLES, 4, None),
    }
)
SUPPORTED_FLYING_V_LAYOUTS = frozenset({
    (TournamentFormat.SINGLES, 8, None),
    (TournamentFormat.SINGLES, 8, FLYING_V_VERTICALLY_REVERSED),
    (TournamentFormat.DOUBLES, 3, None),
})
SUPPORTED_EYES_LAYOUTS = frozenset(
    {
        *((TournamentFormat.SINGLES, count, None) for count in (8, 10, 15, 16, 20, 25)),
        (TournamentFormat.DOUBLES, 3, None),
        (TournamentFormat.DOUBLES, 4, None),
    }
)


def prepare_format_preview(
    style: PodiumStyle,
    event_format: TournamentFormat,
    entrant_count: int,
    variant: str | None = None,
    *,
    transparent: bool = False,
    podium_colors: PodiumColorConfiguration | None = None,
    header_layout: Mapping[str, str] | None = None,
    font: PodiumFont = PodiumFont.TYROWO,
    custom_font_bytes: bytes | None = None,
    text_settings: TextSettings | None = None,
    creation_mode: CreationMode = CreationMode.PODIUM,
    entrants: list[SinglesEntrant] | list[DoublesTeam] | None = None,
    tournament: Tournament | None = None,
    formatting_colors: GeometricFormattingColors | None = None,
    tournament_logo: Image.Image | None = None,
    logo_scale: float | None = None,
    animated: bool | None = None,
    composite_background: Image.Image | None = None,
    composite_overlay: Image.Image | None = None,
    entrant_visibility: list[dict] | None = None,
) -> Image.Image | ClappingLayout:
    """Return a full example render for one supported frontend format."""

    if not isinstance(style, PodiumStyle):
        raise TypeError("style must be a PodiumStyle")
    layout = (event_format, entrant_count, variant)
    supported_layouts = (
        SUPPORTED_LAYOUTS
        if creation_mode is CreationMode.PODIUM
        else SUPPORTED_SQUARE_LAYOUTS
        if creation_mode is CreationMode.SQUARES
        else SUPPORTED_EYES_LAYOUTS
        if creation_mode is CreationMode.EYES
        else frozenset({(TournamentFormat.SINGLES, 8, None), (TournamentFormat.DOUBLES, 4, None)})
        if creation_mode is CreationMode.RADIAL
        else SUPPORTED_FLYING_V_LAYOUTS
        if creation_mode is CreationMode.FLYING_V
        else frozenset()
    )
    if layout not in supported_layouts:
        raise ValueError("Unsupported format preview layout")

    selection = ModeSelection(
        creation_mode,
        ModeOptions(
            event_format=event_format,
            entrant_count=entrant_count,
            variant=variant,
            podium_style=style if creation_mode is CreationMode.PODIUM else None,
            animated=animated,
        ),
    )
    preferences = ModePreferenceRepository().load(selection)
    text_settings = text_settings or TextSettings(**layout_text_defaults(selection))
    preferences = numbered_preferences(preferences, text_settings.use_tournament_placing)
    output_size = preferences.canvas_size
    if transparent:
        background = BackgroundRequest(size=output_size)
    else:
        source_size = BUILTIN_BACKGROUND_SIZES[PREVIEW_BACKGROUND_ASSET_ID]
        background = BackgroundRequest(
            size=output_size,
            image=ImagePlacement(
                asset_id=PREVIEW_BACKGROUND_ASSET_ID,
                source_crop=cover_crop(source_size, output_size),
                destination=PixelRect(0, 0, output_size.width, output_size.height),
            ),
        )
    randomizer = random.Random(2026)
    if entrants is None:
        entrants = (
            (
                sample_top_8_entrants(randomizer)
                if entrant_count == 8
                else sample_singles_entrants(entrant_count, randomizer)
            )
            if event_format is TournamentFormat.SINGLES
            else (sample_top_8_teams(randomizer) if entrant_count == 8 else sample_top_4_teams(randomizer)[:entrant_count])
        )
    else:
        expected_type = SinglesEntrant if event_format is TournamentFormat.SINGLES else DoublesTeam
        if len(entrants) < entrant_count or any(not isinstance(entrant, expected_type) for entrant in entrants[:entrant_count]):
            raise ValueError("Preview entrants do not match the selected layout")
        entrants = entrants[:entrant_count]
    entrants = apply_visibility(entrants, entrant_visibility)
    preferences = visible_preferences(preferences, entrants)
    podium_colors = (
        podium_colors or PodiumColorConfiguration.from_preset(PodiumColorPreset.LEGACY)
        if creation_mode is CreationMode.PODIUM and style is PodiumStyle.CUSTOMIZABLE
        else None
    )
    podium_colors = resolve_clapping_podium_colors(selection, podium_colors)
    if creation_mode in {CreationMode.EYES, CreationMode.SQUARES, CreationMode.RADIAL} and formatting_colors is None:
        raise ValueError("Eyes, Squares, and Radial previews require formatting colors")
    request = CreationRequest(
        selection=selection,
        background=background,
        entrants=entrants,
        tournament=tournament or sample_tournament(event_format),
        podium_colors=podium_colors,
        formatting_colors=formatting_colors,
        header_layout=header_layout,
        text_settings=text_settings,
    )
    # Format previews intentionally use the preview rendering path while these
    # reviewed preference files remain marked ready:false. Production creation
    # continues to refuse unfinished preference sets in CreationPipeline.
    canvas = create_background(background)
    formatted = FormattingAssetRenderer().draw(
        canvas,
        preferences,
        podium_colors or formatting_colors,
    )
    if creation_mode is CreationMode.PODIUM and variant in {"four_podium", "clapping", *GRID_VARIANTS}:
        renderer_type = (
            ClappingGridContentRenderer if variant in GRID_VARIANTS
            else DoublesClappingContentRenderer if event_format is TournamentFormat.DOUBLES
            else SinglesTop16ClappingContentRenderer if entrant_count == 16
            else PodiumsClappingContentRenderer
        )
        renderer = renderer_type(font=font, custom_font_bytes=custom_font_bytes)
        return renderer.prepare(formatted, request, preferences, background=composite_background, overlay=composite_overlay)
    renderer = (
        LegacyPodiumContentRenderer(font=font, custom_font_bytes=custom_font_bytes)
        if creation_mode is CreationMode.PODIUM
        else EyesContentRenderer(font=font, custom_font_bytes=custom_font_bytes)
        if creation_mode is CreationMode.EYES
        else RadialContentRenderer(font=font, tournament_logo=tournament_logo, custom_font_bytes=custom_font_bytes, logo_scale=logo_scale)
        if creation_mode is CreationMode.RADIAL
        else FlyingVContentRenderer(font=font, custom_font_bytes=custom_font_bytes)
        if creation_mode is CreationMode.FLYING_V
        else SquaresContentRenderer(font=font, custom_font_bytes=custom_font_bytes)
    )
    return renderer.draw(formatted, request, preferences)


def render_format_preview(*args, **kwargs) -> Image.Image:
    """Return a still render for offline reviews and non-animated callers."""
    result = prepare_format_preview(*args, **kwargs)
    return result.frame() if isinstance(result, ClappingLayout) else result


"""Render deterministic example images for the frontend Format-step preview."""

from __future__ import annotations

from functools import lru_cache
from io import BytesIO
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
from DrawPodium import PodiumFont
from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from formatting_assets import FormattingAssetRenderer
from legacy_podium_content_renderer import LegacyPodiumContentRenderer
from mode_preferences import ModePreferenceRepository
from models import TournamentFormat
from podium_colors import PodiumColorConfiguration, PodiumColorPreset
from sample_creation_data import sample_top_4_teams, sample_top_8_entrants, sample_tournament


PREVIEW_BACKGROUND_ASSET_ID = "00_Battlefield_5000_5000_resaved.png"
SUPPORTED_LAYOUTS = frozenset(
    {
        (TournamentFormat.SINGLES, 3, None),
        (TournamentFormat.SINGLES, 4, None),
        (TournamentFormat.SINGLES, 8, None),
        (TournamentFormat.SINGLES, 8, "four_podium"),
        (TournamentFormat.DOUBLES, 3, None),
        (TournamentFormat.DOUBLES, 4, None),
    }
)


def render_format_preview(
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
) -> Image.Image:
    """Return a full example render for one currently supported podium format."""

    if not isinstance(style, PodiumStyle):
        raise TypeError("style must be a PodiumStyle")
    layout = (event_format, entrant_count, variant)
    if layout not in SUPPORTED_LAYOUTS:
        raise ValueError("Unsupported format preview layout")

    selection = ModeSelection(
        CreationMode.PODIUM,
        ModeOptions(
            event_format=event_format,
            entrant_count=entrant_count,
            variant=variant,
            podium_style=style,
        ),
    )
    preferences = ModePreferenceRepository().load(selection)
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
    entrants = (
        sample_top_8_entrants(randomizer)[:entrant_count]
        if event_format is TournamentFormat.SINGLES
        else sample_top_4_teams(randomizer)[:entrant_count]
    )
    podium_colors = (
        podium_colors or PodiumColorConfiguration.from_preset(PodiumColorPreset.LEGACY)
        if style is PodiumStyle.CUSTOMIZABLE
        else None
    )
    request = CreationRequest(
        selection=selection,
        background=background,
        entrants=entrants,
        tournament=sample_tournament(event_format),
        podium_colors=podium_colors,
        header_layout=header_layout,
        text_settings=text_settings or TextSettings(),
    )
    # Format previews intentionally use the preview rendering path while these
    # reviewed preference files remain marked ready:false. Production creation
    # continues to refuse unfinished preference sets in CreationPipeline.
    canvas = create_background(background)
    formatted = FormattingAssetRenderer().draw(canvas, preferences, podium_colors)
    return LegacyPodiumContentRenderer(font=font, custom_font_bytes=custom_font_bytes).draw(formatted, request, preferences)


@lru_cache(maxsize=len(SUPPORTED_LAYOUTS) * len(PodiumStyle) * 2)
def render_format_preview_png(
    style: PodiumStyle,
    event_format: TournamentFormat,
    entrant_count: int,
    variant: str | None = None,
    *,
    transparent: bool = False,
) -> bytes:
    """Return cached PNG bytes for a supported example render."""

    image = render_format_preview(
        style,
        event_format,
        entrant_count,
        variant,
        transparent=transparent,
    )
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


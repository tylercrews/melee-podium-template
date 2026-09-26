"""Coordinate the complete mode-driven image creation pipeline."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from PIL import Image

from background_builder import (
    BUILTIN_BACKGROUND_ASSETS,
    BackgroundAssetProvider,
    BackgroundRequest,
    create_background,
)
from content_renderer import ContentRenderer
from creation_modes import CreationMode, ModeSelection, PodiumStyle
from formatting_assets import FormattingAssetRenderer, FormattingRenderer
from mode_preferences import (
    ModePreferenceRepository,
    ModePreferences,
    ModePreferencesProvider,
)
from models import DoublesTeam, SinglesEntrant, Tournament, TournamentFormat
from podium_colors import PodiumColorConfiguration, PodiumColorInput, PodiumColorSelection


EntrantResult = SinglesEntrant | DoublesTeam


class PreferencesNotReadyError(RuntimeError):
    """Raised when a scaffold layout has not been populated and reviewed yet."""


@dataclass(frozen=True, slots=True)
class CreationRequest:
    """Everything needed after the user has selected a mode and its options."""

    selection: ModeSelection
    background: BackgroundRequest
    entrants: Sequence[EntrantResult]
    tournament: Tournament
    podium_colors: PodiumColorInput | None = None
    header_layout: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.selection, ModeSelection):
            raise TypeError("selection must be a ModeSelection")
        if not isinstance(self.background, BackgroundRequest):
            raise TypeError("background must be a BackgroundRequest")
        if not isinstance(self.tournament, Tournament):
            raise TypeError("tournament must be a Tournament")
        if self.podium_colors is not None and not isinstance(
            self.podium_colors,
            (PodiumColorSelection, PodiumColorConfiguration),
        ):
            raise TypeError(
                "podium_colors must be a PodiumColorSelection, "
                "PodiumColorConfiguration, or null"
            )
        if self.header_layout is not None:
            expected_positions = {"top_left", "top_middle", "top_right"}
            expected_contents = {"tournament_logo", "tournament_title", "metadata"}
            if set(self.header_layout) != expected_positions or set(self.header_layout.values()) != expected_contents:
                raise ValueError("header_layout must assign each header item to one unique top position")
            object.__setattr__(self, "header_layout", dict(self.header_layout))
        entrants = tuple(self.entrants)
        object.__setattr__(self, "entrants", entrants)
        options = self.selection.options
        if len(entrants) != options.entrant_count:
            raise ValueError(
                f"Expected {options.entrant_count} included entrants, got {len(entrants)}"
            )
        if self.tournament.event_format is not options.event_format:
            raise ValueError("Tournament format must match the selected mode options")
        expected_type = (
            SinglesEntrant
            if options.event_format is TournamentFormat.SINGLES
            else DoublesTeam
        )
        if any(not isinstance(entrant, expected_type) for entrant in entrants):
            raise TypeError(
                f"{options.event_format.value} mode requires {expected_type.__name__} entrants"
            )
        customizable = (
            self.selection.mode is CreationMode.PODIUM
            and options.podium_style is PodiumStyle.CUSTOMIZABLE
        )
        if customizable and self.podium_colors is None:
            raise ValueError("Customizable podiums require podium_colors")
        if not customizable and self.podium_colors is not None:
            raise ValueError("podium_colors are only valid for customizable podiums")


@dataclass(slots=True)
class CreationPipeline:
    """Resolve preferences, background, framing assets, then layered content."""

    content_renderers: Mapping[CreationMode, ContentRenderer]
    preferences: ModePreferencesProvider = field(
        default_factory=ModePreferenceRepository
    )
    formatting_renderer: FormattingRenderer = field(
        default_factory=FormattingAssetRenderer
    )
    background_assets: BackgroundAssetProvider = BUILTIN_BACKGROUND_ASSETS

    def create(self, request: CreationRequest) -> Image.Image:
        mode_preferences = self.preferences.load(request.selection)
        self._validate_preferences(request, mode_preferences)

        background = create_background(
            request.background,
            assets=self.background_assets,
        )
        formatted = self.formatting_renderer.draw(
            background,
            mode_preferences,
            request.podium_colors,
        )
        self._validate_stage_image("formatting", formatted, request.background)

        try:
            content_renderer = self.content_renderers[request.selection.mode]
        except KeyError as error:
            raise NotImplementedError(
                f"No content renderer is registered for {request.selection.mode.value} mode"
            ) from error
        result = content_renderer.draw(formatted, request, mode_preferences)
        self._validate_stage_image("content", result, request.background)
        return result

    @staticmethod
    def _validate_preferences(
        request: CreationRequest,
        preferences: ModePreferences,
    ) -> None:
        if preferences.selection != request.selection:
            raise ValueError("Loaded preferences do not match the mode selection")
        if not preferences.ready:
            raise PreferencesNotReadyError(
                "Preferences are still a scaffold for "
                f"{request.selection.mode.value}/{request.selection.submode_id}"
            )
        if preferences.canvas_size != request.background.size:
            raise ValueError(
                "Background dimensions must match the selected mode preferences"
            )

    @staticmethod
    def _validate_stage_image(
        stage: str,
        image: object,
        background: BackgroundRequest,
    ) -> None:
        if not isinstance(image, Image.Image):
            raise TypeError(f"{stage} renderer must return a Pillow image")
        if image.mode != "RGBA" or image.size != background.size.as_tuple():
            raise ValueError(
                f"{stage} renderer must preserve the RGBA canvas dimensions"
            )

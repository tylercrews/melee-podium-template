"""Draw mode-specific framing assets over a constructed background."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PIL import Image

from creation_modes import CreationMode, ModeSelection, PodiumStyle
from mode_preferences import FormattingAssetPlacement, ModePreferences
from podium_colors import (
    PodiumColorInput,
    apply_podium_colors,
    podium_color_for_slot,
)


PROJECT_ROOT = Path(__file__).resolve().parent
FORMATTING_ASSET_FOLDER = PROJECT_ROOT / "formatting_assets"
PLACEMENT_TAG_ASSET_FOLDER = FORMATTING_ASSET_FOLDER / "placement_numbers"


class FormattingAssetProvider(Protocol):
    def open(self, selection: ModeSelection, asset_id: str) -> Image.Image:
        """Return a caller-owned RGBA image for a formatting asset."""


class PlacementTagAssetProvider(Protocol):
    def open(self, asset_id: str) -> Image.Image:
        """Return a caller-owned RGBA image for a placement-number asset."""


class FormattingRenderer(Protocol):
    def draw(
        self,
        canvas: Image.Image,
        preferences: ModePreferences,
        podium_colors: PodiumColorInput | None = None,
    ) -> Image.Image:
        """Draw the mode's framing assets over ``canvas``."""


@dataclass(frozen=True, slots=True)
class LocalFormattingAssets:
    """Load assets from the selected mode/style's formatting-asset folder."""

    root: Path = FORMATTING_ASSET_FOLDER

    def open(self, selection: ModeSelection, asset_id: str) -> Image.Image:
        if not isinstance(asset_id, str) or Path(asset_id).name != asset_id:
            raise ValueError("formatting asset_id must be a filename, not a path")
        folder = self.root / selection.mode.value
        if selection.mode is CreationMode.PODIUM:
            assert selection.options.podium_style is not None
            folder /= selection.options.podium_style.value
        path = folder / asset_id
        if path.suffix.casefold() != ".png" or not path.is_file():
            raise FileNotFoundError(f"Formatting asset does not exist: {asset_id}")
        with Image.open(path) as source:
            return source.convert("RGBA")


@dataclass(frozen=True, slots=True)
class LocalPlacementTagAssets:
    """Load canonical placement-number PNGs shared by podium layouts."""

    root: Path = PLACEMENT_TAG_ASSET_FOLDER

    def open(self, asset_id: str) -> Image.Image:
        if not isinstance(asset_id, str) or Path(asset_id).name != asset_id:
            raise ValueError("placement tag asset_id must be a filename, not a path")
        path = self.root / asset_id
        if path.suffix.casefold() != ".png" or not path.is_file():
            raise FileNotFoundError(f"Placement tag asset does not exist: {asset_id}")
        with Image.open(path) as source:
            return source.convert("RGBA")


@dataclass(frozen=True, slots=True)
class FormattingAssetRenderer:
    assets: FormattingAssetProvider = LocalFormattingAssets()
    placement_tag_assets: PlacementTagAssetProvider = LocalPlacementTagAssets()

    def draw(
        self,
        canvas: Image.Image,
        preferences: ModePreferences,
        podium_colors: PodiumColorInput | None = None,
    ) -> Image.Image:
        """Composite mode assets in their mode-specific visual order."""

        customizable = (
            preferences.selection.mode is CreationMode.PODIUM
            and preferences.selection.options.podium_style
            is PodiumStyle.CUSTOMIZABLE
        )
        if customizable and podium_colors is None:
            raise ValueError("Customizable podiums require podium_colors")
        if not customizable and podium_colors is not None:
            raise ValueError("podium_colors are only valid for customizable podiums")

        result = canvas.convert("RGBA")
        for placement in _formatting_asset_draw_order(preferences):
            source = self.assets.open(preferences.selection, placement.asset_id)
            try:
                layer = source.copy()
            finally:
                source.close()
            destination = placement.destination
            if customizable:
                assert podium_colors is not None
                try:
                    slot = int(placement.slot_id.removeprefix("podium_"))
                except ValueError:
                    # Generic/custom providers may expose a single asset under
                    # a semantic ID rather than a numbered layout slot.
                    slot = 1
                layer = apply_podium_colors(
                    layer,
                    podium_color_for_slot(podium_colors, slot),
                )
            if layer.size != (destination.width, destination.height):
                # Recolor semantic masks before resampling. Lanczos creates
                # intermediate colors at class boundaries; if it runs first,
                # cyan/blue/red fringe pixels no longer reliably identify
                # their semantic class and can leak into the final podium.
                layer = layer.resize(
                    (destination.width, destination.height),
                    Image.Resampling.LANCZOS,
                )
            _composite_clipped(result, layer, destination.as_tuple())

        for placement in sorted(
            preferences.placement_tags,
            key=lambda item: (item.z_index, item.slot_id),
        ):
            source = self.placement_tag_assets.open(placement.asset_id)
            try:
                layer = source.copy()
            finally:
                source.close()
            layer.thumbnail(
                placement.max_size.as_tuple(),
                Image.Resampling.LANCZOS,
            )
            left = placement.anchor.x - layer.width // 2
            top = placement.anchor.y - layer.height // 2
            _composite_clipped(
                result,
                layer,
                (left, top, left + layer.width, top + layer.height),
            )
        return result


def _formatting_asset_draw_order(
    preferences: ModePreferences,
) -> tuple[FormattingAssetPlacement, ...]:
    """Return framing assets in the order appropriate for their mode geometry."""

    if preferences.selection.mode is CreationMode.PODIUM:
        # The legacy and customizable podium boxes are viewed from above/right.
        # Drawing from left to right keeps each box's right-facing edge in front
        # of the podium immediately to its left.
        return tuple(
            sorted(
                preferences.formatting_assets,
                key=lambda item: (
                    item.destination.left,
                    item.destination.top,
                    item.slot_id,
                ),
            )
        )
    return tuple(
        sorted(
            preferences.formatting_assets,
            key=lambda item: (item.z_index, item.slot_id),
        )
    )


def _composite_clipped(
    canvas: Image.Image,
    layer: Image.Image,
    destination: tuple[int, int, int, int],
) -> None:
    left, top, right, bottom = destination
    visible_left = max(0, left)
    visible_top = max(0, top)
    visible_right = min(canvas.width, right)
    visible_bottom = min(canvas.height, bottom)
    if visible_right <= visible_left or visible_bottom <= visible_top:
        return
    visible_layer = layer.crop(
        (
            visible_left - left,
            visible_top - top,
            visible_right - left,
            visible_bottom - top,
        )
    )
    canvas.alpha_composite(visible_layer, (visible_left, visible_top))

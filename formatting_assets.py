"""Draw mode-specific framing assets over a constructed background."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageDraw

from creation_modes import CreationMode, ModeSelection, PodiumStyle
from geometric_formatting_colors import GeometricFormattingColors
from mode_preferences import FormattingAssetPlacement, ModePreferences
from podium_colors import (
    PodiumColorConfiguration,
    PodiumColorInput,
    PodiumColorSelection,
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
        colors: PodiumColorInput | GeometricFormattingColors | None = None,
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
        colors: PodiumColorInput | GeometricFormattingColors | None = None,
    ) -> Image.Image:
        """Composite mode assets in their mode-specific visual order."""

        customizable = (
            preferences.selection.mode is CreationMode.PODIUM
            and preferences.selection.options.podium_style
            is PodiumStyle.CUSTOMIZABLE
        )
        geometric = preferences.selection.mode in {
            CreationMode.EYES,
            CreationMode.SQUARES,
        }
        if customizable and not isinstance(colors, (PodiumColorSelection, PodiumColorConfiguration)):
            raise ValueError("Customizable podiums require podium_colors")
        if geometric and not isinstance(colors, GeometricFormattingColors):
            raise ValueError("Eyes and Squares require geometric formatting colors")
        if not customizable and not geometric and colors is not None:
            raise ValueError("Formatting colors are not valid for this mode")

        result = canvas.convert("RGBA")
        for placement in _formatting_asset_draw_order(preferences):
            if geometric:
                assert isinstance(colors, GeometricFormattingColors)
                _draw_geometric_asset(result, preferences, placement, colors)
                continue
            source = self.assets.open(preferences.selection, placement.asset_id)
            try:
                layer = source.copy()
            finally:
                source.close()
            destination = placement.destination
            if customizable:
                assert isinstance(colors, (PodiumColorSelection, PodiumColorConfiguration))
                try:
                    slot = int(placement.slot_id.removeprefix("podium_"))
                except ValueError:
                    # Generic/custom providers may expose a single asset under
                    # a semantic ID rather than a numbered layout slot.
                    slot = 1
                layer = apply_podium_colors(
                    layer,
                    podium_color_for_slot(colors, slot),
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


def _draw_geometric_asset(
    canvas: Image.Image,
    preferences: ModePreferences,
    placement: FormattingAssetPlacement,
    colors: GeometricFormattingColors,
) -> None:
    """Draw scalable mode-owned framing without maintaining raster masks."""

    destination = placement.destination
    size = (destination.width, destination.height)
    layer = Image.new("RGBA", size, "#00000000")
    draw = ImageDraw.Draw(layer)
    if placement.asset_id == "eyes_header_bar":
        draw.rounded_rectangle(
            (0, 0, size[0] - 1, size[1] - 1),
            radius=min(30, size[0] // 6),
            fill="#05070BE6",
        )
    else:
        try:
            slot = int(placement.slot_id.rsplit("_", 1)[1])
        except (IndexError, ValueError):
            slot = 1
        palette = colors.for_slot(slot)
        if placement.asset_id == "eyes_rectangle":
            draw.rounded_rectangle(
                (0, 0, size[0] - 1, size[1] - 1),
                radius=max(8, min(30, size[1] // 7)),
                fill=palette.background_color,
            )
        elif placement.asset_id == "square_card":
            trim = palette.trim_color or "#FFFFFFFF"
            outline_width = max(8, round(min(size) * 0.025))
            draw.rectangle(
                (0, 0, size[0] - 1, size[1] - 1),
                fill=palette.background_color,
                outline=trim,
                width=outline_width,
            )
            footer_height = max(62, round(size[1] * 0.17))
            draw.rectangle(
                (
                    outline_width,
                    size[1] - footer_height,
                    size[0] - outline_width - 1,
                    size[1] - outline_width - 1,
                ),
                fill=trim,
            )
        else:
            raise ValueError(
                f"Unknown {preferences.selection.mode.value} formatting asset: "
                f"{placement.asset_id}"
            )
    _composite_clipped(canvas, layer, destination.as_tuple())


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

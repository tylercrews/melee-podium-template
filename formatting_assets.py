"""Draw mode-specific framing assets over a constructed background."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PIL import Image

from creation_modes import CreationMode, ModeSelection
from mode_preferences import ModePreferences


PROJECT_ROOT = Path(__file__).resolve().parent
FORMATTING_ASSET_FOLDER = PROJECT_ROOT / "formatting_assets"


class FormattingAssetProvider(Protocol):
    def open(self, selection: ModeSelection, asset_id: str) -> Image.Image:
        """Return a caller-owned RGBA image for a formatting asset."""


class FormattingRenderer(Protocol):
    def draw(
        self,
        canvas: Image.Image,
        preferences: ModePreferences,
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
class FormattingAssetRenderer:
    assets: FormattingAssetProvider = LocalFormattingAssets()

    def draw(
        self,
        canvas: Image.Image,
        preferences: ModePreferences,
    ) -> Image.Image:
        """Composite configured mode assets in ascending ``z_index`` order."""

        result = canvas.convert("RGBA")
        for placement in sorted(
            preferences.formatting_assets,
            key=lambda item: (item.z_index, item.slot_id),
        ):
            source = self.assets.open(preferences.selection, placement.asset_id)
            try:
                layer = source.copy()
            finally:
                source.close()
            destination = placement.destination
            if layer.size != (destination.width, destination.height):
                layer = layer.resize(
                    (destination.width, destination.height),
                    Image.Resampling.LANCZOS,
                )
            _composite_clipped(result, layer, destination.as_tuple())
        return result


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

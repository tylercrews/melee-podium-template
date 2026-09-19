"""Build an RGBA background from a color and an optionally placed image.

The data classes in this module intentionally mirror a JSON-friendly request:
an output size, an RGBA hex fill, and image placement expressed as source and
destination rectangles.  This keeps background preferences independent from
the UI and from the eventual asset storage provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping, Protocol

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parent
BACKGROUND_ASSET_FOLDER = PROJECT_ROOT / "backgrounds"
DEFAULT_BACKGROUND_COLOR = "#00000000"

_RGBA_HEX = re.compile(r"^#[0-9a-fA-F]{8}$")


def _require_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    return value


@dataclass(frozen=True, slots=True)
class PixelSize:
    """A positive width and height in pixels."""

    width: int
    height: int

    def __post_init__(self) -> None:
        _require_int(self.width, "width")
        _require_int(self.height, "height")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be greater than 0")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> PixelSize:
        return cls(
            width=_require_int(value.get("width"), "width"),
            height=_require_int(value.get("height"), "height"),
        )

    def to_dict(self) -> dict[str, int]:
        return {"width": self.width, "height": self.height}

    def as_tuple(self) -> tuple[int, int]:
        return self.width, self.height


@dataclass(frozen=True, slots=True)
class PixelRect:
    """A half-open pixel rectangle: ``[left, right) x [top, bottom)``."""

    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self) -> None:
        for name in ("left", "top", "right", "bottom"):
            _require_int(getattr(self, name), name)
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("rectangle right/bottom must be beyond left/top")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> PixelRect:
        return cls(
            left=_require_int(value.get("left"), "left"),
            top=_require_int(value.get("top"), "top"),
            right=_require_int(value.get("right"), "right"),
            bottom=_require_int(value.get("bottom"), "bottom"),
        )

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def to_dict(self) -> dict[str, int]:
        return {
            "left": self.left,
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
        }

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom


@dataclass(frozen=True, slots=True)
class ImagePlacement:
    """The saved selection and canvas position for one background image."""

    asset_id: str
    source_crop: PixelRect
    destination: PixelRect

    def __post_init__(self) -> None:
        if not isinstance(self.asset_id, str) or not self.asset_id.strip():
            raise ValueError("asset_id must be a non-empty string")
        if not isinstance(self.source_crop, PixelRect):
            raise TypeError("source_crop must be a PixelRect")
        if not isinstance(self.destination, PixelRect):
            raise TypeError("destination must be a PixelRect")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ImagePlacement:
        asset_id = value.get("asset_id")
        source_crop = value.get("source_crop")
        destination = value.get("destination")
        if not isinstance(source_crop, Mapping):
            raise TypeError("source_crop must be an object")
        if not isinstance(destination, Mapping):
            raise TypeError("destination must be an object")
        return cls(
            asset_id=asset_id if isinstance(asset_id, str) else "",
            source_crop=PixelRect.from_dict(source_crop),
            destination=PixelRect.from_dict(destination),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "source_crop": self.source_crop.to_dict(),
            "destination": self.destination.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class BackgroundRequest:
    """A complete, persistable request for a newly composed background."""

    size: PixelSize
    fill_color: str = DEFAULT_BACKGROUND_COLOR
    image: ImagePlacement | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.size, PixelSize):
            raise TypeError("size must be a PixelSize")
        parse_rgba_hex(self.fill_color)
        object.__setattr__(self, "fill_color", self.fill_color.upper())
        if self.image is not None and not isinstance(self.image, ImagePlacement):
            raise TypeError("image must be an ImagePlacement or null")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> BackgroundRequest:
        size = value.get("size")
        image = value.get("image")
        if not isinstance(size, Mapping):
            raise TypeError("size must be an object")
        if image is not None and not isinstance(image, Mapping):
            raise TypeError("image must be an object or null")
        fill_color = value.get("fill_color", DEFAULT_BACKGROUND_COLOR)
        if not isinstance(fill_color, str):
            raise TypeError("fill_color must be an RGBA hex string")
        return cls(
            size=PixelSize.from_dict(size),
            fill_color=fill_color,
            image=ImagePlacement.from_dict(image) if image is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "size": self.size.to_dict(),
            "fill_color": self.fill_color.upper(),
            "image": self.image.to_dict() if self.image is not None else None,
        }


@dataclass(frozen=True, slots=True)
class BackgroundAsset:
    """Metadata the picker needs for a selectable background image."""

    asset_id: str
    size: PixelSize

    def to_dict(self) -> dict[str, Any]:
        return {"asset_id": self.asset_id, "size": self.size.to_dict()}


class BackgroundAssetProvider(Protocol):
    """Storage boundary shared by built-in and future cloud-backed assets."""

    def open(self, asset_id: str) -> Image.Image:
        """Return a caller-owned RGBA image for ``asset_id``."""


@dataclass(frozen=True, slots=True)
class LocalBackgroundAssets:
    """Load trusted filenames from one local asset directory."""

    folder: Path = BACKGROUND_ASSET_FOLDER

    def _path(self, asset_id: str) -> Path:
        if not isinstance(asset_id, str) or not asset_id:
            raise ValueError("asset_id must be a non-empty string")
        if Path(asset_id).name != asset_id:
            raise ValueError("asset_id must be a filename, not a path")
        path = self.folder / asset_id
        if path.suffix.casefold() != ".png" or not path.is_file():
            raise FileNotFoundError(f"Background asset does not exist: {asset_id}")
        return path

    def open(self, asset_id: str) -> Image.Image:
        path = self._path(asset_id)
        with Image.open(path) as source:
            return source.convert("RGBA")

    def list_assets(self) -> tuple[BackgroundAsset, ...]:
        assets: list[BackgroundAsset] = []
        if not self.folder.is_dir():
            return ()
        for path in sorted(self.folder.glob("*.png")):
            with Image.open(path) as source:
                assets.append(
                    BackgroundAsset(path.name, PixelSize(source.width, source.height))
                )
        return tuple(assets)


BUILTIN_BACKGROUND_ASSETS = LocalBackgroundAssets()


def parse_rgba_hex(value: str) -> tuple[int, int, int, int]:
    """Convert a ``#RRGGBBAA`` string into a Pillow RGBA tuple."""

    if not isinstance(value, str) or _RGBA_HEX.fullmatch(value) is None:
        raise ValueError("color must use 8-digit RGBA hex format: #RRGGBBAA")
    return tuple(int(value[index : index + 2], 16) for index in range(1, 9, 2))  # type: ignore[return-value]


def centered_cover_crop(source: PixelSize, destination: PixelSize) -> PixelRect:
    """Return a centered source crop that fills ``destination`` without bars."""

    if source.width * destination.height > destination.width * source.height:
        crop_width = round(source.height * destination.width / destination.height)
        left = (source.width - crop_width) // 2
        return PixelRect(left, 0, left + crop_width, source.height)

    crop_height = round(source.width * destination.height / destination.width)
    top = (source.height - crop_height) // 2
    return PixelRect(0, top, source.width, top + crop_height)


def default_placement(
    format_id: str,
    asset_id: str,
) -> ImagePlacement:
    """Return the configured full-canvas placement for a built-in asset."""

    try:
        output_size = BACKGROUND_FORMAT_SIZES[format_id]
        source_crop = DEFAULT_CROP_POSITIONS[format_id][asset_id]
    except KeyError as error:
        raise KeyError(
            f"No default background placement for {format_id!r} and {asset_id!r}"
        ) from error
    return ImagePlacement(
        asset_id=asset_id,
        source_crop=source_crop,
        destination=PixelRect(0, 0, output_size.width, output_size.height),
    )


def create_background(
    request: BackgroundRequest,
    *,
    assets: BackgroundAssetProvider = BUILTIN_BACKGROUND_ASSETS,
) -> Image.Image:
    """Create and return the RGBA image described by ``request``."""

    canvas = Image.new("RGBA", request.size.as_tuple(), parse_rgba_hex(request.fill_color))
    placement = request.image
    if placement is None:
        return canvas

    source = assets.open(placement.asset_id)
    try:
        crop = placement.source_crop
        if (
            crop.left < 0
            or crop.top < 0
            or crop.right > source.width
            or crop.bottom > source.height
        ):
            raise ValueError(
                "source_crop must stay within the selected image "
                f"({source.width}x{source.height})"
            )
        layer = source.crop(crop.as_tuple())
    finally:
        source.close()
    destination = placement.destination
    if layer.size != (destination.width, destination.height):
        layer = layer.resize(
            (destination.width, destination.height),
            Image.Resampling.LANCZOS,
        )

    visible_left = max(0, destination.left)
    visible_top = max(0, destination.top)
    visible_right = min(request.size.width, destination.right)
    visible_bottom = min(request.size.height, destination.bottom)
    if visible_right <= visible_left or visible_bottom <= visible_top:
        return canvas

    visible_layer = layer.crop(
        (
            visible_left - destination.left,
            visible_top - destination.top,
            visible_right - destination.left,
            visible_bottom - destination.top,
        )
    )
    canvas.alpha_composite(visible_layer, (visible_left, visible_top))
    return canvas


# Formats remain separate keys because their preferred framing may diverge even
# while they share dimensions. Add future formats and hand-tuned crop overrides
# here without changing the request or rendering code.
BACKGROUND_FORMAT_SIZES: dict[str, PixelSize] = {
    "doubles_top_3": PixelSize(1672, 941),
    "doubles_top_4": PixelSize(1672, 941),
    "singles_top_3": PixelSize(1672, 941),
    "singles_top_4": PixelSize(1672, 941),
    "singles_top_8": PixelSize(1672, 941),
    "singles_top_8_four_podium": PixelSize(1672, 941),
}

BUILTIN_BACKGROUND_SIZES: dict[str, PixelSize] = {
    "00_Battlefield_5000_5000_resaved.png": PixelSize(5000, 5000),
    "01_Dreamland_5000_5000_resaved.png": PixelSize(5000, 5000),
    "02_FinalDestinationCloud_5000_5000_resaved.png": PixelSize(5000, 5000),
    "03_FinalDestinationSpace_4000_4000_resaved.png": PixelSize(4000, 3000),
    "04_FinalDestinationCyber_5000_5000_resaved.png": PixelSize(5000, 5000),
    "05_FinalDestinationSpace_5000_5000_resaved.png": PixelSize(5000, 5000),
    "06_FinalDestinationTunnel_5000_5000_resaved.png": PixelSize(5000, 5000),
    "07_FinalDestinationWormhole_5000_5000_resaved.png": PixelSize(5000, 5000),
    "08_FountainOfDreams_5000_5000_resaved.png": PixelSize(5000, 5000),
    "09_PokemonStadium_5000_5000_resaved.png": PixelSize(5000, 5000),
    "10_YoshisStory_5000_5000_resaved.png": PixelSize(5000, 5000),
}

DEFAULT_CROP_POSITIONS: dict[str, dict[str, PixelRect]] = {
    format_id: {
        asset_id: centered_cover_crop(asset_size, output_size)
        for asset_id, asset_size in BUILTIN_BACKGROUND_SIZES.items()
    }
    for format_id, output_size in BACKGROUND_FORMAT_SIZES.items()
}

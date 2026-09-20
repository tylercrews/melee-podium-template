"""Serializable color inputs and semantic recoloring for customizable podiums."""

from __future__ import annotations

from colorsys import hls_to_rgb, rgb_to_hls
from dataclasses import dataclass
from statistics import median
from typing import Any, Mapping

from PIL import Image

from color_values import format_rgba_hex, normalize_rgba_hex, parse_rgba_hex
from constants import PODIUM_BOX_COLORS_BY_SLOT, RGB


MAIN_MASK_COLOR = (255, 0, 0)
FACE_MASK_COLOR = (0, 255, 255)
BASE_MASK_COLOR = (0, 0, 255)


def _lightness(color: RGB) -> float:
    return rgb_to_hls(*(channel / 255 for channel in color))[1]


def _existing_face_lightness_ratio() -> float:
    """Return the representative face/main ratio in the existing palettes."""

    ratios = tuple(
        _lightness(pair.interior_line) / main_lightness
        for pair in PODIUM_BOX_COLORS_BY_SLOT
        if (main_lightness := _lightness(pair.exterior_line)) > 0
    )
    return median(ratios)


FACE_LIGHTNESS_RATIO = _existing_face_lightness_ratio()


def default_face_color(main_color: str) -> str:
    """Derive a darker face while preserving the main color's hue and alpha."""

    red, green, blue, alpha = parse_rgba_hex(
        main_color,
        field_name="main_color",
    )
    hue, lightness, saturation = rgb_to_hls(
        red / 255,
        green / 255,
        blue / 255,
    )
    face = hls_to_rgb(
        hue,
        lightness * FACE_LIGHTNESS_RATIO,
        saturation,
    )
    face_channels = tuple(round(channel * 255) for channel in face)
    return format_rgba_hex(*face_channels, alpha)


@dataclass(frozen=True, slots=True)
class ResolvedPodiumColors:
    """The three concrete semantic colors consumed by the podium renderer."""

    main_color: str
    face_color: str
    base_color: str
    metallic: bool

    def __post_init__(self) -> None:
        for field_name in ("main_color", "face_color", "base_color"):
            object.__setattr__(
                self,
                field_name,
                normalize_rgba_hex(getattr(self, field_name), field_name=field_name),
            )
        if not isinstance(self.metallic, bool):
            raise TypeError("metallic must be a boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "main_color": self.main_color,
            "face_color": self.face_color,
            "base_color": self.base_color,
            "metallic": self.metallic,
        }


@dataclass(frozen=True, slots=True)
class PodiumColorSelection:
    """User-entered podium colors before optional values are resolved."""

    main_color: str
    face_color: str | None = None
    base_color: str | None = None
    metallic: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "main_color",
            normalize_rgba_hex(self.main_color, field_name="main_color"),
        )
        for field_name in ("face_color", "base_color"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    normalize_rgba_hex(value, field_name=field_name),
                )
        if not isinstance(self.metallic, bool):
            raise TypeError("metallic must be a boolean")

    def resolve(self) -> ResolvedPodiumColors:
        """Fill omitted face/base colors and inherit the main alpha for both."""

        main_alpha = self.main_color[-2:]
        return ResolvedPodiumColors(
            main_color=self.main_color,
            face_color=self.face_color or default_face_color(self.main_color),
            base_color=self.base_color or f"#000000{main_alpha}",
            metallic=self.metallic,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> PodiumColorSelection:
        main_color = value.get("main_color")
        face_color = value.get("face_color")
        base_color = value.get("base_color")
        metallic = value.get("metallic", False)
        if not isinstance(main_color, str):
            raise TypeError("main_color must be an RGBA hex string")
        for field_name, color in (
            ("face_color", face_color),
            ("base_color", base_color),
        ):
            if color is not None and not isinstance(color, str):
                raise TypeError(f"{field_name} must be an RGBA hex string or null")
        return cls(main_color, face_color, base_color, metallic)

    def to_dict(self) -> dict[str, Any]:
        return {
            "main_color": self.main_color,
            "face_color": self.face_color,
            "base_color": self.base_color,
            "metallic": self.metallic,
        }


def apply_podium_colors(
    mask: Image.Image,
    selection: PodiumColorSelection,
) -> Image.Image:
    """Replace the red/main, cyan/face, and blue/base mask classes."""

    if not isinstance(mask, Image.Image):
        raise TypeError("mask must be a Pillow image")
    if not isinstance(selection, PodiumColorSelection):
        raise TypeError("selection must be a PodiumColorSelection")

    colors = selection.resolve()
    replacements = {
        MAIN_MASK_COLOR: parse_rgba_hex(colors.main_color),
        FACE_MASK_COLOR: parse_rgba_hex(colors.face_color),
        BASE_MASK_COLOR: parse_rgba_hex(colors.base_color),
    }
    source = mask.convert("RGBA")
    output: list[tuple[int, int, int, int]] = []
    for red, green, blue, source_alpha in source.getdata():
        replacement = replacements.get((red, green, blue))
        if replacement is None:
            output.append((red, green, blue, source_alpha))
            continue
        output.append(
            (
                replacement[0],
                replacement[1],
                replacement[2],
                round(source_alpha * replacement[3] / 255),
            )
        )

    result = Image.new("RGBA", source.size)
    result.putdata(output)
    return result

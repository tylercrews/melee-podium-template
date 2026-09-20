"""Serializable color inputs and semantic recoloring for customizable podiums."""

from __future__ import annotations

from colorsys import hls_to_rgb, rgb_to_hls
from dataclasses import dataclass
from enum import Enum
from statistics import median
from typing import Any, Mapping

from PIL import Image

from color_values import format_rgba_hex, normalize_rgba_hex, parse_rgba_hex
from constants import (
    BRONZE_PODIUM,
    GOLD_PODIUM,
    PODIUM_BOX_COLORS_BY_SLOT,
    SEVENTH_PLACE_GRAY_BOX,
    SILVER_PODIUM,
    PodiumBoxColors,
    RGB,
)


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
    """Concrete semantic and text colors consumed by the podium renderers."""

    main_color: str
    face_color: str
    base_color: str
    text_color: str
    metallic: bool

    def __post_init__(self) -> None:
        for field_name in ("main_color", "face_color", "base_color", "text_color"):
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
            "text_color": self.text_color,
            "metallic": self.metallic,
        }


@dataclass(frozen=True, slots=True)
class PodiumColorSelection:
    """User-entered podium colors before optional values are resolved."""

    main_color: str
    face_color: str | None = None
    base_color: str | None = None
    metallic: bool = False
    text_color: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "main_color",
            normalize_rgba_hex(self.main_color, field_name="main_color"),
        )
        for field_name in ("face_color", "base_color", "text_color"):
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
            text_color=self.text_color or self.main_color,
            metallic=self.metallic,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> PodiumColorSelection:
        main_color = value.get("main_color")
        face_color = value.get("face_color")
        base_color = value.get("base_color")
        metallic = value.get("metallic", False)
        text_color = value.get("text_color")
        if not isinstance(main_color, str):
            raise TypeError("main_color must be an RGBA hex string")
        for field_name, color in (
            ("face_color", face_color),
            ("base_color", base_color),
            ("text_color", text_color),
        ):
            if color is not None and not isinstance(color, str):
                raise TypeError(f"{field_name} must be an RGBA hex string or null")
        return cls(main_color, face_color, base_color, metallic, text_color)

    def to_dict(self) -> dict[str, Any]:
        return {
            "main_color": self.main_color,
            "face_color": self.face_color,
            "base_color": self.base_color,
            "metallic": self.metallic,
            "text_color": self.text_color,
        }


class PodiumColorMode(str, Enum):
    PRESET = "preset"
    CUSTOM = "custom"
    ALTERNATING = "alternating"


class PodiumColorPreset(str, Enum):
    LEGACY = "legacy"
    MEDALS = "medals"


def _rgba(color: RGB, alpha: int = 255) -> str:
    return format_rgba_hex(*color, alpha)


def _selection_from_box(
    colors: PodiumBoxColors,
    *,
    metallic: bool = False,
) -> PodiumColorSelection:
    return PodiumColorSelection(
        main_color=_rgba(colors.exterior_line),
        face_color=_rgba(colors.interior_line),
        base_color=_rgba(colors.background),
        metallic=metallic,
    )


LEGACY_PRESET_COLORS = tuple(
    _selection_from_box(colors) for colors in PODIUM_BOX_COLORS_BY_SLOT
)
MEDAL_PRESET_COLORS = (
    _selection_from_box(GOLD_PODIUM, metallic=True),
    _selection_from_box(SILVER_PODIUM, metallic=True),
    _selection_from_box(BRONZE_PODIUM, metallic=True),
) + tuple(_selection_from_box(SEVENTH_PLACE_GRAY_BOX) for _ in range(5))
PODIUM_COLOR_PRESETS = {
    PodiumColorPreset.LEGACY: LEGACY_PRESET_COLORS,
    PodiumColorPreset.MEDALS: MEDAL_PRESET_COLORS,
}


@dataclass(frozen=True, slots=True)
class PodiumColorConfiguration:
    """Serializable selection of preset, per-podium, or alternating colors."""

    mode: PodiumColorMode
    colors: tuple[PodiumColorSelection, ...] = ()
    preset: PodiumColorPreset | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, PodiumColorMode):
            raise TypeError("mode must be a PodiumColorMode")
        if not isinstance(self.colors, tuple) or any(
            not isinstance(color, PodiumColorSelection) for color in self.colors
        ):
            raise TypeError("colors must be a tuple of PodiumColorSelection values")
        if self.mode is PodiumColorMode.PRESET:
            if self.preset is None or self.colors:
                raise ValueError("preset mode requires a preset and no explicit colors")
        elif self.preset is not None:
            raise ValueError("preset is only valid in preset mode")
        elif self.mode is PodiumColorMode.CUSTOM and not self.colors:
            raise ValueError("custom mode requires at least one podium color")
        elif self.mode is PodiumColorMode.ALTERNATING and len(self.colors) != 2:
            raise ValueError("alternating mode requires exactly two colors")

    @classmethod
    def from_preset(cls, preset: PodiumColorPreset) -> PodiumColorConfiguration:
        return cls(PodiumColorMode.PRESET, preset=preset)

    @classmethod
    def per_podium(
        cls, *colors: PodiumColorSelection
    ) -> PodiumColorConfiguration:
        return cls(PodiumColorMode.CUSTOM, tuple(colors))

    @classmethod
    def alternating(
        cls, first: PodiumColorSelection, second: PodiumColorSelection
    ) -> PodiumColorConfiguration:
        return cls(PodiumColorMode.ALTERNATING, (first, second))

    def color_for_slot(self, slot: int) -> PodiumColorSelection:
        if isinstance(slot, bool) or not isinstance(slot, int) or slot <= 0:
            raise ValueError("podium slot must be a positive integer")
        if self.mode is PodiumColorMode.PRESET:
            assert self.preset is not None
            colors = PODIUM_COLOR_PRESETS[self.preset]
            if slot > len(colors):
                raise ValueError(f"Preset {self.preset.value} has no podium slot {slot}")
            return colors[slot - 1]
        if self.mode is PodiumColorMode.ALTERNATING:
            return self.colors[(slot - 1) % 2]
        if slot > len(self.colors):
            raise ValueError(f"Custom colors have no podium slot {slot}")
        return self.colors[slot - 1]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> PodiumColorConfiguration:
        try:
            mode = PodiumColorMode(value.get("mode"))
        except ValueError as error:
            raise ValueError("Unknown podium color mode") from error
        preset_value = value.get("preset")
        preset = None if preset_value is None else PodiumColorPreset(preset_value)
        raw_colors = value.get("colors", [])
        if not isinstance(raw_colors, list):
            raise TypeError("colors must be an array")
        colors = tuple(
            PodiumColorSelection.from_dict(color)
            for color in raw_colors
            if isinstance(color, Mapping)
        )
        if len(colors) != len(raw_colors):
            raise TypeError("every colors item must be an object")
        return cls(mode, colors, preset)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "preset": None if self.preset is None else self.preset.value,
            "colors": [color.to_dict() for color in self.colors],
        }


PodiumColorInput = PodiumColorSelection | PodiumColorConfiguration


def podium_color_for_slot(
    colors: PodiumColorInput,
    slot: int,
) -> PodiumColorSelection:
    """Resolve a podium slot while retaining single-color backwards compatibility."""

    if isinstance(colors, PodiumColorSelection):
        return colors
    if isinstance(colors, PodiumColorConfiguration):
        return colors.color_for_slot(slot)
    raise TypeError("colors must be a podium color selection or configuration")


def apply_podium_colors(
    mask: Image.Image,
    selection: PodiumColorSelection,
) -> Image.Image:
    """Replace semantic mask classes, including their shaded edge variants."""

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
    for pixel_index, (red, green, blue, source_alpha) in enumerate(source.getdata()):
        source_rgb = (red, green, blue)
        if red == green == blue:
            output.append((red, green, blue, source_alpha))
            continue
        if red >= 2 * max(green, blue) and red > 0:
            semantic = MAIN_MASK_COLOR
        elif min(green, blue) >= 2 * red and min(green, blue) > 0:
            semantic = FACE_MASK_COLOR
        elif blue >= 2 * max(red, green) and blue > 0:
            semantic = BASE_MASK_COLOR
        else:
            output.append((red, green, blue, source_alpha))
            continue
        replacement = replacements[semantic]
        active_channels = tuple(
            index for index, channel in enumerate(semantic) if channel
        )
        intensity = sum(source_rgb[index] for index in active_channels) / (
            255 * len(active_channels)
        )
        rendered_rgb = tuple(round(channel * intensity) for channel in replacement[:3])
        if colors.metallic and semantic == MAIN_MASK_COLOR:
            x = pixel_index % source.width
            y = pixel_index // source.width
            diagonal = x / max(1, source.width - 1) + 0.3 * y / max(
                1, source.height - 1
            )
            highlight = max(0.0, 1.0 - abs(diagonal - 0.62) / 0.13) * 0.32
            rendered_rgb = tuple(
                round(channel + (255 - channel) * highlight)
                for channel in rendered_rgb
            )
        output.append(
            (*rendered_rgb, round(source_alpha * replacement[3] / 255))
        )

    result = Image.new("RGBA", source.size)
    result.putdata(output)
    return result

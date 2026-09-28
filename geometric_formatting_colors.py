"""Serializable colors for Eyes rectangles and Squares cards."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from color_values import normalize_rgba_hex


@dataclass(frozen=True, slots=True)
class GeometricFormattingColor:
    """Colors for one visible non-podium formatting asset."""

    background_color: str
    trim_color: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "background_color",
            normalize_rgba_hex(
                self.background_color,
                field_name="formatting background color",
            ),
        )
        if self.trim_color is not None:
            object.__setattr__(
                self,
                "trim_color",
                normalize_rgba_hex(
                    self.trim_color,
                    field_name="formatting trim color",
                ),
            )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "background_color": self.background_color,
            "trim_color": self.trim_color,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> GeometricFormattingColor:
        background = value.get("background_color")
        trim = value.get("trim_color")
        if not isinstance(background, str):
            raise TypeError("background_color must be a string")
        if trim is not None and not isinstance(trim, str):
            raise TypeError("trim_color must be a string or null")
        return cls(background, trim)


@dataclass(frozen=True, slots=True)
class GeometricFormattingColors:
    """One or more palettes repeated across visible formatting slots."""

    colors: tuple[GeometricFormattingColor, ...]

    def __post_init__(self) -> None:
        colors = tuple(self.colors)
        if not colors:
            raise ValueError("At least one geometric formatting color is required")
        if any(not isinstance(color, GeometricFormattingColor) for color in colors):
            raise TypeError("colors must contain GeometricFormattingColor values")
        object.__setattr__(self, "colors", colors)

    @classmethod
    def one(
        cls,
        background_color: str,
        trim_color: str | None = None,
    ) -> GeometricFormattingColors:
        return cls((GeometricFormattingColor(background_color, trim_color),))

    def for_slot(self, one_based_slot: int) -> GeometricFormattingColor:
        if one_based_slot <= 0:
            raise ValueError("Formatting slots are one-based")
        return self.colors[(one_based_slot - 1) % len(self.colors)]

    def to_dict(self) -> dict[str, object]:
        return {"colors": [color.to_dict() for color in self.colors]}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> GeometricFormattingColors:
        raw_colors = value.get("colors")
        if not isinstance(raw_colors, list):
            raise TypeError("colors must be an array")
        if any(not isinstance(color, Mapping) for color in raw_colors):
            raise TypeError("each formatting color must be an object")
        return cls(
            tuple(
                GeometricFormattingColor.from_dict(color)
                for color in raw_colors
            )
        )

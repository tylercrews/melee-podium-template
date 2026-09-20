"""Validate and convert the project's canonical RGBA hex color values."""

from __future__ import annotations

import re


RGBAHex = str
RGBA = tuple[int, int, int, int]

_RGBA_HEX = re.compile(r"^#[0-9a-fA-F]{8}$")


def normalize_rgba_hex(value: str, *, field_name: str = "color") -> RGBAHex:
    """Return an uppercase ``#RRGGBBAA`` value or reject the input."""

    if not isinstance(value, str) or _RGBA_HEX.fullmatch(value) is None:
        raise ValueError(
            f"{field_name} must use 8-digit RGBA hex format: #RRGGBBAA"
        )
    return value.upper()


def parse_rgba_hex(value: str, *, field_name: str = "color") -> RGBA:
    """Convert a canonical RGBA hex string into a Pillow-compatible tuple."""

    normalized = normalize_rgba_hex(value, field_name=field_name)
    return tuple(
        int(normalized[index : index + 2], 16) for index in range(1, 9, 2)
    )  # type: ignore[return-value]


def format_rgba_hex(red: int, green: int, blue: int, alpha: int) -> RGBAHex:
    """Convert four byte channels to the canonical color representation."""

    channels = (red, green, blue, alpha)
    if any(
        isinstance(channel, bool)
        or not isinstance(channel, int)
        or not 0 <= channel <= 255
        for channel in channels
    ):
        raise ValueError("RGBA channels must be integers from 0 through 255")
    return f"#{red:02X}{green:02X}{blue:02X}{alpha:02X}"

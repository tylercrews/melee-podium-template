"""Translate primary and box colors into Radial background and border colors."""

from geometric_formatting_colors import GeometricFormattingColor
from podium_colors import PodiumColorSelection


def radial_palette_color(selection: PodiumColorSelection) -> GeometricFormattingColor:
    resolved = selection.resolve()
    return GeometricFormattingColor(resolved.main_color, resolved.base_color)

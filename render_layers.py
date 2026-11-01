"""Ordered content and header layers that flatten into one exact render.

Renderers draw each tournament header into its own transparent layer between
the content drawn below and above it. Flattening the stack reproduces the
complete image, while a preview can replace only the header layers when just
the tournament text or its settings change.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from PIL import Image


LayerKind = Literal["content", "header"]


@dataclass(frozen=True, slots=True)
class RenderLayer:
    kind: LayerKind
    image: Image.Image

    def __post_init__(self) -> None:
        if self.kind not in {"content", "header"}:
            raise ValueError("Render layers must be content or header layers")
        if not isinstance(self.image, Image.Image) or self.image.mode != "RGBA":
            raise TypeError("Render layers must be RGBA Pillow images")


def transparent_layer(size: tuple[int, int]) -> Image.Image:
    return Image.new("RGBA", size, "#00000000")


def drawn_layer(size: tuple[int, int], draw: Callable[[Image.Image], object]) -> Image.Image:
    """Run one drawing step on a fresh transparent layer."""

    layer = transparent_layer(size)
    draw(layer)
    return layer


def flatten_layers(layers: Sequence[RenderLayer]) -> Image.Image:
    """Composite the stack bottom to top into a new RGBA image."""

    if not layers:
        raise ValueError("At least one render layer is required")
    result = layers[0].image.copy()
    for layer in layers[1:]:
        if layer.image.size != result.size:
            raise ValueError("Render layers must share one canvas size")
        result.alpha_composite(layer.image)
    return result


def header_images(layers: Sequence[RenderLayer]) -> tuple[Image.Image, ...]:
    return tuple(layer.image for layer in layers if layer.kind == "header")

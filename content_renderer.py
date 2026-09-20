"""Boundary for drawing character assets and text as one layered content pass."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from PIL import Image

if TYPE_CHECKING:
    from creation import CreationRequest
    from mode_preferences import ModePreferences


class ContentRenderer(Protocol):
    def draw(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        preferences: ModePreferences,
    ) -> Image.Image:
        """Interleave characters and text according to their configured z-index."""

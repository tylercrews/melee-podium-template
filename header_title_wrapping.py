"""Wrap enlarged header titles rather than shrinking them back into their slot."""

from __future__ import annotations

from PIL import Image, ImageDraw

from DrawPodium import PodiumFont, _adjusted_font_size, _font_settings, _font_to_fit, _load_truetype


def _block_bottom(text: str, face) -> int:
    return ImageDraw.Draw(Image.new("L", (1, 1))).multiline_textbbox((0, 0), text, font=face, anchor="la")[3]


def wrap_enlarged_title(
    text: str,
    *,
    max_width: int,
    preferred_size: int,
    adjustment: int,
    font: PodiumFont,
    max_height: int | None = None,
) -> tuple[str, int]:
    """Return the title and preferred size, split onto two lines when that renders larger.

    Fit-to-width shrinking cancels a positive size adjustment for any title that
    already fills its slot. An enlarged title therefore wraps onto two balanced
    lines when they fit a larger size within ``max_width`` and the optional
    ``max_height``. Default and reduced sizes keep the historical single line.
    """
    words = text.split()
    if adjustment <= 0 or len(words) < 2:
        return text, preferred_size
    source, _ = _font_settings(font)
    requested = _load_truetype(source, _adjusted_font_size(preferred_size, font))
    wrapped = min(
        ("\n".join((" ".join(words[:index]), " ".join(words[index:]))) for index in range(1, len(words))),
        key=lambda candidate: max(requested.getlength(line) for line in candidate.splitlines()),
    )
    single_line_size = _font_to_fit(text, max_width, preferred_size, font).size
    for size in range(preferred_size, 0, -1):
        face = _load_truetype(source, _adjusted_font_size(size, font))
        if face.size <= single_line_size:
            break
        if (max(face.getlength(line) for line in wrapped.splitlines()) <= max_width
                and (max_height is None or _block_bottom(wrapped, face) <= max_height)):
            return wrapped, size
    return text, preferred_size


def added_title_height(text: str, *, max_width: int, preferred_size: int, font: PodiumFont) -> int:
    """Return how far a wrapped title's extra lines push the content beneath it."""
    if "\n" not in text:
        return 0
    face = _font_to_fit(text, max_width, preferred_size, font)
    return (_block_bottom("Ag\nAg", face) - _block_bottom("Ag", face)) * text.count("\n")

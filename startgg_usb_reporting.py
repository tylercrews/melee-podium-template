"""Decode Replay Reporter costume metadata stored in Start.gg game scores.

Replay Reporter for Slippi optionally stores a Slippi costume index in the
hundreds portion of each entrant's per-game stock count.  Those indices are
fighter-specific, while this project addresses costumes by the color names in
its character asset filenames.  This module is the translation boundary
between the two schemes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class UsbReportScore:
    """The costume metadata and real stock count decoded from one score."""

    costume_index: int
    stocks_remaining: int


# Ordered by Slippi costume index.  Values are the color labels used by this
# project's character renders, which are not always the visual color names
# used by other APIs (for example, Ice Climbers index 2 is named ``cyan`` in
# this asset set, and Jigglypuff's crown costume is named ``white``).
USB_COSTUMES_BY_FIGHTER: Final[dict[str, tuple[str, ...]]] = {
    "Bowser": ("default", "red", "blue", "black"),
    "Captain Falcon": ("default", "black", "red", "white", "green", "blue"),
    "Donkey Kong": ("default", "black", "red", "blue", "green"),
    "Dr. Mario": ("default", "red", "blue", "green", "black"),
    "Falco": ("default", "red", "blue", "green"),
    "Fox": ("default", "red", "blue", "green"),
    "Ganondorf": ("default", "red", "blue", "green", "purple"),
    "Ice Climbers": ("default", "green", "cyan", "red"),
    "Jigglypuff": ("default", "red", "blue", "green", "white"),
    "Kirby": ("default", "yellow", "blue", "red", "green", "white"),
    "Link": ("default", "red", "blue", "black", "white"),
    "Luigi": ("default", "white", "blue", "red"),
    "Mario": ("default", "yellow", "black", "blue", "green"),
    "Marth": ("default", "red", "green", "black", "white"),
    "Mewtwo": ("default", "red", "blue", "green"),
    "Mr. Game and Watch": ("default", "red", "blue", "green"),
    "Ness": ("default", "yellow", "blue", "green"),
    "Peach": ("default", "yellow", "white", "blue", "green"),
    "Pichu": ("default", "red", "blue", "green"),
    "Pikachu": ("default", "red", "blue", "green"),
    "Roy": ("default", "red", "blue", "green", "white"),
    "Samus": ("default", "pink", "black", "green", "blue"),
    "Sheik": ("default", "red", "blue", "green", "white"),
    "Yoshi": ("default", "red", "blue", "yellow", "pink", "cyan"),
    "Young Link": ("default", "red", "blue", "white", "black"),
    "Zelda": ("default", "red", "blue", "green", "white"),
}

_STARTGG_NAME_ALIASES: Final[dict[str, str]] = {
    "mr. game & watch": "Mr. Game and Watch",
    **{fighter.casefold(): fighter for fighter in USB_COSTUMES_BY_FIGHTER},
}


def canonical_fighter_name(name: str) -> str:
    """Translate Start.gg's fighter spelling to the renderer's spelling."""

    stripped = name.strip()
    return _STARTGG_NAME_ALIASES.get(stripped.casefold(), stripped)


def decode_usb_score(score: object) -> UsbReportScore | None:
    """Decode an encoded score, or return ``None`` for an ordinary score.

    The upstream format is ``(costume_index + 1) * 100 + stocks_remaining``.
    A score below 100 therefore contains no USB Reporting metadata.
    """

    if isinstance(score, bool) or not isinstance(score, int) or score < 100:
        return None
    return UsbReportScore(costume_index=(score // 100) - 1, stocks_remaining=score % 100)


def costume_for_usb_score(fighter_name: str, score: object) -> str | None:
    """Return this project's costume label for a valid encoded score.

    Invalid fighter-specific indices are ignored.  Replay Reporter documents
    that the stock icon glitch can produce such out-of-range values.
    """

    decoded = decode_usb_score(score)
    costumes = USB_COSTUMES_BY_FIGHTER.get(canonical_fighter_name(fighter_name))
    if decoded is None or costumes is None or decoded.costume_index >= len(costumes):
        return None
    return costumes[decoded.costume_index]

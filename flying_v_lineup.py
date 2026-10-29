"""Render one Flying V entrant's full-body character lineup inside a frame."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from PIL import Image

from background_builder import PixelRect
from models import Character
from portrait_assets import load_character_source, with_team_color
from portrait_scale_adjustment_to_character_relativity import get_pose_scale


# Additional characters follow the Podium center/left/right stagger at a
# spacing relative to the tallest portrait, so every tier keeps its proportions.
LINEUP_SPREAD = 0.16
STANDING_FRAME = "flying_v_standing_frame"
FRAME_ASSETS = frozenset({STANDING_FRAME})


@dataclass(frozen=True, slots=True)
class PlacedLineup:
    """A composited lineup and the canvas rectangle its visible pixels cover."""

    image: Image.Image
    bounds: PixelRect


@dataclass(frozen=True, slots=True)
class _Source:
    """One character's visible pixels at source resolution and its relativity scale."""

    image: Image.Image
    relativity: float

    def size_at(self, scale: float) -> tuple[float, float]:
        return self.image.width * self.relativity * scale, self.image.height * self.relativity * scale

    def scaled(self, scale: float) -> Image.Image:
        width, height = self.size_at(scale)
        return self.image.resize((max(1, round(width)), max(1, round(height))), Image.Resampling.LANCZOS)


def _load_sources(characters: Sequence[Character], team_color: str | None) -> list[_Source]:
    # Resolve each (possibly random) costume and pose exactly once per render.
    sources = []
    for character in characters:
        image, pose = load_character_source(with_team_color(character, team_color))
        visible = image.getbbox()
        if visible is not None:
            sources.append(_Source(image.crop(visible), get_pose_scale(character.melee_fighter_name, f"00{pose}")))
    return sources


def _compose(portraits: list[Image.Image]) -> tuple[Image.Image, int]:
    """Bottom-align portraits tallest first and return the center anchor's x offset."""
    if not portraits:
        return Image.new("RGBA", (1, 1), "#00000000"), 0
    # The tallest portrait establishes the silhouette; later ones layer over it.
    portraits = sorted(portraits, key=lambda image: image.height, reverse=True)
    spread = round(portraits[0].height * LINEUP_SPREAD)
    pattern = (-spread, spread) if len(portraits) == 2 else (0, -spread, spread)
    offsets = [pattern[index % len(pattern)] for index in range(len(portraits))]
    left = min(offset - image.width / 2 for offset, image in zip(offsets, portraits))
    right = max(offset + image.width / 2 for offset, image in zip(offsets, portraits))
    height = portraits[0].height
    lineup = Image.new("RGBA", (round(right - left), height), "#00000000")
    for offset, image in zip(offsets, portraits):
        lineup.alpha_composite(image, (round(offset - image.width / 2 - left), height - image.height))
    return lineup, round(-left)


def render_lineup(
    characters: Sequence[Character],
    scale: float,
    *,
    team_color: str | None = None,
) -> tuple[Image.Image, int]:
    """Bottom-align a lineup and return it with its center anchor's x offset."""

    if not characters:
        raise ValueError("A Flying V entrant must have at least one character")
    return _compose([source.scaled(scale) for source in _load_sources(characters, team_color)])


@dataclass(frozen=True, slots=True)
class LineupSlot:
    """One teammate's characters, tier scale, standing frame, and center anchor."""

    characters: Sequence[Character]
    scale: float
    frame: PixelRect
    anchor_x: int | None = None


def _fit(sources: list[_Source], scale: float, frame: PixelRect) -> float:
    """Return the factor that keeps the largest single character inside the frame."""
    if not sources:
        return 1.0
    widest = max(source.size_at(scale)[0] for source in sources)
    tallest = max(source.size_at(scale)[1] for source in sources)
    return min(1.0, frame.width / widest, frame.height / tallest)


def _stand(sources: list[_Source], scale: float, frame: PixelRect, anchor_x: int | None) -> PlacedLineup:
    lineup, lineup_anchor_x = _compose([source.scaled(scale) for source in sources])
    if lineup.width <= frame.width:
        # Center the primary character, then keep uneven lineups inside the frame.
        center_x = (frame.left + frame.right) // 2 if anchor_x is None else anchor_x
        left = min(max(center_x - lineup_anchor_x, frame.left), frame.right - lineup.width)
    else:
        left = (frame.left + frame.right - lineup.width) // 2
    top = frame.bottom - lineup.height
    return PlacedLineup(lineup, PixelRect(left, top, left + lineup.width, top + lineup.height))


def place_team(slots: Sequence[LineupSlot], *, team_color: str | None = None) -> list[PlacedLineup]:
    """Place teammates' lineups, shrinking every member by one shared factor.

    A character too large for its frame shrinks its whole team equally, so
    doubles partners keep their true relative sizes. The frame limits each
    character rather than the staggered lineup, so entrants with several
    characters match single-character entrants in the same tier. Lineups stand
    on the frame's bottom, where the placement art covers their feet. Each
    primary character centers on its ``anchor_x`` (the frame center by
    default), sliding only as far as needed to keep a wide lineup inside the
    frame.
    """

    if any(slot.scale <= 0 for slot in slots):
        raise ValueError("Flying V scales must be greater than zero")
    if any(not slot.characters for slot in slots):
        raise ValueError("A Flying V entrant must have at least one character")
    sources = [_load_sources(slot.characters, team_color) for slot in slots]
    fit = min((_fit(member, slot.scale, slot.frame) for member, slot in zip(sources, slots)), default=1.0)
    return [_stand(member, slot.scale * fit, slot.frame, slot.anchor_x) for member, slot in zip(sources, slots)]


def place_lineup(
    characters: Sequence[Character],
    scale: float,
    frame: PixelRect,
    *,
    team_color: str | None = None,
    anchor_x: int | None = None,
) -> PlacedLineup:
    """Scale one entrant's lineup to its tier, shrinking it only when a character is too large for the frame."""

    return place_team([LineupSlot(characters, scale, frame, anchor_x)], team_color=team_color)[0]

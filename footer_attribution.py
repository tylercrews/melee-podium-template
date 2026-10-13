"""Choose a podium footer position from measured content bounds."""

from dataclasses import dataclass
from collections.abc import Iterable


Bounds = tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class FooterPlacement:
    origin_x: int
    bounds: Bounds


def choose_footer_placement(canvas_width: int, text_bounds: Bounds,
                            obstacles: Iterable[Bounds], *, side_margin: int = 10) -> FooterPlacement:
    """Compare bottom left, middle, and right; equal overlap prefers left."""
    left, top, right, bottom = text_bounds
    width = right - left
    targets = (side_margin, (canvas_width - width) // 2, canvas_width - side_margin - width)
    obstacles = tuple(obstacles)
    candidates = tuple(FooterPlacement(target - left, (target, top, target + width, bottom))
                       for target in targets)

    def overlap(candidate: FooterPlacement) -> int:
        a, b, c, d = candidate.bounds
        return sum(max(0, min(c, box[2]) - max(a, box[0]))
                   * max(0, min(d, box[3]) - max(b, box[1])) for box in obstacles)

    return min(candidates, key=overlap)

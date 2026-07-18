"""Edit the values below, then run this file to create one singles top-8 image."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import draw_singles_top_8
from example_entrants import (
    BUSTA,
    CHOI,
    HBK,
    OSMICS,
    QWAIN,
    SHENAL,
    SILENT_SKYLER,
    TYRO,
)
from models import Entrant, SinglesEntrant


TOURNAMENT = {"tournament_name": "Shenfest Singles", "tournament_date": "07/17/2026", "entrants_count": 16}


def result(entrant: Entrant, seed: int | None, placement: int) -> SinglesEntrant:
    """Apply this tournament's result data to a reusable entrant."""
    return SinglesEntrant(
        seed=seed,
        placement=placement,
        characters=entrant.characters,
        tag=entrant.tag,
        bluesky_handle=entrant.bluesky_handle,
        x_handle=entrant.x_handle,
    )


if __name__ == "__main__":
    draw_singles_top_8(
        result(HBK, seed=2, placement=1),
        result(BUSTA, seed=1, placement=2),
        result(QWAIN, seed=3, placement=3),
        result(CHOI, seed=4, placement=4),
        result(SHENAL, seed=10, placement=5),
        result(SILENT_SKYLER, seed=8, placement=5),
        result(TYRO, seed=6, placement=7),
        result(OSMICS, seed=5, placement=7),
        **TOURNAMENT,
        output_path=Path(__file__).with_name("singles_top_8.png"),
    )

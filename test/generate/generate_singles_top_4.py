"""Edit the values below, then run this file to create one singles top-4 image."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import draw_singles_top_4
from models import Character, SinglesEntrant


TOURNAMENT = {"tournament_name": "Example Tournament", "tournament_date": "July 12, 2026", "entrants_count": 64}


def entrant(seed: int | None, placement: int, tag: str, fighter: str) -> SinglesEntrant:
    return SinglesEntrant(seed=seed, placement=placement, characters=[Character(fighter)], tag=tag)


if __name__ == "__main__":
    draw_singles_top_4(
        entrant(1, 1, "Player One", "Fox"),
        entrant(2, 2, "Player Two", "Marth"),
        entrant(3, 3, "Player Three", "Pikachu"),
        entrant(4, 4, "Player Four", "Peach"),
        **TOURNAMENT,
        output_path=Path(__file__).with_name("singles_top_4.png"),
    )

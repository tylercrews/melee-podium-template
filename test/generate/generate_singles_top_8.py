"""Edit the values below, then run this file to create one singles top-8 image."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import draw_singles_top_8
from models import Character, SinglesEntrant


TOURNAMENT = {
    "tournament_name": "Moon Dog Melee #11: med1cinal's Birthday Bash! Secondaries Singles",
    "tournament_date": "7/17/2026",
    "entrants_count": 19,
}


def entrant(
    seed: int | None,
    placement: int,
    tag: str,
    characters: list[Character],
) -> SinglesEntrant:
    return SinglesEntrant(
        seed=seed,
        placement=placement,
        characters=characters,
        tag=tag,
    )


if __name__ == "__main__":
    draw_singles_top_8(
        entrant(1, 1, "BU$TA", [Character("Captain Falcon", "white")]),
        entrant(
            2,
            2,
            "Magnificent Tide",
            [Character("Sheik", pose="b"), Character("Marth", "red")],
        ),
        entrant(3, 3, "HBK", [Character("Fox")]),
        entrant(
            4,
            4,
            "DukDota",
            [Character("Falco"), Character("Captain Falcon", "black")],
        ),
        entrant(10, 5, "Felipé", [Character("Captain Falcon", "green")]),
        entrant(
            8,
            5,
            "Qwain",
            [Character("Sheik", pose="b"), Character("Marth"), Character("Captain Falcon")],
        ),
        entrant(6, 7, "Tyro", [Character("Peach", "yellow")]),
        entrant(
            5,
            7,
            "Shenal",
            [
                Character("Marth"),
                Character("Fox"),
                Character("Falco"),
                Character("Mewtwo"),
                Character("Captain Falcon"),
                Character("Kirby"),
            ],
        ),
        **TOURNAMENT,
        output_path=Path(__file__).with_name("singles_top_8.png"),
    )

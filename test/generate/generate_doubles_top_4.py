"""Edit the values below, then run this file to create one doubles top-4 image."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import draw_doubles_top_4
from models import Character, DoublesTeam, Entrant


TOURNAMENT = {
    "tournament_name": "take your med.icine! 2 Doubles!!",
    "tournament_date": "7/11/2026",
    "entrants_count": 11,
}


def team(
    seed: int | None,
    placement: int,
    name: str,
    tag_1: str,
    character_1: Character,
    tag_2: str,
    character_2: Character,
    team_color: str | None = None,
) -> DoublesTeam:
    return DoublesTeam(
        seed=seed,
        placement=placement,
        entrant_1=Entrant(characters=[character_1], tag=tag_1),
        entrant_2=Entrant(characters=[character_2], tag=tag_2),
        team_name=name,
        team_color=team_color,
    )


if __name__ == "__main__":
    draw_doubles_top_4(
        team(
            1, 1, "Bl@ckChris + 1", "Bl@ckChris",
            Character("Fox", pose="b"), "Timebones", Character("Marth"), "green",
        ),
        team(
            2, 2, "LabubuRave", "meenis tiny", Character("Fox", pose="a"),
            "Jennifer", Character("Fox", pose="a"), "red",
        ),
        team(
            6, 3, "Naan Believers", "Siddward", Character("Luigi"),
            "Biscuit", Character("Captain Falcon", pose="b"), "red",
        ),
        team(
            4, 4, "qwain gang", "qwain", Character("Fox", pose="b"),
            "BU$TA", Character("Fox", pose="a"), "green",
        ),
        **TOURNAMENT,
        output_path=Path(__file__).with_name("doubles_top_4.png"),
    )

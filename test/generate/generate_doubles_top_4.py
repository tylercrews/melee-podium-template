"""Edit the values below, then run this file to create one doubles top-4 image."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import draw_doubles_top_4
from models import Character, DoublesTeam, Entrant


TOURNAMENT = {
    "tournament_name": "Moon Dog Melee #11: med1cinal's Birthday Bash! RanDubs",
    "tournament_date": "7/17/2026",
    "entrants_count": 10,
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
            None, 1, "meenis tiny + brooke bustamove", "meenis tiny",
            Character("Donkey Kong", pose=None), "brooke bustamove",
            Character("Donkey Kong", pose=None), "red",
        ),
        team(
            None, 2, "Subie + DukDota", "Subie", Character("Fox", pose=None),
            "DukDota", Character("Fox", pose=None), "blue",
        ),
        team(
            None, 3, "HBK + rosier", "HBK", Character("Fox", pose=None),
            "rosier", Character("Fox", pose=None), "red",
        ),
        team(
            None, 4, "Felipé + wrht", "Felipé",
            Character("Captain Falcon", pose=None), "wrht",
            Character("Captain Falcon", pose=None), "green",
        ),
        **TOURNAMENT,
        output_path=Path(__file__).with_name("doubles_top_4.png"),
    )

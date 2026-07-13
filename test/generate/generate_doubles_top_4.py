"""Edit the values below, then run this file to create one doubles top-4 image."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import draw_doubles_top_4
from models import Character, DoublesTeam


TOURNAMENT = {
    "tournament_name": "Shenfest Randubs",
    "tournament_date": "7/10/2026",
    "entrants_count": 14,
}


def team(
    placement: int,
    name: str,
    tag_1: str,
    character_1: Character,
    tag_2: str,
    character_2: Character,
    team_color: str | None = None,
) -> DoublesTeam:
    return DoublesTeam(
        seed=None,
        placement=placement,
        character_1=character_1,
        character_2=character_2,
        tag_1=tag_1,
        tag_2=tag_2,
        team_name=name,
        team_color=team_color,
    )


if __name__ == "__main__":
    draw_doubles_top_4(
        team(
            1, "Baldur's Gate Baddies", "shenal",
            Character("Mr. Game and Watch"), "killbugs", Character("Peach"), "green",
        ),
        team(
            2, "Hyrule Hustle", "HBK", Character("Sheik", pose="b"),
            "Subie", Character("Samus"), "red",
        ),
        team(
            3, "Judgement", "Geoux", Character("Marth"),
            "Silent Skyler", Character("Sheik", pose="b"), "red",
        ),
        team(
            4, "BarelyBusta", "Busta", Character("Fox", pose="b"),
            "Barely", Character("Fox"), "green",
        ),
        **TOURNAMENT,
        output_path=Path(__file__).with_name("doubles_top_4.png"),
    )

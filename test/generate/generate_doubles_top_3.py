"""Edit the values below, then run this file to create one doubles top-3 image."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import draw_doubles_top_3
from models import Character, DoublesTeam, Entrant, Tournament


TOURNAMENT = Tournament(
    title="Example Tournament",
    date="July 12, 2026",
    entrants_count=64,
)


def team(seed: int | None, placement: int, name: str, player_1: str, player_2: str, color: str | None) -> DoublesTeam:
    return DoublesTeam(
        seed=seed,
        placement=placement,
        entrant_1=Entrant(characters=[Character(player_1)], tag=player_1),
        entrant_2=Entrant(characters=[Character(player_2)], tag=player_2),
        team_name=name,
        team_color=color,
    )


if __name__ == "__main__":
    draw_doubles_top_3(
        team(1, 1, "Team One", "Fox", "Falco", "red"),
        team(2, 2, "Team Two", "Marth", "Sheik", "blue"),
        team(3, 3, "Team Three", "Peach", "Pikachu", "green"),
        tournament=TOURNAMENT,
        output_path=Path(__file__).with_name("doubles_top_3.png"),
    )

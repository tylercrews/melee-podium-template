"""Edit the values below, then run this file to create one doubles top-4 image."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import draw_doubles_top_4
from example_entrants import FELIPE, HBK, MEENIS_TINY, SUBIE
from models import Character, DoublesTeam, Entrant, Tournament


TOURNAMENT = Tournament(
    title="Moon Dog Melee #11",
    subtitle="med1cinal's Birthday Bash!",
    date="7/17/2026",
    entrants_count=10,
)


def team(
    seed: int | None,
    placement: int,
    name: str,
    entrant_1: Entrant,
    entrant_2: Entrant,
    team_color: str | None = None,
) -> DoublesTeam:
    return DoublesTeam(
        seed=seed,
        placement=placement,
        entrant_1=entrant_1,
        entrant_2=entrant_2,
        team_name=name,
        team_color=team_color,
    )


if __name__ == "__main__":
    brooke_bustamove = Entrant(
        characters=[Character("Donkey Kong", pose=None)],
        tag="brooke bustamove",
    )
    dukdota = Entrant(characters=[Character("Fox", pose=None)], tag="DukDota")
    rosier = Entrant(characters=[Character("Fox", pose=None)], tag="rosier")
    wrht = Entrant(
        characters=[Character("Captain Falcon", pose=None)],
        tag="wrht",
    )

    draw_doubles_top_4(
        team(
            None,
            1,
            "meenis tiny + brooke bustamove",
            MEENIS_TINY,
            brooke_bustamove,
            "red",
        ),
        team(None, 2, "Subie + DukDota", SUBIE, dukdota, "blue"),
        team(None, 3, "HBK + rosier", HBK, rosier, "red"),
        team(None, 4, f"{FELIPE.tag} + wrht", FELIPE, wrht, "green"),
        tournament=TOURNAMENT,
        output_path=Path(__file__).with_name("doubles_top_4.png"),
    )

"""Render the extended clapping templates through the same path as downloads."""

from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from creation_modes import PodiumStyle
from DrawPodium import PodiumFont
from format_preview import prepare_format_preview
from models import TournamentFormat
from portrait_assets import resolve_character_path, PORTRAIT_FILENAME
from sample_creation_data import sample_top_8_teams, sample_singles_entrants, sample_tournament


def fixed_member(member):
    characters = []
    for character in member.characters:
        match = PORTRAIT_FILENAME.match(resolve_character_path(character).name)
        characters.append(replace(character, pose=match["pose"], color=match["color"]))
    return replace(member, characters=characters)


def generate():
    output = ROOT / "test/generated/extended_clapping"
    output.mkdir(parents=True, exist_ok=True)
    singles = [fixed_member(entrant) for entrant in sample_singles_entrants(16,
               placements=(1, 2, 3, 4, 5, 5, 7, 7, 9, 9, 9, 9, 13, 13, 13, 13))]
    teams = [replace(team, placement=(1, 2, 3, 4, 5, 5, 7, 7)[index],
             entrant_1=fixed_member(team.entrant_1), entrant_2=fixed_member(team.entrant_2),
             team_name=f"Team {index + 1}") for index, team in enumerate(sample_top_8_teams())]
    for event_format, count, variant, entrants in (
        (TournamentFormat.DOUBLES, 8, "four_podium", teams),
        (TournamentFormat.SINGLES, 16, "clapping", singles),
    ):
        tournament = replace(sample_tournament(event_format), title="Podiums+Clapping",
                             subtitle=f"{'Doubles' if count == 8 else 'Singles'} Top {count}")
        for style in PodiumStyle:
            layout = prepare_format_preview(style, event_format, count, variant,
                       font=PodiumFont.UBUNTU, entrants=entrants, tournament=tournament,
                       header_layout={"top_left": "tournament_title", "top_middle": "tournament_logo", "top_right": "metadata"})
            for extension, data in (("png", layout.png()), ("gif", layout.gif())):
                path = output / f"{style.value}-{event_format.value}-top-{count}.{extension}"
                path.write_bytes(data)
                print(path)


if __name__ == "__main__":
    generate()

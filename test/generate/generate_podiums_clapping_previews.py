"""Regenerate still and animated examples using the runtime content renderer."""

from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from creation_modes import PodiumStyle
from DrawPodium import PodiumFont
from format_preview import prepare_format_preview
from models import TournamentFormat
from portrait_assets import PORTRAIT_FILENAME, resolve_character_path
from sample_creation_data import sample_clapping_top_8_entrants, sample_tournament


def generate():
    output = ROOT / "test/clapping_portrait_previews/four_podium_placement"
    output.mkdir(parents=True, exist_ok=True)
    entrants = sample_clapping_top_8_entrants()
    for index, entrant in enumerate(entrants):
        characters = []
        for character in entrant.characters:
            match = PORTRAIT_FILENAME.match(resolve_character_path(character).name)
            characters.append(replace(character, pose=match["pose"], color=match["color"]))
        entrants[index] = replace(entrant, characters=characters)
    tournament = replace(sample_tournament(), title="Podiums+Clapping Preview", subtitle="Four podiums and four portrait panels")
    for style in PodiumStyle:
        layout = prepare_format_preview(style, TournamentFormat.SINGLES, 8, "four_podium",
                                        font=PodiumFont.UBUNTU, entrants=entrants, tournament=tournament)
        for animated in (True, False):
            destination = output / f"{style.value}-podiums-clapping-{'animated' if animated else 'still'}.png"
            destination.write_bytes(layout.png(animated))
            print(destination)


if __name__ == "__main__":
    generate()

"""Review Sandbag's podium scale, clapping windows, and Eyes focal profiles."""

from dataclasses import replace
from pathlib import Path
import random
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from clapping_portrait_renderer import render_clapping_portrait
from creation_modes import PodiumStyle
from DrawPodium import PodiumFont
from eyes_portrait_renderer import render_eye_portrait
from format_preview import render_format_preview
from models import Character, TournamentFormat
from sample_creation_data import sample_top_8_entrants, sample_top_4_teams


def generate():
    output = ROOT / "test/sandbag_portrait_previews"
    output.mkdir(parents=True, exist_ok=True)
    randomizer = random.Random(2026)
    singles = sample_top_8_entrants(randomizer)[:4]
    for index, (name, pose) in enumerate([("Sandbag", "a"), ("Fox", "e"), ("Mario", "c"), ("Sandbag", "a")]):
        singles[index] = replace(singles[index], tag=name, characters=[Character(name, pose=pose)])
    teams = sample_top_4_teams(randomizer)
    for index, team in enumerate(teams):
        teams[index] = replace(team, team_name="Sandbag / Mario",
            team_color=["red", "green", "blue", "red"][index],
            entrant_1=replace(team.entrant_1, tag="Sandbag", characters=[Character("Sandbag")]),
            entrant_2=replace(team.entrant_2, tag="Mario", characters=[Character("Mario", pose="c")]))
    for style in PodiumStyle:
        for event_format, entrants in [(TournamentFormat.SINGLES, singles), (TournamentFormat.DOUBLES, teams)]:
            preview = render_format_preview(style, event_format, 4, font=PodiumFont.UBUNTU, entrants=entrants)
            preview.save(output / f"{style.value}-{event_format.value}-podiums.png")

    clapping = Image.new("RGBA", (1000, 415), "#303030FF")
    draw = ImageDraw.Draw(clapping)
    for index, (name, placement) in enumerate([("Sandbag", 2), ("Sandbag", 3), ("Sandbag", 4), ("Fox", 3), ("Mario", 3)]):
        portrait = render_clapping_portrait(Character(name), (112, 172), placement=placement,
                                           background_color="#666666FF")
        portrait = portrait.resize((190, 292), Image.Resampling.LANCZOS)
        clapping.alpha_composite(portrait, (index * 200 + 5, 50))
        draw.text((index * 200 + 8, 20), f"{name} - profile {placement}", fill="#FFFFFFFF")
    draw.text((10, 370), "Profile 3 is used for every lower result. All team-color copies share these proportions.", fill="#FFFFFFFF")
    clapping.save(output / "clapping-proportions.png")

    eyes = Image.new("RGBA", (800, 820), "#303030FF")
    draw = ImageDraw.Draw(eyes)
    for row, (name, pose, doubles) in enumerate([("Sandbag", "a", False), ("Fox", "e", False), ("Sandbag", "a", True), ("Fox", "e", True)]):
        width = 390 if doubles else 780
        portrait = render_eye_portrait(Character(name, pose=pose), (width, 160), doubles=doubles)
        eyes.alpha_composite(portrait, (10, row * 200 + 35))
        draw.text((10, row * 200 + 10), f"{name} - {'Doubles member' if doubles else 'Singles'}", fill="#FFFFFFFF")
        draw.line((width // 2 + 2, row * 200 + 115, width // 2 + 18, row * 200 + 115), fill="#FF69B4FF", width=2)
        draw.line((width // 2 + 10, row * 200 + 107, width // 2 + 10, row * 200 + 123), fill="#FF69B4FF", width=2)
    eyes.save(output / "eyes-proportions.png")
    print(output)


if __name__ == "__main__":
    generate()

"""Generate preview images for all five supported podium layouts."""

from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from DrawPodium import (
    draw_doubles_top_3,
    draw_doubles_top_4,
    draw_singles_top_3,
    draw_singles_top_4,
    draw_singles_top_8,
)
from models import Character, DoublesTeam, Entrant, SinglesEntrant, Tournament


OUTPUT_FOLDER = Path(__file__).with_name("podiums_test_outputs")
OVERVIEW_PATH = Path(__file__).with_name("podiums_test_output.png")
TOURNAMENT = Tournament(
    title="Podium Rendering Test",
    date="July 12, 2026",
    entrants_count=64,
    link="https://www.example.test/brackets/podium-rendering-test",
)


def singles_entrant(
    placement: int,
    fighter: str,
    *,
    color: str = "default",
    pose: str = "a",
) -> SinglesEntrant:
    return SinglesEntrant(
        seed=placement,
        placement=placement,
        characters=[Character(fighter, color, pose)],
        tag=fighter,
    )


def doubles_team(
    placement: int,
    fighter_1: str,
    fighter_2: str,
    *,
    pose_1: str = "a",
    pose_2: str = "b",
    team_color: str | None = None,
) -> DoublesTeam:
    return DoublesTeam(
        seed=placement,
        placement=placement,
        entrant_1=Entrant(
            characters=[Character(fighter_1, "default", pose_1)], tag=fighter_1
        ),
        entrant_2=Entrant(
            characters=[Character(fighter_2, "default", pose_2)], tag=fighter_2
        ),
        team_name=f"{fighter_1} / {fighter_2}",
        team_color=team_color,
    )


def create_overview(outputs: list[tuple[str, Path]]) -> None:
    """Create a half-size contact sheet for comparing all five layouts."""
    preview_size = (836, 470)
    label_height = 30
    columns = 2
    rows = (len(outputs) + columns - 1) // columns
    overview = Image.new(
        "RGB",
        (preview_size[0] * columns, (preview_size[1] + label_height) * rows),
        (22, 22, 26),
    )
    draw = ImageDraw.Draw(overview)
    font = ImageFont.load_default(size=18)

    for index, (label, path) in enumerate(outputs):
        with Image.open(path) as image:
            preview = image.convert("RGB").resize(
                preview_size,
                Image.Resampling.LANCZOS,
            )
        column = index % columns
        row = index // columns
        x = column * preview_size[0]
        y = row * (preview_size[1] + label_height)
        overview.paste(preview, (x, y))
        draw.text((x + 10, y + preview_size[1] + 5), label, fill="white", font=font)

    overview.save(OVERVIEW_PATH)


def main() -> None:
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    outputs: list[tuple[str, Path]] = []

    doubles_top_3 = [
        doubles_team(1, "Bowser", "Fox", pose_1="b", team_color="red"),
        doubles_team(2, "Bowser", "Falco", pose_1="a", team_color="blue"),
        doubles_team(3, "Kirby", "Pichu", team_color="green"),
    ]
    path = OUTPUT_FOLDER / "doubles_top_3.png"
    draw_doubles_top_3(*doubles_top_3, tournament=TOURNAMENT, output_path=path)
    outputs.append(("Doubles Top 3", path))

    doubles_top_4 = [
        doubles_team(1, "Bowser", "Captain Falcon", pose_1="b", team_color="red"),
        doubles_team(2, "Bowser", "Peach", pose_1="a", team_color="blue"),
        doubles_team(3, "Marth", "Jigglypuff", team_color="green"),
        doubles_team(4, "Pichu", "Pikachu", team_color="red"),
    ]
    path = OUTPUT_FOLDER / "doubles_top_4.png"
    draw_doubles_top_4(*doubles_top_4, tournament=TOURNAMENT, output_path=path)
    outputs.append(("Doubles Top 4", path))

    singles_top_3 = [
        singles_entrant(1, "Bowser", pose="b"),
        singles_entrant(2, "Pichu"),
        singles_entrant(3, "Bowser", pose="a"),
    ]
    path = OUTPUT_FOLDER / "singles_top_3.png"
    draw_singles_top_3(*singles_top_3, tournament=TOURNAMENT, output_path=path)
    outputs.append(("Singles Top 3", path))

    singles_top_4 = [
        singles_entrant(1, "Bowser", pose="a"),
        singles_entrant(2, "Bowser", pose="b"),
        singles_entrant(3, "Marth"),
        singles_entrant(4, "Pichu"),
    ]
    path = OUTPUT_FOLDER / "singles_top_4.png"
    draw_singles_top_4(*singles_top_4, tournament=TOURNAMENT, output_path=path)
    outputs.append(("Singles Top 4", path))

    top_8_placements = [1, 2, 3, 4, 5, 5, 7, 7]
    top_8_characters = [
        ("Bowser", "b"),
        ("Bowser", "a"),
        ("Donkey Kong", "a"),
        ("Sheik", "a"),
        ("Fox", "a"),
        ("Falco", "a"),
        ("Kirby", "a"),
        ("Pichu", "a"),
    ]
    singles_top_8 = [
        singles_entrant(placement, fighter, pose=pose)
        for placement, (fighter, pose) in zip(top_8_placements, top_8_characters)
    ]
    path = OUTPUT_FOLDER / "singles_top_8.png"
    draw_singles_top_8(*singles_top_8, tournament=TOURNAMENT, output_path=path)
    outputs.append(("Singles Top 8", path))

    create_overview(outputs)
    print(f"Generated {len(outputs)} podium previews in {OUTPUT_FOLDER}")
    print(f"Generated overview: {OVERVIEW_PATH}")


if __name__ == "__main__":
    main()

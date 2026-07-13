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
from models import Character, DoublesTeam, SinglesEntrant


OUTPUT_FOLDER = Path(__file__).with_name("podiums_test_outputs")
OVERVIEW_PATH = Path(__file__).with_name("podiums_test_output.png")
TOURNAMENT_DETAILS = {
    "tournament_name": "Podium Rendering Test",
    "tournament_date": "July 12, 2026",
    "entrants_count": 64,
    "location": "Test Location",
    "tournament_time": "7:00 PM",
}


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
        character=Character(fighter, color, pose),
        tag=fighter,
    )


def doubles_team(
    placement: int,
    fighter_1: str,
    fighter_2: str,
    *,
    pose_1: str = "a",
    pose_2: str = "b",
) -> DoublesTeam:
    return DoublesTeam(
        seed=placement,
        placement=placement,
        character_1=Character(fighter_1, "default", pose_1),
        character_2=Character(fighter_2, "default", pose_2),
        tag_1=fighter_1,
        tag_2=fighter_2,
        team_name=f"{fighter_1} / {fighter_2}",
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
        doubles_team(1, "Bowser", "Fox", pose_1="b"),
        doubles_team(2, "Sheik", "Falco"),
        doubles_team(3, "Kirby", "Pichu"),
    ]
    path = OUTPUT_FOLDER / "doubles_top_3.png"
    draw_doubles_top_3(*doubles_top_3, **TOURNAMENT_DETAILS, output_path=path)
    outputs.append(("Doubles Top 3", path))

    doubles_top_4 = [
        doubles_team(1, "Bowser", "Captain Falcon", pose_1="b"),
        doubles_team(2, "Donkey Kong", "Peach"),
        doubles_team(3, "Marth", "Jigglypuff"),
        doubles_team(4, "Pichu", "Pikachu"),
    ]
    path = OUTPUT_FOLDER / "doubles_top_4.png"
    draw_doubles_top_4(*doubles_top_4, **TOURNAMENT_DETAILS, output_path=path)
    outputs.append(("Doubles Top 4", path))

    singles_top_3 = [
        singles_entrant(1, "Bowser", pose="b"),
        singles_entrant(2, "Pichu"),
        singles_entrant(3, "Fox"),
    ]
    path = OUTPUT_FOLDER / "singles_top_3.png"
    draw_singles_top_3(*singles_top_3, **TOURNAMENT_DETAILS, output_path=path)
    outputs.append(("Singles Top 3", path))

    singles_top_4 = [
        singles_entrant(1, "Bowser", pose="b"),
        singles_entrant(2, "Sheik"),
        singles_entrant(3, "Marth"),
        singles_entrant(4, "Pichu"),
    ]
    path = OUTPUT_FOLDER / "singles_top_4.png"
    draw_singles_top_4(*singles_top_4, **TOURNAMENT_DETAILS, output_path=path)
    outputs.append(("Singles Top 4", path))

    top_8_placements = [1, 2, 3, 4, 5, 5, 7, 7]
    top_8_fighters = [
        "Bowser",
        "Captain Falcon",
        "Donkey Kong",
        "Sheik",
        "Fox",
        "Falco",
        "Kirby",
        "Pichu",
    ]
    singles_top_8 = [
        singles_entrant(placement, fighter, pose="b" if fighter == "Bowser" else "a")
        for placement, fighter in zip(top_8_placements, top_8_fighters)
    ]
    path = OUTPUT_FOLDER / "singles_top_8.png"
    draw_singles_top_8(*singles_top_8, **TOURNAMENT_DETAILS, output_path=path)
    outputs.append(("Singles Top 8", path))

    create_overview(outputs)
    print(f"Generated {len(outputs)} podium previews in {OUTPUT_FOLDER}")
    print(f"Generated overview: {OVERVIEW_PATH}")


if __name__ == "__main__":
    main()

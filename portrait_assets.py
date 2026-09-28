"""Resolve and load character portraits independently of any layout renderer."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from random import choice
import re

from PIL import Image

from models import Character
from portrait_scale_adjustment_to_character_relativity import get_pose_scale


PROJECT_ROOT = Path(__file__).resolve().parent
CHARACTER_FOLDER = PROJECT_ROOT / "char_assets" / "renders"
PORTRAIT_FILENAME = re.compile(
    r"^(?P<color_code>\d+)(?P<pose>[a-z]+)_(?P<color>[^_]+)_",
    re.IGNORECASE,
)


def resolve_character_path(character: Character) -> Path:
    """Resolve one selected costume/pose without exposing filename rules."""

    folder = CHARACTER_FOLDER / character.melee_fighter_name
    if not folder.is_dir():
        raise FileNotFoundError(f"Character folder does not exist: {folder}")

    matches: list[Path] = []
    available: set[str] = set()
    requested_color = (
        character.color.casefold() if character.color is not None else None
    )
    requested_pose = character.pose.casefold() if character.pose is not None else None
    random_color = requested_color is None
    random_pose = requested_pose is None

    for path in sorted(folder.glob("*.png")):
        match = PORTRAIT_FILENAME.match(path.name)
        if match is None:
            continue
        color_code = match.group("color_code").casefold()
        color_name = match.group("color").casefold()
        pose = match.group("pose").casefold()
        available.add(f"{color_name}/{pose}")
        if (random_pose or pose == requested_pose) and (
            random_color
            or requested_color in {color_name, color_code, f"{color_code}_{color_name}"}
        ):
            matches.append(path)

    if not matches:
        options = ", ".join(sorted(available)) or "none"
        raise ValueError(
            f"No {character.melee_fighter_name} image exists for color "
            f"{character.color!r} and pose {character.pose!r}. "
            f"Available color/pose combinations: {options}"
        )
    if random_color or random_pose:
        return choice(matches)
    if len(matches) > 1:
        raise ValueError(
            f"Expected one {character.melee_fighter_name} image for color "
            f"{character.color!r} and pose {character.pose!r}; found {len(matches)}"
        )
    return matches[0]


def load_character_source(character: Character) -> tuple[Image.Image, str]:
    """Return an RGBA source portrait and its stable lower-case pose code."""

    path = resolve_character_path(character)
    match = PORTRAIT_FILENAME.match(path.name)
    if match is None:
        raise ValueError(f"Cannot determine pose from portrait filename: {path.name}")
    with Image.open(path) as source:
        image = source.convert("RGBA")
    pose = match.group("pose").casefold()
    if character.mirror_horizontally:
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return image, pose


def load_scaled_portrait(character: Character, mode_scale: float) -> Image.Image:
    """Apply shared pose relativity followed by a layout-specific scale."""

    if mode_scale <= 0:
        raise ValueError("mode_scale must be greater than zero")
    image, pose = load_character_source(character)
    total_scale = get_pose_scale(
        character.melee_fighter_name,
        f"00{pose}",
    ) * mode_scale
    image = image.resize(
        (
            max(1, round(image.width * total_scale)),
            max(1, round(image.height * total_scale)),
        ),
        Image.Resampling.LANCZOS,
    )
    return image


def with_team_color(character: Character, team_color: str | None) -> Character:
    """Return a doubles-color portrait request without mutating the entrant."""

    return character if team_color is None else replace(character, color=team_color)

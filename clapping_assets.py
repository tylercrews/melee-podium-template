"""Resolve costume-correct clapping GIFs independently of static portrait poses."""

from __future__ import annotations

import json
from pathlib import Path
from random import choice

from PIL import Image

from models import Character


CLAPPING_FOLDER = Path(__file__).resolve().parent / "char_assets/animated_renders/clapping"


def resolve_clapping_path(character: Character) -> Path:
    """Resolve the animation's costume; the selected static pose is irrelevant."""

    manifest = json.loads((CLAPPING_FOLDER / "manifest.json").read_text(encoding="utf-8"))
    matches = []
    for asset in manifest["assets"]:
        if asset["character"] != character.melee_fighter_name:
            continue
        if character.color is None or character.color.casefold() in {
            asset["color"].casefold(),
            asset["color_code"],
            f"{asset['color_code']}_{asset['color']}".casefold(),
        }:
            path = CLAPPING_FOLDER / asset["path"]
            if not path.resolve().is_relative_to(CLAPPING_FOLDER.resolve()):
                raise ValueError("Clapping asset path must stay inside its collection")
            matches.append(path)
    if not matches:
        raise ValueError(
            f"No clapping animation for {character.melee_fighter_name} color {character.color!r}"
        )
    path = choice(matches) if character.color is None else matches[0]
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def load_clapping_frame(character: Character, frame_index: int = 0) -> Image.Image:
    """Return a detached RGBA GIF frame without applying crop or mirroring."""

    if isinstance(frame_index, bool) or not isinstance(frame_index, int) or frame_index < 0:
        raise ValueError("frame_index must be a non-negative integer")
    with Image.open(resolve_clapping_path(character)) as animation:
        if frame_index >= animation.n_frames:
            raise ValueError(f"frame_index must be less than {animation.n_frames}")
        animation.seek(frame_index)
        return animation.convert("RGBA")

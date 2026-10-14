"""Cached PR header defaults without tournament links or a single-date placeholder."""

from itertools import permutations
from pathlib import Path

from creation import TextSettings
from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from DrawPodium import PodiumFont
from layout_text_defaults import layout_text_defaults
from models import TournamentFormat
from preview_layers import HEADER_CONTENTS, HEADER_POSITIONS, header_permutation_id, render_header_layer, render_eye_header_layer


def generate_pr_preview_layers(root: Path, *, include_eyes: bool = True):
    selection = ModeSelection(CreationMode.PODIUM, ModeOptions(TournamentFormat.SINGLES, 11, "clapping_grid_4", PodiumStyle.CUSTOMIZABLE))
    settings = TextSettings(**layout_text_defaults(selection))
    paths = []
    for font in PodiumFont:
        for contents in permutations(HEADER_CONTENTS):
            layout = dict(zip(HEADER_POSITIONS, contents, strict=True))
            path = root / "headers/pr" / font.value / f"{header_permutation_id(layout)}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            render_header_layer(font, layout, text_settings=settings).save(path, optimize=True)
            paths.append(path)
            if include_eyes:
                for count in (10, 15, 20, 25):
                    path = root / "eye_headers" / font.value / f"singles_top_{count}" / f"{header_permutation_id(layout)}.png"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    render_eye_header_layer(font, f"singles_top_{count}", layout).save(path, optimize=True)
                    paths.append(path)
    return paths

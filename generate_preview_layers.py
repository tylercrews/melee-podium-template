"""Regenerate browser-composited Format preview layers."""

import argparse
from functools import partial
from pathlib import Path

from preview_layers import (
    generate_eye_color_preview_layers,
    generate_eye_preview_layers,
    generate_preview_layers,
    generate_square_preview_layers,
)
from radial_preview_layers import generate_radial_preview_layers
from flying_v_preview_layers import generate_flying_v_preview_layers
from clapping_preview_layers import generate_extended_clapping_layers
from placement_preview_layers import generate_numbering_preview_assets, generate_placement_number_layers
from pr_preview_layers import generate_pr_preview_layers


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--squares-only",
        action="store_true",
        help="Regenerate only Squares preset and header layers.",
    )
    parser.add_argument(
        "--eyes-colors-only",
        action="store_true",
        help="Regenerate only the combined Eyes preset-color layers.",
    )
    parser.add_argument(
        "--eyes-only",
        action="store_true",
        help="Regenerate only Eyes preset and header layers.",
    )
    parser.add_argument("--radial-only", action="store_true", help="Regenerate only Radial slice and center-header layers.")
    parser.add_argument("--flying-v-only", action="store_true", help="Regenerate only Flying V figure placeholders and header layers.")
    parser.add_argument("--extended-clapping-only", action="store_true", help="Regenerate all Singles and Doubles clapping preview layers.")
    parser.add_argument("--numbering-only", action="store_true", help="Regenerate formatting layers and both placement-number choices.")
    parser.add_argument("--clapping-grids-only", action="store_true", help="Regenerate Customizable Singles PR clap grids and their numbers.")
    parser.add_argument("--pr-headers-only", action="store_true", help="Regenerate Podium and Eyes PR headers with date-range defaults.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent / "frontend" / "public" / "format_preview_layers"
    if sum((args.squares_only, args.eyes_only, args.eyes_colors_only, args.radial_only, args.flying_v_only, args.extended_clapping_only, args.numbering_only, args.clapping_grids_only, args.pr_headers_only)) > 1:
        parser.error("Choose only one mode-specific generation flag.")
    generator = (
        generate_pr_preview_layers
        if args.pr_headers_only
        else partial(generate_extended_clapping_layers, grid_only=True)
        if args.clapping_grids_only
        else generate_numbering_preview_assets
        if args.numbering_only
        else generate_extended_clapping_layers
        if args.extended_clapping_only
        else generate_radial_preview_layers
        if args.radial_only
        else generate_flying_v_preview_layers
        if args.flying_v_only
        else
        generate_square_preview_layers
        if args.squares_only
        else generate_eye_preview_layers
        if args.eyes_only
        else generate_eye_color_preview_layers
        if args.eyes_colors_only
        else generate_preview_layers
    )
    generated = generator(root)
    if any((args.squares_only, args.eyes_only, args.eyes_colors_only, args.radial_only, args.flying_v_only, args.extended_clapping_only, args.clapping_grids_only)):
        generated.extend(generate_placement_number_layers(root, grid_only=args.clapping_grids_only))
    print(f"Generated {len(generated)} preview layers in {root}")

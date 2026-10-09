"""Regenerate browser-composited Format preview layers."""

import argparse
from pathlib import Path

from preview_layers import (
    generate_eye_color_preview_layers,
    generate_eye_preview_layers,
    generate_preview_layers,
    generate_square_preview_layers,
)
from radial_preview_layers import generate_radial_preview_layers


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
    args = parser.parse_args()
    root = Path(__file__).resolve().parent / "frontend" / "public" / "format_preview_layers"
    if sum((args.squares_only, args.eyes_only, args.eyes_colors_only, args.radial_only)) > 1:
        parser.error("Choose only one mode-specific generation flag.")
    generator = (
        generate_radial_preview_layers
        if args.radial_only
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
    print(f"Generated {len(generated)} preview layers in {root}")

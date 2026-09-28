"""Regenerate browser-composited Format preview layers."""

import argparse
from pathlib import Path

from preview_layers import (
    generate_eye_preview_layers,
    generate_preview_layers,
    generate_square_preview_layers,
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--squares-only",
        action="store_true",
        help="Regenerate only Squares preset and header layers.",
    )
    parser.add_argument(
        "--eyes-only",
        action="store_true",
        help="Regenerate only Eyes preset and header layers.",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent / "frontend" / "public" / "format_preview_layers"
    if args.squares_only and args.eyes_only:
        parser.error("Choose only one mode-specific generation flag.")
    generator = (
        generate_square_preview_layers
        if args.squares_only
        else generate_eye_preview_layers
        if args.eyes_only
        else generate_preview_layers
    )
    generated = generator(root)
    print(f"Generated {len(generated)} preview layers in {root}")

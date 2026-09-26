"""Regenerate browser-composited Format preview layers."""

from pathlib import Path

from preview_layers import generate_preview_layers


if __name__ == "__main__":
    root = Path(__file__).resolve().parent / "frontend" / "public" / "format_preview_layers"
    generated = generate_preview_layers(root)
    print(f"Generated {len(generated)} preview layers in {root}")

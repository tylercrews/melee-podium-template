"""Shared inventory for Customizable Top 3 podiums with a singles clap grid."""

import json
from pathlib import Path


GRID_LAYOUTS = tuple(json.loads(Path(__file__).with_suffix(".json").read_text(encoding="utf-8")))
GRID_VARIANTS = frozenset(f"clapping_grid_{row['columns']}" for row in GRID_LAYOUTS)


def grid_layout(count, variant):
    return next((row for row in GRID_LAYOUTS
                 if row["entrant_count"] == count and variant == f"clapping_grid_{row['columns']}"), None)


def grid_submode(row):
    return f"singles_top_{row['entrant_count']}_clapping_grid_{row['columns']}"

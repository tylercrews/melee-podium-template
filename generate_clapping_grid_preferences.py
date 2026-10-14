"""Extract Top 3 geometry and scaffold the separately reviewed singles clap grids."""

import copy
import json
from pathlib import Path

from clapping_grid_layouts import GRID_LAYOUTS, grid_submode
from placement_numbering import ordinal_asset_id


ROOT = Path(__file__).resolve().parent


def generate_preferences():
    folder = ROOT / "preferences/podium/customizable"
    source = json.loads((folder / "singles_top_3.json").read_text(encoding="utf-8"))
    layouts = {}
    for layout in GRID_LAYOUTS:
        submode = grid_submode(layout)
        preference = copy.deepcopy(source)
        preference["selection"]["options"].update(entrant_count=layout["entrant_count"],
            variant=f"clapping_grid_{layout['columns']}", animated=True)
        preference["canvas_size"]["height"] = layout["height"]
        path = folder / f"{submode}.json"
        preference["ready"] = json.loads(path.read_text())["ready"] if path.exists() else False
        path.write_text(json.dumps(preference, indent=2) + "\n", encoding="utf-8")
        panels, tags = [], []
        step = 1860 // layout["columns"]
        for index in range(layout["entrant_count"] - 3):
            row, column = divmod(index, layout["columns"])
            slot = index + 4
            left, top = 34 + column * step, 920 + row * 190
            right, bottom = left + 94, top + 142
            panels.append(dict(entrant_slot=slot, portrait_rect=[left, top, right, bottom],
                               text_x=right + 14, text_max_width=step - 126,
                               text_alignment="left", identity_scale=.85))
            tags.append(dict(slot_id=f"entrant_{slot}_placement_tag", asset_id=ordinal_asset_id(slot),
                             anchor=dict(x=right + 26, y=bottom + 8),
                             max_size=dict(width=66, height=40), z_index=200 + index))
        layouts[submode] = dict(canvas_size=preference["canvas_size"], panels=panels, placement_tags=tags)
    (ROOT / "preferences/portraits/clapping_grid.json").write_text(
        json.dumps(dict(schema_version=1, layouts=layouts), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    generate_preferences()

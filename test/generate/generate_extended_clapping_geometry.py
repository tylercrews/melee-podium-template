"""Regenerate visually reviewed extended geometry from podium calibrations."""

from copy import deepcopy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def generate():
    layouts = {"doubles_top_8_four_podium": {}, "singles_top_16_clapping": {}}
    original = json.loads((ROOT / "preferences/portraits/podiums_clapping.json").read_text())
    for style in ("legacy", "customizable"):
        folder = ROOT / "preferences/podium" / style
        doubles = json.loads((folder / "doubles_top_4.json").read_text())
        doubles["selection"]["options"].update(entrant_count=8, variant="four_podium", animated=True)
        doubles["canvas_size"]["height"] = 1280
        doubles["ready"] = True
        write_json(folder / "doubles_top_8_four_podium.json", doubles)
        profile = deepcopy(original["styles"][style])
        profile["canvas_size"] = doubles["canvas_size"]
        profile["panels"] = []
        profile["team_names"] = []
        for panel in original["styles"][style]["panels"]:
            for member in (1, 2):
                row = deepcopy(panel)
                row["member_slot"] = member
                row["portrait_rect"][1] = 925 + (member - 1) * 122
                row["portrait_rect"][3] = row["portrait_rect"][1] + 104
                profile["panels"].append(row)
            # Center the team label beneath both member rows, like the podium labels.
            left = panel["text_x"] - panel["text_max_width"] if panel["text_alignment"] == "right" else panel["portrait_rect"][0]
            right = panel["portrait_rect"][2] if panel["text_alignment"] == "right" else panel["text_x"] + panel["text_max_width"]
            profile["team_names"].append({"entrant_slot": panel["entrant_slot"],
                "anchor": {"x": (left + right) // 2, "y": 1180}, "max_width": right - left,
                "pillow_anchor": "ma", "preferred_size": 34})
        for index, badge in enumerate(profile["placement_tags"]):
            badge["anchor"]["y"] = 995 + (index % 2) * 80
        layouts["doubles_top_8_four_podium"][style] = profile

        singles = json.loads((folder / "singles_top_8.json").read_text())
        singles["selection"]["options"].update(entrant_count=16, variant="clapping", animated=True)
        singles["canvas_size"]["height"] = 1000
        singles["ready"] = True
        singles["text_slots"] = [row for row in singles["text_slots"] if row["field"] != "entrant.primary_character_name"]
        if style == "customizable":
            # The original file calibrates only its three largest numerals.
            # Explicitly give every remaining small podium canonical artwork.
            for index in range(3, 8):
                box = singles["formatting_assets"][index]["destination"]
                number_height = max(14, round((box["bottom"] - box["top"]) * .42))
                rank = (4, 5, 5, 7, 7)[index - 3]
                singles["placement_tags"].append({"slot_id": f"podium_{index + 1}_placement_tag",
                    "asset_id": f"{rank:02d}th.png",
                    "anchor": {"x": (box["left"] + box["right"]) // 2 - 5,
                               "y": box["bottom"] - (box["bottom"] - box["top"]) // 3},
                    "max_size": {"width": round(number_height * 1.5), "height": number_height}, "z_index": index})
        for row in singles["formatting_assets"]:
            row["destination"]["top"] -= 48
            row["destination"]["bottom"] -= 48
        for key in ("placement_tags", "character_slots", "text_slots"):
            for row in singles[key]:
                row["anchor"]["y"] -= 48
        write_json(folder / "singles_top_16_clapping.json", singles)
        width = singles["canvas_size"]["width"]
        profile = {"canvas_size": singles["canvas_size"], "panels": [], "placement_tags": []}
        for index in range(8):
            left = round(index * width / 8) + 12
            right = round((index + 1) * width / 8) - 12
            profile["panels"].append({"entrant_slot": index + 9,
                "portrait_rect": [left, 850, left + 52, 930], "text_x": left + 61,
                "text_max_width": right - left - 61, "text_alignment": "left", "identity_scale": 0.7})
            profile["placement_tags"].append({"slot_id": f"entrant_{index + 9}_placement_tag",
                "asset_id": "09th.png" if index < 4 else "13th.png",
                "anchor": {"x": left + 52 + 20, "y": 942},
                "max_size": {"width": 42, "height": 24}, "z_index": 200 + index})
        layouts["singles_top_16_clapping"][style] = profile
    write_json(ROOT / "preferences/portraits/extended_clapping.json", {"schema_version": 1, "layouts": layouts})


if __name__ == "__main__":
    generate()

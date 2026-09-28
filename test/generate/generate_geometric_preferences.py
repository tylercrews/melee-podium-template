"""Regenerate reviewed Eyes and Squares preference JSON files."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREFERENCES = PROJECT_ROOT / "preferences"


def _selection(mode: str, event_format: str, count: int) -> dict[str, object]:
    return {
        "mode": mode,
        "options": {
            "event_format": event_format,
            "entrant_count": count,
            "variant": None,
            "podium_style": None,
        },
    }


def _formatting(slot: int, asset: str, rect: tuple[int, int, int, int]) -> dict[str, object]:
    left, top, right, bottom = rect
    return {
        "slot_id": f"entrant_{slot}",
        "asset_id": asset,
        "destination": {"left": left, "top": top, "right": right, "bottom": bottom},
        "z_index": 0,
    }


def _character(
    slot: int,
    x: int,
    y: int,
    *,
    member: int | None = None,
    scale: float = 1.0,
) -> dict[str, object]:
    suffix = f"_member_{member}" if member is not None else ""
    return {
        "slot_id": f"entrant_{slot}{suffix}_character",
        "entrant_slot": slot,
        "member_slot": member,
        "anchor": {"x": x, "y": y},
        "scale": scale,
        "z_index": 10 + slot,
    }


def _text(
    slot_id: str,
    field: str,
    entrant_slot: int,
    x: int,
    y: int,
    width: int,
    size: int,
    *,
    anchor: str = "ma",
    member: int | None = None,
    color: str = "#FFFFFFFF",
    z_index: int = 30,
) -> dict[str, object]:
    return {
        "slot_id": slot_id,
        "field": field,
        "entrant_slot": entrant_slot,
        "member_slot": member,
        "anchor": {"x": x, "y": y},
        "max_width": width,
        "pillow_anchor": anchor,
        "preferred_size": size,
        "wrap": False,
        "z_index": z_index,
        "color": color,
    }


def _eyes_preferences(event_format: str, count: int) -> dict[str, object]:
    if event_format == "singles" and count == 8:
        rectangles = [
            (30, 28 + index * 231, 820, 188 + index * 231)
            for index in range(8)
        ]
    elif event_format == "doubles" and count == 3:
        rectangles = [
            (30, top, 820, top + 380)
            for top in (90, 660, 1230)
        ]
    elif event_format == "doubles" and count == 4:
        rectangles = [
            (30, top, 820, top + 320)
            for top in (70, 520, 970, 1420)
        ]
    else:
        raise ValueError("Unsupported reviewed Eyes layout")

    formatting = [
        {
            "slot_id": "header_bar",
            "asset_id": "eyes_header_bar",
            "destination": {"left": 850, "top": 20, "right": 1060, "bottom": 1900},
            "z_index": 0,
        }
    ] + [
        _formatting(index, "eyes_rectangle", rectangle)
        for index, rectangle in enumerate(rectangles, start=1)
    ]
    characters: list[dict[str, object]] = []
    text: list[dict[str, object]] = []
    for slot, (left, top, right, bottom) in enumerate(rectangles, start=1):
        if event_format == "singles":
            characters.append(_character(slot, (left + right) // 2, (top + bottom) // 2))
            tag_field = "entrant.tag"
            tag_size = 52
        else:
            characters.extend(
                (
                    _character(slot, left + (right - left) // 4, (top + bottom) // 2, member=1),
                    _character(slot, left + 3 * (right - left) // 4, (top + bottom) // 2, member=2),
                )
            )
            tag_field = "entrant.team_name"
            tag_size = 62 if count == 3 else 54
        text.extend(
            (
                _text(
                    f"entrant_{slot}_placement",
                    "entrant.placement",
                    slot,
                    right - 22,
                    (top + bottom) // 2,
                    130,
                    round((bottom - top) * 0.68),
                    anchor="rm",
                    color="#FFD400FF",
                ),
                _text(
                    f"entrant_{slot}_label",
                    tag_field,
                    slot,
                    left + 18,
                    bottom + 8,
                    right - left - 36,
                    tag_size,
                    anchor="la",
                ),
            )
        )
    return {
        "schema_version": 1,
        "ready": True,
        "selection": _selection("eyes", event_format, count),
        "canvas_size": {"width": 1080, "height": 1920},
        "formatting_assets": formatting,
        "placement_tags": [],
        "character_slots": characters,
        "text_slots": text,
    }


def _squares_preferences(event_format: str, count: int) -> dict[str, object]:
    if event_format == "singles" and count == 8:
        rectangles = [
            (80, 190, 630, 890),
            (680, 190, 1060, 560),
            (1090, 190, 1470, 560),
            (1500, 190, 1880, 560),
            (680, 590, 960, 890),
            (980, 590, 1260, 890),
            (1280, 590, 1560, 890),
            (1580, 590, 1860, 890),
        ]
        scales = (1.70, 1.05, 1.05, 1.05, 0.88, 0.88, 0.88, 0.88)
    elif event_format == "doubles" and count == 3:
        rectangles = [
            (70, 220, 630, 880),
            (680, 220, 1240, 880),
            (1290, 220, 1850, 880),
        ]
        scales = (1.0, 1.0, 1.0)
    elif event_format == "doubles" and count == 4:
        rectangles = [
            (50, 245, 485, 870),
            (510, 245, 945, 870),
            (970, 245, 1405, 870),
            (1430, 245, 1865, 870),
        ]
        scales = (1.0, 1.0, 1.0, 1.0)
    else:
        raise ValueError("Unsupported reviewed Squares layout")

    formatting = [
        _formatting(index, "square_card", rectangle)
        for index, rectangle in enumerate(rectangles, start=1)
    ]
    characters: list[dict[str, object]] = []
    text: list[dict[str, object]] = []
    for slot, ((left, top, right, bottom), scale) in enumerate(
        zip(rectangles, scales, strict=True),
        start=1,
    ):
        footer_height = max(62, round((bottom - top) * 0.17))
        portrait_bottom = bottom - footer_height
        if event_format == "singles":
            characters.append(
                _character(slot, (left + right) // 2, portrait_bottom, scale=scale)
            )
            label_field = "entrant.tag"
        else:
            characters.extend(
                (
                    _character(slot, left + (right - left) // 4, portrait_bottom, member=1, scale=scale),
                    _character(slot, left + 3 * (right - left) // 4, portrait_bottom, member=2, scale=scale),
                )
            )
            label_field = "entrant.team_name"
        placement_size = 150 if slot == 1 and count == 8 else 86
        text.extend(
            (
                _text(
                    f"entrant_{slot}_placement",
                    "entrant.placement",
                    slot,
                    left + 28,
                    top + 18,
                    min(170, right - left - 50),
                    placement_size,
                    anchor="la",
                ),
                _text(
                    f"entrant_{slot}_label",
                    label_field,
                    slot,
                    (left + right) // 2,
                    bottom - footer_height // 2,
                    right - left - 34,
                    70 if slot == 1 and count == 8 else 45,
                    anchor="mm",
                ),
                _text(
                    f"entrant_{slot}_seed",
                    "entrant.seed",
                    slot,
                    right - 22,
                    top + 18,
                    100,
                    27,
                    anchor="ra",
                ),
            )
        )
    return {
        "schema_version": 1,
        "ready": True,
        "selection": _selection("squares", event_format, count),
        "canvas_size": {"width": 1920, "height": 1080},
        "formatting_assets": formatting,
        "placement_tags": [],
        "character_slots": characters,
        "text_slots": text,
    }


def _write(mode: str, event_format: str, count: int, value: dict[str, object]) -> None:
    path = PREFERENCES / mode / f"{event_format}_top_{count}.json"
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(path)


def main() -> None:
    for mode, builder in (("eyes", _eyes_preferences), ("squares", _squares_preferences)):
        for event_format, count in (("singles", 8), ("doubles", 3), ("doubles", 4)):
            _write(mode, event_format, count, builder(event_format, count))
        # Retain the reserved singles scaffolds but give them the mode's real
        # output dimensions so selecting a future layout cannot mis-size assets.
        for count in (3, 4):
            path = PREFERENCES / mode / f"singles_top_{count}.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["canvas_size"] = (
                {"width": 1080, "height": 1920}
                if mode == "eyes"
                else {"width": 1920, "height": 1080}
            )
            path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
            print(path)


if __name__ == "__main__":
    main()

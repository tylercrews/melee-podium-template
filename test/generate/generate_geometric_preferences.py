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


def _ordinal_asset(placement: int) -> str:
    suffix = "th"
    if placement % 100 not in {11, 12, 13}:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(placement % 10, "th")
    return f"{placement:02d}{suffix}.png"


def _placement_tag(
    slot: int,
    placement: int,
    x: int,
    y: int,
    width: int,
    height: int,
) -> dict[str, object]:
    return {
        "slot_id": f"entrant_{slot}_placement_tag",
        "asset_id": _ordinal_asset(placement),
        "anchor": {"x": x, "y": y},
        "max_size": {"width": width, "height": height},
        "z_index": slot,
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
    placement_tags: list[dict[str, object]] = []
    text: list[dict[str, object]] = []
    placements = (1, 2, 3, 4, 5, 5, 7, 7) if count == 8 else tuple(range(1, count + 1))
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
        tag_width = 130 if slot == 1 else 112
        tag_height = 150 if event_format == "singles" else 180 if slot == 1 else 120
        placement_tags.append(
            _placement_tag(
                slot,
                placements[slot - 1],
                right - tag_width // 2 - 8,
                (top + bottom) // 2,
                tag_width,
                tag_height,
            )
        )
        text.append(
            _text(
                f"entrant_{slot}_label",
                tag_field,
                slot,
                left + 18,
                bottom + 8,
                right - left - 36,
                tag_size,
                anchor="la",
            )
        )
    return {
        "schema_version": 1,
        "ready": True,
        "selection": _selection("eyes", event_format, count),
        "canvas_size": {"width": 1080, "height": 1920},
        "formatting_assets": formatting,
        "placement_tags": placement_tags,
        "character_slots": characters,
        "text_slots": text,
    }


def _squares_preferences(event_format: str, count: int) -> dict[str, object]:
    if event_format == "singles" and count == 8:
        rectangles = [
            (40, 50, 630, 870),
            (680, 50, 1060, 470),
            (1090, 50, 1470, 470),
            (1500, 50, 1880, 470),
            (680, 490, 960, 870),
            (980, 490, 1260, 870),
            (1280, 490, 1560, 870),
            (1580, 490, 1860, 870),
        ]
        scales = (1.0,) * 8
    elif event_format == "doubles" and count == 3:
        rectangles = [
            (40, 50, 1220, 870),
            (1260, 50, 1880, 445),
            (1260, 475, 1880, 870),
        ]
        scales = (1.0,) * 3
    elif event_format == "doubles" and count == 4:
        rectangles = [
            (40, 50, 1220, 870),
            (1260, 50, 1880, 310),
            (1260, 330, 1880, 590),
            (1260, 610, 1880, 870),
        ]
        scales = (1.0,) * 4
    else:
        raise ValueError("Unsupported reviewed Squares layout")

    formatting = [
        _formatting(index, "square_card", rectangle)
        for index, rectangle in enumerate(rectangles, start=1)
    ]
    characters: list[dict[str, object]] = []
    placement_tags: list[dict[str, object]] = []
    text: list[dict[str, object]] = []
    placements = (1, 2, 3, 4, 5, 5, 7, 7) if count == 8 else tuple(range(1, count + 1))
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
        if slot == 1:
            tag_size = (190, 215) if event_format == "doubles" else (155, 175)
        else:
            tag_size = (100, 95) if event_format == "doubles" else (92, 88)
        placement_tags.append(
            _placement_tag(
                slot,
                placements[slot - 1],
                left + tag_size[0] // 2 + 18,
                top + tag_size[1] // 2 + 14,
                *tag_size,
            )
        )
        if event_format == "singles":
            text.extend(
                (
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
            continue

        card_width = right - left
        footer_center_y = bottom - footer_height // 2
        names_left = left + 18
        names_right = right - 18
        member_region_width = (names_right - names_left) // 2
        team_x = left + tag_size[0] + 36
        member_size = 76 if slot == 1 else 52 if count == 3 else 46
        seed_size = 44 if slot == 1 else 34
        team_size = 64 if slot == 1 else 44 if count == 3 else 38
        text.extend(
            (
                _text(
                    f"entrant_{slot}_team_name",
                    "entrant.team_name",
                    slot,
                    team_x,
                    top + 22,
                    right - team_x - 24,
                    team_size,
                    anchor="la",
                    z_index=5,
                ),
                _text(
                    f"entrant_{slot}_member_1_tag",
                    "member.tag",
                    slot,
                    names_left + member_region_width // 2,
                    footer_center_y,
                    member_region_width - 18,
                    member_size,
                    anchor="mm",
                    member=1,
                ),
                _text(
                    f"entrant_{slot}_member_2_tag",
                    "member.tag",
                    slot,
                    names_left + member_region_width + member_region_width // 2,
                    footer_center_y,
                    member_region_width - 18,
                    member_size,
                    anchor="mm",
                    member=2,
                ),
                _text(
                    f"entrant_{slot}_seed",
                    "entrant.seed",
                    slot,
                    right - 18,
                    portrait_bottom - 12,
                    105 if slot == 1 else 78,
                    seed_size,
                    anchor="rs",
                ),
            )
        )
    return {
        "schema_version": 1,
        "ready": True,
        "selection": _selection("squares", event_format, count),
        "canvas_size": {"width": 1920, "height": 1080},
        "formatting_assets": formatting,
        "placement_tags": placement_tags,
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

"""Validated, request-local pixel offsets for independently sized text."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from creation import TextSettings
    from models import DoublesTeam, SinglesEntrant


def validate_font_size_adjustment(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not -20 <= value <= 20:
        raise ValueError(f"{field_name} must be an integer between -20 and 20")


def adjusted_size(preferred_size: int, adjustment: int) -> int:
    return max(11, preferred_size + adjustment)


def result_text_adjustment(
    settings: TextSettings,
    result: SinglesEntrant | DoublesTeam | None,
    field: str,
    member_slot: int | None = None,
) -> int:
    if field == "entrant.seed":
        return settings.seed_font_size_adjustment
    if field == "entrant.team_name":
        return result.team_name_font_size_adjustment
    if field.startswith("member."):
        member = result.entrant_1 if member_slot == 1 else result.entrant_2
        return member.name_font_size_adjustment
    if field in {"entrant.tag", "entrant.player_tag", "entrant.sponsor"}:
        return result.name_font_size_adjustment
    return 0

"""Serializable, fixed source windows for each character's clapping animation."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path


CALIBRATION_PATH = Path(__file__).resolve().parent / "preferences/portraits/clapping.json"


@dataclass(frozen=True, slots=True)
class ClappingPortraitLayer:
    """A source member cutout translated onto the shared animation canvas."""

    source_crop: tuple[float, float, float, float]
    offset: tuple[float, float]
    layer_order: int

    def __post_init__(self) -> None:
        if len(self.source_crop) != 4 or len(self.offset) != 2 or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            for v in (*self.source_crop, *self.offset)
        ):
            raise ValueError("Member crops and offsets must have finite coordinates")
        left, top, right, bottom = self.source_crop
        if right <= left or bottom <= top:
            raise ValueError("Member crop must have positive width and height")
        if isinstance(self.layer_order, bool) or not isinstance(self.layer_order, int):
            raise ValueError("Member layer_order must be an integer")

    def to_dict(self) -> dict:
        return {
            "source_crop": list(self.source_crop),
            "offset": list(self.offset),
            "layer_order": self.layer_order,
        }

    @classmethod
    def from_dict(cls, value: dict) -> ClappingPortraitLayer:
        return cls(tuple(value["source_crop"]), tuple(value["offset"]), value["layer_order"])


@dataclass(frozen=True, slots=True)
class ClappingPortraitAdjustment:
    source_size: tuple[int, int]
    source_crop: tuple[float, float, float, float]
    member_layers: tuple[ClappingPortraitLayer, ...] = ()

    def __post_init__(self) -> None:
        if len(self.source_size) != 2 or any(
            isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in self.source_size
        ):
            raise ValueError("source_size must contain two positive integers")
        if len(self.source_crop) != 4 or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            for v in self.source_crop
        ):
            raise ValueError("source_crop must contain four finite coordinates")
        left, top, right, bottom = self.source_crop
        if right <= left or bottom <= top:
            raise ValueError("source_crop must have positive width and height")
        if any(not isinstance(layer, ClappingPortraitLayer) for layer in self.member_layers):
            raise ValueError("member_layers must contain validated portrait layers")
        if len({layer.layer_order for layer in self.member_layers}) != len(self.member_layers):
            raise ValueError("Member layer orders must be unique")
        # A window may extend outside the source; that area stays transparent.

    def to_dict(self) -> dict:
        value = {"source_size": list(self.source_size), "source_crop": list(self.source_crop)}
        if self.member_layers:
            value["member_layers"] = [layer.to_dict() for layer in self.member_layers]
        return value

    @classmethod
    def from_dict(cls, value: dict) -> ClappingPortraitAdjustment:
        return cls(
            tuple(value["source_size"]), tuple(value["source_crop"]),
            tuple(ClappingPortraitLayer.from_dict(layer) for layer in value.get("member_layers", [])),
        )


def get_clapping_portrait_profile(character_name: str, placement: int | None = None) -> dict:
    """Resolve a saved placement profile; normal callers use the selected default."""
    preferences = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    if preferences["schema_version"] not in (1, 2):
        raise ValueError("Unsupported clapping portrait calibration version")
    selected = preferences.get("default_placement", 3) if placement is None else placement
    if isinstance(selected, bool) or not isinstance(selected, int) or selected not in (2, 3, 4):
        raise ValueError("Clapping portrait placement must be 2, 3, or 4")
    try:
        character = preferences["characters"][character_name]
        if preferences["schema_version"] == 1:
            if placement is not None and selected != 3:
                raise ValueError("Legacy clapping calibration has no placement variants")
            return dict(character)
        profile = character["placement_profiles"][str(selected)]
        return {**{key: value for key, value in character.items() if key != "placement_profiles"},
                **profile, "placement": selected}
    except KeyError as error:
        raise ValueError(f"Missing {selected} placement clapping crop for {character_name}") from error


def get_clapping_portrait_adjustment(character_name: str, placement: int | None = None) -> ClappingPortraitAdjustment:
    return ClappingPortraitAdjustment.from_dict(get_clapping_portrait_profile(character_name, placement))

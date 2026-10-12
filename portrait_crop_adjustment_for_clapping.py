"""Serializable, fixed source windows for each character's clapping animation."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path


CALIBRATION_PATH = Path(__file__).resolve().parent / "preferences/portraits/clapping.json"


@dataclass(frozen=True, slots=True)
class ClappingPortraitAdjustment:
    source_size: tuple[int, int]
    source_crop: tuple[float, float, float, float]

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
        # A window may extend outside the source; that area stays transparent.

    def to_dict(self) -> dict:
        return {"source_size": list(self.source_size), "source_crop": list(self.source_crop)}

    @classmethod
    def from_dict(cls, value: dict) -> ClappingPortraitAdjustment:
        return cls(tuple(value["source_size"]), tuple(value["source_crop"]))


def get_clapping_portrait_adjustment(character_name: str) -> ClappingPortraitAdjustment:
    preferences = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    if preferences["schema_version"] != 1:
        raise ValueError("Unsupported clapping portrait calibration version")
    try:
        return ClappingPortraitAdjustment.from_dict(preferences["characters"][character_name])
    except KeyError as error:
        raise ValueError(f"Missing clapping crop for {character_name}") from error

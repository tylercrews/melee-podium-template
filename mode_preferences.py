"""Load and validate position preferences for creation modes and sub-modes."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Protocol

from background_builder import PixelRect, PixelSize
from creation_modes import CreationMode, ModeSelection


PROJECT_ROOT = Path(__file__).resolve().parent
MODE_PREFERENCES_FOLDER = PROJECT_ROOT / "preferences"
PREFERENCE_SCHEMA_VERSION = 1


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be an object")
    return value


def _items(value: object, name: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be an array")
    return [_mapping(item, f"{name} item") for item in value]


@dataclass(frozen=True, slots=True)
class PixelPoint:
    x: int
    y: int

    def __post_init__(self) -> None:
        _integer(self.x, "x")
        _integer(self.y, "y")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> PixelPoint:
        return cls(_integer(value.get("x"), "x"), _integer(value.get("y"), "y"))

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True, slots=True)
class FormattingAssetPlacement:
    slot_id: str
    asset_id: str
    destination: PixelRect
    z_index: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.slot_id, str) or not self.slot_id.strip():
            raise ValueError("formatting asset slot_id must be a non-empty string")
        if not isinstance(self.asset_id, str) or not self.asset_id.strip():
            raise ValueError("formatting asset asset_id must be a non-empty string")
        if not isinstance(self.destination, PixelRect):
            raise TypeError("formatting asset destination must be a PixelRect")
        _integer(self.z_index, "z_index")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> FormattingAssetPlacement:
        destination = _mapping(value.get("destination"), "destination")
        return cls(
            slot_id=value.get("slot_id") if isinstance(value.get("slot_id"), str) else "",
            asset_id=value.get("asset_id") if isinstance(value.get("asset_id"), str) else "",
            destination=PixelRect.from_dict(destination),
            z_index=_integer(value.get("z_index", 0), "z_index"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "asset_id": self.asset_id,
            "destination": self.destination.to_dict(),
            "z_index": self.z_index,
        }


@dataclass(frozen=True, slots=True)
class CharacterPlacement:
    slot_id: str
    entrant_slot: int
    anchor: PixelPoint
    member_slot: int | None = None
    scale: float = 1.0
    z_index: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.slot_id, str) or not self.slot_id.strip():
            raise ValueError("character slot_id must be a non-empty string")
        _integer(self.entrant_slot, "entrant_slot")
        if self.entrant_slot <= 0:
            raise ValueError("entrant_slot is one-based and must be greater than 0")
        if self.member_slot is not None:
            _integer(self.member_slot, "member_slot")
            if self.member_slot <= 0:
                raise ValueError("member_slot is one-based and must be greater than 0")
        if not isinstance(self.anchor, PixelPoint):
            raise TypeError("character anchor must be a PixelPoint")
        if isinstance(self.scale, bool) or not isinstance(self.scale, (int, float)):
            raise TypeError("character scale must be a number")
        if self.scale <= 0:
            raise ValueError("character scale must be greater than 0")
        _integer(self.z_index, "z_index")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> CharacterPlacement:
        anchor = _mapping(value.get("anchor"), "anchor")
        member_slot = value.get("member_slot")
        if member_slot is not None:
            member_slot = _integer(member_slot, "member_slot")
        scale = value.get("scale", 1.0)
        if isinstance(scale, bool) or not isinstance(scale, (int, float)):
            raise TypeError("character scale must be a number")
        return cls(
            slot_id=value.get("slot_id") if isinstance(value.get("slot_id"), str) else "",
            entrant_slot=_integer(value.get("entrant_slot"), "entrant_slot"),
            member_slot=member_slot,
            anchor=PixelPoint.from_dict(anchor),
            scale=float(scale),
            z_index=_integer(value.get("z_index", 0), "z_index"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "entrant_slot": self.entrant_slot,
            "member_slot": self.member_slot,
            "anchor": self.anchor.to_dict(),
            "scale": self.scale,
            "z_index": self.z_index,
        }


@dataclass(frozen=True, slots=True)
class TextPlacement:
    slot_id: str
    field: str
    anchor: PixelPoint
    max_width: int
    entrant_slot: int | None = None
    member_slot: int | None = None
    z_index: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.slot_id, str) or not self.slot_id.strip():
            raise ValueError("text slot_id must be a non-empty string")
        if not isinstance(self.field, str) or not self.field.strip():
            raise ValueError("text field must be a non-empty string")
        if not isinstance(self.anchor, PixelPoint):
            raise TypeError("text anchor must be a PixelPoint")
        _integer(self.max_width, "max_width")
        if self.max_width <= 0:
            raise ValueError("max_width must be greater than 0")
        for name in ("entrant_slot", "member_slot"):
            value = getattr(self, name)
            if value is not None:
                _integer(value, name)
                if value <= 0:
                    raise ValueError(f"{name} is one-based and must be greater than 0")
        _integer(self.z_index, "z_index")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> TextPlacement:
        anchor = _mapping(value.get("anchor"), "anchor")
        entrant_slot = value.get("entrant_slot")
        member_slot = value.get("member_slot")
        if entrant_slot is not None:
            entrant_slot = _integer(entrant_slot, "entrant_slot")
        if member_slot is not None:
            member_slot = _integer(member_slot, "member_slot")
        return cls(
            slot_id=value.get("slot_id") if isinstance(value.get("slot_id"), str) else "",
            field=value.get("field") if isinstance(value.get("field"), str) else "",
            anchor=PixelPoint.from_dict(anchor),
            max_width=_integer(value.get("max_width"), "max_width"),
            entrant_slot=entrant_slot,
            member_slot=member_slot,
            z_index=_integer(value.get("z_index", 0), "z_index"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "field": self.field,
            "entrant_slot": self.entrant_slot,
            "member_slot": self.member_slot,
            "anchor": self.anchor.to_dict(),
            "max_width": self.max_width,
            "z_index": self.z_index,
        }


@dataclass(frozen=True, slots=True)
class ModePreferences:
    """All layout positions owned by one mode/sub-mode combination."""

    selection: ModeSelection
    canvas_size: PixelSize
    ready: bool = False
    formatting_assets: tuple[FormattingAssetPlacement, ...] = ()
    character_slots: tuple[CharacterPlacement, ...] = ()
    text_slots: tuple[TextPlacement, ...] = ()
    schema_version: int = PREFERENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PREFERENCE_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported preference schema version: {self.schema_version}"
            )
        if not isinstance(self.selection, ModeSelection):
            raise TypeError("selection must be a ModeSelection")
        if not isinstance(self.canvas_size, PixelSize):
            raise TypeError("canvas_size must be a PixelSize")
        if not isinstance(self.ready, bool):
            raise TypeError("ready must be a boolean")
        placement_fields = (
            ("formatting_assets", FormattingAssetPlacement),
            ("character_slots", CharacterPlacement),
            ("text_slots", TextPlacement),
        )
        for field_name, expected_type in placement_fields:
            placements = tuple(getattr(self, field_name))
            if any(not isinstance(item, expected_type) for item in placements):
                raise TypeError(
                    f"{field_name} must contain only {expected_type.__name__} values"
                )
            object.__setattr__(self, field_name, placements)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ModePreferences:
        version = _integer(value.get("schema_version"), "schema_version")
        ready = value.get("ready")
        if not isinstance(ready, bool):
            raise TypeError("ready must be a boolean")
        selection = _mapping(value.get("selection"), "selection")
        canvas_size = _mapping(value.get("canvas_size"), "canvas_size")
        return cls(
            selection=ModeSelection.from_dict(selection),
            canvas_size=PixelSize.from_dict(canvas_size),
            ready=ready,
            formatting_assets=tuple(
                FormattingAssetPlacement.from_dict(item)
                for item in _items(value.get("formatting_assets"), "formatting_assets")
            ),
            character_slots=tuple(
                CharacterPlacement.from_dict(item)
                for item in _items(value.get("character_slots"), "character_slots")
            ),
            text_slots=tuple(
                TextPlacement.from_dict(item)
                for item in _items(value.get("text_slots"), "text_slots")
            ),
            schema_version=version,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "ready": self.ready,
            "selection": self.selection.to_dict(),
            "canvas_size": self.canvas_size.to_dict(),
            "formatting_assets": [item.to_dict() for item in self.formatting_assets],
            "character_slots": [item.to_dict() for item in self.character_slots],
            "text_slots": [item.to_dict() for item in self.text_slots],
        }


@dataclass(frozen=True, slots=True)
class ModePreferenceRepository:
    root: Path = MODE_PREFERENCES_FOLDER

    def path_for(self, selection: ModeSelection) -> Path:
        folder = self.root / selection.mode.value
        if selection.mode is CreationMode.PODIUM:
            assert selection.options.podium_style is not None
            folder /= selection.options.podium_style.value
        return folder / f"{selection.submode_id}.json"

    def load(self, selection: ModeSelection) -> ModePreferences:
        path = self.path_for(selection)
        if not path.is_file():
            raise FileNotFoundError(
                "No preferences exist for "
                f"{selection.mode.value}/{selection.submode_id}"
            )
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid preference JSON: {path}") from error
        preferences = ModePreferences.from_dict(_mapping(raw, "preference file"))
        if preferences.selection != selection:
            raise ValueError(f"Preference selection does not match its path: {path}")
        return preferences

    def list_preferences(
        self, mode: CreationMode | None = None
    ) -> tuple[ModePreferences, ...]:
        modes = (mode,) if mode is not None else tuple(CreationMode)
        preferences: list[ModePreferences] = []
        for current_mode in modes:
            folder = self.root / current_mode.value
            for path in sorted(folder.rglob("*.json")):
                raw = json.loads(path.read_text(encoding="utf-8"))
                preference = ModePreferences.from_dict(_mapping(raw, "preference file"))
                if preference.selection.mode is not current_mode:
                    raise ValueError(f"Preference mode does not match its folder: {path}")
                if path != self.path_for(preference.selection):
                    raise ValueError(f"Preference selection does not match its path: {path}")
                preferences.append(preference)
        return tuple(preferences)


class ModePreferencesProvider(Protocol):
    """Preference source boundary used by the creation coordinator."""

    def load(self, selection: ModeSelection) -> ModePreferences:
        """Load the exact preference set identified by ``selection``."""

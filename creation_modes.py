"""Serializable selection of a creation mode and its mode-specific options."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
from typing import Any, Mapping

from models import TournamentFormat


_VARIANT_ID = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


class CreationMode(StrEnum):
    PODIUM = "podium"
    EYES = "eyes"
    SQUARES = "squares"


@dataclass(frozen=True, slots=True)
class ModeOptions:
    """Options that identify one preference set inside a creation mode."""

    event_format: TournamentFormat
    entrant_count: int
    variant: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.event_format, TournamentFormat):
            raise TypeError("event_format must be a TournamentFormat")
        if self.event_format is TournamentFormat.UNKNOWN:
            raise ValueError("event_format must be singles or doubles")
        if isinstance(self.entrant_count, bool) or not isinstance(
            self.entrant_count, int
        ):
            raise TypeError("entrant_count must be an integer")
        if self.entrant_count <= 0:
            raise ValueError("entrant_count must be greater than 0")
        if self.variant is not None:
            if not isinstance(self.variant, str) or _VARIANT_ID.fullmatch(
                self.variant
            ) is None:
                raise ValueError(
                    "variant must contain lowercase letters, numbers, and underscores"
                )

    @property
    def submode_id(self) -> str:
        suffix = f"_{self.variant}" if self.variant is not None else ""
        return f"{self.event_format.value}_top_{self.entrant_count}{suffix}"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ModeOptions:
        raw_format = value.get("event_format")
        raw_count = value.get("entrant_count")
        raw_variant = value.get("variant")
        try:
            event_format = TournamentFormat(raw_format)
        except (TypeError, ValueError) as error:
            raise ValueError("event_format must be singles or doubles") from error
        if isinstance(raw_count, bool) or not isinstance(raw_count, int):
            raise TypeError("entrant_count must be an integer")
        if raw_variant is not None and not isinstance(raw_variant, str):
            raise TypeError("variant must be a string or null")
        return cls(event_format, raw_count, raw_variant)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_format": self.event_format.value,
            "entrant_count": self.entrant_count,
            "variant": self.variant,
        }


@dataclass(frozen=True, slots=True)
class ModeSelection:
    """The first choice in creation: a mode together with its sub-mode options."""

    mode: CreationMode
    options: ModeOptions

    def __post_init__(self) -> None:
        if not isinstance(self.mode, CreationMode):
            raise TypeError("mode must be a CreationMode")
        if not isinstance(self.options, ModeOptions):
            raise TypeError("options must be ModeOptions")

    @property
    def submode_id(self) -> str:
        return self.options.submode_id

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ModeSelection:
        raw_mode = value.get("mode")
        raw_options = value.get("options")
        try:
            mode = CreationMode(raw_mode)
        except (TypeError, ValueError) as error:
            choices = ", ".join(item.value for item in CreationMode)
            raise ValueError(f"mode must be one of: {choices}") from error
        if not isinstance(raw_options, Mapping):
            raise TypeError("options must be an object")
        return cls(mode, ModeOptions.from_dict(raw_options))

    def to_dict(self) -> dict[str, Any]:
        return {"mode": self.mode.value, "options": self.options.to_dict()}

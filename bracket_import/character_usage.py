"""Provider-neutral selection of reported character histories."""

from typing import TypeVar


Character = TypeVar("Character")


def select_import_characters(
    played: tuple[Character, ...], won: tuple[Character, ...], *, import_all_characters: bool
) -> tuple[Character, ...]:
    """Prefer winning selections, retaining played characters for winless players."""
    return played if import_all_characters or not won else won

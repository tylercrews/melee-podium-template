"""Request-local entrant omissions preserve the layout's original slot geometry."""

from dataclasses import replace
import re


def slot_from_id(slot_id):
    match = re.search(r"(?:podium|entrant|slice|number)_(\d+)", slot_id)
    return int(match[1]) if match else None


def visibility_flags(value):
    flags = {key: value.get(key, False) for key in ("omit_entrant", "omit_placement")}
    if any(not isinstance(flag, bool) for flag in flags.values()):
        raise ValueError("Entrant omission settings must be booleans")
    return flags


def apply_visibility(entrants, settings):
    if settings is None:
        return entrants
    if not isinstance(settings, list) or len(settings) > len(entrants) or any(not isinstance(row, dict) for row in settings):
        raise ValueError("entrant_visibility must contain one settings object per included slot")
    flags = [visibility_flags(row) for row in settings]
    return [replace(entrant, **flags[index]) if index < len(flags) else entrant
            for index, entrant in enumerate(entrants)]


def visible_placement_tags(tags, entrants):
    hidden = {index for index, entrant in enumerate(entrants, 1) if entrant.omit_entrant or entrant.omit_placement}
    return tuple(tag for tag in tags if slot_from_id(tag.slot_id) not in hidden)


def visible_preferences(preferences, entrants):
    hidden = {index for index, entrant in enumerate(entrants, 1) if entrant.omit_entrant}
    portrait_slots = {row.slot_id: row.entrant_slot for row in preferences.character_slots}
    return replace(preferences,
        omitted_entrant_slots=tuple(sorted(hidden)),
        full_formatting_assets=preferences.full_formatting_assets or preferences.formatting_assets,
        formatting_assets=tuple(row for row in preferences.formatting_assets
                                if portrait_slots.get(row.slot_id, slot_from_id(row.slot_id)) not in hidden),
        placement_tags=visible_placement_tags(preferences.placement_tags, entrants),
        character_slots=tuple(row for row in preferences.character_slots if row.entrant_slot not in hidden),
        text_slots=tuple(row for row in preferences.text_slots if row.entrant_slot not in hidden
                         and not (row.field == "entrant.placement" and row.entrant_slot is not None
                                  and entrants[row.entrant_slot - 1].omit_placement)))


def validation_entrants(entrants):
    """Empty slots do not prevent validation of the remaining placement order."""
    sequences = [list(range(1, len(entrants) + 1))]
    if len(entrants) == 8:
        sequences.append([1, 2, 3, 4, 5, 5, 7, 7])
    for sequence in sequences:
        if all(entrant.omit_entrant or entrant.placement == rank for entrant, rank in zip(entrants, sequence)):
            return tuple(replace(entrant, placement=rank) if entrant.omit_entrant else entrant
                         for entrant, rank in zip(entrants, sequence))
    return entrants

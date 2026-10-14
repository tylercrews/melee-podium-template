"""Rank-based player colors for Singles Top 16's podium and clapping rows."""

from creation_modes import CreationMode
from podium_colors import PodiumColorConfiguration, PodiumColorMode, PodiumColorPreset


# Four leading colors, then one color per tied tournament placement group.
TOP16_PLAYER_COLOR_SLOTS = (1, 2, 3, 4, 5, 5, 6, 6, 7, 7, 7, 7, 8, 8, 8, 8)


def top16_player_colors(source):
    """Retain all palette channels and finishes while grouping tied ranks."""
    return PodiumColorConfiguration.per_podium(
        *(source.color_for_slot(slot) for slot in TOP16_PLAYER_COLOR_SLOTS)
    )


def resolve_clapping_podium_colors(selection, colors):
    """Expand the default player preset; explicit colors and other presets stay editable."""
    if (selection.mode is CreationMode.PODIUM and selection.submode_id == "singles_top_16_clapping"
            and isinstance(colors, PodiumColorConfiguration)
            and colors.mode is PodiumColorMode.PRESET and colors.preset is PodiumColorPreset.LEGACY):
        return top16_player_colors(colors)
    return colors


def legacy_top16_text_slot(entrant_slot):
    """Keep the eight fixed podium colors, then reverse them across the lower row."""
    return entrant_slot if entrant_slot <= 8 else 17 - entrant_slot

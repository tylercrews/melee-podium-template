"""Transparent numbering layers shared by every cached palette preview."""

from dataclasses import replace
import json
from pathlib import Path

from PIL import Image

from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from format_preview import SUPPORTED_LAYOUTS, SUPPORTED_EYES_LAYOUTS, SUPPORTED_SQUARE_LAYOUTS
from formatting_assets import draw_placement_tags
from mode_preferences import ModePreferenceRepository, PlacementTagPlacement
from models import TournamentFormat
from placement_numbering import numbered_preferences
from clapping_grid_layouts import GRID_VARIANTS
from clapping_grid_renderer import grid_profile


def preview_selections():
    for style in PodiumStyle:
        for event_format, count, variant in sorted(SUPPORTED_LAYOUTS, key=str):
            if variant in GRID_VARIANTS and style is PodiumStyle.LEGACY:
                continue
            yield ModeSelection(CreationMode.PODIUM, ModeOptions(event_format, count, variant, style))
    for mode, layouts in ((CreationMode.EYES, SUPPORTED_EYES_LAYOUTS), (CreationMode.SQUARES, SUPPORTED_SQUARE_LAYOUTS),
                          (CreationMode.RADIAL, ((TournamentFormat.SINGLES, 8, None), (TournamentFormat.DOUBLES, 4, None))),
                          (CreationMode.FLYING_V, ((TournamentFormat.SINGLES, 8, None), (TournamentFormat.DOUBLES, 3, None)))):
        for event_format, count, variant in sorted(layouts, key=str):
            yield ModeSelection(mode, ModeOptions(event_format, count, variant))


def render_placement_number_layer(selection, use_tournament_placing):
    preferences = ModePreferenceRepository().load(selection)
    if selection.mode is CreationMode.PODIUM and selection.options.variant in {"clapping", "four_podium", *GRID_VARIANTS}:
        from podiums_clapping_renderer import PROFILE as TOP8_PROFILE
        from extended_clapping_renderer import PROFILE
        profile = (grid_profile(selection) if selection.options.variant in GRID_VARIANTS else json.loads(TOP8_PROFILE.read_text(encoding="utf-8"))["styles"][selection.options.podium_style.value]
                   if selection.submode_id == "singles_top_8_four_podium"
                   else json.loads(PROFILE.read_text(encoding="utf-8"))["layouts"][selection.submode_id][selection.options.podium_style.value])
        lower = tuple(PlacementTagPlacement.from_dict(row) for row in profile["placement_tags"])
        preferences = replace(preferences, placement_tags=preferences.placement_tags + lower)
    if selection.mode is CreationMode.FLYING_V:
        # Match the placeholder figures and the exact render's outlined art.
        from flying_v_content_renderer import draw_outlined_placement_tags
        from flying_v_preview_layers import placeholder_preview
        preferences = numbered_preferences(placeholder_preview(preferences)[1], use_tournament_placing)
        layer = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
        draw_outlined_placement_tags(layer, preferences)
        return layer
    preferences = numbered_preferences(preferences, use_tournament_placing)
    layer = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
    draw_placement_tags(layer, preferences)
    return layer


def generate_placement_number_layers(root: Path, *, grid_only: bool = False):
    outputs = []
    for selection in preview_selections():
        if grid_only and selection.options.variant not in GRID_VARIANTS:
            continue
        folder = root / "placement_numbers" / selection.mode.value
        if selection.options.podium_style is not None:
            folder /= selection.options.podium_style.value
        for tournament in (True, False):
            path = folder / selection.submode_id / ("tournament.png" if tournament else "sequential.png")
            path.parent.mkdir(parents=True, exist_ok=True)
            render_placement_number_layer(selection, tournament).save(path, optimize=True)
            outputs.append(path)
    return outputs


def generate_numbering_preview_assets(root: Path):
    """Refresh formatting-only layers and add both numbering choices without rebuilding headers."""
    from preview_layers import LAYOUTS, EYE_LAYOUTS, SQUARE_LAYOUTS, COLOR_LAYER_IDS, render_podium_layer, render_eye_layer, render_square_layer
    from clapping_preview_layers import generate_extended_clapping_layers
    outputs = []
    for layout in LAYOUTS:
        for style in PodiumStyle:
            for color in ((None,) if style is PodiumStyle.LEGACY else ("smash_player_colors", "olympic_medals", "rainbow", "custom_red")):
                path = root / "podiums" / style.value / (f"{layout}.png" if color is None else f"{layout}/{color}.png")
                path.parent.mkdir(parents=True, exist_ok=True)
                render_podium_layer(style, layout, color).save(path, optimize=True)
                outputs.append(path)
    outputs.extend(generate_extended_clapping_layers(root, include_top8=False))
    for folder, layouts, renderer in (("eyes", EYE_LAYOUTS, render_eye_layer), ("squares", SQUARE_LAYOUTS, render_square_layer)):
        for layout in layouts:
            for color in COLOR_LAYER_IDS:
                path = root / folder / layout / f"{color}.png"
                path.parent.mkdir(parents=True, exist_ok=True)
                renderer(layout, color).save(path, optimize=True)
                outputs.append(path)
    outputs.extend(generate_placement_number_layers(root))
    return outputs

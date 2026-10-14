"""Combined transparent formatting layers for the extended clapping layouts."""

from dataclasses import replace
import json
from pathlib import Path

from PIL import Image, ImageDraw

from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from clapping_colors import top16_player_colors, legacy_top16_text_slot
from extended_clapping_renderer import PROFILE
from podiums_clapping_renderer import PROFILE as TOP8_PROFILE
from formatting_assets import FormattingAssetRenderer, draw_placement_tags
from mode_preferences import ModePreferenceRepository, PlacementTagPlacement
from models import TournamentFormat
from preview_layers import _customizable_colors, _repeat_colors
from podium_colors import PodiumColorConfiguration, PodiumColorPreset


EXTENDED_CLAPPING_LAYOUTS = {
    "doubles_top_8_four_podium": (TournamentFormat.DOUBLES, 8, "four_podium"),
    "singles_top_16_clapping": (TournamentFormat.SINGLES, 16, "clapping"),
}
CLAPPING_LAYOUTS = {
    "singles_top_8_four_podium": (TournamentFormat.SINGLES, 8, "four_podium"),
    **EXTENDED_CLAPPING_LAYOUTS,
}


def render_extended_clapping_layer(style, layout_id, color_id=None):
    event_format, count, variant = CLAPPING_LAYOUTS[layout_id]
    selection = ModeSelection(CreationMode.PODIUM, ModeOptions(event_format, count, variant, style))
    preferences = ModePreferenceRepository().load(selection)
    canvas = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
    colors = _customizable_colors(color_id or "smash_player_colors", 8) if style is PodiumStyle.CUSTOMIZABLE else None
    if colors is not None and variant == "four_podium" and color_id == "rainbow":
        four_colors = _customizable_colors("rainbow", 4)
        colors = _repeat_colors(tuple(four_colors.color_for_slot(slot) for slot in range(1, 5)), 8)
    top16 = layout_id == "singles_top_16_clapping"
    if top16 and style is PodiumStyle.CUSTOMIZABLE and color_id in {None, "smash_player_colors"}:
        colors = top16_player_colors(colors)
    result = FormattingAssetRenderer().draw(canvas, replace(preferences, placement_tags=()), colors)
    profile = (json.loads(TOP8_PROFILE.read_text(encoding="utf-8"))["styles"][style.value]
               if layout_id == "singles_top_8_four_podium"
               else json.loads(PROFILE.read_text(encoding="utf-8"))["layouts"][layout_id][style.value])
    draw = ImageDraw.Draw(result)
    for panel in profile["panels"]:
        slot = panel["entrant_slot"]
        if top16 and style is PodiumStyle.LEGACY:
            slot = legacy_top16_text_slot(slot)
        elif not (top16 and colors is not None and len(colors.colors) == 16):
            slot = (slot - 1) % 8 + 1
        palette = colors or PodiumColorConfiguration.from_preset(PodiumColorPreset.LEGACY)
        text_color = palette.color_for_slot(slot).resolve().text_color
        left, top, right, bottom = panel["portrait_rect"]
        draw.rectangle((left, top, right - 1, bottom - 1), fill=f"{text_color[:7]}40", outline=text_color, width=2)
        x = panel["text_x"]
        size = min(110, panel["text_max_width"])
        start = x - size if panel["text_alignment"] == "right" else x
        for offset, inset in ((20, 12), (48, 24), (76, 0)):
            y = top + round(offset * panel.get("identity_scale", 1))
            draw.line((start + inset, y, start + size, y), fill=text_color, width=5)
    for row in profile.get("team_names", []):
        x, y = row["anchor"]["x"], row["anchor"]["y"]
        draw.line((x - 80, y + 20, x + 80, y + 20), fill="#D8DCE8CC", width=7)
    return result


def generate_extended_clapping_layers(output_root: Path, *, include_top8: bool = True):
    paths = []
    for layout_id in (CLAPPING_LAYOUTS if include_top8 else EXTENDED_CLAPPING_LAYOUTS):
        asset_layout_id = "top_8_four_podiums" if layout_id == "singles_top_8_four_podium" else layout_id
        for style in PodiumStyle:
            for color_id in ((None,) if style is PodiumStyle.LEGACY else ("smash_player_colors", "olympic_medals", "rainbow", "custom_red")):
                path = output_root / "podiums" / style.value / (
                    f"{asset_layout_id}.png" if color_id is None else f"{asset_layout_id}/{color_id}.png")
                path.parent.mkdir(parents=True, exist_ok=True)
                render_extended_clapping_layer(style, layout_id, color_id).save(path, optimize=True)
                paths.append(path)
    return paths

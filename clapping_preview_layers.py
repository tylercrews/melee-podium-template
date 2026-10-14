"""Combined transparent formatting layers for the extended clapping layouts."""

from dataclasses import replace
import json
from pathlib import Path

from PIL import Image, ImageDraw

from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from extended_clapping_renderer import PROFILE
from formatting_assets import FormattingAssetRenderer, draw_placement_tags
from mode_preferences import ModePreferenceRepository, PlacementTagPlacement
from models import TournamentFormat
from preview_layers import _customizable_colors


EXTENDED_CLAPPING_LAYOUTS = {
    "doubles_top_8_four_podium": (TournamentFormat.DOUBLES, 8, "four_podium"),
    "singles_top_16_clapping": (TournamentFormat.SINGLES, 16, "clapping"),
}


def render_extended_clapping_layer(style, layout_id, color_id=None):
    event_format, count, variant = EXTENDED_CLAPPING_LAYOUTS[layout_id]
    selection = ModeSelection(CreationMode.PODIUM, ModeOptions(event_format, count, variant, style))
    preferences = ModePreferenceRepository().load(selection)
    canvas = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
    colors = _customizable_colors(color_id or "smash_player_colors", 8) if style is PodiumStyle.CUSTOMIZABLE else None
    result = FormattingAssetRenderer().draw(canvas, preferences, colors)
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))["layouts"][layout_id][style.value]
    draw = ImageDraw.Draw(result)
    for panel in profile["panels"]:
        left, top, right, bottom = panel["portrait_rect"]
        draw.rectangle((left, top, right - 1, bottom - 1), fill="#8E95AF40", outline="#D8DCE8CC", width=2)
        x = panel["text_x"]
        size = min(110, panel["text_max_width"])
        start = x - size if panel["text_alignment"] == "right" else x
        for offset, inset in ((20, 12), (48, 24), (76, 0)):
            y = top + round(offset * panel.get("identity_scale", 1))
            draw.line((start + inset, y, start + size, y), fill="#D8DCE8CC", width=5)
    for row in profile.get("team_names", []):
        x, y = row["anchor"]["x"], row["anchor"]["y"]
        draw.line((x - 80, y + 20, x + 80, y + 20), fill="#D8DCE8CC", width=7)
    badges = tuple(PlacementTagPlacement.from_dict(row) for row in profile["placement_tags"])
    draw_placement_tags(result, replace(preferences, placement_tags=badges))
    return result


def generate_extended_clapping_layers(output_root: Path):
    paths = []
    for layout_id in EXTENDED_CLAPPING_LAYOUTS:
        for style in PodiumStyle:
            for color_id in ((None,) if style is PodiumStyle.LEGACY else ("smash_player_colors", "olympic_medals", "rainbow", "custom_red")):
                path = output_root / "podiums" / style.value / (
                    f"{layout_id}.png" if color_id is None else f"{layout_id}/{color_id}.png")
                path.parent.mkdir(parents=True, exist_ok=True)
                render_extended_clapping_layer(style, layout_id, color_id).save(path, optimize=True)
                paths.append(path)
    return paths

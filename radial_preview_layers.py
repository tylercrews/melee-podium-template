"""Generate the Radial browser layers without embedding an overlapping logo."""

from itertools import permutations
from pathlib import Path

from PIL import Image

from background_builder import BackgroundRequest
from creation import CreationRequest, TextSettings
from DrawPodium import PodiumFont
from formatting_assets import FormattingAssetRenderer, draw_placement_tags
from geometric_formatting_colors import GeometricFormattingColor, GeometricFormattingColors
from mode_preferences import ModePreferenceRepository
from creation_modes import CreationMode, ModeOptions, ModeSelection
from models import TournamentFormat
from preview_layers import COLOR_LAYER_IDS, HEADER_CONTENTS, HEADER_POSITIONS, _boxed_logo_placeholder, _customizable_colors, header_permutation_id
from radial_content_renderer import RadialContentRenderer, radial_header_boxes
from radial_geometry import draw_radial_dividers
from radial_palette import radial_palette_color
from sample_creation_data import sample_top_8_entrants, sample_top_4_teams, sample_tournament


def _generate_radial_layout_layers(output_root: Path, event_format: TournamentFormat, count: int) -> list[Path]:
    selection = ModeSelection(CreationMode.RADIAL, ModeOptions(event_format, count))
    preferences = ModePreferenceRepository().load(selection)
    doubles = event_format is TournamentFormat.DOUBLES
    entrants = sample_top_4_teams() if doubles else sample_top_8_entrants()
    outputs = []

    def save(layer, relative):
        path = output_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        layer.save(path, format="PNG", optimize=True)
        outputs.append(path)

    for color_id in COLOR_LAYER_IDS:
        palettes = _customizable_colors(color_id, count)
        colors = GeometricFormattingColors(tuple(radial_palette_color(palettes.color_for_slot(slot)) for slot in range(1, count + 1)))
        layer = FormattingAssetRenderer().draw(Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000"), preferences, colors)
        draw_radial_dividers(layer, preferences, colors)
        save(layer, f"radial/{selection.submode_id}/{color_id}.png")

    labels = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
    draw_placement_tags(labels, preferences)
    save(labels, "radial_labels_doubles.png" if doubles else "radial_labels.png")

    if not doubles:
        for position, box in radial_header_boxes(preferences).items():
            layer = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
            _boxed_logo_placeholder(layer, box.as_tuple())
            save(layer, f"radial_logos/{position}.png")

    for font in PodiumFont:
        for contents in permutations(HEADER_CONTENTS):
            layout = dict(zip(HEADER_POSITIONS, contents, strict=True))
            layer = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
            request = CreationRequest(selection, BackgroundRequest(preferences.canvas_size), entrants, sample_tournament(event_format), formatting_colors=GeometricFormattingColors.one("#00000000"), header_layout=layout, text_settings=TextSettings())
            RadialContentRenderer(font=font)._draw_header(layer, request, preferences)
            save(layer, f"radial_headers/{font.value}/{'doubles/' if doubles else ''}{header_permutation_id(layout)}.png")
    return outputs


def generate_radial_preview_layers(output_root: Path) -> list[Path]:
    """Generate both reviewed Radial layouts with their own sample headers."""
    return (
        _generate_radial_layout_layers(output_root, TournamentFormat.SINGLES, 8)
        + _generate_radial_layout_layers(output_root, TournamentFormat.DOUBLES, 4)
    )

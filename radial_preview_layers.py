"""Generate the Radial browser layers without embedding an overlapping logo."""

from itertools import permutations
from pathlib import Path

from PIL import Image, ImageDraw

from background_builder import BackgroundRequest
from creation import CreationRequest, TextSettings
from DrawPodium import PodiumFont, _draw_text
from formatting_assets import FormattingAssetRenderer
from geometric_formatting_colors import GeometricFormattingColor, GeometricFormattingColors
from mode_preferences import ModePreferenceRepository
from creation_modes import CreationMode, ModeOptions, ModeSelection
from models import TournamentFormat
from preview_layers import COLOR_LAYER_IDS, HEADER_CONTENTS, HEADER_POSITIONS, _boxed_logo_placeholder, _customizable_colors, header_permutation_id
from radial_content_renderer import RadialContentRenderer, radial_header_boxes
from sample_creation_data import sample_top_8_entrants, sample_tournament


def generate_radial_preview_layers(output_root: Path) -> list[Path]:
    selection = ModeSelection(CreationMode.RADIAL, ModeOptions(TournamentFormat.SINGLES, 8))
    preferences = ModePreferenceRepository().load(selection)
    entrants = sample_top_8_entrants()
    outputs = []

    def save(layer, relative):
        path = output_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        layer.save(path, format="PNG", optimize=True)
        outputs.append(path)

    for color_id in COLOR_LAYER_IDS:
        palettes = _customizable_colors(color_id, 8)
        colors = GeometricFormattingColors(tuple(GeometricFormattingColor(palettes.color_for_slot(slot).main_color) for slot in range(1, 9)))
        layer = FormattingAssetRenderer().draw(Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000"), preferences, colors)
        save(layer, f"radial/singles_top_8/{color_id}.png")

    labels = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
    for text in preferences.text_slots:
        if text.field == "entrant.placement":
            rank = (1, 2, 3, 4, 5, 5, 7, 7)[text.entrant_slot - 1]
            _draw_text(ImageDraw.Draw(labels), (text.anchor.x, text.anchor.y), f"#{rank}", anchor=text.pillow_anchor, max_width=text.max_width, preferred_size=text.preferred_size, font=PodiumFont.UBUNTU, fill="#FFFFFFFF")
    save(labels, "radial_labels.png")

    for position, box in radial_header_boxes(preferences).items():
        layer = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
        _boxed_logo_placeholder(layer, box.as_tuple())
        save(layer, f"radial_logos/{position}.png")

    for font in PodiumFont:
        for contents in permutations(HEADER_CONTENTS):
            layout = dict(zip(HEADER_POSITIONS, contents, strict=True))
            layer = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
            request = CreationRequest(selection, BackgroundRequest(preferences.canvas_size), entrants, sample_tournament(TournamentFormat.SINGLES), formatting_colors=GeometricFormattingColors.one("#00000000"), header_layout=layout, text_settings=TextSettings())
            RadialContentRenderer(font=font)._draw_header(layer, request, preferences)
            save(layer, f"radial_headers/{font.value}/{header_permutation_id(layout)}.png")
    return outputs

"""Generate the cached Flying V figure placeholders and header layers."""

from __future__ import annotations

from itertools import permutations
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from background_builder import BackgroundRequest
from creation import CreationRequest, TextSettings
from creation_modes import CreationMode, ModeOptions, ModeSelection
from DrawPodium import PodiumFont
from flying_v_content_renderer import (
    FlyingVContentRenderer,
    flying_v_header_boxes,
    labelled_preferences,
    place_figures,
)
from formatting_assets import _composite_clipped
from mode_preferences import ModePreferenceRepository, ModePreferences
from models import Character, DoublesTeam, Entrant, SinglesEntrant, TournamentFormat
from preview_layers import HEADER_CONTENTS, HEADER_POSITIONS, _boxed_logo_placeholder, header_permutation_id
from sample_creation_data import sample_tournament


FLYING_V_LAYOUTS = {
    "singles_top_8": (TournamentFormat.SINGLES, 8),
    "doubles_top_3": (TournamentFormat.DOUBLES, 3),
}
# A median-height pose shows every tier at its typical size without implying
# which characters the user's entrants will play.
PLACEHOLDER_CHARACTER = Character("Fox", color="default", pose="a")
PLACEHOLDER_FILL = (142, 149, 175, 140)
PLACEHOLDER_OUTLINE = (46, 50, 64, 200)
GUIDE_FILL = "#8E95AFE6"


def flying_v_selection(layout_id: str) -> ModeSelection:
    event_format, count = FLYING_V_LAYOUTS[layout_id]
    return ModeSelection(CreationMode.FLYING_V, ModeOptions(event_format, count))


def _placeholder_entrants(event_format: TournamentFormat, count: int) -> list[SinglesEntrant] | list[DoublesTeam]:
    if event_format is TournamentFormat.SINGLES:
        return [SinglesEntrant(tag=f"Player {slot}", characters=[PLACEHOLDER_CHARACTER], seed=slot, placement=slot)
                for slot in range(1, count + 1)]
    member = Entrant(tag="Player", characters=[PLACEHOLDER_CHARACTER])
    return [DoublesTeam(seed=slot, placement=slot, entrant_1=member, entrant_2=member, team_name=f"Team {slot}")
            for slot in range(1, count + 1)]


def placeholder_preview(preferences: ModePreferences):
    """Place mannequin figures and return them with the labels that follow them."""
    options = preferences.selection.options
    request = CreationRequest(
        preferences.selection, BackgroundRequest(preferences.canvas_size),
        _placeholder_entrants(options.event_format, options.entrant_count),
        sample_tournament(options.event_format),
    )
    figures = place_figures(request, preferences)
    return figures, labelled_preferences(preferences, figures)


def render_placeholder_layer(layout_id: str) -> Image.Image:
    """Draw translucent figures plus guide bars where each name will appear."""
    preferences = ModePreferenceRepository().load(flying_v_selection(layout_id))
    figures, labelled = placeholder_preview(preferences)
    layer = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
    for figure in sorted(figures.values(), key=lambda item: (item.z_index, item.slot_id)):
        alpha = figure.lineup.image.getchannel("A")
        outline = alpha.filter(ImageFilter.MaxFilter(7))
        silhouette = Image.new("RGBA", alpha.size, PLACEHOLDER_OUTLINE)
        silhouette.putalpha(ImageChops.multiply(outline, Image.new("L", alpha.size, PLACEHOLDER_OUTLINE[3])))
        fill = Image.new("RGBA", alpha.size, PLACEHOLDER_FILL)
        fill.putalpha(ImageChops.multiply(alpha, Image.new("L", alpha.size, PLACEHOLDER_FILL[3])))
        silhouette.alpha_composite(fill)
        _composite_clipped(layer, silhouette, figure.lineup.bounds.as_tuple())
    draw = ImageDraw.Draw(layer)
    for placement in labelled.text_slots:
        if placement.field in {"entrant.seed", "entrant.sponsor"}:
            continue
        size = placement.preferred_size or 40
        width = min(placement.max_width, size * 5)
        # Above-head identities sit on their baseline; result names hang from their top.
        top = placement.anchor.y - size * 3 // 4 if placement.pillow_anchor.endswith("s") else placement.anchor.y + size // 8
        draw.rounded_rectangle((placement.anchor.x - width // 2, top, placement.anchor.x + width // 2, top + size // 2),
                               radius=size // 4, fill=GUIDE_FILL)
    return layer


def render_flying_v_header_layer(font: PodiumFont, event_format: TournamentFormat, header_layout: dict[str, str]) -> Image.Image:
    layout_id = next(key for key, (layout_format, _count) in FLYING_V_LAYOUTS.items() if layout_format is event_format)
    selection = flying_v_selection(layout_id)
    preferences = ModePreferenceRepository().load(selection)
    canvas = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
    request = CreationRequest(
        selection, BackgroundRequest(preferences.canvas_size),
        _placeholder_entrants(event_format, selection.options.entrant_count), sample_tournament(event_format),
        header_layout=header_layout, text_settings=TextSettings(),
    )
    FlyingVContentRenderer(font=font)._draw_header(canvas, request, preferences)
    logo_position = next(position for position, content in header_layout.items() if content == "tournament_logo")
    _boxed_logo_placeholder(canvas, flying_v_header_boxes(preferences)[logo_position].as_tuple())
    return canvas


def generate_flying_v_preview_layers(output_root: Path) -> list[Path]:
    """Generate figure placeholders and all font/header permutations for both layouts."""
    outputs = []

    def save(image: Image.Image, relative: str) -> None:
        path = output_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, format="PNG", optimize=True)
        outputs.append(path)

    for layout_id, (event_format, _count) in FLYING_V_LAYOUTS.items():
        save(render_placeholder_layer(layout_id), f"flying_v/{layout_id}/placeholders.png")
        for font in PodiumFont:
            for contents in permutations(HEADER_CONTENTS):
                layout = dict(zip(HEADER_POSITIONS, contents, strict=True))
                save(render_flying_v_header_layer(font, event_format, layout),
                     f"flying_v_headers/{font.value}/{event_format.value}/{header_permutation_id(layout)}.png")
    return outputs

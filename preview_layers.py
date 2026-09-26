"""Generate reusable transparent layers for the browser Format preview."""

from __future__ import annotations

from itertools import permutations
from pathlib import Path

from PIL import Image, ImageDraw

from background_builder import BackgroundRequest, PixelSize
from creation import CreationRequest, TextSettings
from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from DrawPodium import PodiumFont, PodiumMode
from formatting_assets import FormattingAssetRenderer
from legacy_podium_content_renderer import LegacyPodiumContentRenderer
from mode_preferences import ModePreferenceRepository
from models import TournamentFormat
from podium_colors import PodiumColorConfiguration, PodiumColorPreset, PodiumColorSelection
from sample_creation_data import sample_top_8_entrants, sample_tournament


LAYER_CANVAS_SIZE = PixelSize(1920, 941)
HEADER_POSITIONS = ("top_left", "top_middle", "top_right")
HEADER_CONTENTS = ("tournament_logo", "tournament_title", "metadata")
LAYOUTS = {
    "top_3": (3, None),
    "top_4": (4, None),
    "top_8": (8, None),
    "top_8_four_podiums": (8, "four_podium"),
}
RAINBOW_MAIN_COLORS = (
    "#F23838FF", "#F28C28FF", "#F2D338FF", "#3BC65AFF",
    "#32C7CFFF", "#3478F6FF", "#5746C7FF", "#A84BE0FF",
)
CUSTOM_RED = PodiumColorSelection("#E53935FF", "#8E1B18FF", "#000000FF")


def header_permutation_id(header_layout: dict[str, str]) -> str:
    aliases = {
        "tournament_logo": "logo",
        "tournament_title": "title",
        "metadata": "metadata",
    }
    return "-".join(aliases[header_layout[position]] for position in HEADER_POSITIONS)


def _logo_placeholder(canvas: Image.Image, position: str) -> None:
    draw = ImageDraw.Draw(canvas)
    width, height = 240, 120
    if position == "top_left":
        left = 20
    elif position == "top_middle":
        left = (canvas.width - width) // 2
    else:
        left = canvas.width - width - 20
    top = 20
    right, bottom = left + width, top + height
    color = "#8E95AFFF"
    draw.rounded_rectangle((left, top, right, bottom), radius=10, outline=color, width=5)
    draw.line((left + 18, top + 18, right - 18, bottom - 18), fill=color, width=5)
    draw.line((right - 18, top + 18, left + 18, bottom - 18), fill=color, width=5)


def render_header_layer(font: PodiumFont, header_layout: dict[str, str]) -> Image.Image:
    selection = ModeSelection(
        CreationMode.PODIUM,
        ModeOptions(
            event_format=TournamentFormat.SINGLES,
            entrant_count=3,
            podium_style=PodiumStyle.LEGACY,
        ),
    )
    canvas = Image.new("RGBA", LAYER_CANVAS_SIZE.as_tuple(), (0, 0, 0, 0))
    request = CreationRequest(
        selection=selection,
        background=BackgroundRequest(size=LAYER_CANVAS_SIZE),
        entrants=sample_top_8_entrants()[:3],
        tournament=sample_tournament(TournamentFormat.SINGLES),
        header_layout=header_layout,
        text_settings=TextSettings(),
    )
    renderer = LegacyPodiumContentRenderer(font=font)
    renderer._draw_assigned_tournament_text(canvas, request, PodiumMode.SINGLES_TOP_3)
    logo_position = next(position for position, content in header_layout.items() if content == "tournament_logo")
    _logo_placeholder(canvas, logo_position)
    return canvas


def _repeat_colors(colors: tuple[PodiumColorSelection, ...], count: int = 8) -> PodiumColorConfiguration:
    return PodiumColorConfiguration.per_podium(*(colors[index % len(colors)] for index in range(count)))


def _rainbow_colors(asset_count: int) -> PodiumColorConfiguration:
    indexes = (0, 3, 7) if asset_count == 3 else (1, 3, 5, 7) if asset_count == 4 else tuple(range(8))
    return _repeat_colors(tuple(PodiumColorSelection(RAINBOW_MAIN_COLORS[index]) for index in indexes))


def _customizable_colors(layer_id: str, asset_count: int) -> PodiumColorConfiguration:
    if layer_id == "smash_player_colors":
        return PodiumColorConfiguration.from_preset(PodiumColorPreset.LEGACY)
    if layer_id == "olympic_medals":
        return PodiumColorConfiguration.from_preset(PodiumColorPreset.MEDALS)
    if layer_id == "rainbow":
        return _rainbow_colors(asset_count)
    if layer_id == "custom_red":
        return _repeat_colors((CUSTOM_RED,))
    raise ValueError(f"Unknown customizable preview layer: {layer_id}")


def render_podium_layer(style: PodiumStyle, layout_id: str, color_id: str | None = None) -> Image.Image:
    entrant_count, variant = LAYOUTS[layout_id]
    selection = ModeSelection(
        CreationMode.PODIUM,
        ModeOptions(
            event_format=TournamentFormat.SINGLES,
            entrant_count=entrant_count,
            variant=variant,
            podium_style=style,
        ),
    )
    preferences = ModePreferenceRepository().load(selection)
    canvas = Image.new("RGBA", preferences.canvas_size.as_tuple(), (0, 0, 0, 0))
    colors = None
    if style is PodiumStyle.CUSTOMIZABLE:
        asset_count = 4 if variant == "four_podium" else entrant_count
        colors = _customizable_colors(color_id or "smash_player_colors", asset_count)
    result = FormattingAssetRenderer().draw(canvas, preferences, colors)
    if variant == "four_podium":
        draw = ImageDraw.Draw(result)
        for placement in preferences.text_slots:
            if placement.field != "entrant.summary":
                continue
            x, y = placement.anchor.x, placement.anchor.y
            half_width = min(70, placement.max_width // 2)
            draw.line((x - half_width, y - 8, x + half_width, y - 8), fill="#D8DCE8CC", width=7)
            draw.line((x - half_width + 18, y + 10, x + half_width - 18, y + 10), fill="#8E95AFCC", width=6)
    return result


def generate_preview_layers(output_root: Path) -> list[Path]:
    outputs: list[Path] = []
    header_root = output_root / "headers"
    for font in PodiumFont:
        for contents in permutations(HEADER_CONTENTS):
            layout = dict(zip(HEADER_POSITIONS, contents, strict=True))
            path = header_root / font.value / f"{header_permutation_id(layout)}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            render_header_layer(font, layout).save(path, format="PNG", optimize=True)
            outputs.append(path)

    podium_root = output_root / "podiums"
    for layout_id in LAYOUTS:
        path = podium_root / "legacy" / f"{layout_id}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        render_podium_layer(PodiumStyle.LEGACY, layout_id).save(path, format="PNG", optimize=True)
        outputs.append(path)
        for color_id in ("smash_player_colors", "olympic_medals", "rainbow", "custom_red"):
            path = podium_root / "customizable" / layout_id / f"{color_id}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            render_podium_layer(PodiumStyle.CUSTOMIZABLE, layout_id, color_id).save(path, format="PNG", optimize=True)
            outputs.append(path)
    return outputs

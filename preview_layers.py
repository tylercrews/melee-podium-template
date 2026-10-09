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
from geometric_content_renderer import (
    EyesContentRenderer,
    SquaresContentRenderer,
    _eyes_header_boxes,
    _squares_header_boxes,
)
from geometric_formatting_colors import GeometricFormattingColor, GeometricFormattingColors
from legacy_podium_content_renderer import LegacyPodiumContentRenderer
from mode_preferences import ModePreferenceRepository
from models import TournamentFormat
from podium_colors import PodiumColorConfiguration, PodiumColorPreset, PodiumColorSelection
from sample_creation_data import (
    sample_singles_entrants,
    sample_top_4_teams,
    sample_top_8_entrants,
    sample_tournament,
)


LAYER_CANVAS_SIZE = PixelSize(1920, 941)
HEADER_POSITIONS = ("top_left", "top_middle", "top_right")
HEADER_CONTENTS = ("tournament_logo", "tournament_title", "metadata")
LAYOUTS = {
    "top_3": (3, None),
    "top_4": (4, None),
    "top_8": (8, None),
    "top_8_four_podiums": (8, "four_podium"),
}
SQUARE_LAYOUTS = {
    "singles_top_8": (TournamentFormat.SINGLES, 8),
    "doubles_top_3": (TournamentFormat.DOUBLES, 3),
    "doubles_top_4": (TournamentFormat.DOUBLES, 4),
}
SQUARE_HEADER_LAYOUTS = {
    "singles": (TournamentFormat.SINGLES, 8),
    "doubles": (TournamentFormat.DOUBLES, 4),
}
EYE_LAYOUTS = {
    **{
        f"singles_top_{count}": (TournamentFormat.SINGLES, count)
        for count in (8, 10, 15, 16, 20, 25)
    },
    "doubles_top_3": (TournamentFormat.DOUBLES, 3),
    "doubles_top_4": (TournamentFormat.DOUBLES, 4),
}
COLOR_LAYER_IDS = ("smash_player_colors", "olympic_medals", "rainbow", "pick_all")
RAINBOW_MAIN_COLORS = (
    "#F23838FF", "#F28C28FF", "#F2D338FF", "#3BC65AFF",
    "#32C7CFFF", "#3478F6FF", "#5746C7FF", "#A84BE0FF",
)
CUSTOM_RED = PodiumColorSelection("#E53935FF", "#8E1B18FF", "#000000FF")
PICK_ALL_COLORS = (
    PodiumColorSelection("#FF4D6DFF", "#8D1830FF", "#20050BFF"),
    PodiumColorSelection("#4D96FFFF", "#1F579EFF", "#06162BFF"),
    PodiumColorSelection("#FFD93DFF", "#9B781AFF", "#2B2105FF"),
    PodiumColorSelection("#6BCB77FF", "#2F7D3BFF", "#09230EFF"),
    PodiumColorSelection("#FF9234FF", "#A74D0FFF", "#2C1204FF"),
    PodiumColorSelection("#35D0BAFF", "#167869FF", "#052723FF"),
    PodiumColorSelection("#B76DFFFF", "#6B31A3FF", "#1C092EFF"),
    PodiumColorSelection("#D7D9E0FF", "#737784FF", "#17191FFF"),
)


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


def _boxed_logo_placeholder(canvas: Image.Image, box: tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(canvas)
    left, top, right, bottom = box
    inset = 12
    left, top, right, bottom = left + inset, top + inset, right - inset, bottom - inset
    color = "#8E95AFFF"
    draw.rounded_rectangle((left, top, right, bottom), radius=10, outline=color, width=5)
    draw.line((left + 12, top + 12, right - 12, bottom - 12), fill=color, width=5)
    draw.line((right - 12, top + 12, left + 12, bottom - 12), fill=color, width=5)


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


def render_square_header_layer(
    font: PodiumFont,
    header_layout_id: str,
    header_layout: dict[str, str],
) -> Image.Image:
    event_format, entrant_count = SQUARE_HEADER_LAYOUTS[header_layout_id]
    selection = ModeSelection(
        CreationMode.SQUARES,
        ModeOptions(event_format=event_format, entrant_count=entrant_count),
    )
    preferences = ModePreferenceRepository().load(selection)
    canvas = Image.new("RGBA", preferences.canvas_size.as_tuple(), (0, 0, 0, 0))
    request = CreationRequest(
        selection=selection,
        background=BackgroundRequest(size=preferences.canvas_size),
        entrants=(
            sample_top_8_entrants()[:entrant_count]
            if event_format is TournamentFormat.SINGLES
            else sample_top_4_teams()[:entrant_count]
        ),
        tournament=sample_tournament(event_format),
        formatting_colors=GeometricFormattingColors.one("#000000FF", "#E53935FF"),
        header_layout=header_layout,
        text_settings=TextSettings(),
    )
    renderer = SquaresContentRenderer(font=font)
    renderer._draw_header(canvas, request, preferences)
    logo_position = next(
        position
        for position, content in header_layout.items()
        if content == "tournament_logo"
    )
    logo_box = _squares_header_boxes(canvas, preferences)[logo_position][0]
    _boxed_logo_placeholder(canvas, logo_box.as_tuple())
    return canvas


def render_eye_header_layer(
    font: PodiumFont,
    layout_id: str,
    header_layout: dict[str, str],
) -> Image.Image:
    event_format, entrant_count = EYE_LAYOUTS[layout_id]
    selection = ModeSelection(
        CreationMode.EYES,
        ModeOptions(event_format=event_format, entrant_count=entrant_count),
    )
    preferences = ModePreferenceRepository().load(selection)
    canvas = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
    entrants = (
        sample_singles_entrants(entrant_count)
        if event_format is TournamentFormat.SINGLES
        else sample_top_4_teams()[:entrant_count]
    )
    request = CreationRequest(
        selection=selection,
        background=BackgroundRequest(size=preferences.canvas_size),
        entrants=entrants,
        tournament=sample_tournament(event_format),
        formatting_colors=GeometricFormattingColors.one("#E53935FF"),
        header_layout=header_layout,
        text_settings=TextSettings(),
    )
    EyesContentRenderer(font=font)._draw_header(canvas, request, preferences)
    logo_position = next(
        position
        for position, content in header_layout.items()
        if content == "tournament_logo"
    )
    logo_box = _eyes_header_boxes(preferences)[logo_position][0]
    _boxed_logo_placeholder(canvas, logo_box.as_tuple())
    return canvas


def _repeat_colors(colors: tuple[PodiumColorSelection, ...], count: int = 8) -> PodiumColorConfiguration:
    return PodiumColorConfiguration.per_podium(*(colors[index % len(colors)] for index in range(count)))


def _rainbow_colors(asset_count: int) -> PodiumColorConfiguration:
    indexes = (
        (0, 3, 7)
        if asset_count == 3
        else (1, 3, 5, 7)
        if asset_count == 4
        else tuple(range(8))
        if asset_count >= 8
        else tuple(
            round(index * 7 / max(1, asset_count - 1))
            for index in range(asset_count)
        )
    )
    return _repeat_colors(
        tuple(PodiumColorSelection(RAINBOW_MAIN_COLORS[index]) for index in indexes),
        asset_count,
    )


def _customizable_colors(layer_id: str, asset_count: int) -> PodiumColorConfiguration:
    if layer_id == "smash_player_colors":
        preset = PodiumColorConfiguration.from_preset(PodiumColorPreset.LEGACY)
        return _repeat_colors(
            tuple(preset.color_for_slot(slot) for slot in range(1, 9)),
            asset_count,
        )
    if layer_id == "olympic_medals":
        preset = PodiumColorConfiguration.from_preset(PodiumColorPreset.MEDALS)
        medal_colors = tuple(
            preset.color_for_slot(slot)
            for slot in range(1, min(3, asset_count) + 1)
        ) + tuple(
            preset.color_for_slot(4)
            for _slot in range(4, asset_count + 1)
        )
        return PodiumColorConfiguration.per_podium(*medal_colors)
    if layer_id == "rainbow":
        return _rainbow_colors(asset_count)
    if layer_id == "custom_red":
        return _repeat_colors((CUSTOM_RED,), asset_count)
    if layer_id == "pick_all":
        return _repeat_colors(PICK_ALL_COLORS, asset_count)
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


def render_square_layer(layout_id: str, color_id: str) -> Image.Image:
    event_format, entrant_count = SQUARE_LAYOUTS[layout_id]
    selection = ModeSelection(
        CreationMode.SQUARES,
        ModeOptions(event_format=event_format, entrant_count=entrant_count),
    )
    preferences = ModePreferenceRepository().load(selection)
    source_colors = _customizable_colors(color_id, entrant_count)
    colors = GeometricFormattingColors(
        tuple(
            GeometricFormattingColor(
                resolved.base_color,
                resolved.main_color,
            )
            for resolved in (
                source_colors.color_for_slot(slot).resolve()
                for slot in range(1, entrant_count + 1)
            )
        )
    )
    canvas = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
    return FormattingAssetRenderer().draw(canvas, preferences, colors)


def render_eye_layer(layout_id: str, color_id: str) -> Image.Image:
    event_format, entrant_count = EYE_LAYOUTS[layout_id]
    selection = ModeSelection(
        CreationMode.EYES,
        ModeOptions(event_format=event_format, entrant_count=entrant_count),
    )
    preferences = ModePreferenceRepository().load(selection)
    source_colors = _customizable_colors(color_id, entrant_count)
    colors = GeometricFormattingColors(
        tuple(
            GeometricFormattingColor(resolved.main_color)
            for resolved in (
                source_colors.color_for_slot(slot).resolve()
                for slot in range(1, entrant_count + 1)
            )
        )
    )
    canvas = Image.new("RGBA", preferences.canvas_size.as_tuple(), "#00000000")
    return FormattingAssetRenderer().draw(canvas, preferences, colors)


def generate_eye_preview_layers(output_root: Path) -> list[Path]:
    """Generate Eyes header permutations and combined preset-rectangle layers."""

    outputs: list[Path] = []
    for font in PodiumFont:
        for contents in permutations(HEADER_CONTENTS):
            layout = dict(zip(HEADER_POSITIONS, contents, strict=True))
            for layout_id in EYE_LAYOUTS:
                path = (
                    output_root
                    / "eye_headers"
                    / font.value
                    / layout_id
                    / f"{header_permutation_id(layout)}.png"
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                render_eye_header_layer(font, layout_id, layout).save(
                    path,
                    format="PNG",
                    optimize=True,
                )
                outputs.append(path)

    outputs.extend(generate_eye_color_preview_layers(output_root))
    return outputs


def generate_eye_color_preview_layers(output_root: Path) -> list[Path]:
    """Generate only the combined Eyes preset-rectangle layers."""

    outputs: list[Path] = []
    eye_root = output_root / "eyes"
    for layout_id in EYE_LAYOUTS:
        for color_id in COLOR_LAYER_IDS:
            path = eye_root / layout_id / f"{color_id}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            render_eye_layer(layout_id, color_id).save(
                path,
                format="PNG",
                optimize=True,
            )
            outputs.append(path)
    return outputs


def generate_square_preview_layers(output_root: Path) -> list[Path]:
    """Generate only Squares headers and combined preset-card layers."""

    outputs: list[Path] = []
    for font in PodiumFont:
        for contents in permutations(HEADER_CONTENTS):
            layout = dict(zip(HEADER_POSITIONS, contents, strict=True))
            for header_layout_id in SQUARE_HEADER_LAYOUTS:
                square_path = (
                    output_root
                    / "square_headers"
                    / font.value
                    / header_layout_id
                    / f"{header_permutation_id(layout)}.png"
                )
                square_path.parent.mkdir(parents=True, exist_ok=True)
                render_square_header_layer(font, header_layout_id, layout).save(
                    square_path,
                    format="PNG",
                    optimize=True,
                )
                outputs.append(square_path)

    square_root = output_root / "squares"
    for layout_id in SQUARE_LAYOUTS:
        for color_id in COLOR_LAYER_IDS:
            path = square_root / layout_id / f"{color_id}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            render_square_layer(layout_id, color_id).save(
                path,
                format="PNG",
                optimize=True,
            )
            outputs.append(path)
    return outputs


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
    outputs.extend(generate_square_preview_layers(output_root))
    outputs.extend(generate_eye_preview_layers(output_root))
    from radial_preview_layers import generate_radial_preview_layers
    outputs.extend(generate_radial_preview_layers(output_root))
    return outputs

"""Shared formatting-stage preview generation for podium preference files."""

from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from background_builder import (  # noqa: E402
    BUILTIN_BACKGROUND_SIZES,
    BackgroundRequest,
    ImagePlacement,
    PixelRect,
    cover_crop,
    create_background,
)
from creation_modes import (  # noqa: E402
    CreationMode,
    ModeOptions,
    ModeSelection,
    PodiumStyle,
)
from formatting_assets import FormattingAssetRenderer  # noqa: E402
from legacy_podium_content_renderer import LegacyPodiumContentRenderer  # noqa: E402
from mode_preferences import ModePreferenceRepository  # noqa: E402
from models import TournamentFormat  # noqa: E402
from podium_colors import PodiumColorInput  # noqa: E402
from creation import CreationRequest  # noqa: E402
from sample_creation_data import (  # noqa: E402
    sample_top_4_teams,
    sample_top_8_entrants,
    sample_tournament,
)


BACKGROUND_ASSET_ID = "00_Battlefield_5000_5000_resaved.png"
OUTPUT_ROOT = Path(__file__).with_name("outputs")

LAYOUTS = (
    ("doubles_top_3", TournamentFormat.DOUBLES, 3, None),
    ("doubles_top_4", TournamentFormat.DOUBLES, 4, None),
    ("singles_top_3", TournamentFormat.SINGLES, 3, None),
    ("singles_top_4", TournamentFormat.SINGLES, 4, None),
    ("singles_top_8", TournamentFormat.SINGLES, 8, None),
    ("singles_top_8_four_podium", TournamentFormat.SINGLES, 8, "four_podium"),
)


def generate_previews(
    style: PodiumStyle,
    *,
    podium_colors: PodiumColorInput | None = None,
) -> tuple[Path, ...]:
    """Render all podium formatting layouts and return their output paths."""

    output_folder = OUTPUT_ROOT / style.value
    output_folder.mkdir(parents=True, exist_ok=True)
    repository = ModePreferenceRepository()
    renderer = FormattingAssetRenderer()
    outputs: list[tuple[str, Path]] = []

    for submode_id, event_format, entrant_count, variant in LAYOUTS:
        selection = ModeSelection(
            CreationMode.PODIUM,
            ModeOptions(
                event_format=event_format,
                entrant_count=entrant_count,
                variant=variant,
                podium_style=style,
            ),
        )
        preferences = repository.load(selection)
        size = preferences.canvas_size
        source_size = BUILTIN_BACKGROUND_SIZES[BACKGROUND_ASSET_ID]
        crop = cover_crop(source_size, size)
        request = BackgroundRequest(
            size=size,
            image=ImagePlacement(
                asset_id=BACKGROUND_ASSET_ID,
                source_crop=crop,
                destination=PixelRect(0, 0, size.width, size.height),
            ),
        )
        background = create_background(request)
        preview = renderer.draw(background, preferences, podium_colors)
        path = output_folder / f"{submode_id}.png"
        preview.save(path)
        outputs.append((submode_id.replace("_", " ").title(), path))

    overview_path = output_folder / "overview.png"
    _create_overview(outputs, overview_path)
    return tuple(path for _, path in outputs) + (overview_path,)


def generate_creation_previews(
    style: PodiumStyle,
    *,
    podium_colors: PodiumColorInput | None = None,
    output_variant: str | None = None,
) -> tuple[Path, ...]:
    """Render sample entrants and text for every podium preference under review."""

    output_folder = OUTPUT_ROOT / "creation" / style.value
    if output_variant is not None:
        output_folder /= output_variant
    output_folder.mkdir(parents=True, exist_ok=True)
    repository = ModePreferenceRepository()
    formatting_renderer = FormattingAssetRenderer()
    content_renderer = LegacyPodiumContentRenderer()
    outputs: list[tuple[str, Path]] = []

    for submode_id, event_format, entrant_count, variant in LAYOUTS:
        selection = ModeSelection(
            CreationMode.PODIUM,
            ModeOptions(
                event_format=event_format,
                entrant_count=entrant_count,
                variant=variant,
                podium_style=style,
            ),
        )
        preferences = repository.load(selection)
        size = preferences.canvas_size
        source_size = BUILTIN_BACKGROUND_SIZES[BACKGROUND_ASSET_ID]
        background_request = BackgroundRequest(
            size=size,
            image=ImagePlacement(
                asset_id=BACKGROUND_ASSET_ID,
                source_crop=cover_crop(source_size, size),
                destination=PixelRect(0, 0, size.width, size.height),
            ),
        )
        entrants = (
            sample_top_8_entrants()[:entrant_count]
            if event_format is TournamentFormat.SINGLES
            else sample_top_4_teams()[:entrant_count]
        )
        request = CreationRequest(
            selection=selection,
            background=background_request,
            entrants=entrants,
            tournament=sample_tournament(event_format),
            podium_colors=podium_colors,
        )
        background = create_background(background_request)
        formatted = formatting_renderer.draw(
            background, preferences, podium_colors
        )
        preview = content_renderer.draw(formatted, request, preferences)
        path = output_folder / f"{submode_id}.png"
        preview.save(path)
        outputs.append((submode_id.replace("_", " ").title(), path))

    overview_path = output_folder / "overview.png"
    _create_overview(outputs, overview_path)
    return tuple(path for _, path in outputs) + (overview_path,)


def _create_overview(outputs: list[tuple[str, Path]], path: Path) -> None:
    """Write a two-column contact sheet without assuming equal canvas widths."""

    cell_width = 868
    image_height = 470
    label_height = 30
    columns = 2
    rows = (len(outputs) + columns - 1) // columns
    overview = Image.new(
        "RGB",
        (cell_width * columns, (image_height + label_height) * rows),
        (22, 22, 26),
    )
    draw = ImageDraw.Draw(overview)
    font = ImageFont.load_default(size=18)

    for index, (label, output_path) in enumerate(outputs):
        with Image.open(output_path) as source:
            preview = source.convert("RGB")
            preview.thumbnail((cell_width, image_height), Image.Resampling.LANCZOS)
        column = index % columns
        row = index // columns
        cell_left = column * cell_width
        cell_top = row * (image_height + label_height)
        x = cell_left + (cell_width - preview.width) // 2
        y = cell_top + (image_height - preview.height) // 2
        overview.paste(preview, (x, y))
        draw.text(
            (cell_left + 10, cell_top + image_height + 5),
            label,
            fill="white",
            font=font,
        )

    overview.save(path)

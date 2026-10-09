"""Serializable triangular sections and shared Radial mask geometry."""

from PIL import Image, ImageChops, ImageDraw

from geometric_formatting_colors import GeometricFormattingColors
from mode_preferences import FormattingAssetPlacement, ModePreferences


DIVIDER_COLOR = "#FFFFFFFF"


def radial_sections(preferences: ModePreferences) -> dict[int, FormattingAssetPlacement]:
    sections = {
        int(item.slot_id.rsplit("_", 1)[1]): item
        for item in preferences.formatting_assets
        if item.asset_id == "radial_slice"
    }
    if set(sections) != set(range(1, preferences.selection.options.entrant_count + 1)):
        raise ValueError("Radial requires one polygon section per entrant")
    if any(not section.polygon for section in sections.values()):
        raise ValueError("Radial sections require polygon vertices")
    return sections


def polygon_mask(placement: FormattingAssetPlacement) -> Image.Image:
    """Build an antialiased mask in the section's local pixel coordinates."""
    size = (placement.destination.width, placement.destination.height)
    mask = Image.new("L", (size[0] * 3, size[1] * 3), 0)
    ImageDraw.Draw(mask).polygon([(p.x * 3, p.y * 3) for p in placement.polygon], fill=255)
    return mask.resize(size, Image.Resampling.LANCZOS)


def clip_to_section(image: Image.Image, placement: FormattingAssetPlacement) -> Image.Image:
    expected = (placement.destination.width, placement.destination.height)
    if image.size != expected:
        raise ValueError("Section image dimensions must match its polygon destination")
    clipped = image.convert("RGBA")
    clipped.putalpha(ImageChops.multiply(clipped.getchannel("A"), polygon_mask(placement)))
    return clipped


def draw_radial_dividers(canvas: Image.Image, preferences: ModePreferences) -> None:
    """Redraw the internal rays above portraits, preserving the reference gaps."""
    center = (canvas.width // 2, canvas.height // 2)
    endpoints = set()
    for section in radial_sections(preferences).values():
        rect = section.destination
        endpoints.update((rect.left + p.x, rect.top + p.y) for p in section.polygon)
    draw = ImageDraw.Draw(canvas)
    for point in sorted(endpoints - {center}):
        draw.line((center, point), fill=DIVIDER_COLOR, width=max(2, round(canvas.width / 213)))


def draw_radial_formatting(
    canvas: Image.Image,
    preferences: ModePreferences,
    colors: GeometricFormattingColors,
) -> Image.Image:
    result = canvas.convert("RGBA")
    for slot, section in radial_sections(preferences).items():
        rect = section.destination
        layer = Image.new("RGBA", (rect.width, rect.height), colors.for_slot(slot).background_color)
        result.alpha_composite(clip_to_section(layer, section), (rect.left, rect.top))
    draw_radial_dividers(result, preferences)
    return result

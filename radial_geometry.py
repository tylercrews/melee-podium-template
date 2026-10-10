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


def draw_radial_dividers(
    canvas: Image.Image,
    preferences: ModePreferences,
    colors: GeometricFormattingColors | None = None,
) -> None:
    """Draw each section's border inside its own triangle, including shared rays."""
    for slot, section in radial_sections(preferences).items():
        rect = section.destination
        layer = Image.new("RGBA", (rect.width, rect.height), "#00000000")
        points = [(p.x, p.y) for p in section.polygon]
        color = colors.for_slot(slot).trim_color if colors is not None else None
        ImageDraw.Draw(layer).line(
            points + points[:1], fill=color or DIVIDER_COLOR,
            width=max(2, round(canvas.width / 213)), joint="curve",
        )
        canvas.alpha_composite(clip_to_section(layer, section), (rect.left, rect.top))


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
    return result

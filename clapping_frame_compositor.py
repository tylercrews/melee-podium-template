"""Reposition synchronized character-member cutouts before portrait cropping."""

from __future__ import annotations

from PIL import Image

from portrait_crop_adjustment_for_clapping import ClappingPortraitAdjustment


def compose_clapping_member_layers(
    source: Image.Image,
    adjustment: ClappingPortraitAdjustment,
) -> Image.Image:
    """Draw member layers from the same GIF frame, back to front.

    Ice Climbers exports show their two members side by side. The calibrated
    cutouts move the rear member behind the front member without adding a second
    animation clock or modifying the original GIF. Coordinates scale with the
    actual source dimensions; ordinary single-character frames pass through.
    """

    if not adjustment.member_layers:
        return source
    rgba = source.convert("RGBA")
    composed = Image.new("RGBA", source.size, "#00000000")
    scale_x = source.width / adjustment.source_size[0]
    scale_y = source.height / adjustment.source_size[1]
    for layer in sorted(adjustment.member_layers, key=lambda item: item.layer_order):
        left, top, right, bottom = layer.source_crop
        bounds = (
            round(left * scale_x), round(top * scale_y),
            round(right * scale_x), round(bottom * scale_y),
        )
        cutout = rgba.crop(bounds)
        offset_x, offset_y = layer.offset
        destination = (
            bounds[0] + round(offset_x * scale_x),
            bounds[1] + round(offset_y * scale_y),
        )
        composed.alpha_composite(cutout, destination)
    return composed

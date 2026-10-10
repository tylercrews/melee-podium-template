"""Reference-positioned Radial portraits and overlapping center header."""

from dataclasses import dataclass
import math

from PIL import Image, ImageFilter

from creation import CreationRequest
from creation_modes import CreationMode
from DrawPodium import PodiumFont, _temporary_font_settings
from formatting_assets import draw_placement_tags
from eyes_portrait_renderer import render_eye_portrait
from geometric_content_renderer import (
    LogoInput,
    _draw_horizontal_header_item,
    _draw_result_text,
    _open_logo,
    _primary_character,
)
from legacy_podium_content_renderer import LegacyPodiumContentRenderer
from mode_preferences import ModePreferences
from radial_geometry import clip_to_section, draw_radial_dividers, radial_sections


DEFAULT_RADIAL_HEADER_LAYOUT = {
    "top_left": "tournament_title",
    "top_middle": "tournament_logo",
    "top_right": "metadata",
}


def radial_header_boxes(preferences: ModePreferences):
    return {
        item.slot_id.removeprefix("header_"): item.destination
        for item in preferences.formatting_assets
        if item.asset_id == "radial_header_region"
    }


def _composite_outlined_text(canvas: Image.Image, layer: Image.Image) -> None:
    """Keep identities readable over bright portraits and central logos."""
    outline = Image.new("RGBA", canvas.size, "#000000FF")
    outline.putalpha(layer.getchannel("A").filter(ImageFilter.MaxFilter(5)))
    canvas.alpha_composite(outline)
    canvas.alpha_composite(layer)


@dataclass(frozen=True, slots=True)
class RadialContentRenderer:
    font: PodiumFont = PodiumFont.TYROWO
    tournament_logo: LogoInput = None
    custom_font_bytes: bytes | None = None
    logo_scale: float | None = None

    def __post_init__(self) -> None:
        if self.logo_scale is not None and (isinstance(self.logo_scale, bool) or not isinstance(self.logo_scale, (int, float)) or not math.isfinite(self.logo_scale) or not .001 <= self.logo_scale <= 100):
            raise ValueError("logo_scale must be a number between .001 and 100")

    def draw(self, canvas: Image.Image, request: CreationRequest, preferences: ModePreferences) -> Image.Image:
        if request.selection.mode is not CreationMode.RADIAL:
            raise ValueError("RadialContentRenderer requires Radial mode")
        result = canvas.convert("RGBA")
        sections = radial_sections(preferences)
        portrait_sections = {p.slot_id: p for p in preferences.formatting_assets if p.asset_id == "radial_portrait_slice"}
        if portrait_sections and set(portrait_sections) != {p.slot_id for p in preferences.character_slots}:
            raise ValueError("Radial portrait sections must match the character slots")
        with _temporary_font_settings(request.text_settings.font_size_adjustment, self.custom_font_bytes):
            for placement in sorted(preferences.character_slots, key=lambda item: (item.z_index, item.slot_id)):
                section = portrait_sections.get(placement.slot_id, sections[placement.entrant_slot])
                rect = section.destination
                entrant = request.entrants[placement.entrant_slot - 1]
                portrait = render_eye_portrait(
                    _primary_character(entrant, placement),
                    (rect.width, rect.height),
                    doubles=True,
                    zoom_multiplier=placement.scale,
                    framing_width=preferences.canvas_size.width / 6,
                    focal_destination=(placement.anchor.x - rect.left, placement.anchor.y - rect.top),
                )
                result.alpha_composite(clip_to_section(portrait, section), (rect.left, rect.top))
            draw_radial_dividers(result, preferences, request.formatting_colors)
            self._draw_header(result, request, preferences)
            # Both result labels and central text remain above an oversized logo.
            text_layer = Image.new("RGBA", result.size, "#00000000")
            _draw_result_text(text_layer, request, preferences, self.font)
            _composite_outlined_text(result, text_layer)
            draw_placement_tags(result, preferences)
        return result

    def _draw_header(self, canvas: Image.Image, request: CreationRequest, preferences: ModePreferences) -> None:
        layout = request.header_layout or DEFAULT_RADIAL_HEADER_LAYOUT
        boxes = radial_header_boxes(preferences)
        logo = _open_logo(self.tournament_logo)
        # Logo first regardless of the assignment/permutation order.
        logo_position = next(position for position, content in layout.items() if content == "tournament_logo")
        box = boxes[logo_position]
        if logo is not None and self.logo_scale is not None:
            size = (max(1, round(logo.width * self.logo_scale)), max(1, round(logo.height * self.logo_scale)))
            # Transform only the visible viewport, avoiding huge allocations at 100x.
            left = (box.left + box.right - size[0]) / 2
            top = (box.top + box.bottom - size[1]) / 2
            visible = logo.transform(canvas.size, Image.Transform.AFFINE, (1 / self.logo_scale, 0, -left / self.logo_scale, 0, 1 / self.logo_scale, -top / self.logo_scale), Image.Resampling.BICUBIC)
            canvas.alpha_composite(visible)
        elif logo is not None:
            _draw_horizontal_header_item(canvas, request, "tournament_logo", box, self.font, logo, "ma")
        metadata_renderer = LegacyPodiumContentRenderer(font=self.font)
        text_layer = Image.new("RGBA", canvas.size, "#00000000")
        for position, content in layout.items():
            if content == "tournament_logo":
                continue
            box = boxes[position]
            if content == "metadata":
                y = box.top
                for row in metadata_renderer._metadata_items(request):
                    y += metadata_renderer._draw_joined_metadata_row(text_layer, request, [(text, 26) for text, _size in row], x=(box.left + box.right) // 2, y=y, anchor="ma", max_width=box.width) + 5
            else:
                _draw_horizontal_header_item(text_layer, request, content, box, self.font, None, "ma", title_preferred_size=48)
        _composite_outlined_text(canvas, text_layer)

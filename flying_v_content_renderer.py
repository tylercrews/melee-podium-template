"""Full-body Flying V figures, their labels, corner headers, and attribution."""

from __future__ import annotations

from dataclasses import dataclass, replace

from PIL import Image, ImageDraw

from background_builder import PixelRect
from creation import CreationRequest
from creation_modes import CreationMode
from DrawPodium import CharacterTag, PodiumFont, _draw_character_tag, _resolve_doubles_tag_collisions, _temporary_font_settings
from entrant_visibility import slot_from_id
from flying_v_lineup import FRAME_ASSETS, HANGING_FRAME, PlacedLineup, place_lineup
from font_size_adjustments import adjusted_size
from formatting_assets import _composite_clipped, draw_placement_tags
from geometric_content_renderer import (
    LogoInput,
    _composite_watermark,
    _draw_header_lines,
    _draw_logo_in_box,
    _draw_result_text,
    _explicit_entrant_color,
    _member_for_placement,
    _open_logo,
    _watermark_color,
)
from legacy_podium_content_renderer import LegacyPodiumContentRenderer
from mode_preferences import ModePreferences, TextPlacement
from models import DoublesTeam
from radial_content_renderer import _composite_outlined_text


DEFAULT_FLYING_V_HEADER_LAYOUT = {
    "top_left": "tournament_logo",
    "top_middle": "tournament_title",
    "top_right": "metadata",
}
HEADER_ANCHORS = {"top_left": "la", "top_middle": "ma", "top_right": "ra"}
# The attribution owns a slim top row so the outer seventh-place figures and
# the top-center header never cover it.
WATERMARK_ROW_HEIGHT = 44
WATERMARK_MARGIN = 16
LABEL_GAP = 6
NAME_ABOVE_HEAD_OFFSET = 15


@dataclass(frozen=True, slots=True)
class PlacedFigure:
    slot_id: str
    entrant_slot: int
    z_index: int
    hanging: bool
    lineup: PlacedLineup


def flying_v_header_boxes(preferences: ModePreferences) -> dict[str, PixelRect]:
    return {
        item.slot_id.removeprefix("header_"): item.destination
        for item in preferences.formatting_assets
        if item.asset_id == "flying_v_header_region"
    }


def place_figures(request: CreationRequest, preferences: ModePreferences) -> dict[str, PlacedFigure]:
    """Resolve every visible entrant's lineup inside its serialized frame."""
    frames = {item.slot_id: item for item in preferences.formatting_assets if item.asset_id in FRAME_ASSETS}
    figures = {}
    for placement in preferences.character_slots:
        frame = frames[placement.slot_id]
        result = request.entrants[placement.entrant_slot - 1]
        member = _member_for_placement(result, placement)
        hanging = frame.asset_id == HANGING_FRAME
        figures[placement.slot_id] = PlacedFigure(
            placement.slot_id, placement.entrant_slot, placement.z_index, hanging,
            place_lineup(member.characters, placement.scale, frame.destination, hanging=hanging,
                         team_color=result.team_color if isinstance(result, DoublesTeam) else None),
        )
    return figures


def _label_shift(preferences: ModePreferences, figure: PlacedFigure, figures: dict[str, PlacedFigure]) -> int:
    """Raise a hanging figure's label to its feet, staying clear of figures in front."""
    tags = [tag for tag in preferences.placement_tags if slot_from_id(tag.slot_id) == figure.entrant_slot]
    names = [item for item in preferences.text_slots if item.entrant_slot == figure.entrant_slot and item.field != "member.tag"]
    if not tags and not names:
        return 0
    top = min([tag.anchor.y - tag.max_size.height // 2 for tag in tags] + [item.anchor.y for item in names])
    bottom = max([tag.anchor.y + tag.max_size.height // 2 for tag in tags]
                 + [item.anchor.y + round((item.preferred_size or 24) * 1.25) for item in names])
    half_width = max([item.max_width // 2 for item in names] + [tag.max_size.width // 2 for tag in tags])
    center_x = (figure.lineup.bounds.left + figure.lineup.bounds.right) // 2
    desired = figure.lineup.bounds.bottom + LABEL_GAP
    in_front = [other.lineup.bounds.top for other in figures.values()
                if other.z_index > figure.z_index
                and other.lineup.bounds.left < center_x + half_width and other.lineup.bounds.right > center_x - half_width]
    if in_front:
        desired = min(desired, min(in_front) - (bottom - top) - LABEL_GAP)
    desired = max(desired, figure.lineup.bounds.top)
    return min(0, desired - top)


def labelled_preferences(preferences: ModePreferences, figures: dict[str, PlacedFigure]) -> ModePreferences:
    """Return label anchors that follow the rendered figures for this request."""
    shifts = {figure.entrant_slot: _label_shift(preferences, figure, figures) for figure in figures.values() if figure.hanging}

    def moved(item, slot):
        return replace(item, anchor=replace(item.anchor, y=item.anchor.y + shifts.get(slot, 0)))

    text = []
    for item in preferences.text_slots:
        if item.field == "member.tag":
            figure = figures.get(f"entrant_{item.entrant_slot}_member_{item.member_slot}")
            if figure is not None:
                text.append(replace(item, anchor=replace(item.anchor, y=figure.lineup.bounds.top - NAME_ABOVE_HEAD_OFFSET)))
            continue
        text.append(moved(item, item.entrant_slot))
    return replace(
        preferences,
        placement_tags=tuple(moved(tag, slot_from_id(tag.slot_id)) for tag in preferences.placement_tags),
        text_slots=tuple(text),
    )


def _entrant_text_style(request: CreationRequest, placement: TextPlacement) -> tuple[str, bool]:
    chosen = _explicit_entrant_color(request, placement.entrant_slot)
    if chosen is None:
        return placement.color or "#FFFFFFFF", False
    settings = request.text_settings
    index = {"pick_1": 0, "pick_2": (placement.entrant_slot - 1) % 2}.get(settings.entrant_text_color_mode, placement.entrant_slot - 1)
    return chosen, settings.entrant_text_metallic[index]


def _draw_member_names(canvas: Image.Image, request: CreationRequest, placements: list[TextPlacement], font: PodiumFont) -> None:
    """Draw doubles identities above each member's head, sponsor on the line above."""
    draw = ImageDraw.Draw(canvas)
    by_team: dict[int, list[CharacterTag]] = {}
    for placement in sorted(placements, key=lambda item: (item.entrant_slot, item.member_slot)):
        team = request.entrants[placement.entrant_slot - 1]
        member = team.entrant_1 if placement.member_slot == 1 else team.entrant_2
        color, metallic = _entrant_text_style(request, placement)
        size = adjusted_size(placement.preferred_size or 40, member.name_font_size_adjustment)
        by_team.setdefault(placement.entrant_slot, []).append(CharacterTag(
            (placement.anchor.x, placement.anchor.y), member.tag, color, placement.max_width,
            size, max(14, size * 3 // 5), metallic,
        ))
    for tags in by_team.values():
        for tag in _resolve_doubles_tag_collisions(draw, tags, font, canvas.width):
            _draw_character_tag(draw, tag, font)


@dataclass(frozen=True, slots=True)
class FlyingVContentRenderer:
    font: PodiumFont = PodiumFont.TYROWO
    tournament_logo: LogoInput = None
    custom_font_bytes: bytes | None = None

    def draw(self, canvas: Image.Image, request: CreationRequest, preferences: ModePreferences) -> Image.Image:
        if request.selection.mode is not CreationMode.FLYING_V:
            raise ValueError("FlyingVContentRenderer requires Flying V mode")
        result = canvas.convert("RGBA")
        watermark_box = PixelRect(result.width // 2, 0, result.width - WATERMARK_MARGIN, WATERMARK_ROW_HEIGHT)
        watermark_color = _watermark_color(result, watermark_box)
        with _temporary_font_settings(request.text_settings.font_size_adjustment, self.custom_font_bytes):
            figures = place_figures(request, preferences)
            # Smaller figures stand farther back; the leader is drawn last.
            for figure in sorted(figures.values(), key=lambda item: (item.z_index, item.slot_id)):
                _composite_clipped(result, figure.lineup.image, figure.lineup.bounds.as_tuple())
            labelled = labelled_preferences(preferences, figures)
            text_layer = Image.new("RGBA", result.size, "#00000000")
            _draw_result_text(text_layer, request, labelled, self.font,
                              [item for item in labelled.text_slots if item.field != "member.tag"])
            _draw_member_names(text_layer, request, [item for item in labelled.text_slots if item.field == "member.tag"], self.font)
            _composite_outlined_text(result, text_layer)
            draw_placement_tags(result, labelled)
            self._draw_header(result, request, preferences)
            _composite_watermark(
                result,
                position=(result.width - WATERMARK_MARGIN, 10),
                anchor="ra",
                max_width=watermark_box.width,
                font=self.font,
                fill=watermark_color,
            )
        return result

    def _draw_header(self, canvas: Image.Image, request: CreationRequest, preferences: ModePreferences) -> None:
        layout = request.header_layout or DEFAULT_FLYING_V_HEADER_LAYOUT
        boxes = flying_v_header_boxes(preferences)
        logo = _open_logo(self.tournament_logo)
        for position, content in layout.items():
            box = boxes[position]
            if content == "tournament_logo":
                _draw_logo_in_box(canvas, logo, box)
                continue
            layer = self.header_text_layer(request, content, box, HEADER_ANCHORS[position])
            visible = layer.getbbox()
            if visible is None:
                continue
            # Corner blocks hug the canvas bottom; the top-center block hangs from the top.
            offset = 0 if position == "top_middle" else max(0, box.height - visible[3])
            canvas.alpha_composite(layer, (box.left, box.top + offset))

    def header_text_layer(self, request: CreationRequest, content: str, box: PixelRect, anchor: str) -> Image.Image:
        """Draw one title or metadata block into a transparent box-sized layer."""
        layer = Image.new("RGBA", (box.width, box.height), "#00000000")
        local = PixelRect(0, 0, box.width, box.height)
        if content == "tournament_title":
            _draw_header_lines(layer, request, content, local, self.font, anchor, title_size=64)
            return layer
        renderer = LegacyPodiumContentRenderer(font=self.font)
        x = {"l": 0, "m": box.width // 2, "r": box.width}[anchor[0]]
        y = 0
        for row in renderer._metadata_items(request, preferred_size=28):
            y += renderer._draw_joined_metadata_row(layer, request, row, x=x, y=y, anchor=anchor, max_width=box.width, exact_size=True) + 5
        return layer

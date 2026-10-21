"""Full-body Flying V figures, their labels, corner headers, and attribution."""

from __future__ import annotations

from dataclasses import dataclass, replace

from PIL import Image, ImageDraw, ImageFilter

from background_builder import PixelRect
from creation import CreationRequest
from creation_modes import CreationMode
from DrawPodium import (
    CharacterTag,
    PodiumFont,
    _character_tag_bounds,
    _draw_character_tag,
    _resolve_doubles_tag_collisions,
    _temporary_font_settings,
)
from entrant_visibility import slot_from_id
from flying_v_lineup import FRAME_ASSETS, HANGING_FRAME, PlacedLineup, place_lineup
from font_size_adjustments import adjusted_size
from formatting_assets import LocalPlacementTagAssets, PlacementTagAssetProvider, _composite_clipped
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
NAME_ABOVE_HEAD_OFFSET = 15
LABEL_GAP = 6
# Placement tags with this slot suffix sit centered between a team's member names.
BETWEEN_NAMES_SUFFIX = "_between_names"
CREST_NAME_GUTTER = 12
# Placement art other than the first-place crest gets a black outline so it
# stays legible where it overlaps a figure.
FIRST_PLACE_ART = "01st.png"
PLACEMENT_OUTLINE_RATIO = .07


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


def text_vertical_extent(item: TextPlacement) -> tuple[int, int]:
    """Approximate the rows a result label covers from its Pillow anchor."""
    size = item.preferred_size or 24
    vertical = item.pillow_anchor[1]
    if vertical == "s":
        return item.anchor.y - size, item.anchor.y + size // 4
    if vertical == "m":
        return item.anchor.y - size // 2, item.anchor.y + size // 2
    return item.anchor.y, item.anchor.y + round(size * 1.25)


def _clear_of_front_shift(preferences: ModePreferences, figure: PlacedFigure, figures: dict[str, PlacedFigure]) -> int:
    """Lift a hanging figure's fixed label only when it would cover a nearer figure's head."""
    tags = [tag for tag in preferences.placement_tags if slot_from_id(tag.slot_id) == figure.entrant_slot]
    names = [item for item in preferences.text_slots if item.entrant_slot == figure.entrant_slot and item.field != "member.tag"]
    extents = [(tag.anchor.y - tag.max_size.height // 2, tag.anchor.y + tag.max_size.height // 2) for tag in tags]
    extents += [text_vertical_extent(item) for item in names]
    if not extents:
        return 0
    top, bottom = min(extent[0] for extent in extents), max(extent[1] for extent in extents)
    center_x = (tags or names)[0].anchor.x
    half_width = max([item.max_width // 2 for item in names] + [tag.max_size.width // 2 for tag in tags])
    in_front = [other.lineup.bounds.top for other in figures.values()
                if other.z_index > figure.z_index
                and other.lineup.bounds.left < center_x + half_width and other.lineup.bounds.right > center_x - half_width]
    if not in_front or bottom + LABEL_GAP <= min(in_front):
        return 0
    return min(0, max(min(in_front) - LABEL_GAP - bottom, figure.lineup.bounds.top - top))


def labelled_preferences(preferences: ModePreferences, figures: dict[str, PlacedFigure]) -> ModePreferences:
    """Return label anchors that follow the rendered figures for this request.

    Doubles member names sit just above each visible head. A team crest marked
    with ``BETWEEN_NAMES_SUFFIX`` is centered vertically on those names, and its
    seed moves with it. A hanging figure's label keeps its serialized position
    unless that would cover a nearer figure's head. Every other label is fixed.
    """
    lifts = {figure.entrant_slot: _clear_of_front_shift(preferences, figure, figures)
             for figure in figures.values() if figure.hanging}
    preferences = replace(
        preferences,
        placement_tags=tuple(replace(tag, anchor=replace(tag.anchor, y=tag.anchor.y + lifts.get(slot_from_id(tag.slot_id), 0)))
                             for tag in preferences.placement_tags),
        text_slots=tuple(replace(item, anchor=replace(item.anchor, y=item.anchor.y + lifts.get(item.entrant_slot, 0)))
                         if item.field != "member.tag" else item for item in preferences.text_slots),
    )
    text = []
    names: dict[int, list[TextPlacement]] = {}
    for item in preferences.text_slots:
        if item.field == "member.tag":
            figure = figures.get(f"entrant_{item.entrant_slot}_member_{item.member_slot}")
            if figure is None:
                continue
            item = replace(item, anchor=replace(item.anchor, y=figure.lineup.bounds.top - NAME_ABOVE_HEAD_OFFSET))
            names.setdefault(item.entrant_slot, []).append(item)
        text.append(item)
    shifts: dict[int, int] = {}
    tags = []
    for tag in preferences.placement_tags:
        slot = slot_from_id(tag.slot_id)
        if tag.slot_id.endswith(BETWEEN_NAMES_SUFFIX) and names.get(slot):
            # Baselines sit below each name's visual middle by about a third of its size.
            center = round(sum(item.anchor.y - (item.preferred_size or 40) * 7 // 20 for item in names[slot]) / len(names[slot]))
            shifts[slot] = center - tag.anchor.y
            tag = replace(tag, anchor=replace(tag.anchor, y=center))
        tags.append(tag)
    text = [replace(item, anchor=replace(item.anchor, y=item.anchor.y + shifts[item.entrant_slot]))
            if item.field == "entrant.seed" and item.entrant_slot in shifts else item for item in text]
    return replace(preferences, placement_tags=tuple(tags), text_slots=tuple(text))


def crest_clearances(preferences: ModePreferences, include_seeding: bool) -> dict[int, tuple[int, int, int, int]]:
    """Return the area each between-names crest and its seed keep free of member names."""
    seeds = {item.entrant_slot: item for item in preferences.text_slots if item.field == "entrant.seed"}
    clearances = {}
    for tag in preferences.placement_tags:
        if not tag.slot_id.endswith(BETWEEN_NAMES_SUFFIX):
            continue
        slot = slot_from_id(tag.slot_id)
        left, top = tag.anchor.x - tag.max_size.width // 2, tag.anchor.y - tag.max_size.height // 2
        right, bottom = tag.anchor.x + tag.max_size.width // 2, tag.anchor.y + tag.max_size.height // 2
        seed = seeds.get(slot)
        if include_seeding and seed is not None:
            # Short seeds such as "12s" span about two em widths.
            size = seed.preferred_size or 24
            right = max(right, seed.anchor.x + size * 2)
            top = min(top, text_vertical_extent(seed)[0])
        clearances[slot] = (left, top, right, bottom)
    return clearances


def draw_outlined_placement_tags(
    canvas: Image.Image,
    preferences: ModePreferences,
    assets: PlacementTagAssetProvider = LocalPlacementTagAssets(),
) -> None:
    """Draw canonical placement art, outlining everything except the first-place crest."""
    for tag in sorted(preferences.placement_tags, key=lambda item: (item.z_index, item.slot_id)):
        layer = assets.open(tag.asset_id)
        layer.thumbnail(tag.max_size.as_tuple(), Image.Resampling.LANCZOS)
        if tag.asset_id != FIRST_PLACE_ART:
            radius = max(2, round(min(layer.size) * PLACEMENT_OUTLINE_RATIO))
            padded = Image.new("RGBA", (layer.width + radius * 2, layer.height + radius * 2), "#00000000")
            padded.alpha_composite(layer, (radius, radius))
            outlined = Image.new("RGBA", padded.size, "#000000FF")
            outlined.putalpha(padded.getchannel("A").filter(ImageFilter.MaxFilter(radius * 2 + 1)))
            outlined.alpha_composite(padded)
            layer = outlined
        left = tag.anchor.x - layer.width // 2
        top = tag.anchor.y - layer.height // 2
        _composite_clipped(canvas, layer, (left, top, left + layer.width, top + layer.height))


def _entrant_text_style(request: CreationRequest, placement: TextPlacement) -> tuple[str, bool]:
    chosen = _explicit_entrant_color(request, placement.entrant_slot)
    if chosen is None:
        return placement.color or "#FFFFFFFF", False
    settings = request.text_settings
    index = {"pick_1": 0, "pick_2": (placement.entrant_slot - 1) % 2}.get(settings.entrant_text_color_mode, placement.entrant_slot - 1)
    return chosen, settings.entrant_text_metallic[index]


def _clear_of(draw: ImageDraw.ImageDraw, tag: CharacterTag, box: tuple[int, int, int, int] | None, font: PodiumFont) -> CharacterTag:
    """Move a member name outward until it no longer covers the team crest."""
    if box is None:
        return tag
    left, top, right, bottom = _character_tag_bounds(draw, tag, font)
    if right <= box[0] or left >= box[2] or bottom <= box[1] or top >= box[3]:
        return tag
    if (left + right) / 2 < (box[0] + box[2]) / 2:
        dx = box[0] - CREST_NAME_GUTTER - right
    else:
        dx = box[2] + CREST_NAME_GUTTER - left
    return replace(tag, position=(tag.position[0] + dx, tag.position[1]))


def _draw_member_names(canvas: Image.Image, request: CreationRequest, placements: list[TextPlacement], font: PodiumFont,
                       crests: dict[int, tuple[int, int, int, int]]) -> None:
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
    for slot, tags in by_team.items():
        for tag in _resolve_doubles_tag_collisions(draw, tags, font, canvas.width):
            _draw_character_tag(draw, _clear_of(draw, tag, crests.get(slot), font), font)


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
            labelled = labelled_preferences(preferences, figures)
            # Smaller figures stand farther back; the leader is drawn last.
            # Placement art layered below a figure is drawn just before it.
            pending = sorted(labelled.placement_tags, key=lambda item: (item.z_index, item.slot_id))
            for figure in sorted(figures.values(), key=lambda item: (item.z_index, item.slot_id)):
                behind = [tag for tag in pending if tag.z_index < figure.z_index]
                pending = [tag for tag in pending if tag.z_index >= figure.z_index]
                draw_outlined_placement_tags(result, replace(labelled, placement_tags=tuple(behind)))
                _composite_clipped(result, figure.lineup.image, figure.lineup.bounds.as_tuple())
            text_layer = Image.new("RGBA", result.size, "#00000000")
            _draw_result_text(text_layer, request, labelled, self.font,
                              [item for item in labelled.text_slots if item.field != "member.tag"])
            _draw_member_names(text_layer, request, [item for item in labelled.text_slots if item.field == "member.tag"],
                               self.font, crest_clearances(labelled, request.text_settings.include_seeding))
            _composite_outlined_text(result, text_layer)
            draw_outlined_placement_tags(result, replace(labelled, placement_tags=tuple(pending)))
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

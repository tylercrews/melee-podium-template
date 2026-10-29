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
    _draw_text,
    _resolve_doubles_tag_collisions,
    _temporary_font_settings,
    _wrap_text,
)
from entrant_visibility import slot_from_id
from flying_v_lineup import FRAME_ASSETS, LineupSlot, PlacedLineup, place_team
from font_size_adjustments import adjusted_size, result_text_adjustment
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
    _text_value,
    _watermark_color,
)
from legacy_podium_content_renderer import LegacyPodiumContentRenderer
from mode_preferences import CharacterPlacement, ModePreferences, TextPlacement
from models import DoublesTeam


DEFAULT_FLYING_V_HEADER_LAYOUT = {
    "top_left": "tournament_logo",
    "top_middle": "tournament_title",
    "top_right": "metadata",
}
HEADER_ANCHORS = {"top_left": "la", "top_middle": "ma", "top_right": "ra"}
# The attribution owns a slim serialized row (top edge, or bottom edge when
# vertically reversed) so the outer seventh-place figures and header never cover it.
WATERMARK_REGION = "flying_v_watermark_region"
WATERMARK_ROW_HEIGHT = 44
NAME_ABOVE_HEAD_OFFSET = 15
# Placement tags with this slot suffix sit centered between a team's member names.
BETWEEN_NAMES_SUFFIX = "_between_names"
CREST_NAME_GUTTER = 12
# Placement art other than the first-place crest gets a black outline so it
# stays legible where it overlaps a figure.
FIRST_PLACE_ART = "01st.png"
PLACEMENT_OUTLINE_RATIO = .07
# Wrapped result names break at the corner header boxes' width even when their
# serialized width lets a long unbroken name run on (behind any nearer figures)
# before shrinking, so typical team names stay within two lines above the boxes.
NAME_WRAP_WIDTH = 440
NAME_OUTLINE_FILTER_SIZE = 5


@dataclass(frozen=True, slots=True)
class PlacedFigure:
    slot_id: str
    entrant_slot: int
    z_index: int
    lineup: PlacedLineup


def flying_v_header_boxes(preferences: ModePreferences) -> dict[str, PixelRect]:
    return {
        item.slot_id.removeprefix("header_"): item.destination
        for item in preferences.formatting_assets
        if item.asset_id == "flying_v_header_region"
    }


def flying_v_watermark_row(preferences: ModePreferences) -> PixelRect:
    return next(item.destination for item in preferences.formatting_assets if item.asset_id == WATERMARK_REGION)


def place_figures(request: CreationRequest, preferences: ModePreferences) -> dict[str, PlacedFigure]:
    """Resolve every visible entrant's lineup inside its serialized frame.

    A doubles team's members share one shrink factor, so partners keep their
    true relative sizes even when only one of them is too large for its frame.
    """
    frames = {item.slot_id: item.destination for item in preferences.formatting_assets if item.asset_id in FRAME_ASSETS}
    teams: dict[int, list[CharacterPlacement]] = {}
    for placement in preferences.character_slots:
        teams.setdefault(placement.entrant_slot, []).append(placement)
    figures = {}
    for entrant_slot, placements in teams.items():
        result = request.entrants[entrant_slot - 1]
        lineups = place_team(
            [LineupSlot(_member_for_placement(result, placement).characters, placement.scale,
                        frames[placement.slot_id], placement.anchor.x) for placement in placements],
            team_color=result.team_color if isinstance(result, DoublesTeam) else None,
        )
        for placement, lineup in zip(placements, lineups):
            figures[placement.slot_id] = PlacedFigure(placement.slot_id, entrant_slot, placement.z_index, lineup)
    return figures


def text_vertical_extent(item: TextPlacement) -> tuple[int, int]:
    """Approximate the rows a result label covers from its Pillow anchor."""
    size = item.preferred_size or 24
    vertical = item.pillow_anchor[1]
    if vertical == "s":
        return item.anchor.y - size, item.anchor.y + size // 4
    if vertical == "m":
        return item.anchor.y - size // 2, item.anchor.y + size // 2
    if vertical == "d":
        return item.anchor.y - round(size * 1.25), item.anchor.y
    return item.anchor.y, item.anchor.y + round(size * 1.25)


def labelled_preferences(preferences: ModePreferences, figures: dict[str, PlacedFigure]) -> ModePreferences:
    """Return label anchors that follow the rendered figures for this request.

    Doubles member names sit just above each visible head. A team crest marked
    with ``BETWEEN_NAMES_SUFFIX`` is centered vertically on those names, and its
    seed moves with it. Every other result label keeps its serialized position.
    """
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


def composite_outlined_names(canvas: Image.Image, layer: Image.Image) -> None:
    """Composite names and their black outline as one unit at each name's alpha.

    The outline is the name's alpha dilated around its letters. Inside the
    letters the name fully covers its outline, so a translucent name shows the
    background at its own transparency instead of a darkening black underlay,
    and its outline ring carries that same alpha. Opaque names are unchanged.
    """
    outline_alpha = layer.getchannel("A").filter(ImageFilter.MaxFilter(NAME_OUTLINE_FILTER_SIZE))
    # Premultiplied color over the dilated alpha unpremultiplies to the name's
    # color blended with black in proportion to the letters' coverage.
    red, green, blue, _alpha = layer.convert("RGBa").split()
    canvas.alpha_composite(Image.merge("RGBa", (red, green, blue, outline_alpha)).convert("RGBA"))


def _entrant_text_style(request: CreationRequest, placement: TextPlacement) -> tuple[str, bool]:
    chosen = _explicit_entrant_color(request, placement.entrant_slot)
    if chosen is None:
        return placement.color or "#FFFFFFFF", False
    settings = request.text_settings
    index = {"pick_1": 0, "pick_2": (placement.entrant_slot - 1) % 2}.get(settings.entrant_text_color_mode, placement.entrant_slot - 1)
    return chosen, settings.entrant_text_metallic[index]


def _draw_wrapped_names(canvas: Image.Image, request: CreationRequest, placements: list[TextPlacement], font: PodiumFont) -> None:
    """Break names early at the wrap width, shrinking only past their wider run-on width.

    Extra lines stack downward from a top anchor (or upward from a bottom one)
    and follow its left or right alignment, so a long name grows away from its
    placement art.
    """
    draw = ImageDraw.Draw(canvas)
    for placement in placements:
        result = request.entrants[placement.entrant_slot - 1]
        value = _text_value(placement, result, request.text_settings.include_seeding)
        if value is None:
            continue
        size = adjusted_size(placement.preferred_size or 42,
                             result_text_adjustment(request.text_settings, result, placement.field, placement.member_slot))
        color, metallic = _entrant_text_style(request, placement)
        _draw_text(draw, (placement.anchor.x, placement.anchor.y), _wrap_text(value, NAME_WRAP_WIDTH, size, font),
                   anchor=placement.pillow_anchor, max_width=placement.max_width, preferred_size=size, font=font,
                   fill=color, metallic=metallic, align={"l": "left", "r": "right"}.get(placement.pillow_anchor[0], "center"))


def _draw_labels(canvas: Image.Image, request: CreationRequest, preferences: ModePreferences,
                 placements: list[TextPlacement], font: PodiumFont) -> None:
    """Draw result labels (never member names) with the shared black outline."""
    if not placements:
        return
    layer = Image.new("RGBA", canvas.size, "#00000000")
    _draw_result_text(layer, request, preferences, font, [item for item in placements if not item.wrap])
    _draw_wrapped_names(layer, request, [item for item in placements if item.wrap], font)
    composite_outlined_names(canvas, layer)


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
        watermark_box = flying_v_watermark_row(preferences)
        watermark_color = _watermark_color(result, watermark_box)
        with _temporary_font_settings(request.text_settings.font_size_adjustment, self.custom_font_bytes):
            figures = place_figures(request, preferences)
            labelled = labelled_preferences(preferences, figures)
            # Smaller figures stand farther back; the leader is drawn last.
            # Placement art and labels layered below a figure are drawn just before it.
            pending = sorted(labelled.placement_tags, key=lambda item: (item.z_index, item.slot_id))
            labels = [item for item in labelled.text_slots if item.field != "member.tag"]
            for figure in sorted(figures.values(), key=lambda item: (item.z_index, item.slot_id)):
                behind = [tag for tag in pending if tag.z_index < figure.z_index]
                pending = [tag for tag in pending if tag.z_index >= figure.z_index]
                draw_outlined_placement_tags(result, replace(labelled, placement_tags=tuple(behind)))
                _draw_labels(result, request, labelled, [item for item in labels if item.z_index < figure.z_index], self.font)
                labels = [item for item in labels if item.z_index >= figure.z_index]
                _composite_clipped(result, figure.lineup.image, figure.lineup.bounds.as_tuple())
            text_layer = Image.new("RGBA", result.size, "#00000000")
            _draw_result_text(text_layer, request, labelled, self.font, [item for item in labels if not item.wrap])
            _draw_wrapped_names(text_layer, request, [item for item in labels if item.wrap], self.font)
            _draw_member_names(text_layer, request, [item for item in labelled.text_slots if item.field == "member.tag"],
                               self.font, crest_clearances(labelled, request.text_settings.include_seeding))
            composite_outlined_names(result, text_layer)
            draw_outlined_placement_tags(result, replace(labelled, placement_tags=tuple(pending)))
            self._draw_header(result, request, preferences)
            _composite_watermark(
                result,
                position=(watermark_box.right, watermark_box.top + 10),
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
            # Blocks in the lower half hug the canvas bottom and grow upward rather
            # than clipping; upper blocks hang from the top of their box.
            lower = box.top + box.bottom > canvas.height
            area = PixelRect(box.left, box.top, box.right, box.top + box.height * 2) if lower else box
            layer = self.header_text_layer(request, content, area, HEADER_ANCHORS[position])
            visible = layer.getbbox()
            if visible is None:
                continue
            top = box.bottom - visible[3] if lower else box.top
            _composite_clipped(canvas, layer, (box.left, top, box.left + layer.width, top + layer.height))

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

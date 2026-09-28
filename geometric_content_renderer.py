"""Character, result text, and header rendering for Eyes and Squares modes."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from background_builder import PixelRect
from creation import CreationRequest
from creation_modes import CreationMode
from DrawPodium import (
    ATTRIBUTION_TEXT,
    PodiumFont,
    _draw_text,
    _font_to_fit,
    _temporary_font_settings,
)
from eyes_portrait_renderer import render_eye_portrait
from mode_preferences import CharacterPlacement, ModePreferences, TextPlacement
from models import Character, DoublesTeam, Entrant, SinglesEntrant, TournamentFormat
from portrait_assets import with_team_color
from square_portrait_renderer import (
    render_square_portrait_group,
    square_portrait_scale_key,
)


LogoInput = Image.Image | str | Path | None
WATERMARK_WHITE = "#FFFFFF40"
WATERMARK_BLACK = "#00000040"


def _open_logo(value: LogoInput) -> Image.Image | None:
    if value is None:
        return None
    if isinstance(value, Image.Image):
        return value.convert("RGBA")
    with Image.open(value) as source:
        return source.convert("RGBA")


def _metadata_lines(request: CreationRequest) -> list[str]:
    tournament = request.tournament
    count_label = (
        "Teams"
        if tournament.event_format is TournamentFormat.DOUBLES
        else "Entrants"
    )
    values: Mapping[str, Any] = {
        "event": tournament.event,
        "date": tournament.date,
        "entrants_count": f"{tournament.entrants_count} {count_label}",
        "tournament_link": tournament.link,
        "tournament_location": tournament.location,
        "stream_link": tournament.stream_link,
        "vod_link": tournament.vod_link,
        "to_x_account": tournament.organizer_x_account,
        "to_twitch_account": tournament.organizer_twitch_account,
        "to_bluesky_account": tournament.organizer_bluesky_account,
    }
    return [
        str(values[field])
        for field in request.text_settings.metadata_fields
        if values[field] is not None
    ]


def _entrant_for_slot(request: CreationRequest, one_based_slot: int) -> SinglesEntrant | DoublesTeam:
    return request.entrants[one_based_slot - 1]


def _member_for_placement(
    result: SinglesEntrant | DoublesTeam,
    placement: CharacterPlacement,
) -> Entrant:
    if isinstance(result, SinglesEntrant):
        return result
    if placement.member_slot == 1:
        return result.entrant_1
    if placement.member_slot == 2:
        return result.entrant_2
    raise ValueError("Doubles character placements require member_slot 1 or 2")


def _primary_character(result: SinglesEntrant | DoublesTeam, placement: CharacterPlacement) -> Character:
    member = _member_for_placement(result, placement)
    character = member.characters[0]
    if isinstance(result, DoublesTeam):
        return with_team_color(character, result.team_color)
    return character


def _card_rectangles(preferences: ModePreferences) -> dict[int, PixelRect]:
    cards: dict[int, PixelRect] = {}
    for placement in preferences.formatting_assets:
        if placement.asset_id not in {"eyes_rectangle", "square_card"}:
            continue
        try:
            slot = int(placement.slot_id.rsplit("_", 1)[1])
        except (IndexError, ValueError) as error:
            raise ValueError(
                f"Card slot must end in a one-based number: {placement.slot_id}"
            ) from error
        cards[slot] = placement.destination
    return cards


def _text_value(
    placement: TextPlacement,
    result: SinglesEntrant | DoublesTeam,
    include_seeding: bool,
) -> str | None:
    def identity_part(tag: str, *, sponsor: bool) -> str | None:
        parts = [part.strip() for part in tag.split("|")]
        if len(parts) == 1:
            return None if sponsor else parts[0]
        return " | ".join(parts[:-1]) if sponsor else parts[-1]

    if placement.field == "entrant.placement":
        return str(result.placement)
    if placement.field == "entrant.seed":
        return f"{result.seed}s" if include_seeding and result.seed is not None else None
    if placement.field == "entrant.team_name":
        return result.team_name if isinstance(result, DoublesTeam) else None
    if placement.field == "entrant.tag":
        return result.tag if isinstance(result, SinglesEntrant) else None
    if placement.field == "entrant.sponsor":
        return identity_part(result.tag, sponsor=True) if isinstance(result, SinglesEntrant) else None
    if placement.field == "entrant.player_tag":
        return identity_part(result.tag, sponsor=False) if isinstance(result, SinglesEntrant) else None
    if placement.field == "member.tag" and isinstance(result, DoublesTeam):
        if placement.member_slot == 1:
            return result.entrant_1.tag
        if placement.member_slot == 2:
            return result.entrant_2.tag
    if placement.field in {"member.sponsor", "member.player_tag"} and isinstance(result, DoublesTeam):
        member = result.entrant_1 if placement.member_slot == 1 else result.entrant_2
        return identity_part(member.tag, sponsor=placement.field == "member.sponsor")
    raise ValueError(f"Unknown geometric text field: {placement.field}")


def _explicit_entrant_color(request: CreationRequest, one_based_slot: int) -> str | None:
    settings = request.text_settings
    if settings.entrant_text_color_mode == "match_podium":
        return None
    colors = settings.entrant_text_colors
    if settings.entrant_text_color_mode == "pick_1":
        return colors[0]
    if settings.entrant_text_color_mode == "pick_2":
        return colors[(one_based_slot - 1) % 2]
    return colors[one_based_slot - 1]


def _draw_result_text(
    canvas: Image.Image,
    request: CreationRequest,
    preferences: ModePreferences,
    font: PodiumFont,
    placements: Iterable[TextPlacement] | None = None,
) -> None:
    draw = ImageDraw.Draw(canvas)
    for placement in sorted(
        preferences.text_slots if placements is None else placements,
        key=lambda item: (item.z_index, item.slot_id),
    ):
        if placement.entrant_slot is None:
            continue
        result = _entrant_for_slot(request, placement.entrant_slot)
        value = _text_value(
            placement,
            result,
            request.text_settings.include_seeding,
        )
        if value is None:
            continue
        chosen_color = _explicit_entrant_color(request, placement.entrant_slot)
        fill = chosen_color or placement.color or "#FFFFFFFF"
        metallic = False
        if chosen_color is not None:
            settings = request.text_settings
            color_index = (
                0
                if settings.entrant_text_color_mode == "pick_1"
                else (placement.entrant_slot - 1) % 2
                if settings.entrant_text_color_mode == "pick_2"
                else placement.entrant_slot - 1
            )
            metallic = settings.entrant_text_metallic[color_index]
        _draw_text(
            draw,
            (placement.anchor.x, placement.anchor.y),
            value,
            anchor=placement.pillow_anchor,
            max_width=placement.max_width,
            preferred_size=placement.preferred_size or 42,
            wrap=placement.wrap,
            font=font,
            fill=fill,
            metallic=metallic,
        )


def _draw_logo_in_box(canvas: Image.Image, logo: Image.Image | None, box: PixelRect) -> None:
    if logo is None:
        return
    layer = logo.copy()
    layer.thumbnail((box.width, box.height), Image.Resampling.LANCZOS)
    canvas.alpha_composite(
        layer,
        (
            box.left + (box.width - layer.width) // 2,
            box.top + (box.height - layer.height) // 2,
        ),
    )


def _watermark_color(canvas: Image.Image, sample_box: PixelRect) -> str:
    """Choose a translucent black or white watermark from local brightness."""

    region = canvas.crop(sample_box.as_tuple()).convert("RGBA")
    if region.width <= 0 or region.height <= 0:
        return WATERMARK_WHITE
    luminance_total = 0.0
    pixel_count = region.width * region.height
    for red, green, blue, alpha in region.getdata():
        # Transparent pixels contribute as dark because there is no dependable
        # backing color to make black readable after export.
        luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
        luminance_total += luminance * alpha / 255
    return WATERMARK_BLACK if luminance_total / pixel_count >= 0.55 else WATERMARK_WHITE


def _composite_watermark(
    canvas: Image.Image,
    *,
    position: tuple[int, int],
    anchor: str,
    max_width: int,
    font: PodiumFont,
    fill: str,
) -> None:
    """Blend translucent watermark text instead of replacing canvas pixels."""

    layer = Image.new("RGBA", canvas.size, "#00000000")
    _draw_text(
        ImageDraw.Draw(layer),
        position,
        ATTRIBUTION_TEXT,
        anchor=anchor,
        max_width=max_width,
        preferred_size=20,
        font=font,
        fill=fill,
    )
    canvas.alpha_composite(layer)


def _draw_horizontal_header_item(
    canvas: Image.Image,
    request: CreationRequest,
    content: str,
    box: PixelRect,
    font: PodiumFont,
    logo: Image.Image | None,
    anchor: str,
    title_preferred_size: int = 58,
) -> None:
    if content == "tournament_logo":
        _draw_logo_in_box(canvas, logo, box)
        return
    lines = (
        [request.tournament.title]
        + ([request.tournament.subtitle] if request.tournament.subtitle else [])
        if content == "tournament_title"
        else _metadata_lines(request)
    )
    if not lines:
        return
    text = "\n".join(lines)
    draw_anchor = {"ls": "la", "rs": "ra"}.get(anchor, anchor)
    x = box.left if draw_anchor == "la" else box.right if draw_anchor == "ra" else (box.left + box.right) // 2
    y = box.top
    _draw_text(
        ImageDraw.Draw(canvas),
        (x, y),
        text,
        anchor=draw_anchor,
        max_width=box.width,
        preferred_size=title_preferred_size if content == "tournament_title" else 26,
        wrap=False,
        font=font,
        fill=request.text_settings.heading_color,
        metallic=request.text_settings.heading_metallic,
        align="left" if draw_anchor.startswith("l") else "right" if draw_anchor.startswith("r") else "center",
    )


def _render_rotated_header_item(
    request: CreationRequest,
    content: str,
    box: PixelRect,
    font: PodiumFont,
    logo: Image.Image | None,
) -> Image.Image:
    # Draw horizontally into the inverse dimensions, then rotate clockwise so
    # all three selections read along the Eyes mode's right rail.
    horizontal = Image.new("RGBA", (box.height - 16, box.width - 16), "#00000000")
    inner = PixelRect(4, 4, horizontal.width - 4, horizontal.height - 4)
    if content == "tournament_logo":
        _draw_logo_in_box(horizontal, logo, inner)
    else:
        lines = (
            [request.tournament.title]
            + ([request.tournament.subtitle] if request.tournament.subtitle else [])
            if content == "tournament_title"
            else _metadata_lines(request)
        )
        if lines:
            text = "\n".join(lines)
            draw = ImageDraw.Draw(horizontal)
            preferred = 58 if content == "tournament_title" else 27
            loaded = _font_to_fit(text, inner.width, preferred, font)
            bounds = draw.multiline_textbbox(
                (0, 0),
                text,
                font=loaded,
                spacing=5,
                align="center",
            )
            x = horizontal.width // 2
            y = (horizontal.height - (bounds[3] - bounds[1])) // 2 - bounds[1]
            draw.multiline_text(
                (x, y),
                text,
                font=loaded,
                anchor="ma",
                align="center",
                spacing=5,
                fill=request.text_settings.heading_color,
                stroke_width=2,
                stroke_fill="#000000A0",
            )
    return horizontal.transpose(Image.Transpose.ROTATE_270)


@dataclass(frozen=True, slots=True)
class EyesContentRenderer:
    font: PodiumFont = PodiumFont.TYROWO
    tournament_logo: LogoInput = None
    custom_font_bytes: bytes | None = None

    def draw(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        preferences: ModePreferences,
    ) -> Image.Image:
        if request.selection.mode is not CreationMode.EYES:
            raise ValueError("EyesContentRenderer requires Eyes mode")
        result = canvas.convert("RGBA")
        watermark_box = PixelRect(20, result.height - 50, result.width * 2 // 3, result.height)
        watermark_color = _watermark_color(result, watermark_box)
        with _temporary_font_settings(
            request.text_settings.font_size_adjustment,
            self.custom_font_bytes,
        ):
            cards = _card_rectangles(preferences)
            for placement in sorted(
                preferences.character_slots,
                key=lambda item: (item.z_index, item.slot_id),
            ):
                self._draw_character(result, request, placement, cards)
            _draw_result_text(result, request, preferences, self.font)
            self._draw_header(result, request, preferences)
            _composite_watermark(
                result,
                position=(20, result.height - 12),
                anchor="ls",
                max_width=watermark_box.width,
                font=self.font,
                fill=watermark_color,
            )
        return result

    @staticmethod
    def _draw_character(
        canvas: Image.Image,
        request: CreationRequest,
        placement: CharacterPlacement,
        cards: Mapping[int, PixelRect],
    ) -> None:
        card = cards[placement.entrant_slot]
        number_width = max(
            160 if request.selection.options.event_format is TournamentFormat.SINGLES else 100,
            round(
                card.width
                * (
                    0.22
                    if request.selection.options.event_format is TournamentFormat.SINGLES
                    else 0.16
                )
            ),
        )
        portrait_area = PixelRect(
            card.left + 8,
            card.top + 5,
            card.right - number_width,
            card.bottom - 5,
        )
        if request.selection.options.event_format is TournamentFormat.DOUBLES:
            top_band = max(76, round(card.height * 0.22))
            bottom_band = max(74, round(card.height * 0.20))
            portrait_area = PixelRect(
                portrait_area.left,
                card.top + top_band,
                portrait_area.right,
                card.bottom - bottom_band,
            )
            midpoint = (portrait_area.left + portrait_area.right) // 2
            portrait_area = (
                PixelRect(portrait_area.left, portrait_area.top, midpoint, portrait_area.bottom)
                if placement.member_slot == 1
                else PixelRect(midpoint, portrait_area.top, portrait_area.right, portrait_area.bottom)
            )
        result = _entrant_for_slot(request, placement.entrant_slot)
        character = _primary_character(result, placement)
        viewport = render_eye_portrait(
            character,
            (portrait_area.width, portrait_area.height),
            zoom_multiplier=placement.scale,
            doubles=(
                request.selection.options.event_format
                is TournamentFormat.DOUBLES
            ),
        )
        canvas.alpha_composite(viewport, (portrait_area.left, portrait_area.top))

    def _draw_header(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        preferences: ModePreferences,
    ) -> None:
        bar = next(
            item.destination
            for item in preferences.formatting_assets
            if item.asset_id == "eyes_header_bar"
        )
        layout = request.header_layout or {
            "top": "tournament_logo",
            "middle": "tournament_title",
            "bottom": "metadata",
        }
        logo = _open_logo(self.tournament_logo)
        if bar.width > bar.height:
            gap = 24
            section_width = (bar.width - gap * 2) // 3
            for index, position in enumerate(("top", "middle", "bottom")):
                content = layout.get(position)
                if content is None:
                    continue
                left = bar.left + index * (section_width + gap)
                right = bar.right if index == 2 else left + section_width
                _draw_horizontal_header_item(
                    canvas,
                    request,
                    content,
                    PixelRect(left, bar.top, right, bar.bottom),
                    self.font,
                    logo,
                    ("la", "ma", "ra")[index],
                    title_preferred_size=64,
                )
            return
        section_height = bar.height // 3
        for index, position in enumerate(("top", "middle", "bottom")):
            content = layout[position]
            if content is None:
                continue
            box = PixelRect(
                bar.left + 8,
                bar.top + index * section_height + 8,
                bar.right - 8,
                bar.top + (index + 1) * section_height - 8,
            )
            layer = _render_rotated_header_item(
                request,
                content,
                box,
                self.font,
                logo,
            )
            canvas.alpha_composite(
                layer,
                (
                    box.left + (box.width - layer.width) // 2,
                    box.top + (box.height - layer.height) // 2,
                ),
            )

@dataclass(frozen=True, slots=True)
class SquaresContentRenderer:
    font: PodiumFont = PodiumFont.TYROWO
    tournament_logo: LogoInput = None
    custom_font_bytes: bytes | None = None

    def draw(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        preferences: ModePreferences,
    ) -> Image.Image:
        if request.selection.mode is not CreationMode.SQUARES:
            raise ValueError("SquaresContentRenderer requires Squares mode")
        result = canvas.convert("RGBA")
        watermark_box = PixelRect(result.width // 2, 0, result.width - 40, 45)
        watermark_color = _watermark_color(result, watermark_box)
        with _temporary_font_settings(
            request.text_settings.font_size_adjustment,
            self.custom_font_bytes,
        ):
            cards = _card_rectangles(preferences)
            first_character_z = min(
                (placement.z_index for placement in preferences.character_slots),
                default=0,
            )
            background_text = tuple(
                placement
                for placement in preferences.text_slots
                if placement.z_index < first_character_z
            )
            foreground_text = tuple(
                placement
                for placement in preferences.text_slots
                if placement.z_index >= first_character_z
            )
            _draw_result_text(
                result,
                request,
                preferences,
                self.font,
                background_text,
            )
            for placement in sorted(
                preferences.character_slots,
                key=lambda item: (item.z_index, item.slot_id),
            ):
                self._draw_character(result, request, preferences, placement, cards)
            _draw_result_text(
                result,
                request,
                preferences,
                self.font,
                foreground_text,
            )
            self._draw_header(result, request, preferences)
            _composite_watermark(
                result,
                position=(result.width - 40, 8),
                anchor="ra",
                max_width=watermark_box.width,
                font=self.font,
                fill=watermark_color,
            )
        return result

    @staticmethod
    def _draw_character(
        canvas: Image.Image,
        request: CreationRequest,
        preferences: ModePreferences,
        placement: CharacterPlacement,
        cards: Mapping[int, PixelRect],
    ) -> None:
        card = cards[placement.entrant_slot]
        inset = max(8, round(min(card.width, card.height) * 0.025))
        footer_height = max(62, round(card.height * 0.17))
        content = PixelRect(
            card.left + inset,
            card.top + inset,
            card.right - inset,
            card.bottom - footer_height,
        )
        if request.selection.options.event_format is TournamentFormat.DOUBLES:
            midpoint = (content.left + content.right) // 2
            # Let each teammate's clipped viewport reach slightly through the
            # card center. This shifts both lineups inward and gives their
            # center/left/right portrait stagger more breathing room.
            center_overlap = round(content.width * 0.06)
            content = (
                PixelRect(
                    content.left,
                    content.top,
                    midpoint + center_overlap,
                    content.bottom,
                )
                if placement.member_slot == 1
                else PixelRect(
                    midpoint - center_overlap,
                    content.top,
                    content.right,
                    content.bottom,
                )
            )
        result = _entrant_for_slot(request, placement.entrant_slot)
        member = _member_for_placement(result, placement)
        scale_key = square_portrait_scale_key(
            preferences.selection.options.event_format,
            preferences.selection.options.entrant_count,
            placement.entrant_slot,
        )
        viewport = render_square_portrait_group(
            member.characters,
            (content.width, content.height),
            scale_key=scale_key,
            scale_multiplier=placement.scale,
            team_color=result.team_color if isinstance(result, DoublesTeam) else None,
        )
        canvas.alpha_composite(viewport, (content.left, content.top))

    def _draw_header(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        preferences: ModePreferences,
    ) -> None:
        layout = request.header_layout or {
            "top_left": "tournament_title",
            "top_middle": "tournament_logo",
            "top_right": "metadata",
        }
        logo = _open_logo(self.tournament_logo)
        boxes = _squares_header_boxes(canvas, preferences)
        for position, content in layout.items():
            if content is None:
                continue
            box, anchor = boxes[position]
            _draw_horizontal_header_item(
                canvas,
                request,
                content,
                box,
                self.font,
                logo,
                anchor,
                title_preferred_size=(
                    72
                    if request.selection.options.event_format is TournamentFormat.DOUBLES
                    else 58
                ),
            )

def _squares_header_boxes(
    canvas: Image.Image,
    preferences: ModePreferences,
) -> dict[str, tuple[PixelRect, str]]:
    """Return three bottom header regions using the Podium assignment keys."""

    cards = _card_rectangles(preferences)
    if not cards:
        raise ValueError("Squares layouts require at least one card")
    left = min(card.left for card in cards.values())
    top = max(card.bottom for card in cards.values()) + 18
    right = max(card.right for card in cards.values())
    bottom = canvas.height - 10
    gap = 24
    available_width = right - left - gap * 2
    if preferences.selection.options.event_format is TournamentFormat.DOUBLES:
        # The logo needs less horizontal space than two lines of title or a
        # metadata list.  Wider outer sections also let the deliberately larger
        # Doubles title remain visibly larger instead of width-fitting back to
        # the Singles size.
        side_width = round(available_width * 0.4)
        middle_width = available_width - side_width * 2
    else:
        side_width = available_width // 3
        middle_width = available_width - side_width * 2
    middle_left = left + side_width + gap
    right_left = middle_left + middle_width + gap
    return {
        "top_left": (
            PixelRect(left, top, left + side_width, bottom),
            "la",
        ),
        "top_middle": (
            PixelRect(middle_left, top, middle_left + middle_width, bottom),
            "ma",
        ),
        "top_right": (
            PixelRect(right_left, top, right, bottom),
            "ra",
        ),
    }

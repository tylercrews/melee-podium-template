"""Content-stage adapter for layouts extracted from the legacy podium renderer.

This keeps the new creation coordinator independent from ``DrawPodium`` while
the legacy character and typography helpers are decomposed into new modules.
Layout geometry comes from ``ModePreferences``. Both podium styles can share
these drawing helpers because each preference file supplies independent
character and text anchors.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from pathlib import Path
from random import choice
from urllib.parse import urlsplit

from PIL import Image, ImageDraw

from constants import PODIUM_BOX_COLORS_BY_SLOT
from creation import CreationRequest
from creation_modes import CreationMode, PodiumStyle
from DrawPodium import (
    ATTRIBUTION_PREFERRED_SIZE,
    ATTRIBUTION_SIDE_MARGIN,
    ATTRIBUTION_TEXT,
    DOUBLES_TAG_WIDTHS,
    FOUR_PODIUM_SPONSOR_PREFERRED_SIZE,
    FOUR_PODIUM_TAG_MAX_WIDTH,
    FOUR_PODIUM_TAG_PREFERRED_SIZE,
    MULTI_CHARACTER_X_OFFSETS_NARROW,
    MULTI_CHARACTER_X_OFFSETS_WIDE,
    SINGLES_TAG_WIDTHS,
    SPONSOR_PREFERRED_SIZE,
    TAG_PREFERRED_SIZE,
    CharacterTag,
    PodiumFont,
    PodiumMode,
    _attribution_layout,
    _centered_header_fields,
    _character_with_team_color,
    _draw_character_tag,
    _draw_lower_entrant_summary,
    _draw_text,
    _draw_tournament_subtitle,
    _font_to_fit,
    _metadata_layout,
    _place_characters,
    _resolve_doubles_tag_collisions,
    _tag_anchor,
    _temporary_font_settings,
    _validate_placements,
    _wrap_url,
)
from mode_preferences import CharacterPlacement, ModePreferences, TextPlacement
from models import DoublesTeam, SinglesEntrant, TournamentFormat
from podium_colors import podium_color_for_slot


WEBSITE_ICON_FOLDER = Path(__file__).resolve().parent / "formatting_assets" / "website_icons"
WEBSITE_HOST_ICONS = {
    "start.gg": "startgg.png",
    "youtube.com": "youtube.png",
    "youtu.be": "youtube.png",
    "x.com": "x.png",
    "twitter.com": "x.png",
    "bsky.app": "bluesky.png",
    "bluesky.com": "bluesky.png",
    "parry.gg": "parrygg.png",
    "challonge.com": "challonge.png",
    "challonge.gg": "challonge.png",
    "twitch.tv": "twitch.png",
    "twitch.com": "twitch.png",
}

UNDER_PODIUM_FIELDS = frozenset(
    {"entrant.primary_character_name", "entrant.team_name"}
)


def _under_podium_vertical_center_lines(field: str, mode: PodiumMode) -> int | None:
    """Return the reserved label rows, excluding the calibrated four-podium layout."""

    if mode is PodiumMode.SINGLES_TOP_8_FOUR_PODIUM:
        return None
    return 2 if field in UNDER_PODIUM_FIELDS else None


def _header_geometry(position: str, width: int) -> tuple[tuple[int, int], str, int, str]:
    """Return the x anchor, Pillow anchor, width, and alignment for a header slot."""

    max_width = max(1, width // 3 - 30)
    if position == "top_left":
        return ((15, 0), "la", max_width, "left")
    if position == "top_middle":
        return ((width // 2, 0), "ma", max_width, "center")
    if position == "top_right":
        return ((width - 15, 0), "ra", max_width, "right")
    raise ValueError(f"Unknown header position: {position}")


def _website_icon_and_remainder(value: str) -> tuple[Path, str] | None:
    candidate = value.strip()
    parsed = urlsplit(candidate if "://" in candidate else f"https://{candidate}")
    host = (parsed.hostname or "").casefold().removeprefix("www.")
    filename = WEBSITE_HOST_ICONS.get(host)
    if filename is None:
        return None
    remainder = parsed.path.strip("/")
    if parsed.query:
        remainder = f"{remainder}?{parsed.query}" if remainder else f"?{parsed.query}"
    return WEBSITE_ICON_FOLDER / filename, remainder


def _wrap_website_remainder(
    remainder: str,
    max_width: int,
    preferred_size: int,
    font: PodiumFont,
) -> str:
    """Wrap an icon link's path without shrinking the whole URL to one line."""

    return _wrap_url(remainder, max_width, max_width, preferred_size, font)


@dataclass(frozen=True, slots=True)
class LegacyPodiumContentRenderer:
    """Draw podium portraits and text using serialized layout preferences."""

    font: PodiumFont = PodiumFont.TYROWO
    custom_font_bytes: bytes | None = None

    def draw(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        preferences: ModePreferences,
    ) -> Image.Image:
        with _temporary_font_settings(
            request.text_settings.font_size_adjustment,
            self.custom_font_bytes,
        ):
            return self._draw_with_font(canvas, request, preferences)

    def _draw_with_font(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        preferences: ModePreferences,
    ) -> Image.Image:
        selection = request.selection
        if selection.mode is not CreationMode.PODIUM:
            raise ValueError("LegacyPodiumContentRenderer requires podium mode")

        mode = PodiumMode(selection.submode_id)
        _validate_placements(request.entrants, selection.options.entrant_count)
        result = canvas.convert("RGBA")
        is_doubles = selection.options.event_format is TournamentFormat.DOUBLES
        assigned_header = request.header_layout is not None
        center_title, center_subtitle = (
            _centered_header_fields(
                result,
                request.tournament,
                font=self.font,
                is_doubles=is_doubles,
            )
            if mode.layout_count != 3 and not assigned_header
            else (False, False)
        )

        if assigned_header:
            self._draw_assigned_subtitle(result, request)
        else:
            _draw_tournament_subtitle(
                result,
                request.tournament,
                self.font,
                mode.layout_count,
                center_subtitle,
                request.text_settings.heading_color,
                request.text_settings.heading_metallic,
            )
        if is_doubles:
            self._draw_doubles(result, request, preferences, mode)
        else:
            self._draw_singles(result, request, preferences, mode)
        self._draw_preference_text(result, request, preferences, mode)
        if assigned_header:
            self._draw_assigned_tournament_text(result, request, mode)
        else:
            self._draw_tournament_text(result, request, mode, center_title)
        return result

    def _draw_assigned_subtitle(
        self,
        canvas: Image.Image,
        request: CreationRequest,
    ) -> None:
        if request.tournament.subtitle is None or request.header_layout is None:
            return
        position = next(
            slot for slot, content in request.header_layout.items()
            if content == "tournament_title"
        )
        (x, _), anchor, max_width, align = _header_geometry(position, canvas.width)
        _draw_text(
            ImageDraw.Draw(canvas),
            (x, 110),
            request.tournament.subtitle,
            anchor=anchor,
            max_width=max_width,
            preferred_size=48,
            font=self.font,
            align=align,
            fill=request.text_settings.heading_color,
            metallic=request.text_settings.heading_metallic,
        )

    def _draw_singles(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        preferences: ModePreferences,
        mode: PodiumMode,
    ) -> None:
        placements = sorted(
            preferences.character_slots,
            key=lambda placement: (placement.z_index, placement.slot_id),
        )
        draw = ImageDraw.Draw(canvas)
        four_podium_top_8 = mode is PodiumMode.SINGLES_TOP_8_FOUR_PODIUM
        tag_max_width = (
            FOUR_PODIUM_TAG_MAX_WIDTH
            if four_podium_top_8
            else SINGLES_TAG_WIDTHS[mode.layout_count]
        )
        offsets = (
            MULTI_CHARACTER_X_OFFSETS_NARROW
            if mode.layout_count == 8
            else MULTI_CHARACTER_X_OFFSETS_WIDE
        )

        for placement in placements:
            entrant = request.entrants[placement.entrant_slot - 1]
            assert isinstance(entrant, SinglesEntrant)
            anchor = (placement.anchor.x, placement.anchor.y)
            x, y, portrait = _place_characters(
                canvas,
                entrant.characters,
                anchor,
                placement.scale,
                multi_character_x_offsets=offsets,
            )
            text_color, text_metallic = self._default_text_style(request, placement.entrant_slot)
            tag = CharacterTag(
                _tag_anchor(x, y, portrait, center_x=anchor[0]),
                entrant.tag,
                text_color,
                tag_max_width,
                FOUR_PODIUM_TAG_PREFERRED_SIZE
                if four_podium_top_8
                else TAG_PREFERRED_SIZE,
                FOUR_PODIUM_SPONSOR_PREFERRED_SIZE
                if four_podium_top_8
                else SPONSOR_PREFERRED_SIZE,
                text_metallic,
            )
            _draw_character_tag(draw, tag, self.font)

    def _draw_doubles(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        preferences: ModePreferences,
        mode: PodiumMode,
    ) -> None:
        grouped: dict[int, list[CharacterPlacement]] = {}
        for placement in preferences.character_slots:
            grouped.setdefault(placement.entrant_slot, []).append(placement)
        ordered = sorted(
            grouped.items(),
            key=lambda item: (
                min(placement.z_index for placement in item[1]),
                item[0],
            ),
        )
        draw = ImageDraw.Draw(canvas)

        for entrant_slot, placements in ordered:
            team = request.entrants[entrant_slot - 1]
            assert isinstance(team, DoublesTeam)
            placements.sort(key=lambda placement: placement.member_slot or 0)
            team_color = (
                choice(["red", "green", "blue"])
                if team.team_color == "random"
                else team.team_color
            )
            members = (team.entrant_1, team.entrant_2)
            tags: list[CharacterTag] = []
            for placement, member in zip(placements, members, strict=True):
                characters = [
                    _character_with_team_color(character, team_color)
                    for character in member.characters
                ]
                anchor = (placement.anchor.x, placement.anchor.y)
                x, y, portrait = _place_characters(
                    canvas,
                    characters,
                    anchor,
                    placement.scale,
                    multi_character_x_offsets=MULTI_CHARACTER_X_OFFSETS_NARROW,
                )
                text_color, text_metallic = self._default_text_style(request, entrant_slot)
                tags.append(
                    CharacterTag(
                        _tag_anchor(x, y, portrait, center_x=anchor[0]),
                        member.tag,
                        text_color,
                        DOUBLES_TAG_WIDTHS[mode.layout_count],
                        metallic=text_metallic,
                    )
                )
            for tag in _resolve_doubles_tag_collisions(
                draw,
                tags,
                self.font,
                canvas.width,
            ):
                _draw_character_tag(draw, tag, self.font)

    def _draw_preference_text(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        preferences: ModePreferences,
        mode: PodiumMode,
    ) -> None:
        draw = ImageDraw.Draw(canvas)
        for placement in sorted(
            preferences.text_slots,
            key=lambda item: (item.z_index, item.slot_id),
        ):
            entrant = (
                request.entrants[placement.entrant_slot - 1]
                if placement.entrant_slot is not None
                else None
            )
            if placement.field == "entrant.summary":
                assert isinstance(entrant, SinglesEntrant)
                text_color, text_metallic = self._default_text_style(request, placement.entrant_slot)
                _draw_lower_entrant_summary(
                    canvas,
                    entrant,
                    anchor=(placement.anchor.x, placement.anchor.y),
                    fill=placement.color or text_color,
                    font=self.font,
                    include_seed=request.text_settings.include_seeding,
                    metallic=False if placement.color else text_metallic,
                )
                continue

            if placement.field == "entrant.seed" and not request.text_settings.include_seeding:
                continue

            text = self._text_value(placement, entrant)
            if text is None:
                continue
            default_color, default_metallic = self._default_text_style(request, placement.entrant_slot or 1)
            color = placement.color or default_color
            _draw_text(
                draw,
                (placement.anchor.x, placement.anchor.y),
                text,
                anchor=placement.pillow_anchor,
                max_width=placement.max_width,
                preferred_size=placement.preferred_size or 24,
                font=self.font,
                wrap=placement.wrap,
                fill=color,
                glow_fill=(
                    color
                    if placement.field
                    in {"entrant.primary_character_name", "entrant.team_name"}
                    else None
                ),
                metallic=False if placement.color else default_metallic,
                vertical_center_lines=_under_podium_vertical_center_lines(
                    placement.field, mode
                ),
            )

    @staticmethod
    def _default_text_style(
        request: CreationRequest,
        entrant_slot: int,
    ) -> tuple[tuple[int, int, int] | str, bool]:
        settings = request.text_settings
        if settings.entrant_text_color_mode == "pick_1":
            return settings.entrant_text_colors[0], settings.entrant_text_metallic[0]
        if settings.entrant_text_color_mode == "pick_2":
            index = (entrant_slot - 1) % 2
            return settings.entrant_text_colors[index], settings.entrant_text_metallic[index]
        if settings.entrant_text_color_mode == "pick_all":
            return settings.entrant_text_colors[entrant_slot - 1], settings.entrant_text_metallic[entrant_slot - 1]
        if request.selection.options.podium_style is PodiumStyle.LEGACY:
            return PODIUM_BOX_COLORS_BY_SLOT[entrant_slot - 1].exterior_line, False
        assert request.podium_colors is not None
        podium_color = podium_color_for_slot(
            request.podium_colors, entrant_slot
        ).resolve()
        return podium_color.text_color, podium_color.metallic

    @staticmethod
    def _text_value(
        placement: TextPlacement,
        entrant: SinglesEntrant | DoublesTeam | None,
    ) -> str | None:
        if placement.field == "entrant.primary_character_name":
            assert isinstance(entrant, SinglesEntrant)
            return entrant.characters[0].melee_fighter_name
        if placement.field == "entrant.team_name":
            assert isinstance(entrant, DoublesTeam)
            return entrant.team_name
        if placement.field == "entrant.seed":
            assert entrant is not None
            return None if entrant.seed is None else f"{entrant.seed}s"
        raise ValueError(f"Unsupported legacy text field: {placement.field}")

    def _draw_assigned_tournament_text(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        mode: PodiumMode,
    ) -> None:
        assert request.header_layout is not None
        draw = ImageDraw.Draw(canvas)
        draw_text = partial(_draw_text, font=self.font)
        width = canvas.width
        title_position = next(
            slot for slot, content in request.header_layout.items()
            if content == "tournament_title"
        )
        (title_x, _), title_anchor, title_width, title_align = _header_geometry(
            title_position, width
        )
        draw_text(
            draw,
            (title_x, 5),
            request.tournament.title,
            anchor=title_anchor,
            max_width=title_width,
            preferred_size=72,
            align=title_align,
            fill=request.text_settings.heading_color,
            metallic=request.text_settings.heading_metallic,
        )

        metadata_position = next(
            slot for slot, content in request.header_layout.items()
            if content == "metadata"
        )
        (metadata_x, _), metadata_anchor, metadata_width, metadata_align = (
            _header_geometry(metadata_position, width)
        )
        metadata_rows = self._metadata_items(request)
        y = 3
        for row in metadata_rows:
            if len(row) > 1:
                y += self._draw_joined_metadata_row(
                    canvas,
                    request,
                    row,
                    x=metadata_x,
                    y=y,
                    anchor=metadata_anchor,
                    max_width=metadata_width,
                )
                continue
            text, preferred_size = row[0]
            icon = _website_icon_and_remainder(text) if request.text_settings.replace_base_urls_with_icons else None
            if icon is None:
                draw_text(draw, (metadata_x, y), text, anchor=metadata_anchor, max_width=metadata_width, preferred_size=preferred_size, align=metadata_align, fill=request.text_settings.heading_color, metallic=request.text_settings.heading_metallic)
            else:
                icon_path, remainder = icon
                with Image.open(icon_path) as source:
                    website_icon = source.convert("RGBA")
                    website_icon.thumbnail((32, 32), Image.Resampling.LANCZOS)
                remainder_width = 0
                row_height = website_icon.height
                if remainder:
                    remainder_max_width = metadata_width - website_icon.width - 7
                    remainder = _wrap_website_remainder(
                        remainder,
                        remainder_max_width,
                        preferred_size,
                        self.font,
                    )
                    remainder_font = _font_to_fit(
                        remainder,
                        remainder_max_width,
                        preferred_size,
                        self.font,
                    )
                    remainder_width = round(max(
                        remainder_font.getlength(line)
                        for line in remainder.splitlines()
                    ))
                    line_bounds = remainder_font.getbbox("Ag")
                    line_height = line_bounds[3] - line_bounds[1] + 4
                    row_height = max(
                        row_height,
                        line_height * len(remainder.splitlines()),
                    )
                row_width = website_icon.width + (7 + remainder_width if remainder else 0)
                row_left = (
                    metadata_x
                    if metadata_position == "top_left"
                    else metadata_x - row_width / 2
                    if metadata_position == "top_middle"
                    else metadata_x - row_width
                )
                canvas.alpha_composite(website_icon, (round(row_left), y))
                if remainder:
                    draw_text(draw, (round(row_left) + website_icon.width + 7, y), remainder, anchor="la", max_width=remainder_max_width, preferred_size=preferred_size, align="left", fill=request.text_settings.heading_color, metallic=request.text_settings.heading_metallic)
                y += max(27, row_height + 7)
                continue
            y += max(27, preferred_size + 7)
        self._draw_attribution(canvas, request, mode)

    def _draw_joined_metadata_row(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        row: list[tuple[str, int]],
        *,
        x: int,
        y: int,
        anchor: str,
        max_width: int,
    ) -> int:
        """Draw one compact metadata row while retaining supported URL icons."""

        pieces: list[tuple[Image.Image | None, str]] = []
        for text, _preferred_size in row:
            icon = (
                _website_icon_and_remainder(text)
                if request.text_settings.replace_base_urls_with_icons
                else None
            )
            if icon is None:
                pieces.append((None, text))
                continue
            icon_path, remainder = icon
            with Image.open(icon_path) as source:
                pieces.append((source.convert("RGBA"), remainder))

        preferred_size = min(item[1] for item in row)
        icon_space = sum(39 for icon, remainder in pieces if icon is not None and remainder)
        icon_space += sum(32 for icon, remainder in pieces if icon is not None and not remainder)
        measurement = " • ".join(text for _icon, text in pieces)
        loaded = _font_to_fit(
            measurement or "•",
            max(1, max_width - icon_space),
            preferred_size,
            self.font,
        )
        separator_width = round(loaded.getlength(" • "))
        piece_widths = [
            (32 if icon is not None else 0)
            + (7 if icon is not None and text else 0)
            + round(loaded.getlength(text))
            for icon, text in pieces
        ]
        row_width = sum(piece_widths) + separator_width * (len(pieces) - 1)
        left = x if anchor.startswith("l") else x - row_width // 2 if anchor.startswith("m") else x - row_width
        bounds = loaded.getbbox("Ag")
        text_height = bounds[3] - bounds[1]
        row_height = max(32 if any(icon is not None for icon, _text in pieces) else 0, text_height)
        cursor = left
        draw = ImageDraw.Draw(canvas)
        for index, ((icon, text), piece_width) in enumerate(zip(pieces, piece_widths, strict=True)):
            if icon is not None:
                icon.thumbnail((32, 32), Image.Resampling.LANCZOS)
                canvas.alpha_composite(
                    icon,
                    (round(cursor), y + (row_height - icon.height) // 2),
                )
                cursor += icon.width + (7 if text else 0)
            if text:
                _draw_text(
                    draw,
                    (round(cursor), y),
                    text,
                    anchor="la",
                    max_width=max_width,
                    preferred_size=loaded.size,
                    font=self.font,
                    fill=request.text_settings.heading_color,
                    metallic=request.text_settings.heading_metallic,
                )
            cursor = left + sum(piece_widths[: index + 1]) + separator_width * index
            if index < len(pieces) - 1:
                _draw_text(
                    draw,
                    (round(cursor), y),
                    " • ",
                    anchor="la",
                    max_width=separator_width,
                    preferred_size=loaded.size,
                    font=self.font,
                    fill=request.text_settings.heading_color,
                    metallic=request.text_settings.heading_metallic,
                )
                cursor += separator_width
        return max(27, row_height + 7)

    @staticmethod
    def _metadata_items(request: CreationRequest) -> list[list[tuple[str, int]]]:
        tournament = request.tournament
        selected = request.text_settings.metadata_rows
        assert selected is not None
        count_label = "Teams" if tournament.event_format is TournamentFormat.DOUBLES else "Entrants"
        values = {
            "event": (tournament.event, 34),
            "date": (str(tournament.date), 28),
            "entrants_count": (f"{tournament.entrants_count} {count_label}", 24),
            "tournament_link": (tournament.link, 18),
            "tournament_location": (tournament.location, 18),
            "stream_link": (tournament.stream_link, 18),
            "vod_link": (tournament.vod_link, 18),
            "to_x_account": (tournament.organizer_x_account, 18),
            "to_twitch_account": (tournament.organizer_twitch_account, 18),
            "to_bluesky_account": (tournament.organizer_bluesky_account, 18),
        }
        return [
            [
                (str(values[field][0]), values[field][1])
                for field in row
                if values[field][0] is not None
            ]
            for row in selected
            if any(values[field][0] is not None for field in row)
        ]

    def _draw_tournament_text(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        mode: PodiumMode,
        center_title: bool,
    ) -> None:
        draw = ImageDraw.Draw(canvas)
        draw_text = partial(_draw_text, font=self.font)
        width = canvas.width
        title_max_width = width * 2 // 3
        is_doubles = request.tournament.event_format is TournamentFormat.DOUBLES
        for field in _metadata_layout(
            request.tournament,
            font=self.font,
            width=width,
            is_doubles=is_doubles,
        ):
            field["fill"] = request.text_settings.heading_color
            field["metallic"] = request.text_settings.heading_metallic
            draw_text(draw, **field)

        title_right_aligned = mode.layout_count != 3 and not center_title
        draw_text(
            draw,
            (title_max_width, 5)
            if title_right_aligned
            else ((width // 2, 5) if mode.layout_count != 3 else (15, 5)),
            request.tournament.title,
            anchor="ra"
            if title_right_aligned
            else ("ma" if mode.layout_count != 3 else "la"),
            max_width=title_max_width,
            preferred_size=92,
            fill=request.text_settings.heading_color,
            metallic=request.text_settings.heading_metallic,
        )
        self._draw_attribution(canvas, request, mode)

    def _draw_attribution(
        self,
        canvas: Image.Image,
        request: CreationRequest,
        mode: PodiumMode,
    ) -> None:
        width = canvas.width
        attribution_position, attribution_anchor = _attribution_layout(
            canvas,
            request.entrants,
            font=self.font,
            mode=mode,
        )
        _draw_text(
            ImageDraw.Draw(canvas),
            attribution_position,
            ATTRIBUTION_TEXT,
            anchor=attribution_anchor,
            max_width=width - 2 * ATTRIBUTION_SIDE_MARGIN,
            preferred_size=ATTRIBUTION_PREFERRED_SIZE,
            font=self.font,
            fill="#191919FF",
        )

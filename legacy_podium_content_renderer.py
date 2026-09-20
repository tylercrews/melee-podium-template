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
from random import choice

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
    _metadata_layout,
    _place_characters,
    _resolve_doubles_tag_collisions,
    _tag_anchor,
    _validate_placements,
)
from mode_preferences import CharacterPlacement, ModePreferences, TextPlacement
from models import DoublesTeam, SinglesEntrant, TournamentFormat
from podium_colors import podium_color_for_slot


@dataclass(frozen=True, slots=True)
class LegacyPodiumContentRenderer:
    """Draw podium portraits and text using serialized layout preferences."""

    font: PodiumFont = PodiumFont.TYROWO

    def draw(
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
        center_title, center_subtitle = (
            _centered_header_fields(
                result,
                request.tournament,
                font=self.font,
                is_doubles=is_doubles,
            )
            if mode.layout_count != 3
            else (False, False)
        )

        _draw_tournament_subtitle(
            result,
            request.tournament,
            self.font,
            mode.layout_count,
            center_subtitle,
        )
        if is_doubles:
            self._draw_doubles(result, request, preferences, mode)
        else:
            self._draw_singles(result, request, preferences, mode)
        self._draw_preference_text(result, request, preferences, mode)
        self._draw_tournament_text(result, request, mode, center_title)
        return result

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
            tag = CharacterTag(
                _tag_anchor(x, y, portrait, center_x=anchor[0]),
                entrant.tag,
                self._default_text_color(request, placement.entrant_slot),
                tag_max_width,
                FOUR_PODIUM_TAG_PREFERRED_SIZE
                if four_podium_top_8
                else TAG_PREFERRED_SIZE,
                FOUR_PODIUM_SPONSOR_PREFERRED_SIZE
                if four_podium_top_8
                else SPONSOR_PREFERRED_SIZE,
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
                tags.append(
                    CharacterTag(
                        _tag_anchor(x, y, portrait, center_x=anchor[0]),
                        member.tag,
                        self._default_text_color(request, entrant_slot),
                        DOUBLES_TAG_WIDTHS[mode.layout_count],
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
                _draw_lower_entrant_summary(
                    canvas,
                    entrant,
                    anchor=(placement.anchor.x, placement.anchor.y),
                    fill=placement.color
                    or self._default_text_color(request, placement.entrant_slot),
                    font=self.font,
                )
                continue

            text = self._text_value(placement, entrant)
            if text is None:
                continue
            color = placement.color or self._default_text_color(
                request, placement.entrant_slot or 1
            )
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
            )

    @staticmethod
    def _default_text_color(
        request: CreationRequest,
        entrant_slot: int,
    ) -> tuple[int, int, int] | str:
        if request.selection.options.podium_style is PodiumStyle.LEGACY:
            return PODIUM_BOX_COLORS_BY_SLOT[entrant_slot - 1].exterior_line
        assert request.podium_colors is not None
        podium_slot = entrant_slot
        if (
            request.selection.options.variant == "four_podium"
            and entrant_slot > 4
        ):
            podium_slot -= 4
        return podium_color_for_slot(
            request.podium_colors, podium_slot
        ).resolve().text_color

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
        )
        attribution_position, attribution_anchor = _attribution_layout(
            canvas,
            request.entrants,
            font=self.font,
            mode=mode,
        )
        draw_text(
            draw,
            attribution_position,
            ATTRIBUTION_TEXT,
            anchor=attribution_anchor,
            max_width=width - 2 * ATTRIBUTION_SIDE_MARGIN,
            preferred_size=ATTRIBUTION_PREFERRED_SIZE,
            fill="#191919FF",
        )

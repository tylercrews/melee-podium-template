"""Independent geometry for Doubles Top 8 and Singles Top 16 clapping layouts."""

from dataclasses import replace
import json
from pathlib import Path
from random import choice

from PIL import ImageDraw

from color_values import format_rgba_hex
from clapping_colors import legacy_top16_text_slot, TOP16_PLAYER_COLOR_SLOTS
from creation_modes import PodiumStyle
from DrawPodium import _character_with_team_color, _draw_text, _text_bounds, _wrap_text
from font_size_adjustments import adjusted_size
from models import SinglesEntrant, TournamentFormat
from podiums_clapping_renderer import PodiumsClappingContentRenderer
from podium_colors import PodiumColorConfiguration, PodiumColorMode, PodiumColorPreset


PROFILE = Path(__file__).resolve().parent / "preferences/portraits/extended_clapping.json"


class ExtendedClappingContentRenderer(PodiumsClappingContentRenderer):
    """Reuse the calibrated clap cycle with separately serialized panel geometry."""

    def _profile(self, request):
        return json.loads(PROFILE.read_text(encoding="utf-8"))["layouts"][
            request.selection.submode_id
        ][request.selection.options.podium_style.value]

    def prepare(self, canvas, request, preferences, **kwargs):
        if request.selection.options.event_format is TournamentFormat.DOUBLES:
            # Resolve a random team costume once, consistently for both members,
            # their stock icons, the static podiums, and every animation frame.
            teams = []
            for team in request.entrants:
                color = choice(("red", "green", "blue")) if team.team_color == "random" else team.team_color
                members = [replace(member, characters=[_character_with_team_color(character, color)
                           for character in member.characters]) for member in (team.entrant_1, team.entrant_2)]
                teams.append(replace(team, team_color=None, entrant_1=members[0], entrant_2=members[1]))
            request = replace(request, entrants=teams)
        return super().prepare(canvas, request, preferences, **kwargs)

    @staticmethod
    def _default_text_style(request, entrant_slot):
        if request.text_settings.entrant_text_color_mode == "match_podium":
            entrant_slot = (entrant_slot - 1) % 8 + 1
        return PodiumsClappingContentRenderer._default_text_style(request, entrant_slot)

    def _draw_with_font(self, canvas, request, preferences):
        # The reviewed static composition uses its existing Top 4/Top 8 helpers.
        # The new preference set owns its shifted anchors and larger canvas.
        count = 4 if request.selection.options.event_format is TournamentFormat.DOUBLES else 8
        selection = replace(request.selection, options=replace(request.selection.options,
                            entrant_count=count, variant=None, animated=False))
        text_settings = request.text_settings
        if text_settings.entrant_text_color_mode == "pick_all":
            text_settings = replace(text_settings, entrant_text_colors=text_settings.entrant_text_colors[:count],
                                    entrant_text_metallic=text_settings.entrant_text_metallic[:count])
        return super()._draw_with_font(canvas, replace(request, selection=selection,
                                      entrants=request.entrants[:count], text_settings=text_settings), preferences)


class DoublesClappingContentRenderer(ExtendedClappingContentRenderer):
    def _panel_keys(self, request):
        return tuple((slot, member) for slot in range(5, 9) for member in (1, 2))

    def _panel_subject(self, request, panel):
        team = request.entrants[panel.entrant_slot - 1]
        member = team.entrant_1 if panel.member_slot == 1 else team.entrant_2
        return SinglesEntrant(tag=member.tag, characters=member.characters,
                              name_font_size_adjustment=member.name_font_size_adjustment,
                              placement=team.placement, seed=team.seed if panel.member_slot == 1 else None)

    def _draw_panel_headings(self, base, request, profile):
        obstacles = []
        draw = ImageDraw.Draw(base)
        for row in profile["team_names"]:
            team = request.entrants[row["entrant_slot"] - 1]
            if team.omit_entrant:
                continue
            color, metallic = self._default_text_style(request, row["entrant_slot"])
            if isinstance(color, tuple):
                color = format_rgba_hex(*color[:3], color[3] if len(color) == 4 else 255)
            options = dict(anchor=row["pillow_anchor"], max_width=row["max_width"],
                           preferred_size=adjusted_size(row["preferred_size"], team.team_name_font_size_adjustment),
                           font=self.font, vertical_center_lines=2)
            position = (row["anchor"]["x"], row["anchor"]["y"])
            text = _wrap_text(team.team_name, row["max_width"], options["preferred_size"], self.font)
            if text.count("\n") > 1:
                text = team.team_name
            obstacles.append(_text_bounds(draw, position, text, **options))
            _draw_text(draw, position, text, fill=color, metallic=metallic, **options)
        return obstacles


class SinglesTop16ClappingContentRenderer(ExtendedClappingContentRenderer):
    @staticmethod
    def _default_text_style(request, entrant_slot):
        if request.text_settings.entrant_text_color_mode == "match_podium":
            if request.selection.options.podium_style is PodiumStyle.LEGACY:
                entrant_slot = legacy_top16_text_slot(entrant_slot)
            elif isinstance(request.podium_colors, PodiumColorConfiguration):
                colors = request.podium_colors
                if colors.mode is PodiumColorMode.PRESET and colors.preset is PodiumColorPreset.LEGACY:
                    entrant_slot = TOP16_PLAYER_COLOR_SLOTS[entrant_slot - 1]
                elif colors.mode is PodiumColorMode.PRESET or len(colors.colors) < 16:
                    entrant_slot = (entrant_slot - 1) % 8 + 1
        return PodiumsClappingContentRenderer._default_text_style(request, entrant_slot)

    def _panel_keys(self, request):
        return tuple((slot, None) for slot in range(9, 17))

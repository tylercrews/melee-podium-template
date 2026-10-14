"""Content stage for three customizable podiums above a singles clap grid."""

from dataclasses import replace
import json
from pathlib import Path

from podiums_clapping_renderer import PodiumsClappingContentRenderer
from podium_colors import PodiumColorConfiguration, PodiumColorMode, PodiumColorPreset


PROFILE = Path(__file__).resolve().parent / "preferences/portraits/clapping_grid.json"


def grid_profile(selection):
    return json.loads(PROFILE.read_text(encoding="utf-8"))["layouts"][selection.submode_id]


class ClappingGridContentRenderer(PodiumsClappingContentRenderer):
    def _profile(self, request):
        return grid_profile(request.selection)

    def _panel_keys(self, request):
        return tuple((slot, None) for slot in range(4, request.selection.options.entrant_count + 1))

    def _draw_with_font(self, canvas, request, preferences):
        selection = replace(request.selection, options=replace(request.selection.options,
                            entrant_count=3, variant=None, animated=False))
        text_settings = request.text_settings
        if text_settings.entrant_text_color_mode == "pick_all":
            text_settings = replace(text_settings, entrant_text_colors=text_settings.entrant_text_colors[:3],
                                    entrant_text_metallic=text_settings.entrant_text_metallic[:3])
        return super()._draw_with_font(canvas, replace(request, selection=selection,
                                      entrants=request.entrants[:3], text_settings=text_settings), preferences)

    @staticmethod
    def _default_text_style(request, entrant_slot):
        if request.text_settings.entrant_text_color_mode == "match_podium":
            colors = request.podium_colors
            if isinstance(colors, PodiumColorConfiguration):
                if colors.mode is PodiumColorMode.CUSTOM:
                    entrant_slot = (entrant_slot - 1) % len(colors.colors) + 1
                elif colors.mode is PodiumColorMode.PRESET:
                    entrant_slot = min(entrant_slot, 4) if colors.preset is PodiumColorPreset.MEDALS else (entrant_slot - 1) % 8 + 1
        return PodiumsClappingContentRenderer._default_text_style(request, entrant_slot)

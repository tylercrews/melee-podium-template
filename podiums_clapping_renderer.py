"""Podiums+Clapping's shared static and animated content stage."""

from dataclasses import dataclass, replace
from bisect import bisect_right
from io import BytesIO
from itertools import accumulate
import json
from pathlib import Path

from PIL import Image, ImageDraw

from background_builder import PixelRect
from clapping_assets import resolve_clapping_path
from clapping_portrait_renderer import render_clapping_portrait_frame
from color_values import format_rgba_hex
from creation import CreationRequest
from DrawPodium import (
    ATTRIBUTION_TEXT, ATTRIBUTION_BOTTOM_MARGIN, ATTRIBUTION_PREFERRED_SIZE,
    ATTRIBUTION_SIDE_MARGIN, PodiumFont, _draw_text, _text_bounds, _font_to_fit,
    _load_stock_icon, _temporary_font_settings,
)
from footer_attribution import Bounds, FooterPlacement, choose_footer_placement
from font_size_adjustments import adjusted_size
from formatting_assets import draw_placement_tags
from legacy_podium_content_renderer import LegacyPodiumContentRenderer
from mode_preferences import ModePreferences, PlacementTagPlacement
from gif_animation import encode_animated_gif
from portrait_crop_adjustment_for_clapping import get_clapping_portrait_adjustment
from placement_numbering import number_placement_tags
from entrant_visibility import visible_placement_tags


PROFILE = Path(__file__).resolve().parent / "preferences/portraits/podiums_clapping.json"
CROPS = Path(__file__).resolve().parent / "preferences/portraits/clapping.json"


def draw_clapping_attribution(canvas: Image.Image, font: PodiumFont, obstacles: list[Bounds]) -> FooterPlacement:
    """Use the actual footer text, portrait, and badge bounds instead of the header."""
    y = canvas.height - ATTRIBUTION_BOTTOM_MARGIN
    options = {"anchor": "la", "max_width": canvas.width - 2 * ATTRIBUTION_SIDE_MARGIN,
               "preferred_size": ATTRIBUTION_PREFERRED_SIZE, "font": font}
    measured = _text_bounds(ImageDraw.Draw(canvas), (0, y), ATTRIBUTION_TEXT, **options)
    placement = choose_footer_placement(canvas.width, measured, obstacles, side_margin=ATTRIBUTION_SIDE_MARGIN)
    layer = Image.new("RGBA", canvas.size, "#00000000")
    _draw_text(ImageDraw.Draw(layer), (placement.origin_x, y), ATTRIBUTION_TEXT, fill="#FFFFFF40", **options)
    canvas.alpha_composite(layer)
    return placement


@dataclass(frozen=True)
class ClappingPanel:
    entrant_slot: int
    rect: PixelRect
    text_x: int
    text_max_width: int
    text_alignment: str
    member_slot: int | None = None
    identity_scale: float = 1.0

    @classmethod
    def from_dict(cls, value):
        panel = cls(value["entrant_slot"], PixelRect(*value["portrait_rect"]),
                    value["text_x"], value["text_max_width"], value["text_alignment"],
                    value.get("member_slot"), value.get("identity_scale", 1.0))
        if (panel.entrant_slot not in range(4, 22) or panel.text_alignment not in {"left", "right"}
                or panel.text_max_width <= 0 or panel.member_slot not in {None, 1, 2}
                or not 0 < panel.identity_scale <= 1):
            raise ValueError("Invalid Podiums+Clapping panel")
        return panel


@dataclass
class ClappingTrack:
    panel: ClappingPanel
    frames: list[Image.Image]
    durations: list[int]
    preview_index: int

    def frame_index_at(self, elapsed_ms: int, cycle_ms: int) -> int:
        """Map a shared clap phase into this costume's native frame timeline."""
        native_elapsed = elapsed_ms * sum(self.durations) // cycle_ms
        return min(len(self.frames) - 1, bisect_right(list(accumulate(self.durations)), native_elapsed))


@dataclass
class ClappingLayout:
    base: Image.Image
    tracks: tuple[ClappingTrack, ...]
    badges: tuple[PlacementTagPlacement, ...]
    preferences: ModePreferences
    footer_placement: FooterPlacement | None = None

    @property
    def durations(self) -> list[int]:
        # Keep the longest native loop's cadence and fit shorter claps to it.
        # Ice Climbers' 25-frame clap can therefore share a cycle with 42-frame
        # characters without skipping its tail or making a huge multi-cycle GIF.
        return max(self.tracks, key=lambda track: sum(track.durations)).durations if self.tracks else [20]

    def frame(self, index: int | None = None) -> Image.Image:
        canvas = self.base.copy()
        durations = self.durations
        if index is not None and not 0 <= index < len(durations):
            raise ValueError("Frame index must fit the shared clapping cycle")
        elapsed = sum(durations[:index]) if index is not None else 0
        for track in self.tracks:
            frame_index = track.preview_index if index is None else track.frame_index_at(elapsed, sum(durations))
            canvas.alpha_composite(track.frames[frame_index], (track.panel.rect.left, track.panel.rect.top))
        draw_placement_tags(canvas, replace(self.preferences, placement_tags=self.badges))
        return canvas

    def png(self) -> bytes:
        output = BytesIO()
        self.frame().save(output, format="PNG")
        return output.getvalue()

    def gif(self) -> bytes:
        return encode_animated_gif(self.frame, self.durations,
                                   palette_samples=(frame for track in self.tracks for frame in track.frames))


class PodiumsClappingContentRenderer(LegacyPodiumContentRenderer):
    """Keep the four podiums still and animate the four costume-correct panels."""

    def _draw_attribution(self, canvas, request, mode):
        # The parent draws its header before the lower identities exist. Defer
        # attribution until their actual bounds can participate in the choice.
        pass

    def _profile(self, request):
        return json.loads(PROFILE.read_text(encoding="utf-8"))["styles"][request.selection.options.podium_style.value]

    def _panel_keys(self, request):
        return tuple((slot, None) for slot in range(5, 9))

    def _panel_subject(self, request, panel):
        return request.entrants[panel.entrant_slot - 1]

    def _draw_panel_headings(self, base, request, profile):
        return []

    def prepare(self, canvas: Image.Image, request: CreationRequest, preferences: ModePreferences,
                *, background: Image.Image | None = None, overlay: Image.Image | None = None) -> ClappingLayout:
        profile = self._profile(request)
        if profile["canvas_size"] != preferences.canvas_size.to_dict():
            raise ValueError("Podiums+Clapping geometry does not match its canvas")
        panels = tuple(ClappingPanel.from_dict(row) for row in profile["panels"])
        if tuple((panel.entrant_slot, panel.member_slot) for panel in panels) != self._panel_keys(request) or any(
            panel.rect.left < 0 or panel.rect.top < 0 or panel.rect.right > canvas.width or panel.rect.bottom > canvas.height
            for panel in panels
        ):
            raise ValueError("Podiums+Clapping panels must fit every lower entrant inside the canvas")
        badges = number_placement_tags(tuple(PlacementTagPlacement.from_dict(row) for row in profile["placement_tags"]),
                                      request.text_settings.use_tournament_placing)
        badges = visible_placement_tags(badges, request.entrants)
        panels = tuple(panel for panel in panels if not request.entrants[panel.entrant_slot - 1].omit_entrant)
        preferences = replace(preferences, text_slots=tuple(row for row in preferences.text_slots if row.field != "entrant.summary"))
        base = super().draw(canvas, request, preferences)
        if background is not None:
            if background.size != base.size:
                raise ValueError("Composition background must match the output canvas")
            composed = background.convert("RGBA")
            composed.alpha_composite(base)
            base = composed
        if overlay is not None:
            if overlay.size != base.size:
                raise ValueError("Composition overlay must match the output canvas")
            base.alpha_composite(overlay.convert("RGBA"))
        crops = json.loads(CROPS.read_text(encoding="utf-8"))["characters"]
        tracks = []
        obstacles = [panel.rect.as_tuple() for panel in panels]
        obstacles.extend((badge.anchor.x - badge.max_size.width // 2,
                          badge.anchor.y - badge.max_size.height // 2,
                          badge.anchor.x + badge.max_size.width // 2,
                          badge.anchor.y + badge.max_size.height // 2) for badge in badges)
        with _temporary_font_settings(request.text_settings.font_size_adjustment, self.custom_font_bytes):
            obstacles.extend(self._draw_panel_headings(base, request, profile))
            for panel in panels:
                entrant = self._panel_subject(request, panel)
                color, metallic = self._default_text_style(request, panel.entrant_slot)
                if isinstance(color, tuple):
                    color = format_rgba_hex(*color[:3], color[3] if len(color) == 4 else 255)
                obstacles.extend(self._draw_identity(base, entrant, panel, request, color, metallic))
                character = entrant.characters[0]
                adjustment = get_clapping_portrait_adjustment(character.melee_fighter_name)
                frames, durations = [], []
                with Image.open(resolve_clapping_path(character)) as source:
                    for index in range(source.n_frames):
                        source.seek(index)
                        frames.append(render_clapping_portrait_frame(source.convert("RGBA"), adjustment,
                            (panel.rect.width, panel.rect.height), background_color=color, border_width=1,
                            mirror_horizontally=character.mirror_horizontally))
                        durations.append(source.info.get("duration", 20))
                tracks.append(ClappingTrack(panel, frames, durations, crops[character.melee_fighter_name]["preview_frame_index"]))
            footer = draw_clapping_attribution(base, self.font, obstacles)
        return ClappingLayout(base, tuple(tracks), badges, preferences, footer)

    def draw(self, canvas, request, preferences):
        return self.prepare(canvas, request, preferences).frame()

    def _draw_identity(self, canvas, entrant, panel, request, color, metallic):
        draw = ImageDraw.Draw(canvas)
        obstacles = []
        def paint(position, text, anchor, preferred_size):
            options = {"anchor": anchor, "max_width": panel.text_max_width,
                       "preferred_size": preferred_size, "font": self.font}
            obstacles.append(_text_bounds(draw, position, text, **options))
            _draw_text(draw, position, text, fill=color, metallic=metallic, **options)
        top, x = panel.rect.top, panel.text_x
        scale = panel.identity_scale
        offset = lambda value: round(value * scale)
        seed_text = f"[{entrant.seed}s]" if request.text_settings.include_seeding and entrant.seed is not None else ""
        seed_size = adjusted_size(offset(17), request.text_settings.seed_font_size_adjustment)
        icons = [_load_stock_icon(character, size=offset(24)) for character in entrant.characters]
        icons_width = sum(icon.width for icon in icons) + 5 * max(0, len(icons) - 1)
        seed_width = round(_font_to_fit(seed_text, panel.text_max_width, seed_size, self.font).getlength(seed_text)) if seed_text else 0
        row_width = icons_width + (12 + seed_width if seed_text else 0)
        row_x = x - row_width if panel.text_alignment == "right" else x
        for icon in icons:
            canvas.alpha_composite(icon, (row_x, top + offset(17) - icon.height // 2))
            row_x += icon.width + 5
        if seed_text:
            paint((row_x + 7, top + offset(20)), seed_text, "lm", seed_size)
        anchor = "rm" if panel.text_alignment == "right" else "lm"
        sponsor, separator, player = entrant.tag.rpartition("|")
        if separator:
            paint((x, top + offset(47)), sponsor.strip(), anchor, adjusted_size(offset(22), entrant.name_font_size_adjustment))
        else:
            player = entrant.tag
        paint((x, top + offset(82 if separator else 63)), player.strip(), anchor, adjusted_size(offset(46), entrant.name_font_size_adjustment))
        return obstacles

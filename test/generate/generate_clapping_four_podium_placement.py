"""Offline static placement proposal for the first animated four-podium layout."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from background_builder import (
    BUILTIN_BACKGROUND_SIZES, BackgroundRequest, ImagePlacement, PixelRect,
    cover_crop, create_background,
)
from clapping_portrait_renderer import render_clapping_portrait
from creation import CreationRequest
from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from DrawPodium import ATTRIBUTION_TEXT, PodiumFont, _load_stock_icon
from formatting_assets import FormattingAssetRenderer
from legacy_podium_content_renderer import LegacyPodiumContentRenderer
from mode_preferences import ModePreferenceRepository
from models import TournamentFormat
from podium_colors import PodiumColorConfiguration, PodiumColorPreset
from portrait_assets import PORTRAIT_FILENAME, resolve_character_path
from sample_creation_data import sample_clapping_top_8_entrants, sample_tournament


OUTPUT = PROJECT_ROOT / "test/clapping_portrait_previews/four_podium_placement"
BACKGROUND_ID = "00_Battlefield_5000_5000_resaved.png"
NAME_COLORS = ("#FB8B00FF", "#00CDC3FF", "#FF00FFFF", "#8D8D8DFF")
PANEL_SIZE = (68, 104)


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(PROJECT_ROOT / "fonts/Ubuntu-Regular.ttf"), size)


def fit_font(text: str, preferred: int, width: int) -> ImageFont.FreeTypeFont:
    size = preferred
    while size > 11 and font(size).getlength(text) > width:
        size -= 1
    return font(size)


class PlacementPreviewContentRenderer(LegacyPodiumContentRenderer):
    """Leave the lower-result band free of the existing footer attribution."""

    def _draw_attribution(self, canvas, request, mode):
        layer = Image.new("RGBA", canvas.size, "#00000000")
        ImageDraw.Draw(layer).text((14, 18), ATTRIBUTION_TEXT, font=font(18), fill="#FFFFFF40")
        canvas.alpha_composite(layer)


def draw_lower_result(canvas, entrant, rect, text_x, max_width, color, rank):
    """Review a portrait and a compact, left-aligned version of the existing summary."""

    left, top, right, bottom = rect
    character = entrant.characters[0]
    frame = json.loads((PROJECT_ROOT / "preferences/portraits/clapping.json").read_text())["characters"][character.melee_fighter_name]["preview_frame_index"]
    portrait = render_clapping_portrait(
        character, (right - left, bottom - top), background_color=color,
        frame_index=frame, border_width=1,
    )
    canvas.alpha_composite(portrait, (left, top))
    draw = ImageDraw.Draw(canvas)
    row_y = top + 17
    rank_text = f"{rank}th"
    draw.text((text_x, row_y), rank_text, font=font(28), anchor="lm", fill=color)
    x = text_x + round(font(28).getlength(rank_text)) + 12
    for character in entrant.characters:
        icon = _load_stock_icon(character, size=24)
        canvas.alpha_composite(icon, (x, row_y - icon.height // 2))
        x += icon.width + 5
    if entrant.seed is not None:
        draw.text((x + 7, row_y + 3), f"[{entrant.seed}s]", font=font(17), anchor="lm", fill=color)
    sponsor, separator, player = entrant.tag.rpartition("|")
    if separator:
        draw.text((text_x, top + 47), sponsor.strip(), font=fit_font(sponsor.strip(), 22, max_width), anchor="lm", fill=color)
        name_y = top + 82
    else:
        player = entrant.tag
        name_y = top + 63
    draw.text((text_x, name_y), player.strip(), font=fit_font(player.strip(), 46, max_width), anchor="lm", fill=color)
    assert 0 <= left < right <= canvas.width and 0 <= top < bottom <= canvas.height


def generate() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    entrants = sample_clapping_top_8_entrants()
    # Freeze random static poses once, so both style previews use the same demo data.
    for index, entrant in enumerate(entrants):
        selected = []
        for character in entrant.characters:
            match = PORTRAIT_FILENAME.match(resolve_character_path(character).name)
            selected.append(replace(character, pose=match["pose"], color=match["color"]))
        entrants[index] = replace(entrant, characters=selected)
    tournament = replace(
        sample_tournament(), title="Clapping Layout Preview",
        subtitle="Singles Top 8 - Four Podiums", date="10/12/2026",
    )
    draft = {"schema_version": 1, "status": "placement_review", "styles": {}}
    for style in (PodiumStyle.LEGACY, PodiumStyle.CUSTOMIZABLE):
        selection = ModeSelection(CreationMode.PODIUM, ModeOptions(
            event_format=TournamentFormat.SINGLES, entrant_count=8,
            variant="four_podium", podium_style=style,
        ))
        preferences = ModePreferenceRepository().load(selection)
        size = preferences.canvas_size
        background = BackgroundRequest(size=size, image=ImagePlacement(
            asset_id=BACKGROUND_ID,
            source_crop=cover_crop(BUILTIN_BACKGROUND_SIZES[BACKGROUND_ID], size),
            destination=PixelRect(0, 0, size.width, size.height),
        ))
        colors = PodiumColorConfiguration.from_preset(PodiumColorPreset.LEGACY) if style is PodiumStyle.CUSTOMIZABLE else None
        request = CreationRequest(
            selection=selection, background=background, entrants=entrants,
            tournament=tournament, podium_colors=colors,
        )
        # This is an explicit offline geometry review, like the existing podium
        # preview scripts. Leave scaffold readiness and runtime preferences intact.
        review_preferences = replace(preferences, text_slots=tuple(
            placement for placement in preferences.text_slots if placement.field != "entrant.summary"
        ))
        formatted = FormattingAssetRenderer().draw(create_background(background), review_preferences, colors)
        preview = PlacementPreviewContentRenderer(font=PodiumFont.UBUNTU).draw(formatted, request, review_preferences)
        rows = []
        for index, body in enumerate(sorted(preferences.formatting_assets, key=lambda item: item.destination.left)):
            rect = [body.destination.left + 7, 830, body.destination.left + 7 + PANEL_SIZE[0], 830 + PANEL_SIZE[1]]
            text_x = rect[2] + 14
            max_width = body.destination.right - text_x - 7
            rank = 5 if index < 2 else 7
            color = NAME_COLORS[index]
            draw_lower_result(preview, entrants[index + 4], rect, text_x, max_width, color, rank)
            rows.append({
                "entrant_slot": index + 5, "rank": rank, "portrait_rect": rect,
                "text_x": text_x, "text_max_width": max_width,
                "background_and_name_color": color,
                "demo_tag": entrants[index + 4].tag,
                "demo_character": entrants[index + 4].characters[0].melee_fighter_name,
                "demo_costume": entrants[index + 4].characters[0].color,
            })
        output = OUTPUT / f"{style.value}-top-8-four-podium-placement.png"
        preview.convert("RGB").save(output)
        preview.crop((0, 818, size.width, size.height)).resize(
            (size.width * 2, (size.height - 818) * 2), Image.Resampling.LANCZOS,
        ).convert("RGB").save(OUTPUT / f"{style.value}-lower-results-detail.png")
        draft["styles"][style.value] = {
            "canvas_size": size.to_dict(), "lower_result_panels": rows,
            "attribution": {"position": [14, 18], "font_size": 18, "color": "#FFFFFF40"},
        }
        print(output)
    (OUTPUT / "placement-draft.json").write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    generate()

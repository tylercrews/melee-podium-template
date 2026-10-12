"""Offline static placement review for Podiums+Clapping."""

from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from background_builder import (
    BUILTIN_BACKGROUND_SIZES, BackgroundRequest, ImagePlacement, PixelRect, PixelSize,
    cover_crop, create_background,
)
from clapping_portrait_renderer import render_clapping_portrait
from creation import CreationRequest
from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from DrawPodium import ATTRIBUTION_TEXT, PodiumFont, _load_stock_icon
from formatting_assets import FormattingAssetRenderer, draw_placement_tags
from legacy_podium_content_renderer import LegacyPodiumContentRenderer
from mode_preferences import ModePreferenceRepository, PixelPoint, PlacementTagPlacement
from models import TournamentFormat
from podium_colors import PodiumColorConfiguration, PodiumColorPreset
from portrait_assets import PORTRAIT_FILENAME, resolve_character_path
from sample_creation_data import sample_clapping_top_8_entrants, sample_tournament


OUTPUT = PROJECT_ROOT / "test/clapping_portrait_previews/four_podium_placement"
BACKGROUND_ID = "00_Battlefield_5000_5000_resaved.png"
NAME_COLORS = ("#FB8B00FF", "#00CDC3FF", "#FF00FFFF", "#8D8D8DFF")
PANEL_SIZE = (68, 104)
SHARED_BADGE_COPY_GAP = 12
LAYOUT_REVIEW_NAME = "Podiums+Clapping"


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


def portrait_column_edges(preferences, body):
    """Use Legacy's visible front corners independently from its side-face bounds."""

    if preferences.selection.options.podium_style is not PodiumStyle.LEGACY:
        return body.destination.left + 7, body.destination.right - 7
    calibration = json.loads((OUTPUT / 'legacy-front-face-edges.json').read_text(encoding='utf-8'))
    measured = calibration['assets'][body.asset_id]
    with Image.open(PROJECT_ROOT / 'formatting_assets/podium/legacy' / body.asset_id) as source:
        if tuple(measured['source_size']) != source.size:
            raise ValueError(f"Legacy front-face calibration is stale for {body.asset_id}")
    source_width = measured['source_size'][0]
    return tuple(body.destination.left + round(measured[side] * body.destination.width / source_width)
                 for side in ('left', 'right'))


def lower_result_geometry(preferences, number_height):
    """Anchor each block to its podium independently of the tiny rank overlay."""

    bodies = sorted(preferences.formatting_assets, key=lambda item: item.destination.left)
    rows, badges = [], []
    for pair_index, asset_id in enumerate(("05th.png", "07th.png")):
        first_index = pair_index * 2
        first, second = bodies[first_index:first_index + 2]
        first_edges = portrait_column_edges(preferences, first)
        second_edges = portrait_column_edges(preferences, second)
        second_left = second_edges[0]
        first_right = first_edges[1]
        first_rect = [first_right - PANEL_SIZE[0], 830, first_right, 830 + PANEL_SIZE[1]]
        second_rect = [second_left, 830, second_left + PANEL_SIZE[0], 830 + PANEL_SIZE[1]]
        with Image.open(PROJECT_ROOT / "formatting_assets/placement_numbers" / asset_id) as source:
            art = source.copy()
        badge_max_size = (math.ceil(art.width * number_height / art.height), number_height)
        art.thumbnail(badge_max_size, Image.Resampling.LANCZOS)
        center_x = (first_right + second_left) // 2
        group_height = 2 * art.height + SHARED_BADGE_COPY_GAP
        group_top = 830 + PANEL_SIZE[1] // 2 - group_height // 2
        for member_index in range(2):
            art_top = group_top + member_index * (art.height + SHARED_BADGE_COPY_GAP)
            badges.append(PlacementTagPlacement(
                slot_id=f"lower_pair_{pair_index + 1}_entrant_{first_index + member_index + 5}_placement_tag",
                asset_id=asset_id,
                anchor=PixelPoint(center_x, art_top + art.height // 2),
                max_size=PixelSize(*badge_max_size), z_index=200 + first_index + member_index,
            ))
        for index, edges, rect, alignment in (
            (first_index, first_edges, first_rect, "right"),
            (first_index + 1, second_edges, second_rect, "left"),
        ):
            text_x = rect[0] - 14 if alignment == "right" else rect[2] + 14
            max_width = text_x - edges[0] if alignment == "right" else edges[1] - text_x
            assert max_width > 0
            rows.append({
                "entrant_slot": index + 5, "rank": 5 if pair_index == 0 else 7,
                "portrait_rect": rect, "text_x": text_x, "text_max_width": max_width,
                "text_alignment": alignment, "background_and_name_color": NAME_COLORS[index],
                "podium_front_face_edges": list(edges),
            })
    return rows, badges


def draw_lower_result(canvas, entrant, rect, text_x, max_width, color, alignment):
    """Draw a portrait with a left- or right-aligned identity and stock/seed row."""

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
    icons = [_load_stock_icon(character, size=24) for character in entrant.characters]
    seed_text = f"[{entrant.seed}s]" if entrant.seed is not None else ""
    icons_width = sum(icon.width for icon in icons) + 5 * max(0, len(icons) - 1)
    row_width = icons_width + (12 + round(font(17).getlength(seed_text)) if seed_text else 0)
    x = text_x - row_width if alignment == "right" else text_x
    for icon in icons:
        canvas.alpha_composite(icon, (x, row_y - icon.height // 2))
        x += icon.width + 5
    if seed_text:
        draw.text((x + 7, row_y + 3), seed_text, font=font(17), anchor="lm", fill=color)
    anchor = "rm" if alignment == "right" else "lm"
    sponsor, separator, player = entrant.tag.rpartition("|")
    if separator:
        draw.text((text_x, top + 47), sponsor.strip(), font=fit_font(sponsor.strip(), 22, max_width), anchor=anchor, fill=color)
        name_y = top + 82
    else:
        player = entrant.tag
        name_y = top + 63
    draw.text((text_x, name_y), player.strip(), font=fit_font(player.strip(), 46, max_width), anchor=anchor, fill=color)
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
        subtitle=LAYOUT_REVIEW_NAME, date="10/12/2026",
    )
    draft = {"schema_version": 1, "status": "placement_review",
             "proposed_display_name": LAYOUT_REVIEW_NAME, "styles": {}}
    reference_selection = ModeSelection(CreationMode.PODIUM, ModeOptions(
        event_format=TournamentFormat.SINGLES, entrant_count=8,
        variant="four_podium", podium_style=PodiumStyle.CUSTOMIZABLE,
    ))
    reference_preferences = ModePreferenceRepository().load(reference_selection)
    fourth = next(tag for tag in reference_preferences.placement_tags if tag.asset_id == "04th.png")
    with Image.open(PROJECT_ROOT / "formatting_assets/placement_numbers/04th.png") as source:
        source.thumbnail(fourth.max_size.as_tuple(), Image.Resampling.LANCZOS)
        number_height = source.height
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
        rows, shared_badges = lower_result_geometry(preferences, number_height)
        review_preferences = replace(
            preferences,
            text_slots=tuple(placement for placement in preferences.text_slots if placement.field != "entrant.summary"),
        )
        formatted = FormattingAssetRenderer().draw(create_background(background), review_preferences, colors)
        preview = PlacementPreviewContentRenderer(font=PodiumFont.UBUNTU).draw(formatted, request, review_preferences)
        for row in rows:
            entrant = entrants[row["entrant_slot"] - 1]
            draw_lower_result(
                preview, entrant, row["portrait_rect"], row["text_x"],
                row["text_max_width"], row["background_and_name_color"], row["text_alignment"],
            )
            row.update({
                "demo_tag": entrant.tag,
                "demo_character": entrant.characters[0].melee_fighter_name,
                "demo_costume": entrant.characters[0].color,
            })
        # The requested shared ranks overlay portraits without affecting geometry.
        draw_placement_tags(preview, replace(review_preferences, placement_tags=tuple(shared_badges)))
        output = OUTPUT / f"{style.value}-top-8-four-podium-placement.png"
        preview.convert("RGB").save(output)
        preview.crop((0, 818, size.width, size.height)).resize(
            (size.width * 2, (size.height - 818) * 2), Image.Resampling.LANCZOS,
        ).convert("RGB").save(OUTPUT / f"{style.value}-lower-results-detail.png")
        if style is PodiumStyle.CUSTOMIZABLE:
            preview.crop((0, 650, size.width, 860)).convert("RGB").save(
                OUTPUT / "customizable-front-number-detail.png",
            )
        draft["styles"][style.value] = {
            "canvas_size": size.to_dict(), "lower_result_panels": rows,
            "shared_placement_tags": [badge.to_dict() for badge in shared_badges],
            "podium_placement_tags": [tag.to_dict() for tag in review_preferences.placement_tags],
            "shared_placement_tags_above_portraits": True,
            "shared_placement_number_height": number_height,
            "attribution": {"position": [14, 18], "font_size": 18, "color": "#FFFFFF40"},
        }
        print(output)
    (OUTPUT / "placement-draft.json").write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    generate()

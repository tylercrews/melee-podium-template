"""PR grid selection, composition, animation boundaries, and numbering coverage."""

from dataclasses import replace
from io import BytesIO
import json
import random
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops

from app import app, _custom_preview_colors
from background_builder import BackgroundRequest
from clapping_grid_layouts import GRID_LAYOUTS, grid_submode
from clapping_grid_renderer import ClappingGridContentRenderer, grid_profile
from creation import CreationPipeline, CreationRequest, TextSettings
from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from DrawPodium import PodiumFont
from format_preview import prepare_format_preview
from mode_preferences import ModePreferenceRepository
from models import TournamentFormat
from placement_numbering import default_tournament_placing, ordinal_asset_id, placement_rank
from placement_preview_layers import render_placement_number_layer
from podium_colors import PodiumColorConfiguration, PodiumColorPreset
from sample_creation_data import sample_singles_entrants, sample_tournament


def selection_for(row):
    return ModeSelection(CreationMode.PODIUM, ModeOptions(TournamentFormat.SINGLES,
        row["entrant_count"], f"clapping_grid_{row['columns']}", PodiumStyle.CUSTOMIZABLE))


class ClappingGridTest(unittest.TestCase):
    def test_every_grid_restores_settings_and_reuses_exact_top3_geometry(self):
        repository = ModePreferenceRepository()
        original = repository.load(ModeSelection(CreationMode.PODIUM,
            ModeOptions(TournamentFormat.SINGLES, 3, podium_style=PodiumStyle.CUSTOMIZABLE)))
        for row in GRID_LAYOUTS:
            selection = selection_for(row)
            self.assertEqual(selection.submode_id, grid_submode(row))
            self.assertTrue(selection.options.animated)
            self.assertFalse(default_tournament_placing(selection))
            still = replace(selection, options=replace(selection.options, animated=False))
            self.assertEqual(ModeSelection.from_dict(still.to_dict()), still)
            preference = repository.load(still)
            self.assertTrue(preference.ready)
            self.assertEqual(preference.canvas_size.as_tuple(), (1920, row["height"]))
            for field in ("formatting_assets", "placement_tags", "character_slots", "text_slots"):
                self.assertEqual(getattr(preference, field), getattr(original, field))

    def test_all_grid_renders_animate_only_panels_and_default_to_sequential_badges(self):
        for row in GRID_LAYOUTS:
            with self.subTest(layout=row):
                selection = selection_for(row)
                layout = prepare_format_preview(PodiumStyle.CUSTOMIZABLE, TournamentFormat.SINGLES,
                    row["entrant_count"], selection.options.variant, transparent=True, font=PodiumFont.UBUNTU)
                self.assertEqual(len(layout.tracks), row["entrant_count"] - 3)
                self.assertEqual([tag.asset_id for tag in layout.badges],
                                 [ordinal_asset_id(slot) for slot in range(4, row["entrant_count"] + 1)])
                self.assertEqual(len({track.panel.rect.top for track in layout.tracks}), row["rows"])
                first, later = layout.frame(0), layout.frame(18)
                self.assertNotEqual(first.tobytes(), later.tobytes())
                difference = ImageChops.difference(first, later)
                for track in layout.tracks:
                    self.assertLessEqual(track.panel.rect.right, first.width)
                    self.assertLessEqual(track.panel.rect.bottom, first.height)
                    difference.paste("#00000000", track.panel.rect.as_tuple())
                self.assertTrue(all(channel.getbbox() is None for channel in difference.split()))
                self.assertGreater(layout.footer_placement.bounds[1], max(tag.anchor.y + tag.max_size.height // 2 for tag in layout.badges))

    def test_numbers_switch_without_changing_grid_geometry_or_bracket_results(self):
        selection = selection_for(GRID_LAYOUTS[-1])
        entrants = sample_singles_entrants(21, random.Random(21))
        original = [entrant.placement for entrant in entrants]
        layout = prepare_format_preview(PodiumStyle.CUSTOMIZABLE, TournamentFormat.SINGLES,
            21, selection.options.variant, transparent=True, entrants=entrants,
            text_settings=TextSettings(use_tournament_placing=True))
        self.assertEqual([tag.asset_id for tag in layout.badges],
                         [ordinal_asset_id(placement_rank(slot)) for slot in range(4, 22)])
        self.assertEqual([entrant.placement for entrant in entrants], original)
        tournament = render_placement_number_layer(selection, True)
        sequential = render_placement_number_layer(selection, False)
        self.assertIsNotNone(ImageChops.difference(tournament, sequential).getbbox())

    def test_api_still_gif_defaults_overrides_and_rejects_invalid_combinations(self):
        from app import prepare_format_preview as real_prepare
        captured = []
        def capture(*args, **kwargs):
            layout = real_prepare(*args, **kwargs)
            captured.append(layout)
            return layout
        payload = dict(style="customizable", event_format="singles", entrant_count=21,
                       variant="clapping_grid_6", transparent=True,
                       formatting_asset_colors=dict(mode="premade", preset="rainbow", colors=[]))
        with patch("app.prepare_format_preview", side_effect=capture):
            for animated in (False, True):
                response = app.test_client().post("/api/format-preview", json={**payload, "animated": animated})
                self.assertEqual(response.status_code, 200, response.data[:200])
                self.assertEqual(response.mimetype, "image/gif" if animated else "image/png")
                with Image.open(BytesIO(response.data)) as image:
                    self.assertEqual(image.size, (1920, 1530))
                    self.assertEqual(image.n_frames, 42 if animated else 1)
                    if animated:
                        self.assertEqual(image.info["loop"], 0)
                self.assertEqual(captured[-1].badges[-1].asset_id, "21st.png")
        for invalid in (dict(style="legacy"), dict(event_format="doubles"), dict(entrant_count=20), dict(variant="clapping_grid_7")):
            response = app.test_client().post("/api/format-preview", json={**payload, **invalid})
            self.assertEqual(response.status_code, 400)

    def test_pipeline_and_explicit_text_colors_cover_all_21_entrants(self):
        selection = selection_for(GRID_LAYOUTS[-1])
        preferences = ModePreferenceRepository().load(selection)
        colors = tuple(f"#{slot:02X}3456FF" for slot in range(1, 22))
        request = CreationRequest(selection, BackgroundRequest(preferences.canvas_size),
            sample_singles_entrants(21, random.Random(21)), sample_tournament(),
            podium_colors=PodiumColorConfiguration.from_preset(PodiumColorPreset.LEGACY),
            text_settings=TextSettings(use_tournament_placing=False, entrant_text_color_mode="pick_all",
                entrant_text_colors=colors, entrant_text_metallic=(False,) * 21))
        renderer = ClappingGridContentRenderer(font=PodiumFont.UBUNTU)
        self.assertEqual(renderer._default_text_style(request, 21), (colors[-1], False))
        image = CreationPipeline({CreationMode.PODIUM: renderer}).create(request)
        self.assertEqual(image.size, (1920, 1530))
        profile = grid_profile(selection)
        for invalid in ("missing", "outside"):
            class InvalidRenderer(ClappingGridContentRenderer):
                def _profile(self, request):
                    value = json.loads(json.dumps(profile))
                    if invalid == "missing":
                        value["panels"].pop()
                    else:
                        value["panels"][-1]["portrait_rect"][2] = 1921
                    return value
            with self.assertRaisesRegex(ValueError, "fit every lower entrant"):
                InvalidRenderer().prepare(image, request, preferences)

    def test_rainbow_uses_three_podium_colors_in_preview_and_api(self):
        from clapping_preview_layers import render_extended_clapping_layer
        selection = selection_for(GRID_LAYOUTS[-1])
        layer = render_extended_clapping_layer(PodiumStyle.CUSTOMIZABLE, selection.submode_id, "rainbow")
        colors = _custom_preview_colors(dict(mode="premade", preset="rainbow", colors=[]), 21, "clapping_grid_6")
        for panel in grid_profile(selection)["panels"]:
            slot = panel["entrant_slot"]
            self.assertEqual(layer.getpixel(tuple(panel["portrait_rect"][:2])),
                             tuple(bytes.fromhex(colors.color_for_slot(slot).resolve().text_color[1:])))

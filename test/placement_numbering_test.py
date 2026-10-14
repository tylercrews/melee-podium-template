"""Placement artwork, persistence boundary, and GIF/still numbering regressions."""

from io import BytesIO
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops

from app import app
from creation import TextSettings
from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from format_preview import prepare_format_preview
from mode_preferences import ModePreferenceRepository
from models import TournamentFormat
from placement_numbering import placement_rank, numbered_preferences, ordinal_asset_id
from placement_preview_layers import preview_selections, render_placement_number_layer


class PlacementNumberingTest(unittest.TestCase):
    def test_rank_sequences_and_ordinal_assets(self):
        self.assertEqual([placement_rank(i) for i in range(1, 26)],
                         [1, 2, 3, 4, 5, 5, 7, 7] + [9] * 4 + [13] * 4 + [17] * 8 + [25])
        self.assertEqual([placement_rank(i, False) for i in range(1, 26)], list(range(1, 26)))
        self.assertEqual([ordinal_asset_id(i) for i in (1, 2, 3, 11, 12, 13, 21, 22, 23)],
                         ["01st.png", "02nd.png", "03rd.png", "11th.png", "12th.png", "13th.png", "21st.png", "22nd.png", "23rd.png"])
        for value in (True, 0, -1, "8"):
            with self.assertRaises(ValueError):
                placement_rank(value)

    def test_numbering_preserves_each_layouts_calibration_and_saved_preferences(self):
        for selection in preview_selections():
            original = ModePreferenceRepository().load(selection)
            for tournament in (True, False):
                numbered = numbered_preferences(original, tournament)
                self.assertEqual(numbered.formatting_assets, original.formatting_assets)
                self.assertEqual(numbered.character_slots, original.character_slots)
                self.assertEqual(numbered.text_slots, original.text_slots)
                by_id = {tag.slot_id: tag for tag in numbered.placement_tags}
                for tag in original.placement_tags:
                    self.assertEqual(by_id[tag.slot_id].anchor, tag.anchor)
                    self.assertEqual(by_id[tag.slot_id].max_size, tag.max_size)
            self.assertEqual(ModePreferenceRepository().load(selection), original)

    def test_all_modes_have_distinct_cached_tournament_and_sequential_numbers(self):
        for mode, count, variant in ((CreationMode.PODIUM, 16, "clapping"),
                                    (CreationMode.EYES, 16, None), (CreationMode.SQUARES, 8, None),
                                    (CreationMode.RADIAL, 8, None)):
            selection = ModeSelection(mode, ModeOptions(TournamentFormat.SINGLES, count, variant,
                                      PodiumStyle.CUSTOMIZABLE if mode is CreationMode.PODIUM else None))
            tournament = render_placement_number_layer(selection, True)
            sequential = render_placement_number_layer(selection, False)
            self.assertIsNotNone(ImageChops.difference(tournament, sequential).getbbox())
            self.assertEqual(tournament.size, sequential.size)

    def test_clapping_singles_and_doubles_badges_number_by_entrant_not_member(self):
        for style in PodiumStyle:
            for event, count, variant, expected in (
                (TournamentFormat.SINGLES, 8, "four_podium", ["05th.png", "06th.png", "07th.png", "08th.png"]),
                (TournamentFormat.DOUBLES, 8, "four_podium", ["05th.png", "06th.png", "07th.png", "08th.png"]),
                (TournamentFormat.SINGLES, 16, "clapping", [ordinal_asset_id(i) for i in range(9, 17)]),
            ):
                layout = prepare_format_preview(style, event, count, variant, transparent=True,
                                                text_settings=TextSettings(use_tournament_placing=False))
                self.assertEqual([tag.asset_id for tag in layout.badges], expected)
                if count == 16:
                    self.assertEqual([tag.asset_id for tag in layout.preferences.placement_tags],
                                     [ordinal_asset_id(i) for i in range(1, 9)])
                self.assertEqual(len(layout.tracks), 8 if count == 16 or event is TournamentFormat.DOUBLES else 4)

    def test_api_migrates_old_layouts_validates_boolean_and_preserves_false_for_gif(self):
        client = app.test_client()
        for bad in (None, "false", 0, 1):
            response = client.post("/api/format-preview", json={"text_settings": {"use_tournament_placing": bad}})
            self.assertEqual(response.status_code, 400)
        captured = []
        from app import prepare_format_preview as real_prepare
        def prepare(*args, **kwargs):
            layout = real_prepare(*args, **kwargs)
            captured.append(layout)
            return layout
        with patch("app.prepare_format_preview", side_effect=prepare):
            response = client.post("/api/format-preview", json={"style": "legacy", "event_format": "singles",
                                   "entrant_count": 8, "variant": "four_podium", "animated": True,
                                   "transparent": True, "text_settings": {"use_tournament_placing": False}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([tag.asset_id for tag in captured[0].badges], ["05th.png", "06th.png", "07th.png", "08th.png"])
        with Image.open(BytesIO(response.data)) as gif:
            self.assertEqual(gif.n_frames, 42)
            self.assertEqual(gif.info["loop"], 0)


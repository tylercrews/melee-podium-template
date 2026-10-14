"""Coverage for the taller doubles and compact Top 16 clapping templates."""

from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
import random
import unittest

from PIL import Image, ImageChops

from app import app
from background_builder import BackgroundRequest
from creation import CreationPipeline, CreationRequest, TextSettings
from clapping_colors import TOP16_PLAYER_COLOR_SLOTS, resolve_clapping_podium_colors
from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from DrawPodium import PodiumFont
from extended_clapping_renderer import DoublesClappingContentRenderer, SinglesTop16ClappingContentRenderer
from format_preview import prepare_format_preview
from mode_preferences import ModePreferenceRepository
from models import Character, TournamentFormat
from podium_colors import PodiumColorConfiguration, PodiumColorPreset
from sample_creation_data import sample_top_8_teams, sample_singles_entrants, sample_tournament


ROOT = Path(__file__).resolve().parents[1]
CASES = ((TournamentFormat.DOUBLES, 8, "four_podium", 1280),
         (TournamentFormat.SINGLES, 16, "clapping", 1000))


class ExtendedClappingTest(unittest.TestCase):
    def test_layout_serialization_geometry_and_animation_regions(self):
        for event_format, count, variant, height in CASES:
            for style in PodiumStyle:
                with self.subTest(event_format=event_format, style=style):
                    selection = ModeSelection(CreationMode.PODIUM, ModeOptions(event_format, count, variant, style))
                    self.assertTrue(selection.options.animated)
                    still = replace(selection, options=replace(selection.options, animated=False))
                    self.assertEqual(ModeSelection.from_dict(still.to_dict()), still)
                    preferences = ModePreferenceRepository().load(still)
                    self.assertEqual(preferences.selection, still)
                    self.assertEqual(preferences.canvas_size.height, height)
                    self.assertTrue(preferences.ready)
                    layout = prepare_format_preview(style, event_format, count, variant,
                               font=PodiumFont.UBUNTU, transparent=True)
                    self.assertEqual(len(layout.tracks), 8)
                    self.assertEqual(len(layout.durations), 42)
                    first, later = layout.frame(0), layout.frame(18)
                    difference = ImageChops.difference(first, later)
                    self.assertNotEqual(first.tobytes(), later.tobytes())
                    for track in layout.tracks:
                        rect = track.panel.rect
                        self.assertGreaterEqual(rect.left, 0)
                        self.assertLessEqual(rect.right, first.width)
                        self.assertLessEqual(rect.bottom, height)
                        difference.paste("#00000000", rect.as_tuple())
                    self.assertTrue(all(channel.getbbox() is None for channel in difference.split()))
                    self.assertGreater(layout.footer_placement.bounds[1], max(track.panel.rect.bottom for track in layout.tracks))
                    if event_format is TournamentFormat.DOUBLES:
                        self.assertEqual([(track.panel.entrant_slot, track.panel.member_slot) for track in layout.tracks],
                                         [(slot, member) for slot in range(5, 9) for member in (1, 2)])
                    else:
                        self.assertEqual([row.asset_id for row in layout.badges], ["09th.png"] * 4 + ["13th.png"] * 4)
                        self.assertFalse(any(row.field == "entrant.primary_character_name" for row in preferences.text_slots))
                        original = ModePreferenceRepository().load(replace(still, options=replace(still.options, entrant_count=8, variant=None)))
                        self.assertEqual([row.anchor.y for row in preferences.character_slots], [row.anchor.y - 48 for row in original.character_slots])

    def test_api_still_and_animated_outputs_composite_the_taller_canvas(self):
        client = app.test_client()
        for event_format, count, variant, height in CASES:
            for animated in (False, True):
                payload = {"style": "customizable", "event_format": event_format.value,
                           "entrant_count": count, "variant": variant, "animated": animated,
                           "transparent": True,
                           "formatting_asset_colors": {"mode": "premade", "preset": "rainbow", "colors": []}}
                response = client.post("/api/format-preview", json=payload)
                self.assertEqual(response.status_code, 200, response.data[:200])
                self.assertEqual(response.mimetype, "image/gif" if animated else "image/png")
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                with Image.open(BytesIO(response.data)) as image:
                    self.assertEqual(image.size, (1920, height))
                    self.assertEqual(image.n_frames, 42 if animated else 1)
                    if animated:
                        self.assertEqual(image.info["loop"], 0)

    def test_doubles_member_costumes_icons_and_seeds_use_one_team_override(self):
        teams = sample_top_8_teams(random.Random(8))
        teams[4] = replace(teams[4], team_color="blue",
                          entrant_1=replace(teams[4].entrant_1, characters=[Character("Fox", color="red")]),
                          entrant_2=replace(teams[4].entrant_2, characters=[Character("Falco", color="red")]))
        captured = []
        class CapturingRenderer(DoublesClappingContentRenderer):
            def _panel_subject(self, request, panel):
                member = super()._panel_subject(request, panel)
                captured.append(member)
                return member
        selection = ModeSelection(CreationMode.PODIUM, ModeOptions(TournamentFormat.DOUBLES, 8, "four_podium", PodiumStyle.LEGACY))
        preferences = ModePreferenceRepository().load(selection)
        request = CreationRequest(selection, BackgroundRequest(preferences.canvas_size), teams, sample_tournament(TournamentFormat.DOUBLES))
        CapturingRenderer(font=PodiumFont.UBUNTU).prepare(Image.new("RGBA", preferences.canvas_size.as_tuple()), request, preferences)
        self.assertEqual([member.characters[0].color for member in captured[:2]], ["blue", "blue"])
        self.assertEqual([member.seed for member in captured[:2]], [teams[4].seed, None])
        self.assertEqual(teams[4].entrant_1.characters[0].color, "red")

    def test_ready_layouts_render_through_creation_pipeline(self):
        for event_format, count, variant, height in CASES:
            selection = ModeSelection(CreationMode.PODIUM, ModeOptions(event_format, count, variant, PodiumStyle.CUSTOMIZABLE))
            preferences = ModePreferenceRepository().load(selection)
            entrants = sample_top_8_teams(random.Random(8)) if count == 8 else sample_singles_entrants(16, random.Random(16))
            request = CreationRequest(selection, BackgroundRequest(preferences.canvas_size), entrants,
                                      sample_tournament(event_format),
                                      podium_colors=PodiumColorConfiguration.from_preset(PodiumColorPreset.LEGACY))
            renderer = DoublesClappingContentRenderer if count == 8 else SinglesTop16ClappingContentRenderer
            image = CreationPipeline({CreationMode.PODIUM: renderer(font=PodiumFont.UBUNTU)}).create(request)
            self.assertEqual(image.size, (1920, height))
            self.assertEqual(image.mode, "RGBA")

    def test_rejects_panels_outside_the_canvas_or_missing_a_team_member(self):
        teams = sample_top_8_teams(random.Random(8))
        selection = ModeSelection(CreationMode.PODIUM, ModeOptions(TournamentFormat.DOUBLES, 8, "four_podium", PodiumStyle.LEGACY))
        preferences = ModePreferenceRepository().load(selection)
        request = CreationRequest(selection, BackgroundRequest(preferences.canvas_size), teams, sample_tournament(TournamentFormat.DOUBLES))
        for invalid in ("outside", "member"):
            class InvalidRenderer(DoublesClappingContentRenderer):
                def _profile(self, request):
                    profile = super()._profile(request)
                    if invalid == "outside":
                        profile["panels"][0]["portrait_rect"][3] = 1281
                    else:
                        profile["panels"].pop()
                    return profile
            with self.assertRaisesRegex(ValueError, "fit every lower entrant"):
                InvalidRenderer().prepare(Image.new("RGBA", preferences.canvas_size.as_tuple()), request, preferences)

    def test_revised_labels_and_badges_follow_portrait_geometry(self):
        for style in PodiumStyle:
            renderer = DoublesClappingContentRenderer()
            selection = ModeSelection(CreationMode.PODIUM, ModeOptions(TournamentFormat.DOUBLES, 8, "four_podium", style))
            profile = renderer._profile(type("Request", (), {"selection": selection})())
            for label in profile["team_names"]:
                panels = [row for row in profile["panels"] if row["entrant_slot"] == label["entrant_slot"]]
                self.assertEqual(panels[0]["portrait_rect"][1], 925)
                self.assertGreater(label["anchor"]["y"], max(row["portrait_rect"][3] for row in panels))
            selection = ModeSelection(CreationMode.PODIUM, ModeOptions(TournamentFormat.SINGLES, 16, "clapping", style))
            profile = SinglesTop16ClappingContentRenderer()._profile(type("Request", (), {"selection": selection})())
            for panel, badge in zip(profile["panels"], profile["placement_tags"], strict=True):
                self.assertEqual(badge["anchor"]["x"], panel["portrait_rect"][2] + 20)
                self.assertEqual(badge["anchor"]["y"], panel["portrait_rect"][3] + 12)

    def test_top16_player_palette_groups_ties_and_legacy_lower_colors_reverse(self):
        from app import _custom_preview_colors
        source = PodiumColorConfiguration.from_preset(PodiumColorPreset.LEGACY)
        teams = sample_singles_entrants(16, random.Random(16))
        for style in PodiumStyle:
            selection = ModeSelection(CreationMode.PODIUM, ModeOptions(TournamentFormat.SINGLES, 16, "clapping", style))
            preferences = ModePreferenceRepository().load(selection)
            colors = resolve_clapping_podium_colors(selection, source) if style is PodiumStyle.CUSTOMIZABLE else None
            request = CreationRequest(selection, BackgroundRequest(preferences.canvas_size), teams,
                                      sample_tournament(), podium_colors=colors)
            actual = [SinglesTop16ClappingContentRenderer._default_text_style(request, slot)[0] for slot in range(1, 17)]
            if style is PodiumStyle.CUSTOMIZABLE:
                expected = [source.color_for_slot(slot).resolve().text_color for slot in TOP16_PLAYER_COLOR_SLOTS]
                self.assertEqual(actual, expected)
            else:
                self.assertEqual(actual[8:], actual[:8][::-1])
            override = replace(request, text_settings=TextSettings(entrant_text_color_mode="pick_1", entrant_text_colors=("#12345678",)))
            self.assertEqual(SinglesTop16ClappingContentRenderer._default_text_style(override, 16), ("#12345678", False))
        api_colors = _custom_preview_colors({"mode": "premade", "preset": "smash_player_colors", "colors": [],
                    "preset_transparency": {"main_color": 50, "face_color": 25, "base_color": 75}}, 16, "clapping")
        for slot, source_slot in enumerate(TOP16_PLAYER_COLOR_SLOTS, start=1):
            actual = api_colors.color_for_slot(slot).resolve()
            original = source.color_for_slot(source_slot).resolve()
            self.assertEqual(actual.main_color, original.main_color[:7] + "80")
            self.assertEqual(actual.face_color, original.face_color[:7] + "BF")
            self.assertEqual(actual.base_color, original.base_color[:7] + "40")

    def test_new_canvas_composition_is_retained_in_every_gif_frame(self):
        def upload(image):
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer
        for event_format, count, variant, height in CASES:
            background = Image.new("RGBA", (1672, height), "#123456FF")
            overlay = Image.new("RGBA", background.size, "#00000000")
            overlay.paste("#CC6633FF", (700, 25, 720, 45))
            response = app.test_client().post("/api/format-preview", data={
                "config": json.dumps({"style": "legacy", "event_format": event_format.value,
                                      "entrant_count": count, "variant": variant, "animated": True, "transparent": True}),
                "composite_background": (upload(background), "background.png"),
                "composite_overlay": (upload(overlay), "overlay.png"),
            })
            self.assertEqual(response.status_code, 200)
            with Image.open(BytesIO(response.data)) as image:
                reference_pixels = {}
                for index in (0, 18, 41):
                    image.seek(index)
                    frame = image.convert("RGBA")
                    # The footer can now choose the middle after team labels move.
                    # Sample the clear gap between the two lower result groups.
                    for point, expected in (((836, height - 100), (18, 52, 86)), ((710, 30), (204, 102, 51))):
                        actual = frame.getpixel(point)
                        self.assertEqual(actual[3], 255)
                        # GIF indexing can shift a rare logo color more in one
                        # channel; check aggregate color error and exact stability.
                        self.assertLess(sum((a - b) ** 2 for a, b in zip(actual[:3], expected)), 3 * 32 ** 2,
                                        f"{event_format} frame {index}, pixel {point}: {actual}")
                        if index == 0:
                            reference_pixels[point] = actual
                        else:
                            self.assertEqual(actual, reference_pixels[point])


if __name__ == "__main__":
    unittest.main()

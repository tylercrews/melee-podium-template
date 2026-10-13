"""Verify persistence, animation compositing, and the reviewed portrait geometry."""

from dataclasses import replace
from io import BytesIO
import unittest

from PIL import Image, ImageChops

from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from DrawPodium import PodiumFont
from format_preview import prepare_format_preview
from mode_preferences import ModePreferenceRepository
from models import TournamentFormat
from gif_animation import encode_animated_gif
from sample_creation_data import sample_clapping_top_8_entrants


class PodiumsClappingTest(unittest.TestCase):
    def test_backward_compatible_selection_and_shared_geometry(self):
        repository = ModePreferenceRepository()
        for style in PodiumStyle:
            selection = ModeSelection(CreationMode.PODIUM, ModeOptions(TournamentFormat.SINGLES, 8, "four_podium", style))
            old = selection.to_dict()
            del old["options"]["animated"]
            self.assertTrue(ModeSelection.from_dict(old).options.animated)
            still = replace(selection, options=replace(selection.options, animated=False))
            self.assertEqual(ModeSelection.from_dict(still.to_dict()), still)
            self.assertEqual(repository.path_for(selection), repository.path_for(still))
            animated_preferences, still_preferences = repository.load(selection), repository.load(still)
            self.assertEqual(still_preferences.selection, still)
            self.assertEqual(animated_preferences.formatting_assets, still_preferences.formatting_assets)
            self.assertFalse(still_preferences.ready)

    def test_rejects_invalid_animation_settings(self):
        for animated in ("false", 1, [], None):
            with self.assertRaises(TypeError):
                ModeOptions.from_dict({"event_format": "singles", "entrant_count": 8,
                                       "variant": "four_podium", "podium_style": "legacy", "animated": animated})
        with self.assertRaises(ValueError):
            ModeOptions(TournamentFormat.SINGLES, 4, podium_style=PodiumStyle.LEGACY, animated=True)

    def test_gif_clears_moving_transparent_pixels_preserves_timing_and_loops(self):
        first = Image.new("RGBA", (8, 6), "#00000000")
        first.putpixel((3, 2), (255, 0, 0, 255))
        first.putpixel((0, 0), (0, 0, 255, 255))
        second = first.copy()
        second.putpixel((3, 2), (0, 0, 0, 0))
        second.putpixel((5, 2), (255, 0, 0, 255))
        data = encode_animated_gif(lambda index: (first, second)[index], [20, 30])
        with Image.open(BytesIO(data)) as animation:
            self.assertEqual(animation.n_frames, 2)
            self.assertEqual(animation.info["loop"], 0)
            self.assertEqual(animation.info["duration"], 20)
            animation.seek(1)
            self.assertEqual(animation.info["duration"], 30)
            self.assertEqual(animation.convert("RGBA").getpixel((3, 2)), (0, 0, 0, 0))
            self.assertEqual(animation.convert("RGBA").getpixel((0, 0)), first.getpixel((0, 0)))

    def test_real_layout_uses_all_frames_and_only_portraits_move(self):
        layout = prepare_format_preview(PodiumStyle.LEGACY, TournamentFormat.SINGLES, 8, "four_podium",
                                        font=PodiumFont.UBUNTU, transparent=True)
        self.assertEqual([track.panel.rect.right for track in layout.tracks[::2]], [424, 1211])
        self.assertEqual([track.panel.rect.left for track in layout.tracks[1::2]], [469, 1243])
        first, later = layout.frame(0), layout.frame(18)
        self.assertIsNotNone(layout.footer_placement)
        self.assertGreaterEqual(layout.footer_placement.bounds[1], 900)
        ink_width = layout.footer_placement.bounds[2] - layout.footer_placement.bounds[0]
        self.assertIn(layout.footer_placement.bounds[0], (10, (first.width - ink_width) // 2, first.width - 10 - ink_width))
        self.assertNotEqual(first.tobytes(), later.tobytes())
        difference = ImageChops.difference(first, later)
        for track in layout.tracks:
            difference.paste("#00000000", track.panel.rect.as_tuple())
        self.assertTrue(all(channel.getbbox() is None for channel in difference.split()))
        with Image.open(BytesIO(layout.gif())) as animation:
            self.assertEqual(animation.format, "GIF")
            self.assertEqual(animation.size, (1672, 941))
            self.assertEqual(animation.n_frames, 42)
            self.assertEqual(animation.info["duration"], 20)
            decoded_first = animation.convert("RGBA")
            animation.seek(18)
            decoded_later = animation.convert("RGBA")
            self.assertNotEqual(decoded_first.tobytes(), decoded_later.tobytes())
            changes = ImageChops.difference(decoded_first, decoded_later)
            for track in layout.tracks:
                changes.paste("#00000000", track.panel.rect.as_tuple())
            self.assertTrue(all(channel.getbbox() is None for channel in changes.split()))
        with Image.open(BytesIO(layout.png())) as still:
            self.assertEqual(still.n_frames, 1)
            self.assertEqual(still.convert("RGBA").tobytes(), layout.frame().tobytes())

    def test_shorter_ice_climbers_clap_shares_the_other_portraits_full_cycle(self):
        layout = prepare_format_preview(PodiumStyle.LEGACY, TournamentFormat.SINGLES, 8, "four_podium",
                                        font=PodiumFont.UBUNTU, transparent=True,
                                        entrants=sample_clapping_top_8_entrants())
        ice = layout.tracks[0]
        self.assertEqual(len(ice.frames), 25)
        self.assertEqual(sum(ice.durations), 500)
        self.assertEqual(len(layout.durations), 42)
        self.assertEqual(sum(layout.durations), 840)
        indices = [ice.frame_index_at(index * 20, 840) for index in range(42)]
        self.assertEqual(set(indices), set(range(25)))
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 24)
        with Image.open(BytesIO(layout.gif())) as animation:
            self.assertEqual(animation.n_frames, 42)
            animation.seek(41)
            self.assertIsNotNone(animation.convert("RGBA").getbbox())
        all_ice = replace(layout, tracks=(ice,))
        with Image.open(BytesIO(all_ice.gif())) as animation:
            self.assertEqual(animation.n_frames, 25)
            self.assertEqual(sum(all_ice.durations), 500)


if __name__ == "__main__":
    unittest.main()

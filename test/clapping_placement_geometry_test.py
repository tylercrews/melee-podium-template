"""Legacy front-corner alignment leaves room for the lower placement numbers."""

from pathlib import Path
import sys
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'test/generate'))

from creation_modes import CreationMode, ModeOptions, ModeSelection, PodiumStyle
from mode_preferences import ModePreferenceRepository
from models import TournamentFormat
from generate_clapping_four_podium_placement import lower_result_geometry


class ClappingPlacementGeometryTests(unittest.TestCase):
    def preferences(self, style):
        return ModePreferenceRepository().load(ModeSelection(CreationMode.PODIUM, ModeOptions(
            event_format=TournamentFormat.SINGLES, entrant_count=8,
            variant='four_podium', podium_style=style,
        )))

    def test_legacy_portraits_follow_visible_front_corners(self):
        rows, badges = lower_result_geometry(self.preferences(PodiumStyle.LEGACY), 23)
        self.assertEqual([row['portrait_rect'][2] for row in rows[::2]], [424, 1211])
        self.assertEqual([row['portrait_rect'][0] for row in rows[1::2]], [469, 1243])
        for pair in range(2):
            first_right = rows[pair * 2]['portrait_rect'][2]
            second_left = rows[pair * 2 + 1]['portrait_rect'][0]
            for badge in badges[pair * 2:pair * 2 + 2]:
                with Image.open(ROOT / 'formatting_assets/placement_numbers' / badge.asset_id) as art:
                    art.thumbnail(badge.max_size.as_tuple())
                    left = badge.anchor.x - art.width // 2
                    self.assertGreaterEqual(left, first_right)
                    self.assertLessEqual(left + art.width, second_left)

    def test_customizable_columns_keep_their_existing_positions(self):
        rows, _ = lower_result_geometry(self.preferences(PodiumStyle.CUSTOMIZABLE), 23)
        self.assertEqual([row['portrait_rect'] for row in rows], [
            [411, 830, 479, 934], [533, 830, 601, 934],
            [1369, 830, 1437, 934], [1491, 830, 1559, 934],
        ])
        self.assertEqual([row['text_x'] for row in rows], [397, 615, 1355, 1573])


if __name__ == '__main__':
    unittest.main()

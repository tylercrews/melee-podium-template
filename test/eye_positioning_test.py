"""Coverage and renderability tests for every Eyes portrait focal point."""

from collections import defaultdict
import unittest

from eyes_portrait_renderer import render_eye_portrait
from models import Character
from portrait_assets import CHARACTER_FOLDER, PORTRAIT_FILENAME
from portrait_scale_adjustment_for_eyes import EYE_PORTRAIT_ADJUSTMENTS


def available_poses() -> dict[str, dict[str, list]]:
    poses = defaultdict(lambda: defaultdict(list))
    for path in sorted(CHARACTER_FOLDER.glob("*/*.png")):
        match = PORTRAIT_FILENAME.match(path.name)
        if match is not None:
            poses[path.parent.name][match.group("pose").casefold()].append(path)
    return {character: dict(character_poses) for character, character_poses in poses.items()}


class EyePositioningTest(unittest.TestCase):
    def test_every_available_pose_has_exactly_one_reviewed_adjustment(self) -> None:
        poses = available_poses()

        self.assertEqual(set(EYE_PORTRAIT_ADJUSTMENTS), set(poses))
        for character, character_poses in poses.items():
            self.assertEqual(
                set(EYE_PORTRAIT_ADJUSTMENTS[character]),
                set(character_poses),
                character,
            )

    def test_every_pose_focal_point_renders_visible_pixels_at_center(self) -> None:
        for character_name, poses in available_poses().items():
            for pose, paths in poses.items():
                path = next(
                    (candidate for candidate in paths if "_default_" in candidate.name),
                    paths[0],
                )
                match = PORTRAIT_FILENAME.match(path.name)
                assert match is not None
                character = Character(
                    character_name,
                    color=match.group("color"),
                    pose=pose,
                )

                with self.subTest(character=character_name, pose=pose):
                    crop = render_eye_portrait(character, (780, 160))
                    self.assertEqual(crop.mode, "RGBA")
                    self.assertEqual(crop.size, (780, 160))
                    center_sample = crop.getchannel("A").crop((370, 60, 410, 100))
                    self.assertIsNotNone(center_sample.getbbox())


if __name__ == "__main__":
    unittest.main()

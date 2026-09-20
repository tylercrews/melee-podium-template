"""Tests for customizable-podium color input and resolution."""

import unittest

from PIL import Image

from color_values import parse_rgba_hex
from podium_colors import (
    FACE_LIGHTNESS_RATIO,
    PodiumColorSelection,
    apply_podium_colors,
)


class PodiumColorsTest(unittest.TestCase):
    def test_main_only_derives_face_and_black_base_with_main_alpha(self) -> None:
        colors = PodiumColorSelection("#D9030080", metallic=True).resolve()

        self.assertEqual(colors.main_color, "#D9030080")
        self.assertEqual(colors.base_color, "#00000080")
        self.assertEqual(colors.face_color[-2:], "80")
        self.assertTrue(colors.metallic)
        main_rgb = parse_rgba_hex(colors.main_color)[:3]
        face_rgb = parse_rgba_hex(colors.face_color)[:3]
        self.assertLess(max(face_rgb), max(main_rgb))

    def test_main_and_face_keep_explicit_face_and_default_the_base(self) -> None:
        colors = PodiumColorSelection(
            main_color="#11223340",
            face_color="#44556670",
        ).resolve()

        self.assertEqual(colors.face_color, "#44556670")
        self.assertEqual(colors.base_color, "#00000040")

    def test_all_three_inputs_are_preserved(self) -> None:
        selection = PodiumColorSelection(
            main_color="#10203040",
            face_color="#50607080",
            base_color="#90A0B0C0",
            metallic=False,
        )

        self.assertEqual(
            selection.resolve().to_dict(),
            {
                "main_color": "#10203040",
                "face_color": "#50607080",
                "base_color": "#90A0B0C0",
                "metallic": False,
            },
        )
        self.assertEqual(
            PodiumColorSelection.from_dict(selection.to_dict()),
            selection,
        )

    def test_every_color_requires_eight_digit_rgba_hex(self) -> None:
        invalid_values = ("#123456", "123456FF", "#GG0000FF", "")
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "#RRGGBBAA"):
                    PodiumColorSelection(value)
        with self.assertRaisesRegex(TypeError, "boolean"):
            PodiumColorSelection("#000000FF", metallic=1)  # type: ignore[arg-type]

    def test_face_ratio_is_derived_from_existing_color_pairs(self) -> None:
        self.assertGreater(FACE_LIGHTNESS_RATIO, 0)
        self.assertLess(FACE_LIGHTNESS_RATIO, 1)

    def test_mask_classes_map_to_main_face_and_base_and_combine_alpha(self) -> None:
        mask = Image.new("RGBA", (4, 1))
        mask.putdata(
            [
                (255, 0, 0, 255),
                (0, 255, 255, 128),
                (0, 0, 255, 255),
                (255, 255, 0, 255),
            ]
        )

        result = apply_podium_colors(
            mask,
            PodiumColorSelection(
                main_color="#10203040",
                face_color="#50607080",
                base_color="#90A0B0C0",
            ),
        )

        self.assertEqual(
            list(result.getdata()),
            [
                (16, 32, 48, 64),
                (80, 96, 112, 64),
                (144, 160, 176, 192),
                (255, 255, 0, 255),
            ],
        )


if __name__ == "__main__":
    unittest.main()

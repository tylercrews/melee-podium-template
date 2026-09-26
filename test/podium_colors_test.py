"""Tests for customizable-podium color input and resolution."""

import unittest

from PIL import Image

from color_values import parse_rgba_hex
from podium_colors import (
    FACE_LIGHTNESS_RATIO,
    PodiumColorConfiguration,
    PodiumColorPreset,
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
        self.assertEqual(colors.text_color, "#11223340")

    def test_explicit_text_color_overrides_the_main_color_default(self) -> None:
        colors = PodiumColorSelection(
            "#112233FF", text_color="#FEDCBAFF"
        ).resolve()
        self.assertEqual(colors.text_color, "#FEDCBAFF")

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
                "text_color": "#10203040",
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

    def test_shaded_semantic_pixels_are_recolored_without_touching_yellow(self) -> None:
        mask = Image.new("RGBA", (4, 1))
        mask.putdata(
            [(215, 40, 40, 255), (40, 215, 215, 255), (0, 0, 40, 255), (255, 255, 0, 255)]
        )
        result = apply_podium_colors(
            mask,
            PodiumColorSelection("#C80000FF", "#640000FF", "#320000FF"),
        )
        pixels = list(result.getdata())
        self.assertEqual(pixels[-1], (255, 255, 0, 255))
        self.assertTrue(all(green == blue == 0 for _, green, blue, _ in pixels[:3]))

    def test_metallic_finish_adds_a_highlight_to_the_main_mask(self) -> None:
        mask = Image.new("RGBA", (5, 1), (255, 0, 0, 255))
        flat = apply_podium_colors(mask, PodiumColorSelection("#806020FF"))
        metallic = apply_podium_colors(
            mask, PodiumColorSelection("#806020FF", metallic=True)
        )
        self.assertNotEqual(list(flat.getdata()), list(metallic.getdata()))
        self.assertGreater(max(red for red, _, _, _ in metallic.getdata()), 128)

    def test_legacy_and_medal_presets_resolve_all_eight_slots(self) -> None:
        legacy = PodiumColorConfiguration.from_preset(PodiumColorPreset.LEGACY)
        medals = PodiumColorConfiguration.from_preset(PodiumColorPreset.MEDALS)
        self.assertEqual(legacy.color_for_slot(1).main_color, "#D90300FF")
        self.assertEqual(legacy.color_for_slot(8).main_color, "#8D8D8DFF")
        self.assertTrue(all(medals.color_for_slot(slot).metallic for slot in (1, 2, 3)))
        self.assertEqual(
            {medals.color_for_slot(slot).main_color for slot in range(4, 9)},
            {"#707070FF"},
        )

    def test_custom_and_alternating_modes_are_serializable(self) -> None:
        red = PodiumColorSelection("#FF0000FF")
        blue = PodiumColorSelection("#0000FFFF")
        custom = PodiumColorConfiguration.per_podium(red, blue)
        alternating = PodiumColorConfiguration.alternating(red, blue)
        self.assertEqual(custom.color_for_slot(2), blue)
        self.assertEqual(alternating.color_for_slot(3), red)
        self.assertEqual(alternating.color_for_slot(4), blue)
        for configuration in (
            custom,
            alternating,
            PodiumColorConfiguration.from_preset(PodiumColorPreset.MEDALS),
        ):
            self.assertEqual(
                PodiumColorConfiguration.from_dict(configuration.to_dict()),
                configuration,
            )


if __name__ == "__main__":
    unittest.main()

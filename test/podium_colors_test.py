"""Tests for customizable-podium color input and resolution."""

import unittest

from PIL import Image, ImageChops

from color_values import parse_rgba_hex
from podium_colors import (
    BASE_MASK_COLOR,
    FACE_LIGHTNESS_RATIO,
    FACE_MASK_COLOR,
    MAIN_MASK_COLOR,
    PodiumColorConfiguration,
    PodiumColorPreset,
    PodiumColorSelection,
    apply_podium_colors,
)


def _per_pixel_podium_colors(mask: Image.Image, selection: PodiumColorSelection) -> Image.Image:
    """The original per-pixel recolor, kept as the reference for the fast path."""

    colors = selection.resolve()
    replacements = {
        MAIN_MASK_COLOR: parse_rgba_hex(colors.main_color),
        FACE_MASK_COLOR: parse_rgba_hex(colors.face_color),
        BASE_MASK_COLOR: parse_rgba_hex(colors.base_color),
    }
    source = mask.convert("RGBA")
    output = []
    for pixel_index, (red, green, blue, source_alpha) in enumerate(source.getdata()):
        if red >= 2 * max(green, blue) and red > 0:
            semantic = MAIN_MASK_COLOR
        elif min(green, blue) >= 2 * red and min(green, blue) > 0:
            semantic = FACE_MASK_COLOR
        elif blue >= 2 * max(red, green) and blue > 0:
            semantic = BASE_MASK_COLOR
        else:
            output.append((red, green, blue, source_alpha))
            continue
        replacement = replacements[semantic]
        active = tuple(index for index, channel in enumerate(semantic) if channel)
        intensity = sum((red, green, blue)[index] for index in active) / (255 * len(active))
        rendered = tuple(round(channel * intensity) for channel in replacement[:3])
        if colors.metallic and semantic == MAIN_MASK_COLOR:
            x, y = pixel_index % source.width, pixel_index // source.width
            diagonal = x / max(1, source.width - 1) + 0.3 * y / max(1, source.height - 1)
            highlight = max(0.0, 1.0 - abs(diagonal - 0.62) / 0.13) * 0.32
            rendered = tuple(round(channel + (255 - channel) * highlight) for channel in rendered)
        output.append((*rendered, round(source_alpha * replacement[3] / 255)))
    result = Image.new("RGBA", source.size)
    result.putdata(output)
    return result


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

    def test_channel_operations_match_the_per_pixel_recolor(self) -> None:
        # Every red/green/blue combination at several alphas crosses each
        # class boundary, including gray, shaded, and unrecognized pixels.
        mask = Image.new("RGBA", (256, 256))
        mask.putdata([
            (x, (y % 16) * 17, (y // 16) * 17, (x * 7 + y * 13) % 256)
            for y in range(256) for x in range(256)
        ])
        selections = (
            PodiumColorSelection("#D90300FF"),
            PodiumColorSelection("#10203040", "#50607080", "#90A0B0C0"),
            PodiumColorSelection("#C9A227FF", metallic=True),
            PodiumColorSelection("#7F7F7F80", "#33445566", metallic=True),
        )
        for selection in selections:
            with self.subTest(selection=selection):
                difference = ImageChops.difference(
                    apply_podium_colors(mask, selection),
                    _per_pixel_podium_colors(mask, selection),
                )
                worst = max(high for _low, high in difference.getextrema())
                # The metallic highlight is sampled along its diagonal, which
                # may round one channel level differently.
                self.assertLessEqual(worst, 1 if selection.metallic else 0)

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

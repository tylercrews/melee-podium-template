"""Focused tests for the independent background compositor."""

import unittest

from PIL import Image

from background_builder import (
    BACKGROUND_FORMAT_SIZES,
    BUILTIN_BACKGROUND_SIZES,
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_CROP_POSITIONS,
    DEFAULT_IMAGE_ALIGNMENTS,
    BackgroundRequest,
    ImagePlacement,
    LocalBackgroundAssets,
    PixelRect,
    PixelSize,
    create_background,
    cover_crop,
    default_placement,
    parse_rgba_hex,
)


class MemoryBackgroundAssets:
    """Small in-memory provider so unit tests do not depend on the filesystem."""

    def __init__(self, **images: Image.Image) -> None:
        self.images = images

    def open(self, asset_id: str) -> Image.Image:
        try:
            return self.images[asset_id].copy()
        except KeyError as error:
            raise FileNotFoundError(asset_id) from error


class BackgroundBuilderTest(unittest.TestCase):
    def test_default_is_fully_transparent_black(self) -> None:
        request = BackgroundRequest(PixelSize(3, 2))

        result = create_background(request)

        self.assertEqual(DEFAULT_BACKGROUND_COLOR, "#00000000")
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, (3, 2))
        self.assertEqual(result.getpixel((1, 1)), (0, 0, 0, 0))

    def test_rgba_hex_keeps_alpha_as_the_last_channel(self) -> None:
        self.assertEqual(parse_rgba_hex("#12345678"), (0x12, 0x34, 0x56, 0x78))
        with self.assertRaisesRegex(ValueError, "#RRGGBBAA"):
            parse_rgba_hex("#123456")

    def test_request_round_trips_through_json_friendly_dict(self) -> None:
        original = BackgroundRequest(
            size=PixelSize(100, 50),
            fill_color="#10203040",
            image=ImagePlacement(
                "example.png",
                source_crop=PixelRect(5, 6, 45, 36),
                destination=PixelRect(-10, 2, 70, 42),
            ),
        )

        restored = BackgroundRequest.from_dict(original.to_dict())

        self.assertEqual(restored, original)

    def test_small_image_is_positioned_over_the_fill_color(self) -> None:
        request = BackgroundRequest(
            size=PixelSize(4, 4),
            fill_color="#0000FFFF",
            image=ImagePlacement(
                asset_id="small.png",
                source_crop=PixelRect(0, 0, 2, 2),
                destination=PixelRect(1, 1, 3, 3),
            ),
        )

        result = create_background(
            request,
            assets=MemoryBackgroundAssets(
                **{"small.png": Image.new("RGBA", (2, 2), (255, 0, 0, 255))}
            ),
        )

        self.assertEqual(result.getpixel((0, 0)), (0, 0, 255, 255))
        self.assertEqual(result.getpixel((1, 1)), (255, 0, 0, 255))
        self.assertEqual(result.getpixel((2, 2)), (255, 0, 0, 255))
        self.assertEqual(result.getpixel((3, 3)), (0, 0, 255, 255))

    def test_large_image_uses_only_the_selected_source_crop(self) -> None:
        source = Image.new("RGBA", (6, 2), (255, 0, 0, 255))
        for x in range(2, 4):
            for y in range(2):
                source.putpixel((x, y), (0, 255, 0, 255))
        request = BackgroundRequest(
            size=PixelSize(4, 4),
            image=ImagePlacement(
                asset_id="large.png",
                source_crop=PixelRect(2, 0, 4, 2),
                destination=PixelRect(0, 0, 4, 4),
            ),
        )

        result = create_background(
            request,
            assets=MemoryBackgroundAssets(**{"large.png": source}),
        )

        self.assertEqual(set(result.getdata()), {(0, 255, 0, 255)})

    def test_destination_is_clipped_to_the_canvas(self) -> None:
        request = BackgroundRequest(
            size=PixelSize(3, 3),
            fill_color="#0000FFFF",
            image=ImagePlacement(
                asset_id="offset.png",
                source_crop=PixelRect(0, 0, 3, 3),
                destination=PixelRect(-2, -2, 1, 1),
            ),
        )

        result = create_background(
            request,
            assets=MemoryBackgroundAssets(
                **{"offset.png": Image.new("RGBA", (3, 3), (255, 0, 0, 255))}
            ),
        )

        self.assertEqual(result.getpixel((0, 0)), (255, 0, 0, 255))
        self.assertEqual(result.getpixel((1, 1)), (0, 0, 255, 255))

    def test_local_provider_rejects_paths_in_asset_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "filename"):
            LocalBackgroundAssets().open("../outside.png")

    def test_every_builtin_has_a_default_crop_for_every_format(self) -> None:
        expected_assets = set(BUILTIN_BACKGROUND_SIZES)
        self.assertEqual(set(DEFAULT_CROP_POSITIONS), set(BACKGROUND_FORMAT_SIZES))
        for format_id, crops in DEFAULT_CROP_POSITIONS.items():
            self.assertEqual(set(crops), expected_assets)
            for asset_id, crop in crops.items():
                source_size = BUILTIN_BACKGROUND_SIZES[asset_id]
                self.assertGreaterEqual(crop.left, 0)
                self.assertGreaterEqual(crop.top, 0)
                self.assertLessEqual(crop.right, source_size.width)
                self.assertLessEqual(crop.bottom, source_size.height)
                placement = default_placement(format_id, asset_id)
                self.assertEqual(
                    (placement.destination.width, placement.destination.height),
                    BACKGROUND_FORMAT_SIZES[format_id].as_tuple(),
                )

    def test_builtin_registry_matches_the_numbered_background_files(self) -> None:
        actual_assets = {
            asset.asset_id for asset in LocalBackgroundAssets().list_assets()
        }

        self.assertEqual(set(BUILTIN_BACKGROUND_SIZES), actual_assets)

    def test_default_images_are_centered_except_final_destination_space(self) -> None:
        self.assertEqual(set(DEFAULT_IMAGE_ALIGNMENTS), set(BUILTIN_BACKGROUND_SIZES))
        bottom_asset = "05_FinalDestinationSpace_5000_5000_resaved.png"
        self.assertEqual(DEFAULT_IMAGE_ALIGNMENTS[bottom_asset], ("center", "bottom"))
        for asset_id, alignment in DEFAULT_IMAGE_ALIGNMENTS.items():
            if asset_id != bottom_asset:
                self.assertEqual(alignment, ("center", "center"))

        for format_id, output_size in BACKGROUND_FORMAT_SIZES.items():
            crops = DEFAULT_CROP_POSITIONS[format_id]
            for asset_id, source_size in BUILTIN_BACKGROUND_SIZES.items():
                horizontal_alignment, vertical_alignment = DEFAULT_IMAGE_ALIGNMENTS[
                    asset_id
                ]
                expected = cover_crop(
                    source_size,
                    output_size,
                    horizontal_alignment=horizontal_alignment,
                    vertical_alignment=vertical_alignment,
                )
                self.assertEqual(crops[asset_id], expected)


if __name__ == "__main__":
    unittest.main()

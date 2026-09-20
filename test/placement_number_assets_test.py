"""Regression checks for the canonical placement-number asset set."""

from pathlib import Path
import unittest

from PIL import Image


ASSET_FOLDER = (
    Path(__file__).resolve().parents[1] / "formatting_assets" / "placement_numbers"
)
TARGET_SILVER_RGBA = "#B7B6B6FF"


def ordinal_suffix(value: int) -> str:
    if 10 < value % 100 < 14:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")


def masked_channel_median(channel: Image.Image, mask: Image.Image) -> int:
    histogram = channel.histogram(mask=mask)
    midpoint = (sum(histogram) + 1) // 2
    running_total = 0
    for value, count in enumerate(histogram):
        running_total += count
        if running_total >= midpoint:
            return value
    raise AssertionError("asset contains no visible pixels")


class PlacementNumberAssetsTest(unittest.TestCase):
    def test_assets_use_canonical_zero_padded_ordinal_names(self) -> None:
        expected = {
            f"{value:02d}{ordinal_suffix(value)}.png" for value in range(1, 26)
        }

        self.assertEqual({path.name for path in ASSET_FOLDER.glob("*.png")}, expected)

    def test_second_through_twenty_fifth_share_the_reference_silver(self) -> None:
        target = tuple(
            int(TARGET_SILVER_RGBA[index : index + 2], 16)
            for index in (1, 3, 5)
        )
        for value in range(2, 26):
            path = ASSET_FOLDER / f"{value:02d}{ordinal_suffix(value)}.png"
            with Image.open(path) as source:
                red, green, blue, alpha = source.convert("RGBA").split()
            mask = alpha.point(lambda channel: 255 if channel >= 128 else 0)
            medians = tuple(
                masked_channel_median(channel, mask)
                for channel in (red, green, blue)
            )
            self.assertTrue(
                all(abs(actual - expected) <= 1 for actual, expected in zip(medians, target)),
                f"{path.name} median color was {medians}",
            )

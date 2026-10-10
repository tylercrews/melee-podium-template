"""Doubles-only focal and zoom adjustments for Eyes portraits.

Singles already calibrates every pose around its eye focal point. Doubles uses
half-width portrait windows, so inheriting the Singles zoom made characters
roughly half-sized. The default 2x multiplier restores the same effective
portrait scale. Pose-specific entries below are the review surface for any
additional doubles-only focus or size corrections.
"""

from __future__ import annotations

from dataclasses import dataclass

from portrait_scale_adjustment_for_eyes import (
    EYE_PORTRAIT_ADJUSTMENTS,
    EyePortraitAdjustment,
    get_eye_portrait_adjustment,
)


@dataclass(frozen=True, slots=True)
class DoublesEyePortraitAdjustment:
    zoom_multiplier: float = 2.0
    focal_x_offset: int = 0
    focal_y_offset: int = 0

    def __post_init__(self) -> None:
        if self.zoom_multiplier <= 0:
            raise ValueError("Doubles eye portrait zoom must be greater than zero")


# How to adjust Doubles: add/edit a character and lowercase pose letter below.
# DoublesEyePortraitAdjustment(zoom_multiplier, focal_x_offset, focal_y_offset)
# resolves to Singles zoom * multiplier and Singles focal point + offsets.
# Unlisted poses use DOUBLES_DEFAULT (2x zoom, zero offsets); an override replaces
# that entire default, so specify all non-default offsets you want to retain.
# Higher multiplier zooms IN; lower multiplier zooms OUT. For unmirrored portraits,
# increase focal_x_offset to move LEFT, decrease it to move RIGHT; increase
# focal_y_offset to move UP, decrease it to move DOWN. Horizontal moves reverse
# when mirrored. For CROP movement over the source, reverse these directions:
# lower X/Y pans the crop LEFT/UP; higher X/Y pans it RIGHT/DOWN.
# Offsets are original source pixels, not viewport pixels; try
# 10-30 pixels or a 0.05-0.10 multiplier change, then inspect the result.
# These overrides affect Doubles and Radial, leaving Eyes Singles unchanged.
# Some entries compensate Singles-only changes to preserve reviewed Doubles
# framing. Their zoom expressions retain old Singles zoom * old multiplier,
# divided by the new Singles zoom. Keep them when adjusting unrelated poses.
# From the project root, regenerate and review the pink-crosshair crop sheets:
# python test/generate/generate_eye_doubles_positioning_previews.py
# python test/generate/generate_eye_positioning_previews.py
EYE_DOUBLES_PORTRAIT_OVERRIDES: dict[
    str,
    dict[str, DoublesEyePortraitAdjustment],
] = {
    "Captain Falcon": {
        "d": DoublesEyePortraitAdjustment(
            3.00 * 2.5 / 8.00,
            focal_x_offset=90,
            focal_y_offset=25,
        ),
        "e": DoublesEyePortraitAdjustment(2.4),
    },
    "Dr. Mario": {
        "a": DoublesEyePortraitAdjustment(1.7),
    },
    "Falco": {
        "e": DoublesEyePortraitAdjustment(1.7, focal_x_offset=100),
    },
    "Fox": {
        "f": DoublesEyePortraitAdjustment(1.45 * 2.0 / 1.35, focal_y_offset=30),
    },
    "Ganondorf": {
        "a": DoublesEyePortraitAdjustment(1.60 * 2.5 / 1.55, focal_y_offset=20),
        "b": DoublesEyePortraitAdjustment(2.2, focal_x_offset=80, focal_y_offset=30),
        "c": DoublesEyePortraitAdjustment(1.70 * 2.0 / 1.80),
    },
    "Ice Climbers": {
        "a": DoublesEyePortraitAdjustment(
            1.8 / 0.80,
            focal_x_offset=-70,
            focal_y_offset=-65,
        ),
        "b": DoublesEyePortraitAdjustment(2.0, focal_x_offset=25),
        "c": DoublesEyePortraitAdjustment(2.0, focal_y_offset=10),
    },
    "Luigi": {
        "b": DoublesEyePortraitAdjustment(2.0, focal_x_offset=-40),
        "c": DoublesEyePortraitAdjustment(1.20 * 2.0 / 1.15),
        "d": DoublesEyePortraitAdjustment(
            1.9500000000000004,
            focal_x_offset=-40,
            focal_y_offset=-65,
        ),
    },
    "Mario": {
        "a": DoublesEyePortraitAdjustment(1.7),
        "b": DoublesEyePortraitAdjustment(2.0, focal_x_offset=20, focal_y_offset=20),
        "c": DoublesEyePortraitAdjustment(1.7, focal_x_offset=40, focal_y_offset=40),
    },
    "Marth": {
        "a": DoublesEyePortraitAdjustment(2.6),
        "d": DoublesEyePortraitAdjustment(3.0),
        "e": DoublesEyePortraitAdjustment(3.2),
    },
    "Mr. Game and Watch": {
        "a": DoublesEyePortraitAdjustment(1.7, focal_y_offset=15),
        "b": DoublesEyePortraitAdjustment(1.7, focal_y_offset=20),
        "c": DoublesEyePortraitAdjustment(
            1.20 * 1.5 / 1.00,
            focal_x_offset=-100,
            focal_y_offset=170,
        ),
    },
    "Ness": {
        "a": DoublesEyePortraitAdjustment(1.6, focal_x_offset=40),
        "b": DoublesEyePortraitAdjustment(1.6),
    },
    "Peach": {
        "b": DoublesEyePortraitAdjustment(
            1.10 * 2.0 / 1.00,
            focal_x_offset=25,
            focal_y_offset=25,
        ),
        "c": DoublesEyePortraitAdjustment(
            3.3 / 1.90,
            focal_x_offset=-35,
            focal_y_offset=20,
        ),
    },
    "Pikachu": {
        "d": DoublesEyePortraitAdjustment(2.0, focal_y_offset=-28),
    },
    "Samus": {
        "b": DoublesEyePortraitAdjustment(1.7607142857142857, focal_y_offset=-30),
        "c": DoublesEyePortraitAdjustment(2.0, focal_y_offset=-40),
        "d": DoublesEyePortraitAdjustment(2.0, focal_y_offset=-20),
    },
    "Sheik": {
        "c": DoublesEyePortraitAdjustment(1.50 * 1.6 / 1.45, focal_y_offset=-30),
        "d": DoublesEyePortraitAdjustment(2.0, focal_y_offset=20),
        "e": DoublesEyePortraitAdjustment(2.0, focal_y_offset=-10),
    },
    "Yoshi": {
        "a": DoublesEyePortraitAdjustment(1.5, focal_y_offset=55),
        "b": DoublesEyePortraitAdjustment(1.20 * 1.4 / 1.05, focal_y_offset=20),
        "c": DoublesEyePortraitAdjustment(2.25 / 1.25, focal_x_offset=-40),
        "d": DoublesEyePortraitAdjustment(1.80 * 1.15 / 1.20),
    },
    "Young Link": {
        "a": DoublesEyePortraitAdjustment(1.6),
        "c": DoublesEyePortraitAdjustment(1.5, focal_y_offset=35),
    },
    "Zelda": {
        "a": DoublesEyePortraitAdjustment(2.0, focal_x_offset=45),
    },
    "Roy": {
        "c": DoublesEyePortraitAdjustment(
            3 / 4.00,
            focal_x_offset=5,
            focal_y_offset=24,
        ),
    },
}

DOUBLES_DEFAULT = DoublesEyePortraitAdjustment()


def get_doubles_eye_portrait_adjustment(
    character: str,
    pose_code: str,
) -> EyePortraitAdjustment:
    """Return a doubles-specific adjustment for one reviewed portrait pose."""

    pose = pose_code.casefold().removeprefix("00")
    base = get_eye_portrait_adjustment(character, pose)
    override = EYE_DOUBLES_PORTRAIT_OVERRIDES.get(character, {}).get(
        pose,
        DOUBLES_DEFAULT,
    )
    return EyePortraitAdjustment(
        focal_x=base.focal_x + override.focal_x_offset,
        focal_y=base.focal_y + override.focal_y_offset,
        zoom=base.zoom * override.zoom_multiplier,
    )


def missing_doubles_pose_profiles() -> tuple[tuple[str, str], ...]:
    """Return source poses that cannot resolve through the doubles profile."""

    missing: list[tuple[str, str]] = []
    for character, poses in EYE_PORTRAIT_ADJUSTMENTS.items():
        for pose in poses:
            try:
                get_doubles_eye_portrait_adjustment(character, pose)
            except (KeyError, ValueError):
                missing.append((character, pose))
    return tuple(missing)

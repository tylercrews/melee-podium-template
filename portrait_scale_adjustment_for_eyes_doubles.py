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


# Add only reviewed exceptions here. Every unlisted pose still has an explicit
# doubles profile through DOUBLES_DEFAULT below. Offsets are source-image
# pixels; positive X moves the focal point right and positive Y moves it down.
EYE_DOUBLES_PORTRAIT_OVERRIDES: dict[
    str,
    dict[str, DoublesEyePortraitAdjustment],
] = {
    "Captain Falcon": {
        "d": DoublesEyePortraitAdjustment(2.5, focal_x_offset=120),
        "e": DoublesEyePortraitAdjustment(2.4),
    },
    "Dr. Mario": {
        "a": DoublesEyePortraitAdjustment(1.7),
    },
    "Falco": {
        "e": DoublesEyePortraitAdjustment(1.7, focal_x_offset=100),
    },
    "Ganondorf": {
        "a": DoublesEyePortraitAdjustment(2.5),
        "b": DoublesEyePortraitAdjustment(2.2, focal_x_offset=-200),
    },
    "Luigi": {
        "d": DoublesEyePortraitAdjustment(
            1.8,
            focal_x_offset=-80,
            focal_y_offset=-10,
        ),
    },
    "Mario": {
        "a": DoublesEyePortraitAdjustment(1.7),
        "c": DoublesEyePortraitAdjustment(1.7),
    },
    "Marth": {
        "a": DoublesEyePortraitAdjustment(2.6),
        "d": DoublesEyePortraitAdjustment(3.0),
        "e": DoublesEyePortraitAdjustment(3.2),
    },
    "Mr. Game and Watch": {
        "a": DoublesEyePortraitAdjustment(1.7),
        "b": DoublesEyePortraitAdjustment(1.7),
        "c": DoublesEyePortraitAdjustment(
            1.5,
            focal_x_offset=-100,
            focal_y_offset=190,
        ),
    },
    "Ness": {
        "a": DoublesEyePortraitAdjustment(1.6),
        "b": DoublesEyePortraitAdjustment(1.6),
    },
    "Samus": {
        "b": DoublesEyePortraitAdjustment(1.7),
    },
    "Sheik": {
        "c": DoublesEyePortraitAdjustment(1.6, focal_y_offset=-60),
    },
    "Yoshi": {
        "a": DoublesEyePortraitAdjustment(1.5),
        "b": DoublesEyePortraitAdjustment(1.4),
        "c": DoublesEyePortraitAdjustment(1.5),
        "d": DoublesEyePortraitAdjustment(1.15),
    },
    "Young Link": {
        "a": DoublesEyePortraitAdjustment(1.6),
        "c": DoublesEyePortraitAdjustment(1.5),
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

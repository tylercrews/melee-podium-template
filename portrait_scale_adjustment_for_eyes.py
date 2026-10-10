"""Per-pose focal points and close-up scaling for Eyes layouts.

The focal coordinates are measured in source-image pixels.  All costumes for a
pose share the same canvas geometry, so one reviewed value applies to every
costume.  ``zoom`` is relative to fitting the portrait's visible alpha bounds
to the width of its Eyes viewport.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EyePortraitAdjustment:
    focal_x: int
    focal_y: int
    zoom: float = 1.0

    def __post_init__(self) -> None:
        if self.focal_x < 0 or self.focal_y < 0:
            raise ValueError("Eye focal coordinates cannot be negative")
        if self.zoom <= 0:
            raise ValueError("Eye portrait zoom must be greater than zero")


# How to adjust a portrait: find its character and lowercase pose letter below.
# EyePortraitAdjustment(focal_x, focal_y, zoom) uses ORIGINAL source-image pixels,
# measured from the canvas top-left (including transparent margins). The renderer
# places that source point at the viewport center, then clips the portrait.
# For an unmirrored portrait: increase focal_x to move LEFT, decrease it to move
# RIGHT; increase focal_y to move UP, decrease it to move DOWN. Horizontal moves
# reverse for mirrored portraits. To pan the CROP over the source instead, use
# the opposite direction: lower focal_x pans the crop LEFT, lower focal_y pans
# it UP; higher values pan the crop RIGHT/DOWN. Higher zoom enlarges the portrait;
# lower zoom
# reveals more of it. Zoom 1.0 fits the visible alpha bounds to the viewport width.
# Start with 10-30 source pixels or a 0.05-0.10 zoom change, then review the crop;
# the visible movement equals the source-pixel change times the rendered scale.
# All costumes of a pose share these values. Doubles (and Radial) inherit this
# table, so for Singles-only edits compensate the Doubles overrides: subtract
# the Singles focal delta from each offset and multiply the Doubles multiplier
# by old Singles zoom / new Singles zoom to preserve the previous framing.
# Regenerate Singles review sheets from the project root with:
# python test/generate/generate_eye_positioning_previews.py
# Regenerate Doubles sheets too when inherited values or overrides change:
# python test/generate/generate_eye_doubles_positioning_previews.py
# The pink crosshair marks the destination focal point; check eyes and cropping.
#
# The point is the visual center between the visible eyes.  Helmet visors and
# Mr. Game & Watch's head center are used for characters without visible eyes.
EYE_PORTRAIT_ADJUSTMENTS: dict[str, dict[str, EyePortraitAdjustment]] = {
    "Bowser": {
        "a": EyePortraitAdjustment(180, 297, 1.00),
        "c": EyePortraitAdjustment(600, 130, 1.05),
    },
    "Captain Falcon": {
        "b": EyePortraitAdjustment(505, 115, 1.25),
        "c": EyePortraitAdjustment(770, 125, 1.25),
        "d": EyePortraitAdjustment(730, 80, 8.00),
        "e": EyePortraitAdjustment(970, 265, 1.50),
    },
    "Donkey Kong": {
        "a": EyePortraitAdjustment(400, 230, 1.00),
        "b": EyePortraitAdjustment(540, 415, 0.95),
        "c": EyePortraitAdjustment(660, 380, 1.00),
    },
    "Dr. Mario": {
        "a": EyePortraitAdjustment(480, 280, 1.25),
        "b": EyePortraitAdjustment(440, 250, 1.15),
        "c": EyePortraitAdjustment(690, 241, 1.25),
    },
    "Falco": {
        "a": EyePortraitAdjustment(450, 180, 1.45),
        "b": EyePortraitAdjustment(550, 200, 1.45),
        "c": EyePortraitAdjustment(520, 260, 1.25),
        "d": EyePortraitAdjustment(450, 300, 1.25),
        "e": EyePortraitAdjustment(620, 100, 1.55),
    },
    "Fox": {
        "a": EyePortraitAdjustment(500, 270, 1.40),
        "b": EyePortraitAdjustment(500, 280, 1.25),
        "c": EyePortraitAdjustment(630, 250, 1.35),
        "d": EyePortraitAdjustment(650, 300, 1.40),
        "e": EyePortraitAdjustment(690, 250, 1.40),
        "f": EyePortraitAdjustment(900, 220, 1.35),
    },
    "Ganondorf": {
        "a": EyePortraitAdjustment(560, 130, 1.55),
        "b": EyePortraitAdjustment(170, 170, 1.40),
        "c": EyePortraitAdjustment(750, 80, 1.80),
    },
    "Ice Climbers": {
        "a": EyePortraitAdjustment(480, 495, 0.80),
        "b": EyePortraitAdjustment(575, 235, 1.00),
        "c": EyePortraitAdjustment(750, 195, 1.05),
        "d": EyePortraitAdjustment(750, 205, 1.05),
        "e": EyePortraitAdjustment(800, 150, 1.20),
        "f": EyePortraitAdjustment(800, 150, 1.20),
    },
    "Jigglypuff": {
        "a": EyePortraitAdjustment(470, 350, 0.80),
        "b": EyePortraitAdjustment(480, 430, 0.78),
        "c": EyePortraitAdjustment(750, 250, 0.78),
        "d": EyePortraitAdjustment(730, 370, 0.70),
        "e": EyePortraitAdjustment(775, 280, 0.85),
    },
    "Kirby": {
        "a": EyePortraitAdjustment(500, 300, 0.82),
        "b": EyePortraitAdjustment(500, 265, 0.82),
        "c": EyePortraitAdjustment(800, 300, 0.85),
    },
    "Link": {
        "a": EyePortraitAdjustment(330, 150, 1.40),
        "b": EyePortraitAdjustment(430, 145, 1.35),
        "c": EyePortraitAdjustment(700, 390, 1.50),
    },
    "Luigi": {
        "a": EyePortraitAdjustment(505, 300, 1.45),
        "b": EyePortraitAdjustment(500, 275, 1.40),
        "c": EyePortraitAdjustment(760, 140, 1.15),
        "d": EyePortraitAdjustment(700, 235, 1.20),
        "e": EyePortraitAdjustment(800, 195, 1.75),
    },
    "Mario": {
        "a": EyePortraitAdjustment(480, 330, 1.35),
        "b": EyePortraitAdjustment(500, 280, 1.25),
        "c": EyePortraitAdjustment(720, 280, 1.40),
    },
    "Marth": {
        "a": EyePortraitAdjustment(650, 120, 1.65),
        "b": EyePortraitAdjustment(500, 140, 1.60),
        "c": EyePortraitAdjustment(760, 100, 1.50),
        "d": EyePortraitAdjustment(850, 120, 1.40),
        "e": EyePortraitAdjustment(900, 120, 1.35),
    },
    "Mewtwo": {
        "a": EyePortraitAdjustment(460, 340, 1.30),
        "b": EyePortraitAdjustment(500, 320, 1.30),
        "c": EyePortraitAdjustment(750, 300, 1.50),
        "d": EyePortraitAdjustment(750, 300, 1.60),
    },
    "Mr. Game and Watch": {
        "a": EyePortraitAdjustment(400, 235, 1.05),
        "b": EyePortraitAdjustment(400, 180, 1.05),
        "c": EyePortraitAdjustment(600, 340, 1.00),
    },
    "Ness": {
        "a": EyePortraitAdjustment(570, 330, 1.35),
        "b": EyePortraitAdjustment(480, 370, 1.40),
        "c": EyePortraitAdjustment(800, 500, 1.25),
    },
    "Peach": {
        "a": EyePortraitAdjustment(380, 225, 1.40),
        "b": EyePortraitAdjustment(475, 215, 1.00),
        "c": EyePortraitAdjustment(735, 170, 1.90),
        "d": EyePortraitAdjustment(700, 150, 1.50),
    },
    "Pichu": {
        "a": EyePortraitAdjustment(520, 540, 0.75),
        "b": EyePortraitAdjustment(700, 420, 0.70),
        "c": EyePortraitAdjustment(720, 350, 0.95),
    },
    "Pikachu": {
        "a": EyePortraitAdjustment(460, 390, 0.80),
        "b": EyePortraitAdjustment(500, 350, 0.90),
        "c": EyePortraitAdjustment(780, 320, 0.92),
        "d": EyePortraitAdjustment(550, 318, 0.82),
    },
    "Roy": {
        "a": EyePortraitAdjustment(650, 220, 1.50),
        "b": EyePortraitAdjustment(540, 200, 1.50),
        "c": EyePortraitAdjustment(795, 156, 4.00),
    },
    "Samus": {
        "a": EyePortraitAdjustment(520, 350, 1.30),
        "b": EyePortraitAdjustment(600, 220, 1.40),
        "c": EyePortraitAdjustment(750, 140, 1.60),
        "d": EyePortraitAdjustment(750, 120, 1.60),
    },
    "Sheik": {
        "c": EyePortraitAdjustment(790, 120, 1.45),
        "d": EyePortraitAdjustment(620, 110, 1.55),
        "e": EyePortraitAdjustment(700, 70, 1.65),
        "f": EyePortraitAdjustment(855, 540, 1.35),
    },
    "Yoshi": {
        "a": EyePortraitAdjustment(500, 195, 1.25),
        "b": EyePortraitAdjustment(400, 180, 1.05),
        "c": EyePortraitAdjustment(690, 150, 1.25),
        "d": EyePortraitAdjustment(650, 180, 1.20),
    },
    "Young Link": {
        "a": EyePortraitAdjustment(500, 400, 1.55),
        "b": EyePortraitAdjustment(600, 220, 1.35),
        "c": EyePortraitAdjustment(700, 115, 1.65),
    },
    "Zelda": {
        "a": EyePortraitAdjustment(565, 120, 1.75),
        "b": EyePortraitAdjustment(620, 180, 1.20),
        "c": EyePortraitAdjustment(720, 80, 1.50),
    },
}


def get_eye_portrait_adjustment(
    character: str, pose_code: str
) -> EyePortraitAdjustment:
    """Return the reviewed source-pixel focal point for a portrait pose."""

    pose = pose_code.casefold().removeprefix("00")
    try:
        return EYE_PORTRAIT_ADJUSTMENTS[character][pose]
    except KeyError as error:
        raise KeyError(f"Missing Eyes adjustment for {character} {pose}") from error

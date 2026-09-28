"""Second-stage portrait scaling for each layout and Squares card tier.

These values are multiplied by the character/pose relativity scale from
portrait_scale_adjustment_to_character_relativity.py. Adjust them to resize all
portraits in one layout or card tier without changing character sizes relative
to each other.
"""


PORTRAIT_SCALE_BY_MODE = {
    "doubles_top_3": 0.28,
    "doubles_top_4": 0.26,
    "singles_top_3": 0.28,
    "singles_top_4": 0.26,
    "singles_top_8": 0.22,
    "singles_top_8_four_podium": 0.26,
    # Squares cards use the same two-stage portrait scaling as podiums. Each
    # geometrically distinct card size has its own value. These are calibrated
    # so the tallest relativity-adjusted portrait reaches both the top and
    # bottom of its available character frame. The current tallest reference
    # is Bowser Pose C at 1172.72 relativity-adjusted source pixels.
    "squares_singles_top_8_first": 0.567910,
    "squares_singles_top_8_second_through_fourth": 0.280544,
    "squares_singles_top_8_fifth_and_seventh": 0.261785,
    "squares_doubles_first": 0.563647,
    "squares_doubles_top_3_second_through_third": 0.271164,
    "squares_doubles_top_4_second_through_fourth": 0.162017,
}


def get_mode_portrait_scale(mode: str | object) -> float:
    """Return the second-stage portrait scale for a mode name or string enum."""
    mode_name = getattr(mode, "value", mode)
    try:
        scale = PORTRAIT_SCALE_BY_MODE[mode_name]
    except (KeyError, TypeError) as error:
        choices = ", ".join(PORTRAIT_SCALE_BY_MODE)
        raise KeyError(f"Missing portrait scale for {mode_name!r}. Expected: {choices}") from error

    if scale <= 0:
        raise ValueError(f"Portrait scale for {mode_name} must be greater than 0")
    return scale

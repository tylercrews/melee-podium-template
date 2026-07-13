"""Second-stage portrait scaling for each podium layout.

These values are multiplied by the character/pose relativity scale from
portrait_scale_adjustment_to_character_relativity.py. Adjust them to resize all
portraits in one layout without changing character sizes relative to each other.
"""


PORTRAIT_SCALE_BY_MODE = {
    "doubles_top_3": 0.30,
    "doubles_top_4": 0.27,
    "singles_top_3": 0.40,
    "singles_top_4": 0.36,
    "singles_top_8": 0.22,
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

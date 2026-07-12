"""Relative scale settings for character portrait poses.

Edit a value below to adjust that character pose in the sizing comparison.
For example, 0.80 displays the pose at 80% of its source dimensions, while
1.25 displays it at 125%.

The initial values cap portraits at the height of the taller default Donkey
Kong pose (1055 px). Donkey Kong's two poses remain at 100% as the reference.
"""


POSE_SCALE = { # the comment at the side are the original scaling, matching all chars to donkey kong's portrait height
    "Bowser": {"00a": 0.9669, "00b": 1.25},  # {"00a": 0.9336, "00b": 1.0}
    "Captain Falcon": {"00a": 0.69, "00b": 0.69},  # {"00a": 0.7143, "00b": 0.7162}
    "Donkey Kong": {"00a": 1.0, "00b": 1.0},  # {"00a": 1.0, "00b": 1.0}
    "Dr. Mario": {"00a": 0.5562, "00b": 0.5680},  # {"00a": 0.7124, "00b": 0.9361}
    "Falco": {"00a": 0.60, "00b": 0.61},  # {"00a": 0.7153, "00b": 0.7424}
    "Fox": {"00a": 0.5750, "00b": 0.58},  # {"00a": 0.7153, "00b": 0.8529}
    "Ganondorf": {"00a": 0.80, "00b": 0.6930},  # {"00a": 0.7430, "00b": 0.8640}
    "Ice Climbers": {"00a": 0.69, "00b": 0.75},  # {"00a": 0.8762, "00b": 1.0}
    "Jigglypuff": {"00a": 0.6, "00b": 0.55},  # {"00a": 1.0, "00b": 1.0}
    "Kirby": {"00a": 0.58, "00b": 0.58},  # {"00a": 1.0, "00b": 1.0}
    "Link": {"00a": 0.7580, "00b": 0.7483},  # {"00a": 0.8880, "00b": 0.8683}
    "Luigi": {"00a": 0.56, "00b": 0.55},  # {"00a": 0.7246, "00b": 0.8097}
    "Mario": {"00a": 0.5238, "00b": 0.5253},  # {"00a": 0.7138, "00b": 0.7153}
    "Marth": {"00a": 0.78, "00b": 0.68},  # {"00a": 0.8122, "00b": 0.7062}
    "Mewtwo": {"00a": 0.77, "00b": 0.6700},  # {"00a": 0.8041, "00b": 0.7100}
    "Mr. Game and Watch": {"00a": 0.4835, "00b": 0.5},  # {"00a": 0.9670, "00b": 1.0}
    "Ness": {"00a": 0.4245, "00b": 0.3836},  # {"00a": 0.8090, "00b": 0.7236}
    "Peach": {"00a": 0.7068, "00b": 0.6806},  # {"00a": 0.7568, "00b": 0.7306}
    "Pichu": {"00a": 0.3853, "00b": 0.3022},  # {"00a": 0.9353, "00b": 0.8522}
    "Pikachu": {"00a": 0.63, "00b": 0.475},  # {"00a": 1.0, "00b": 0.8294}
    "Roy": {"00a": 0.66, "00b": 0.87},  # {"00a": 0.7104, "00b": 1.0}
    "Samus": {"00a": 0.7752, "00b": 0.7001},  # {"00a": 0.7752, "00b": 0.7301}
    "Sheik": {"00a": 0.6253, "00b": 0.5744},  # {"00a": 0.7153, "00b": 0.8084}
    "Yoshi": {"00a": 0.5903, "00b": 0.545},  # {"00a": 0.7903, "00b": 0.7162}
    "Young Link": {"00a": 0.49, "00b": 0.49},  # {"00a": 0.7187, "00b": 0.8591}
    "Zelda": {"00a": 0.6253, "00b": 0.6219},  # {"00a": 0.7153, "00b": 0.7119}
}

def get_pose_scale(character: str, pose_code: str) -> float:
    """Return and validate the configured scale for a character pose."""
    try:
        scale = POSE_SCALE[character][pose_code]
    except KeyError as error:
        raise KeyError(f"Missing scale for {character} {pose_code}") from error

    if scale <= 0:
        raise ValueError(
            f"Scale for {character} {pose_code} must be greater than 0"
        )
    return scale

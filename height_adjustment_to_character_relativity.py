"""Relative scale settings for character portrait poses.

Edit a value below to adjust that character pose in the sizing comparison.
For example, 0.80 displays the pose at 80% of its source dimensions.

The initial values cap portraits at the height of the taller default Donkey
Kong pose (1055 px). Donkey Kong's two poses remain at 100% as the reference.
"""


POSE_SCALE = {
    "Bowser": {"00a": 0.85, "00b": 1.0}, 
    "Captain Falcon": {"00a": 0.69, "00b": 0.69},
    "Donkey Kong": {"00a": 1.0, "00b": 1.0},
    "Dr. Mario": {"00a": 0.3562, "00b": 0.4680},
    "Falco": {"00a": 0.69, "00b": 0.70},
    "Fox": {"00a": 0.69, "00b": 0.69},
    "Ganondorf": {"00a": 0.7430, "00b": 0.7430},
    "Ice Climbers": {"00a": 0.4431, "00b": 0.8},
    "Jigglypuff": {"00a": 0.6, "00b": 0.6},
    "Kirby": {"00a": 0.6, "00b": 0.6},
    "Link": {"00a": 0.8380, "00b": 0.8183},
    "Luigi": {"00a": 0.5546, "00b": 0.5597},
    "Mario": {"00a": 0.5538, "00b": 0.5553},
    "Marth": {"00a": 0.8122, "00b": 0.7062},
    "Mewtwo": {"00a": 0.8041, "00b": 0.7100},
    "Mr. Game and Watch": {"00a": 0.4835, "00b": 0.5},
    "Ness": {"00a": 0.4045, "00b": 0.3636},
    "Peach": {"00a": 0.7268, "00b": 0.7006},
    "Pichu": {"00a": 0.3353, "00b": 0.2822},
    "Pikachu": {"00a": 0.8, "00b": 0.7294},
    "Roy": {"00a": 0.6904, "00b": 0.9},
    "Samus": {"00a": 0.7752, "00b": 0.7001},
    "Sheik": {"00a": 0.6753, "00b": 0.6084},
    "Yoshi": {"00a": 0.5903, "00b": 0.5162},
    "Young Link": {"00a": 0.3587, "00b": 0.4300},
    "Zelda": {"00a": 0.6753, "00b": 0.6719},
}

# for reference in case they need to be reverted back to their original heights
# this is the original scaling to make all heights uniform
# were set to match to donkey kong's height, because I think upright he should be the tallest char in the game
# POSE_SCALE = {
#     "Bowser": {"00a": 0.9336, "00b": 1.0}, 
#     "Captain Falcon": {"00a": 0.7143, "00b": 0.7162},
#     "Donkey Kong": {"00a": 1.0, "00b": 1.0},
#     "Dr. Mario": {"00a": 0.7124, "00b": 0.9361},
#     "Falco": {"00a": 0.7153, "00b": 0.7424},
#     "Fox": {"00a": 0.7153, "00b": 0.8529},
#     "Ganondorf": {"00a": 0.7430, "00b": 0.8640},
#     "Ice Climbers": {"00a": 0.8762, "00b": 1.0},
#     "Jigglypuff": {"00a": 1.0, "00b": 1.0},
#     "Kirby": {"00a": 1.0, "00b": 1.0},
#     "Link": {"00a": 0.8880, "00b": 0.8683},
#     "Luigi": {"00a": 0.7246, "00b": 0.8097},
#     "Mario": {"00a": 0.7138, "00b": 0.7153},
#     "Marth": {"00a": 0.8122, "00b": 0.7062},
#     "Mewtwo": {"00a": 0.8041, "00b": 0.7100},
#     "Mr. Game and Watch": {"00a": 0.9670, "00b": 1.0},
#     "Ness": {"00a": 0.8090, "00b": 0.7236},
#     "Peach": {"00a": 0.7568, "00b": 0.7306},
#     "Pichu": {"00a": 0.9353, "00b": 0.8522},
#     "Pikachu": {"00a": 1.0, "00b": 0.8294},
#     "Roy": {"00a": 0.7104, "00b": 1.0},
#     "Samus": {"00a": 0.7752, "00b": 0.7301},
#     "Sheik": {"00a": 0.7153, "00b": 0.8084},
#     "Yoshi": {"00a": 0.7903, "00b": 0.7162},
#     "Young Link": {"00a": 0.7187, "00b": 0.8591},
#     "Zelda": {"00a": 0.7153, "00b": 0.7119},
# }

def get_pose_scale(character: str, pose_code: str) -> float:
    """Return and validate the configured scale for a character pose."""
    try:
        scale = POSE_SCALE[character][pose_code]
    except KeyError as error:
        raise KeyError(f"Missing scale for {character} {pose_code}") from error

    if not 0 < scale <= 1:
        raise ValueError(
            f"Scale for {character} {pose_code} must be greater than 0 and at most 1"
        )
    return scale

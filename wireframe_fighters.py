"""Fighting Wire Frame portraits that stand in for a Random character pick."""

from __future__ import annotations

from random import Random


WIREFRAME_MALE = "Wireframe-Male"
WIREFRAME_FEMALE = "Wireframe-Female"
WIREFRAME_FIGHTERS = (WIREFRAME_MALE, WIREFRAME_FEMALE)

# Rendered fighter-name labels show what the entrant picked, not the model
# used to draw it.
RANDOM_FIGHTER_LABEL = "Random"

# Each Male pose letter and its matching Female pose letter. A Random bracket
# selection draws one pair for both wireframes; users can then choose either
# pose independently. Keep this a one-to-one mapping over existing poses.
WIREFRAME_POSE_PAIRS = {
    "a": "b",  # Captain Falcon Salute Wave / Peach Wave
    "b": "f",  # Captain Falcon High Kick / Sheik High Kick
    "c": "a",  # Ganondorf Fist Raised / Peach Taunt Victory Hand
    "d": "d",  # Ganondorf Flick Off / Samus Crouch
    "e": "e",  # Marth Jojo Pose / Sheik Jojo Pose
    "f": "c",  # Marth Arm Out / Peach Arm Out
}


def fighter_display_name(fighter_name: str) -> str:
    """Return the fighter name drawn in images."""

    return RANDOM_FIGHTER_LABEL if fighter_name in WIREFRAME_FIGHTERS else fighter_name


def random_wireframe_poses(rng: Random | None = None) -> tuple[str, str]:
    """Choose one matched (Male, Female) pose pair."""

    male_pose = (rng or Random()).choice(sorted(WIREFRAME_POSE_PAIRS))
    return male_pose, WIREFRAME_POSE_PAIRS[male_pose]

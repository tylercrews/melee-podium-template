"""Generate formatting-stage previews for all six legacy podium layouts."""

from preview_support import generate_previews

from creation_modes import PodiumStyle


if __name__ == "__main__":
    outputs = generate_previews(PodiumStyle.LEGACY)
    print(f"Generated {len(outputs) - 1} legacy layouts and {outputs[-1]}")

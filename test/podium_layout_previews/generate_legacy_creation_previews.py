"""Generate full legacy previews with the shared sample entrants and metadata."""

from preview_support import generate_creation_previews

from creation_modes import PodiumStyle


if __name__ == "__main__":
    outputs = generate_creation_previews(PodiumStyle.LEGACY)
    print(f"Generated {len(outputs) - 1} legacy creation previews and {outputs[-1]}")

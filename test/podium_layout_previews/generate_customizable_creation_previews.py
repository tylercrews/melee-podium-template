"""Generate full customizable previews with sample entrants and metadata."""

from preview_support import generate_creation_previews

from creation_modes import PodiumStyle
from podium_colors import PodiumColorSelection


if __name__ == "__main__":
    outputs = generate_creation_previews(
        PodiumStyle.CUSTOMIZABLE,
        podium_colors=PodiumColorSelection(
            main_color="#C73C48FF",
            face_color="#6E9CCAFF",
            base_color="#202735FF",
            metallic=True,
        ),
    )
    print(
        f"Generated {len(outputs) - 1} customizable creation previews "
        f"and {outputs[-1]}"
    )

"""Generate formatting-stage previews for all customizable podium layouts."""

from preview_support import generate_previews

from creation_modes import PodiumStyle
from podium_colors import PodiumColorSelection


if __name__ == "__main__":
    outputs = generate_previews(
        PodiumStyle.CUSTOMIZABLE,
        podium_colors=PodiumColorSelection(
            main_color="#D02020FF",
            metallic=False,
        ),
    )
    print(f"Generated {len(outputs) - 1} customizable layouts and {outputs[-1]}")

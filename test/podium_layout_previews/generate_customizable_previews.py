"""Generate formatting-stage previews for all customizable podium layouts."""

from preview_support import generate_previews

from creation_modes import PodiumStyle
from podium_colors import PodiumColorConfiguration, PodiumColorPreset


if __name__ == "__main__":
    outputs = generate_previews(
        PodiumStyle.CUSTOMIZABLE,
        podium_colors=PodiumColorConfiguration.from_preset(
            PodiumColorPreset.LEGACY
        ),
    )
    print(f"Generated {len(outputs) - 1} customizable layouts and {outputs[-1]}")

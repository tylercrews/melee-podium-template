"""Generate full customizable previews with sample entrants and metadata."""

from preview_support import generate_creation_previews

from creation_modes import PodiumStyle
from podium_colors import PodiumColorConfiguration, PodiumColorPreset


if __name__ == "__main__":
    outputs = generate_creation_previews(
        PodiumStyle.CUSTOMIZABLE,
        podium_colors=PodiumColorConfiguration.from_preset(
            PodiumColorPreset.LEGACY
        ),
    )
    print(
        f"Generated {len(outputs) - 1} customizable creation previews "
        f"and {outputs[-1]}"
    )

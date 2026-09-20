"""Render full previews for every customizable podium color-selection mode."""

from preview_support import generate_creation_previews

from creation_modes import PodiumStyle
from podium_colors import (
    PodiumColorConfiguration,
    PodiumColorPreset,
    PodiumColorSelection,
)


LEGACY = PodiumColorConfiguration.from_preset(PodiumColorPreset.LEGACY)
MEDALS = PodiumColorConfiguration.from_preset(PodiumColorPreset.MEDALS)
PER_PODIUM = PodiumColorConfiguration.per_podium(
    PodiumColorSelection("#E63946FF"),
    PodiumColorSelection("#457B9DFF"),
    PodiumColorSelection("#F4A261FF"),
    PodiumColorSelection("#2A9D8FFF"),
    PodiumColorSelection("#9B5DE5FF"),
    PodiumColorSelection("#00B4D8FF"),
    PodiumColorSelection("#F15BB5FF"),
    PodiumColorSelection("#ADB5BDFF"),
)
ALTERNATING = PodiumColorConfiguration.alternating(
    PodiumColorSelection("#D90429FF"),
    PodiumColorSelection("#4361EEFF"),
)


if __name__ == "__main__":
    for name, colors in (
        ("preset_legacy", LEGACY),
        ("preset_medals", MEDALS),
        ("per_podium", PER_PODIUM),
        ("alternating", ALTERNATING),
    ):
        outputs = generate_creation_previews(
            PodiumStyle.CUSTOMIZABLE,
            podium_colors=colors,
            output_variant=name,
        )
        print(f"Generated {len(outputs) - 1} {name} previews and {outputs[-1]}")

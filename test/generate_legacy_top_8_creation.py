"""Generate a deterministic legacy Top 8 preview through ``creation.py``."""

from pathlib import Path
import random
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from background_builder import (  # noqa: E402
    BACKGROUND_FORMAT_SIZES,
    BackgroundRequest,
    default_placement,
)
from creation import CreationPipeline, CreationRequest  # noqa: E402
from creation_modes import (  # noqa: E402
    CreationMode,
    ModeOptions,
    ModeSelection,
    PodiumStyle,
)
from legacy_podium_content_renderer import (  # noqa: E402
    LegacyPodiumContentRenderer,
)
from models import TournamentFormat  # noqa: E402
from sample_creation_data import (  # noqa: E402
    sample_top_8_entrants,
    sample_tournament,
)


BACKGROUND_ASSET_ID = "00_Battlefield_5000_5000_resaved.png"
FORMAT_ID = "singles_top_8"
OUTPUT_PATH = Path(__file__).with_name("legacy_top_8_creation_output.png")


def main() -> None:
    selection = ModeSelection(
        CreationMode.PODIUM,
        ModeOptions(
            event_format=TournamentFormat.SINGLES,
            entrant_count=8,
            podium_style=PodiumStyle.LEGACY,
        ),
    )
    request = CreationRequest(
        selection=selection,
        background=BackgroundRequest(
            size=BACKGROUND_FORMAT_SIZES[FORMAT_ID],
            image=default_placement(FORMAT_ID, BACKGROUND_ASSET_ID),
        ),
        entrants=sample_top_8_entrants(random.Random(42)),
        tournament=sample_tournament(),
    )
    pipeline = CreationPipeline(
        content_renderers={
            CreationMode.PODIUM: LegacyPodiumContentRenderer(),
        }
    )

    result = pipeline.create(request)
    result.save(OUTPUT_PATH)
    print(f"Generated {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

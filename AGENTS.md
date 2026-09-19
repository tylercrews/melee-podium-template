# Project guidance

## Architecture

- Keep features in small, cohesive modules. Do not add new unrelated responsibilities to a single monolithic file. `DrawPodium.py` is legacy code to be decomposed over time, not a model for new modules.
- Keep rendering logic independent from Flask routes and React UI state. UI/API layers translate requests into renderer data structures; renderers accept validated values and return images.
- Prefer serializable, explicit data models at module boundaries so layout preferences can be saved and restored.

## Background rendering decisions

- Backgrounds are composed at render time; do not create or select fixed Top 3, Top 4, or Top 8 background placeholder assets.
- Every background request specifies its output width and height. Podium format selection is responsible for supplying those dimensions.
- Persist colors as 8-digit RGBA hex strings (`#RRGGBBAA`). The default is fully transparent black (`#00000000`).
- A saved image placement contains an asset ID, a source crop rectangle, and a destination rectangle. Rectangles use Pillow-style half-open pixel coordinates: left/top are included and right/bottom are excluded.
- Compose in this order: create the RGBA canvas with the selected color, crop the selected image, resize the crop to its destination rectangle, composite it over the canvas, and return the new RGBA image.
- Built-in images live in `backgrounds/`. Refer to them by asset ID/filename rather than storing absolute paths. A future cloud-storage provider should implement the same asset-provider boundary instead of changing the compositor.
- Default crop positions are keyed by podium format and background asset. Keep format-specific overrides possible even when several formats currently share the same dimensions.

## Maintenance

- Update this file when the user establishes a durable design or architecture decision.
- Add focused tests with new rendering modules, including serialization and image-boundary behavior.

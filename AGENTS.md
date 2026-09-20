# Project guidance

## Architecture

- Keep features in small, cohesive modules. Do not add new unrelated responsibilities to a single monolithic file. `DrawPodium.py` is legacy code to be decomposed over time, not a model for new modules.
- Keep rendering logic independent from Flask routes and React UI state. UI/API layers translate requests into renderer data structures; renderers accept validated values and return images.
- Prefer serializable, explicit data models at module boundaries so layout preferences can be saved and restored.
- Represent every color code universally as an 8-digit RGBA hex string (`#RRGGBBAA`), including UI, API, constants, defaults, and preference data. Channel tuples are only transient Pillow rendering values converted from RGBA hex.

## Creation modes and pipeline

- The initial creation modes are Podium, Eyes, and Squares. Podium is the first mode being implemented; keep Eyes and Squares explicit even while their renderers are pending, and allow more modes to be added later.
- Select the mode before other creation settings. Keep the mode and its settings, including singles/doubles, included entrant count, and any layout variant, together in one mode-selection value.
- Podium mode has a required second-level choice between `legacy` podiums and `customizable` podiums. Do not treat this as a cosmetic skin: each style owns separate formatting-asset positions and character/text placements because its podium geometry and heights differ.
- `creation.py` is the overall composition coordinator. Do not use a generic `main.py` for this responsibility.
- Run creation stages in this order: resolve mode/sub-mode preferences, build the background, draw mode formatting assets, then draw entrant character assets and text.
- Character assets and text belong to one combined content-rendering stage. Their placements carry layer-order values so text and characters can overlap in either order when a layout requires it.
- Formatting assets vary by mode: Podium uses podiums, Squares uses squares, and Eyes uses rectangles.
- Store layout preferences as JSON under `preferences/<mode>/<sub-mode>.json`. Podium preferences add the required style level: `preferences/podium/<legacy|customizable>/<sub-mode>.json`. Each file owns canvas dimensions plus formatting-asset, character, and text placements for exactly one selection.
- A scaffold preference file stays marked `ready: false` until its real positions have been extracted and reviewed. The creation pipeline must refuse to render with an unfinished preference file rather than silently producing an empty layout.

## Customizable podium colors

- Customizable podiums require a main color and accept optional face and base colors plus a strict `metallic` boolean.
- Preserve whether face and base were omitted in serialized input. Resolve those defaults only for rendering.
- When face is omitted, preserve the main hue and saturation and darken its HSL lightness using the median face-to-main lightness ratio from the existing podium color pairs in `constants.py`.
- When base is omitted, use black. Any omitted color inherits the main color's alpha channel; explicitly supplied colors retain their own alpha.
- In semantic podium masks, main replaces red, face replaces cyan, and base replaces blue. Combine the selected alpha with the mask pixel's existing alpha so antialiased edges stay intact.

## Background rendering decisions

- Backgrounds are composed at render time; do not create or select fixed Top 3, Top 4, or Top 8 background placeholder assets.
- Every background request specifies its output width and height. The selected mode/sub-mode is responsible for supplying those dimensions.
- The default background color is fully transparent black (`#00000000`).
- A saved image placement contains an asset ID, a source crop rectangle, and a destination rectangle. Rectangles use Pillow-style half-open pixel coordinates: left/top are included and right/bottom are excluded.
- Compose in this order: create the RGBA canvas with the selected color, crop the selected image, resize the crop to its destination rectangle, composite it over the canvas, and return the new RGBA image.
- Built-in images live in `backgrounds/`. Refer to them by asset ID/filename rather than storing absolute paths. A future cloud-storage provider should implement the same asset-provider boundary instead of changing the compositor.
- Default crop positions are keyed by podium format and background asset. Keep format-specific overrides possible even when several formats currently share the same dimensions.

## Maintenance

- Update this file when the user establishes a durable design or architecture decision.
- Add focused tests with new rendering modules, including serialization and image-boundary behavior.

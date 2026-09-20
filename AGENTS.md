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
- Legacy Podium preferences preserve the 1672x941 output, portrait scales, character anchors, and fixed label/seed anchors from `DrawPodium.py`. Legacy player-tag vertical anchors are not fixed pixels; retain the rule that derives them from the visible top of each rendered portrait with a 15-pixel upward offset.
- Legacy podium formatting-asset rectangles use half-open visible bounds measured from `top_3.png`, `top_4.png`, and `top_8.png`. The corresponding active legacy assets should be tightly cropped to those visible bounds.
- The reviewed legacy Top 8 layout expands each podium body 15 pixels horizontally on both sides of its extracted `top_8.png` bounds. Each podium after first shifts a further 5 pixels rightward, reducing overlap while allowing the far-right podium to extend 29 pixels beyond the canvas; its character, placement-tag, character-name, and seed anchors use the same per-rank offset.
- Draw podium formatting assets from left to right by their destination position so the right-facing box edges overlap correctly. Keep entrant character/content draw order independent, with lower placements drawn over higher placements where their layout requires it.
- Store podium placement-number art in `formatting_assets/placement_numbers/` using zero-padded ordinal filenames such as `01st.png`, `02nd.png`, and `25th.png`.
- Podium preferences own placement-tag entries separately from podium-body placements. Each entry identifies an asset plus a center anchor and a maximum size; render these tags after podium bodies and before entrant character/text content. Tied legacy Top 8 results use `05th.png` for both fifth-place podiums and `07th.png` for both seventh-place podiums.

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
- Keep reusable sample entrants and complete sample tournament metadata together in `sample_creation_data.py`; generation scripts and tests should import from that single fixture module.

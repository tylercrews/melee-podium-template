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

## Frontend creation workflow

- The image maker uses five ordered steps: Images, Format, Bracket Import, Tournament, and Entrants. Users may return to any completed step but cannot open a later step until every prerequisite step is complete.
- On desktop, the creation workflow occupies the left two-thirds of the screen and a live image preview occupies the right third. The primary action sits above the preview and changes with workflow state, including example-entrant previews after formatting and the finalized-image download after all inputs are complete.
- On the Format step, the preview shows a complete demo image with example entrants rather than separate background and logo cards. Its primary action reads `Continue to Bracket Import` and remains disabled until every required format property is selected.
- Format begins with Podiums selected; Eyes and Squares remain visible but disabled until their settings are ready. Podium formats require an explicit Legacy or Customizable choice, and every format requires an explicit Singles or Doubles choice.
- Podium headers have exactly three positions—top left, top middle, and top right—and assign the tournament logo, tournament title, and metadata bijectively across them. The UI swaps assignments when a user selects content already occupying another position so duplicates and omissions are impossible.
- Format image settings include an eight-digit RGBA background color defaulting to `#00000000`, plus independent logo and background size multipliers of quarter, third, half, one, two, three, or four times the source size. Backgrounds additionally support Scale to Width and Scale to Height, which resolve and serialize the exact multiplier required for the current source and output dimensions.
- Background placement is selected visually against the chosen output canvas. When the scaled asset fits inside the canvas, users position the asset; when it overflows either dimension, users position the output viewport over it. Serialize the resulting asset ID, source crop, and destination rectangle with the format.
- Format settings use versioned JSON that can be pasted in, copied, or downloaded. Signed-in users can load and save named formats through their private `layouts` collection; matching names are compared case-insensitively and require explicit overwrite confirmation.
- The global navigation identifies the app as Melee Podium Maker, exposes account state in the top-right account control, and toggles between Image Maker and Manage Saved Data.
- Label the saved-data navigation `Manage Saved Data`; its management surface has explicit sections for saved images, saved formats, and favorite entrants even while some sections are still scaffolds.
- Firebase browser authentication supports both Google sign-in and email/password account creation and sign-in. Keep both choices available in the same account dialog and route their resulting ID tokens through the same authenticated Flask API boundary.
- The Images step optionally selects one tournament logo and one background. Neither image is required; users can skip the step with zero or one image selected and continue to Format. Signed-in users select private Firebase images by their assigned display names; guest image uploads remain disabled until browser-memory behavior has been stress-tested.
- The background picker includes both user-uploaded images and the built-in assets from `backgrounds/`. Present those as visibly separate collections, never count or delete a built-in as a user upload, and attribute the included stage renders to Malarki_.
- Each signed-in user may store at most 10 tournament logos and 10 backgrounds. Names must be unique case-insensitively within each category, and permanent deletion requires an explicit confirmation dialog.
- Legacy Podium preferences preserve the 1672x941 output, portrait scales, character anchors, and fixed label/seed anchors from `DrawPodium.py`. Legacy player-tag vertical anchors are not fixed pixels; retain the rule that derives them from the visible top of each rendered portrait with a 15-pixel upward offset.
- Legacy podium formatting-asset rectangles use half-open visible bounds measured from `top_3.png`, `top_4.png`, and `top_8.png`. The corresponding active legacy assets should be tightly cropped to those visible bounds.
- The reviewed legacy Top 8 layout expands each podium body 15 pixels horizontally on both sides of its extracted `top_8.png` bounds. Each podium after first shifts a further 5 pixels rightward, reducing overlap while allowing the far-right podium to extend 29 pixels beyond the canvas; its character, placement-tag, character-name, and seed anchors use the same per-rank offset. Portrait anchors sit 8 pixels below their original legacy positions. Seed anchors track the enlarged front-face right edge with an additional 10-pixel offset and use Pillow's `ra` anchor so the `s` suffix stays at that edge while the label grows leftward.
- Legacy four-podium layouts distribute their bodies with 13, 13, and 12 pixels of overlap. The second-place body and all associated content shift 16 pixels right from the extracted legacy coordinates; third-place and its content shift 17 pixels right.
- Draw podium formatting assets from left to right by their destination position so the right-facing box edges overlap correctly. Keep entrant character/content draw order independent, with lower placements drawn over higher placements where their layout requires it.
- Store podium placement-number art in `formatting_assets/placement_numbers/` using zero-padded ordinal filenames such as `01st.png`, `02nd.png`, and `25th.png`.
- Podium preferences own placement-tag entries separately from podium-body placements. Each entry identifies an asset plus a center anchor and a maximum size; render these tags after podium bodies and before entrant character/text content. Tied legacy Top 8 results use `05th.png` for both fifth-place podiums and `07th.png` for both seventh-place podiums.

## Customizable podium colors

- Active customizable podium masks live in `formatting_assets/podium/customizable/` and are tightly cropped from the cleaned semantic masks in `docs/archive/old_podium_iterations/02_3d_second_attempt/`.
- Customizable podium formatting layouts use a 1920x941 canvas. Preserve the customizable asset's aspect ratio and the corresponding legacy podium's bottom edge, enlarge the bodies relative to legacy, and distribute the complete podium group across the wider canvas. Top 8 uses five-pixel gaps instead of overlaps so all eight bodies remain distinct.
- Customizable Top 8 uses x-tall, tall, medium, short, x-short, x-short, flat, and flat assets in placement order. Top 3 uses tall, medium, and short; four-podium layouts append x-short.
- Flat customizable podiums never display placement-number art.
- Customizable Top 8 displays placement-number art only for first through third; fourth, both tied fifths, and both flat tied sevenths omit it. Customizable gray placement-number art is deliberately much smaller than the first-place crest.
- Size customizable placement-number art per layout and podium height rather than sharing bounds across formats. Use as much of the semantic front face as practical while leaving clearance above the bottom trim; very short faces, especially fourth place in four-podium layouts, require correspondingly tiny art.
- Customizable first-place art keeps its taller bounds so the ribbon can hang below the number. Customizable portrait anchors follow the bottom edge of each semantic top face; text is projected horizontally into the corresponding customizable podium bounds. Seed labels are vertically fitted inside each semantic front face immediately above its lower trim, shrinking on the shortest faces when necessary.
- In customizable doubles Top 4, the second member of the first-place team has an additional 20-pixel rightward anchor offset after projection.
- Customizable podiums require a main color and accept optional face and base colors plus a strict `metallic` boolean.
- A customizable podium color configuration has exactly one of three modes: a named stock preset, one explicit color selection per podium, or two selections alternating by odd/even podium slot.
- Stock presets include `legacy` (red, blue, yellow, green, orange, cyan, magenta, gray) and `medals` (metallic gold, silver, bronze, then gray through eighth).
- Preserve whether face and base were omitted in serialized input. Resolve those defaults only for rendering.
- When face is omitted, preserve the main hue and saturation and darken its HSL lightness using the median face-to-main lightness ratio from the existing podium color pairs in `constants.py`.
- When base is omitted, use black. Any omitted color inherits the main color's alpha channel; explicitly supplied colors retain their own alpha.
- In semantic podium masks, main replaces red, face replaces cyan, and base replaces blue. Combine the selected alpha with the mask pixel's existing alpha so antialiased edges stay intact.
- Recolor shaded semantic-mask variants as well as exact red/cyan/blue class pixels so no source-mask blue or cyan leaks into the finished asset. A metallic selection adds a directional highlight to the main-color region.
- Text placements may supply an explicit eight-digit RGBA color. When omitted for a customizable podium, entrant tags, labels, names, summaries, and seeds use that podium slot's resolved text color, which defaults to its main color.
- In the four-podium Top 8 variant, lower summaries for fifth through eighth use color slots five through eight even though they are positioned beneath podium bodies one through four.

## Background rendering decisions

- Backgrounds are composed at render time; do not create or select fixed Top 3, Top 4, or Top 8 background placeholder assets.
- Every background request specifies its output width and height. The selected mode/sub-mode is responsible for supplying those dimensions.
- The default background color is fully transparent black (`#00000000`).
- A saved image placement contains an asset ID, a source crop rectangle, and a destination rectangle. Rectangles use Pillow-style half-open pixel coordinates: left/top are included and right/bottom are excluded.
- Compose in this order: create the RGBA canvas with the selected color, crop the selected image, resize the crop to its destination rectangle, composite it over the canvas, and return the new RGBA image.
- Built-in images live in `backgrounds/`. Refer to them by asset ID/filename rather than storing absolute paths. A future cloud-storage provider should implement the same asset-provider boundary instead of changing the compositor.
- Default crop positions are keyed by podium format and background asset. Keep format-specific overrides possible even when several formats currently share the same dimensions.
- Default built-in background framing uses a centered cover crop. `05_FinalDestinationSpace_5000_5000_resaved.png` is the exception and uses a center-bottom cover crop. Capture future simple framing choices in `DEFAULT_IMAGE_ALIGNMENTS` in `background_builder.py`; the resulting pixel crop remains the serialized preference.

## Firebase cloud services

- Keep Firebase Admin integration in the `firebase_services/` package. Flask
  routes translate authenticated requests into service calls; Firebase code
  must not leak into renderers or React state management.
- Initialize Firebase Admin with Application Default Credentials through
  `GOOGLE_APPLICATION_CREDENTIALS`. Never hard-code a service-account path,
  credential value, project-specific bucket name, or hosting account name in
  committed source or documentation. Never copy credentials into the frontend,
  deployment ZIP, logs, Firestore, or Cloud Storage.
- Browser sign-in belongs to the Firebase Web SDK. The React client will obtain
  a Firebase ID token and send it to Flask over HTTPS as a bearer token. Flask
  verifies that token and derives the current `uid`; never authorize a request
  with a user ID supplied in a URL, request body, or form field.
- Firebase Admin calls bypass Firebase Security Rules. Every Firestore and
  Storage operation must therefore be scoped by the server to the verified
  user's `uid`. Keep client Firestore and Storage rules closed unless direct
  browser access is deliberately designed and protected with tested rules.
- Store user data as separate Firestore documents under
  `users/{uid}/layouts/{layoutId}`, `users/{uid}/entrants/{entrantId}`, and
  `users/{uid}/images/{imageId}`. Do not store a growing user's complete data
  set in one document.
- Saved entrant and layout records use an explicit envelope containing a name,
  schema version, JSON-object data, and server timestamps. Validate their
  structure and size at the API boundary so future schema migrations remain
  possible and Firestore's document limit is not approached accidentally.
- Store uploaded image bytes only in Cloud Storage. Store their stable image
  ID, private Storage path, media type, dimensions, size, and timestamps in the
  corresponding Firestore metadata document. Layouts reference the stable
  image ID, never a temporary signed URL.
- Keep uploaded objects private. Validate actual raster bytes rather than a
  browser-supplied filename or MIME type, enforce byte and pixel limits, and
  accept only explicitly supported formats. Generate short-lived download URLs
  only after verifying ownership.
- `FIREBASE_STORAGE_BUCKET` contains deployment configuration and must remain an
  environment variable. Public examples use placeholders, never the real
  bucket name. Firebase endpoints should fail without exposing credentials or
  internal filesystem paths when configuration or a cloud operation is
  unavailable.

## Maintenance

- Update this file when the user establishes a durable design or architecture decision.
- Add focused tests with new rendering modules, including serialization and image-boundary behavior.
- Keep reusable sample entrants and complete sample tournament metadata together in `sample_creation_data.py`; generation scripts and tests should import from that single fixture module.
- Sample entrant and team helpers return results already sorted in placement order, with unique randomized placements and seeds. Sample teams pair every entrant exactly once and independently randomize each team's color. Preview generators use unseeded randomness; tests may inject `random.Random` for reproducible assertions.
- Add focused tests for Firebase authentication boundaries, per-user path
  scoping, JSON serialization limits, image validation, and deployment archive
  exclusions. Tests must not require live credentials unless they are explicitly
  marked as opt-in integration checks.

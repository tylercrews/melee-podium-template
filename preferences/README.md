# Mode layout preferences

Each JSON file under `<mode>/<sub-mode>.json` owns one complete layout. Podium
mode includes its required podium style in the path:
`podium/<legacy|customizable>/<sub-mode>.json`. The filename is derived from
the remaining selection, for example `singles_top_3.json` or
`singles_top_8_four_podium.json`.

Files remain marked `ready: false` until their real positions and required
assets have been extracted and visually reviewed. A file may therefore contain
partially or fully extracted coordinates while still being unavailable to the
creation pipeline.

The legacy `singles_top_8` layout is the first reviewed preference. Its active,
tightly cropped podium assets live in `formatting_assets/podium/legacy/`.
The initial customizable formatting layouts use a 1920x941 review canvas and
remain unready while their populated character and text placements are being
visually reviewed.
Their tightly cropped semantic masks live in
`formatting_assets/podium/customizable/`.

- `formatting_assets` places podium, square, or rectangle PNGs. Each entry has
  a stable slot ID, asset filename, destination rectangle, and z-index.
- `character_slots` uses one-based entrant/member slots, a pixel anchor, scale,
  and z-index.
- `text_slots` names the source field, optional one-based entrant/member slots,
  a pixel anchor, maximum width, z-index, and optional eight-digit RGBA color.
  When a customizable-podium text color is omitted, it resolves to that
  podium's main color.
- Character and text z-index values share one logical content layer order. The
  eventual content renderer must merge both lists rather than drawing every
  character before every text label (or vice versa).
- Legacy podium destination rectangles are half-open visible bounds measured
  from the old `top_3.png`, `top_4.png`, and `top_8.png` outputs. Their asset IDs
  reserve tightly cropped filenames in `formatting_assets/podium/legacy/`.
- Customizable podiums preserve the matching legacy podium's bottom edge,
  enlarge the body while preserving its aspect ratio, and spread the group
  across the wider canvas. Top 8 uses five-pixel gaps and
  uses x-tall, tall, medium, short, two x-short, and two flat podiums. The
  remaining layouts use tall, medium, short, and x-short as slots permit.
- Flat customizable podiums intentionally omit placement-number art.
- Customizable Top 8 shows placement-number art only for first through third;
  fourth and both tied fifths also omit it. Gray placement-number art uses
  substantially smaller bounds than the first-place crest.
- Customizable placement-number maximum sizes are layout-specific. They should
  fill the usable front-face area while retaining clearance from the bottom
  trim, so shorter podium faces receive progressively smaller art.
- Customizable seed anchors are fitted into the semantic front-face band just
  above its lower trim; their font size shrinks when a short face cannot hold
  the standard 24-pixel size.

Adding a supported sub-mode means adding another validated JSON file; entrant
counts are not hard-coded in the mode model.

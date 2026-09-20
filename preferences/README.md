# Mode layout preferences

Each JSON file under `<mode>/<sub-mode>.json` owns one complete layout. Podium
mode includes its required podium style in the path:
`podium/<legacy|customizable>/<sub-mode>.json`. The filename is derived from
the remaining selection, for example `singles_top_3.json` or
`singles_top_8_four_podium.json`.

The initial files are intentionally empty and marked `ready: false`. Set a file
to `ready: true` only after its real positions have been extracted and visually
reviewed. The creation pipeline rejects unfinished files.

- `formatting_assets` places podium, square, or rectangle PNGs. Each entry has
  a stable slot ID, asset filename, destination rectangle, and z-index.
- `character_slots` uses one-based entrant/member slots, a pixel anchor, scale,
  and z-index.
- `text_slots` names the source field, optional one-based entrant/member slots,
  a pixel anchor, maximum width, and z-index.
- Character and text z-index values share one logical content layer order. The
  eventual content renderer must merge both lists rather than drawing every
  character before every text label (or vice versa).

Adding a supported sub-mode means adding another validated JSON file; entrant
counts are not hard-coded in the mode model.

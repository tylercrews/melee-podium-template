# Podiums+Clapping placement review

Official display name: **Podiums+Clapping**. The existing `four_podium`
selection ID continues to identify older saved settings. The default-on
Animated checkbox is saved as `selection.options.animated`; turning it off
keeps all four portrait panels as still images.

Render the static layout review with:

```powershell
python test/generate/generate_clapping_four_podium_placement.py
```

Regenerate the runtime still and animated examples with:

```powershell
python test/generate/generate_podiums_clapping_previews.py
```

The Legacy and Customizable PNGs use their own existing podium geometry and
canvas dimensions. Each lower result has a 68-by-104-pixel portrait starting
at y=830. The first 5th and first 7th entrants have portraits on the right of
their text blocks, with right-aligned stock/seed rows, sponsors, and names to
their left. Legacy anchors the first portrait's right edge to its podium's
visible front-right corner, and the second portrait's left edge to the next
podium's front-left corner. This creates gaps for the numbers without including
the perspective side faces; `legacy-front-face-edges.json` stores the measured
asset-relative corners. Customizable retains its existing portrait/text positions.
Two copies each of canonical `05th.png` and `07th.png` artwork sit
in a vertical stack with a 12-pixel gap between the corresponding pairs of portraits.
Their height is taken directly from the final Customizable fourth-place artwork;
each ordinal keeps its own aspect ratio. The main four numbers fill the outer
panel inside the thick outer outline, covering the inner stripes while leaving
the outer border visible. First place fits the numeral
1 itself to that span, letting its wreath ribbon hang below the podium.
These four number positions/sizes are saved in the Customizable Top 8
four-podium preference file. Individual summary rank labels are omitted. The numbers
do not reserve space or move the portraits or text and are composited over the
portraits when they overlap. The alternating blocks are anchored directly to
their podium edges. The portrait uses the entrant's first selected character/costume,
the reviewed clapping crop, and the same RGBA background as the player-name
text. The visible lower ranks are 5th, 5th, 7th, and 7th.

The canonical URL chooses bottom left, middle, or bottom right based on the
least overlap with the actual lower-result text, portrait panels, and placement
artwork. Equal overlap prefers bottom left. Its position stays fixed throughout
the animation and keeps the header logo clear. The detail PNGs enlarge the footer uniformly by two
times. `placement-draft.json` records the proposed rectangles, text widths,
colors, text anchors, shared-number placements, and example identities separately
for the two styles.

These placement artifacts use populated scaffold coordinates like the existing
podium geometry review scripts. Readiness flags remain unchanged. The exact
frontend render now uses the reviewed panel geometry from
`preferences/portraits/podiums_clapping.json`. Animated downloads are lossless
looping APNGs (with a `.png` extension); still downloads are ordinary PNGs.
Each uses the same character crops, borders, text colors, and rank overlays.
The `*-podiums-clapping-animated.png` and `*-podiums-clapping-still.png` files
exercise the runtime renderer for both podium styles.

The same fitting rule now covers all Customizable layouts. To recalibrate their
existing number placements from the semantic masks, run
`python test/podium_layout_previews/fit_customizable_podium_numbers.py`.
Numbers are associated with podium slot IDs, including the centered Top 3 winner;
omitted numbers are not added. The first-place numeral fits the panel while the
crest ribbon extends beneath it.

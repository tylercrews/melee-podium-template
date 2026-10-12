# Four-podium clapping portrait placement proposal

Render the static layout review with:

```powershell
python test/generate/generate_clapping_four_podium_placement.py
```

The Legacy and Customizable PNGs use their own existing podium geometry and
canvas dimensions. Each lower result has a 68-by-104-pixel portrait starting
at y=830. The first 5th and first 7th entrants have portraits on the right of
their text blocks, with right-aligned stock/seed rows, sponsors, and names to
their left. The second 5th and second 7th keep their original portrait and text
positions. Shared canonical `05th.png` and `07th.png` artwork sits between each
pair of portraits, with 145-by-104-pixel maximum bounds similar to Legacy's
fourth-place numeral; individual summary rank labels are omitted. The first
members' blocks leave clearance around those badges. The portrait uses the entrant's first selected character/costume,
the reviewed clapping crop, and the same RGBA background as the player-name
text. The visible lower ranks are 5th, 5th, 7th, and 7th.

The canonical URL is proposed in the upper-left header so it does not overlap
the lower-result panels. The detail PNGs enlarge the footer uniformly by two
times. `placement-draft.json` records the proposed rectangles, text widths,
colors, text anchors, shared-number placements, and example identities separately
for the two styles.

These are offline review artifacts, using populated scaffold coordinates like
the existing podium geometry review scripts. No runtime preference readiness
flags, routes, downloads, or animation behavior are changed. After placement
review, the same fixed lower-result rectangles can be composited for each GIF
frame while the rest of the image remains static.

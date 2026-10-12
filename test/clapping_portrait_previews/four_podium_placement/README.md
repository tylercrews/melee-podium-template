# Four-podium clapping portrait placement proposal

Render the static layout review with:

```powershell
python test/generate/generate_clapping_four_podium_placement.py
```

The Legacy and Customizable PNGs use their own existing podium geometry and
canvas dimensions. Each lower result has a 68-by-104-pixel portrait starting
at y=830, with placement, stock icons, seed, sponsor, and name immediately to
its right. The portrait uses the entrant's first selected character/costume,
the reviewed clapping crop, and the same RGBA background as the player-name
text. The visible lower ranks are 5th, 5th, 7th, and 7th.

The canonical URL is proposed in the upper-left header so it does not overlap
the lower-result panels. The detail PNGs enlarge the footer uniformly by two
times. `placement-draft.json` records the proposed rectangles, text widths,
colors, and example identities separately for the two styles.

These are offline review artifacts, using populated scaffold coordinates like
the existing podium geometry review scripts. No runtime preference readiness
flags, routes, downloads, or animation behavior are changed. After placement
review, the same fixed lower-result rectangles can be composited for each GIF
frame while the rest of the image remains static.

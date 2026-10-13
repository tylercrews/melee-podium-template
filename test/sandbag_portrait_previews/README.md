# Sandbag proportions

Regenerate from the project root:

```powershell
.venv/Scripts/python.exe test/generate/generate_sandbag_previews.py
```

- Podiums use a standing-pose relativity scale of `2.42`, followed by each
  layout's existing scale. At the Top 4 scale, Sandbag's visible height is about
  264 pixels, matching Captain Falcon's calibrated salute/high-kick poses.
- Standing PNGs and one-frame GIFs are vertically cropped to `512x420`, removing
  46 transparent rows from each end while retaining the full source width.
- Clapping uses the compact single-frame GIF. Profile 3 shows the whole bag
  inside a fixed 512-pixel-high window; profiles 2 and 4 independently retain
  1.2x and 0.77x relative zoom for later selection. All current lower results
  use profile 3, regardless of rank. Team-color copies use the same crops.
- Eyes centers the standing pose at source coordinates `(267, 173)` with
  zoom `0.65` so both pupils fit vertically. Doubles inherits the shared 2x
  multiplier for its half-width member window; Radial uses that same doubles
  focal profile with its own section geometry.
- Red, green, and blue are byte-identical costume aliases; the bag remains
  neutral-colored. Their static portraits, clapping GIFs, and stock icons all
  resolve through the standard costume naming rules.

The sheets show clapping placement profiles and Singles/Doubles Eyes crops.
The full podium previews compare Sandbag with other characters in both styles.

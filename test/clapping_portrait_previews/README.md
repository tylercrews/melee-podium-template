# Clapping portrait crop review

Generate the demo with:

```powershell
python test/generate/generate_clapping_portrait_previews.py
```

The output is under `test/generated/clapping_portraits/`:

- `clapping-portrait-sheet.png` compares all 26 default costumes with the supplied
  game references. Each row includes a crop with the reference backing and a crop
  whose backing matches its name-color caption.
- `clapping-square-sheet.png` shows square alternatives. Vertical zoom stays the
  same; the source window widens horizontally instead of stretching the image.
- `index.html` displays the reference and the full cropped animation for each
  character, with both backing treatments and a square alternative.
- `portraits/` contains individual PNGs and animated GIFs. Demo GIFs retain the
  source timing and loop count and redraw each frame to avoid ghosting.

`preferences/portraits/clapping.json` stores the initial, reviewable calibration.
`source_crop` is a half-open window in `source_size` coordinates, including
transparent padding outside the image when required. It stays fixed throughout
the animation. `preview_frame_index` selects the still used on the sheet; it does
not limit animated previews. `reference_file` and `reference_crop` identify the
reference used to calibrate that character. These references are offline review
inputs, not runtime renderer dependencies.

Ice Climbers additionally has serialized `member_layers`: the right member is
shifted behind the left member before applying the portrait window. Both cutouts
come from the same costume GIF and frame, keeping their claps synchronized.
The default costume shows Nana behind Popo, while costume-specific member order
is preserved. The source animations remain untouched.

The runtime renderer returns RGBA portraits with configurable output size,
backing color, border color/width, mirroring, and frame selection. The backing
accepts the actual entrant-name color directly. Clapping costume lookup uses the
animation manifest and deliberately ignores the character's static portrait pose.
All 134 available character/color choices are covered by the renderer tests.

```powershell
python -m unittest discover -s test -p clapping_portrait_test.py
```

The Podium layout is unchanged at this review stage.

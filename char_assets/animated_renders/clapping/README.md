# Clapping animations

This collection contains 123 supplied animated GIFs and 11 byte-identical
default-costume aliases. Its 134 entries cover every character/color selection
in `char_assets/renders/` for all 26 playable characters.

The current batch contains lighting-corrected 512x512 GIFs exported from
higher-resolution originals, with the corrected Mr. Game and Watch outlines.
The source batch, individual dimensions, checksums, and animation metadata
are recorded in the manifest.

## Paths and filenames

Character folders use the same display names as `char_assets/renders/`, including
`Captain Falcon`, `Dr. Mario`, and `Mr. Game and Watch`. Filenames follow the
existing render convention:

```text
<color code><pose>_<color>_<Character_Name>_tyro-decomp-anims_clapping.gif
Fox/03g_blue_Fox_tyro-decomp-anims_clapping.gif
Mr. Game and Watch/00d_default_Mr._Game_and_Watch_tyro-decomp-anims_clapping.gif
```

Color codes and names match the existing PNG renders and stock icons rather
than the exporter's costume indices. Each character's clapping pose uses the
next unused letter after that character's existing static poses, so its pose ID
does not collide with a standing or victory pose.

`manifest.json` supplies a complete lookup by `character` and `color`, including
the color code, pose, relative file path, original export filename and costume
index, SHA-256 checksum, dimensions, frame count, total duration, and loop value.
Paths are relative to this directory. For example, an asset's browser URL is
`/char_assets/animated_renders/clapping/` followed by its manifest `path`.

GIF bytes, frame timing, transparency, resolution, and looping are preserved
unchanged. These are animated assets; the current static portrait resolver and
portrait picker continue to read the separate `char_assets/renders/` PNGs.
This organization does not add animated rendering to the image maker.

## Source color translations

The source costume labels below identify the same costumes using different
names. All other source color names already match the project convention.

| Character | Source label | Project label |
| --- | --- | --- |
| Captain Falcon | gray | black |
| Fox | orange / lavender | red / blue |
| Ganondorf | lavender | purple |
| Ice Climbers | orange | cyan |
| Jigglypuff | yellow | white |
| Luigi | aqua / pink | blue / red |
| Mario | red | default |
| Mr. Game and Watch | black | default |
| Roy | yellow | white |
| Samus | lavender | blue |
| Yoshi | aqua | cyan |

The original source filename and color remain recorded in the manifest.
Source artwork is retained as supplied: for example, the Jigglypuff exports
do not show the alternate costumes' head accessories. Renaming does not add
missing accessories to the artwork.

## Default-costume aliases

The static collection offers some default costumes under an additional color
name for team-color selection. Every comparable static pose was verified to
have identical RGBA pixels before creating these GIF copies. Each copy's
`alias_of` points to its original default GIF in the manifest.

| Character | Additional default-costume label |
| --- | --- |
| Bowser | green |
| Ice Climbers | blue |
| Link | green |
| Luigi | green |
| Mario | red |
| Marth | blue |
| Ness | red |
| Peach | red |
| Samus | red |
| Yoshi | green |
| Young Link | green |

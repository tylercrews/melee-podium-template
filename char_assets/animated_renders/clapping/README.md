# Clapping animations

This collection contains 125 supplied animated GIFs, 14 byte-identical
default-costume aliases, and Sandbag's single-frame standing GIF. Its 140
entries cover all 26 playable characters plus Sandbag and the two Fighting
Wire Frames.

The wireframes come from `tyro-decomp-anims`: `Wireframe-Male` performs
Captain Falcon's results clap and `Wireframe-Female` performs Sheik's. Both
use the same camera and 42-frame, 840 ms timing as those fighters, so their
clapping crops reuse the reviewed Captain Falcon and Sheik windows. Each has
one default costume; doubles team colors leave wireframes unchanged instead of
requiring recolored copies.

Sandbag's standing pose comes from `tyro-decomp-anims`. The static portrait is
`char_assets/renders/Sandbag/00a_default_Sandbag_tyro-decomp-anims_standing.png`.
The clapping collection uses `Sandbag/00b_default_Sandbag_tyro-decomp-anims_standing.gif`
as a transparent one-frame version of that PNG. Both retain the native source's
2048-pixel width and are cropped to 1680 pixels tall, removing 184 transparent
rows at each end. The original source is archived in `docs/archive/sandbag/`;
`python generate_sandbag_assets.py` rebuilds the PNGs, GIFs, and
manifest checksums. Its pose ID remains `b` for compatibility, while the filename
describes its actual standing pose. Its preview frame is
zero; it stays still while other characters clap and also supports an entirely
still GIF when all four lower results use Sandbag.

Sandbag's red (`01`), green (`02`), and blue (`03`) costumes are identical
copies of its default standing PNG, clapping GIF, and stock icon. They provide
normal doubles team-color lookup without recoloring its neutral appearance.

The current batch contains lighting-corrected 512x512 GIFs exported from
higher-resolution originals, with the corrected Mr. Game and Watch outlines.
The source batch, individual dimensions, checksums, and animation metadata
are recorded in the manifest.

Ice Climbers uses the updated 25-frame, 500 ms exports. The other characters
retain their 42-frame, 840 ms exports. The standalone GIFs keep their supplied
timing; Podiums+Clapping fits shorter claps to the longest selected loop so all
four portraits start and finish their clap together. Its default and blue
choices remain byte-identical aliases, and the source orange costume retains
the project's cyan name.

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

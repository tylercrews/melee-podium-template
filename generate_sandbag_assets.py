"""Rebuild Sandbag's portraits and standing GIFs from its native PNG."""

from hashlib import sha256
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "docs/archive/sandbag/sandbag-standing-frame-0001-native-2048-yaw-plus43.png"
COSTUMES = (("00", "default"), ("01", "red"), ("02", "green"), ("03", "blue"))


def generate():
    with Image.open(SOURCE) as image:
        source = image.convert("RGBA")
    bounds = source.getchannel("A").getbbox()
    if bounds is None:
        raise ValueError("Sandbag source must contain visible pixels")
    crop = (0, bounds[1], source.width, bounds[3])
    portrait = source.crop(crop)

    # Reserve index 255 for transparency; GIFs cannot retain PNG's partial alpha.
    frame = portrait.convert("RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    palette = frame.getpalette()[:765]
    frame.putpalette(palette + [0] * (768 - len(palette)))
    frame.paste(255, mask=portrait.getchannel("A").point([255] + [0] * 255))

    animation_folder = ROOT / "char_assets/animated_renders/clapping"
    default_gif = "Sandbag/00b_default_Sandbag_tyro-decomp-anims_standing.gif"
    manifest_path = animation_folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for code, color in COSTUMES:
        name = f"{code}a_{color}_Sandbag_tyro-decomp-anims_standing.png"
        portrait.save(ROOT / "char_assets/renders/Sandbag" / name)
        gif_path = f"Sandbag/{code}b_{color}_Sandbag_tyro-decomp-anims_standing.gif"
        output = animation_folder / gif_path
        frame.save(output, duration=20, loop=0, transparency=255, background=255,
                   disposal=2, optimize=False)
        asset = next(row for row in manifest["assets"]
                     if row["character"] == "Sandbag" and row["color"] == color)
        previous = animation_folder / asset["path"]
        asset.update(path=gif_path, source_filename=SOURCE.name, source_crop=list(crop),
                     width=portrait.width, height=portrait.height, sha256=sha256(output.read_bytes()).hexdigest())
        if color != "default":
            asset["alias_of"] = default_gif
        if previous != output and previous.is_file():
            previous.unlink()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Generated 4 PNGs and 4 standing GIFs; vertical crop {crop}, size {portrait.size}.")


if __name__ == "__main__":
    generate()

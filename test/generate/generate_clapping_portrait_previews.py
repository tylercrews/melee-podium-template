"""Generate reference comparisons and animated review cards for clapping crops."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from clapping_assets import resolve_clapping_path
from clapping_portrait_renderer import render_clapping_portrait, render_clapping_portrait_frame
from models import Character, MELEE_FIGHTERS
from portrait_crop_adjustment_for_clapping import CALIBRATION_PATH, get_clapping_portrait_adjustment


# The four existing lower-result colors; the label and backing use the same RGBA.
NAME_COLORS = ("#FB8B00FF", "#00CDC3FF", "#FF00FFFF", "#8D8D8DFF")
SHEET_BACKGROUND = "#20242CFF"
REFERENCE_GRAY = "#666666FF"
REFERENCE_GREEN = "#1A661AFF"


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(PROJECT_ROOT / "fonts/Ubuntu-Regular.ttf"), size)


def _save_animation(path: Path, frames: list[Image.Image], durations: list[int], loop: int) -> None:
    frames[0].save(
        path, save_all=True, append_images=frames[1:], duration=durations,
        loop=loop, disposal=2, optimize=False,
    )


def generate(output_dir: Path) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    portrait_dir = output_dir / "portraits"
    portrait_dir.mkdir(exist_ok=True)
    preferences = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    rows = (len(MELEE_FIGHTERS) + 3) // 4
    sheet = Image.new("RGBA", (1640, 90 + rows * 270), SHEET_BACKGROUND)
    square_sheet = Image.new("RGBA", (1200, 90 + rows * 228), SHEET_BACKGROUND)
    draw, square_draw = ImageDraw.Draw(sheet), ImageDraw.Draw(square_sheet)
    draw.text((20, 14), "Clapping portrait crop review", font=_font(32), fill="#FFFFFFFF")
    draw.text((20, 57), "Game reference / calibrated GIF crop / backing matched to the name color", font=_font(19), fill="#CCD3DEFF")
    square_draw.text((20, 14), "Square portrait comparison", font=_font(30), fill="#FFFFFFFF")
    square_draw.text((20, 55), "Same vertical zoom; wider source window. Background and name use identical RGBA.", font=_font(17), fill="#CCD3DEFF")
    cards = []

    for i, fighter in enumerate(MELEE_FIGHTERS):
        character = Character(fighter)
        profile = preferences["characters"][fighter]
        adjustment = get_clapping_portrait_adjustment(fighter)
        color = NAME_COLORS[i % len(NAME_COLORS)]
        reference_color = REFERENCE_GREEN if fighter == "Sheik" else REFERENCE_GRAY
        slug = fighter.lower().replace(" ", "-").replace(".", "")
        left, top = (i % 4) * 410, 90 + (i // 4) * 270
        draw.text((left + 14, top + 8), fighter, font=_font(20), fill="#FFFFFFFF")
        gray = render_clapping_portrait(character, background_color=reference_color, frame_index=profile["preview_frame_index"])
        colored = render_clapping_portrait(character, background_color=color, frame_index=profile["preview_frame_index"])
        square = render_clapping_portrait(character, (144, 144), background_color=color, frame_index=profile["preview_frame_index"])
        with Image.open(PROJECT_ROOT / preferences["reference_directory"] / profile["reference_file"]) as reference_image:
            x1, y1, x2, y2 = profile["reference_crop"]
            reference = reference_image.crop((x1 - 6, y1 - 6, x2 + 6, y2 + 6)).convert("RGBA")
            reference = reference.resize((112, 172), Image.Resampling.LANCZOS)
        for offset, image, label in [(14, reference, "Reference"), (144, gray, "New GIF crop"), (274, colored, "Name color")]:
            sheet.alpha_composite(image, (left + offset, top + 44))
            draw.text((left + offset, top + 223), label, font=_font(15), fill=color if label == "Name color" else "#CCD3DEFF")
        draw.text((left + 14, top + 246), f"default costume / source frame {profile['preview_frame_index']}", font=_font(13), fill="#929EAEFF")
        square_left, square_top = (i % 4) * 300, 90 + (i // 4) * 228
        square_sheet.alpha_composite(square, (square_left + 78, square_top + 12))
        square_draw.text((square_left + 150, square_top + 166), fighter, font=_font(17), fill=color, anchor="mt")
        square_draw.text((square_left + 150, square_top + 193), "default costume", font=_font(13), fill="#929EAEFF", anchor="mt")
        reference.save(portrait_dir / f"{slug}-reference.png")
        colored.save(portrait_dir / f"{slug}.png")

        gray_frames, colored_frames, square_frames, durations = [], [], [], []
        with Image.open(resolve_clapping_path(character)) as source:
            loop = source.info.get("loop", 0)
            for frame in range(source.n_frames):
                source.seek(frame)
                durations.append(source.info.get("duration", 20))
                image = source.convert("RGBA")
                for collection, size, background in [
                    (gray_frames, (112, 172), reference_color),
                    (colored_frames, (112, 172), color),
                    (square_frames, (144, 144), color),
                ]:
                    collection.append(render_clapping_portrait_frame(image, adjustment, size, background_color=background))
        _save_animation(portrait_dir / f"{slug}-neutral.gif", gray_frames, durations, loop)
        _save_animation(portrait_dir / f"{slug}.gif", colored_frames, durations, loop)
        _save_animation(portrait_dir / f"{slug}-square.gif", square_frames, durations, loop)
        cards.append(f'''<article><h2>{html.escape(fighter)}</h2><div class="views">
<figure><img src="portraits/{slug}-reference.png" width="112" height="172"><figcaption>Game reference</figcaption></figure>
<figure><img src="portraits/{slug}-neutral.gif" width="112" height="172"><figcaption>Calibrated animation</figcaption></figure>
<figure><img src="portraits/{slug}.gif" width="112" height="172"><figcaption style="color:{color}">Name color</figcaption></figure>
</div><div class="square"><img src="portraits/{slug}-square.gif" width="144" height="144"><span style="color:{color}">{html.escape(fighter)}</span></div>
<p>Default costume · fixed crop throughout the clap</p></article>''')
        print(f"Rendered {fighter}", flush=True)

    sheet_path = output_dir / "clapping-portrait-sheet.png"
    square_path = output_dir / "clapping-square-sheet.png"
    index_path = output_dir / "index.html"
    sheet.convert("RGB").save(sheet_path)
    square_sheet.convert("RGB").save(square_path)
    index_path.write_text('''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Clapping portrait review</title>
<style>
*{box-sizing:border-box}body{margin:0;padding:28px;background:#15191FFF;color:#FFFFFFFF;font-family:system-ui,sans-serif}
h1{margin:0 0 10px}header p{color:#CCD3DEFF;max-width:900px;line-height:1.5}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(390px,1fr));gap:20px}
article{padding:18px;border:1px solid #424C5EFF;border-radius:10px;background:#20242CFF}
h2{font-size:20px;margin:0 0 18px}.views{display:flex;justify-content:space-between;gap:12px}
figure{margin:0}img{display:block}figcaption{font-size:12px;margin-top:8px}.square{display:flex;align-items:center;gap:18px;margin-top:20px}
.square span{font-weight:700}article p{color:#929EAEFF;font-size:12px}a{color:#00CDC3FF}
@media(max-width:460px){body{padding:12px}main{grid-template-columns:1fr}.views{gap:6px}.views img{width:88px;height:auto}figcaption{font-size:11px}}
</style><header><h1>Clapping portrait review</h1><p>All 26 characters, compared with the supplied game references.
Each crop stays fixed throughout the full animation. The colored backing and the name use the same color.
The square alternative keeps the same vertical zoom and widens the source window.</p>
<p><a href="clapping-portrait-sheet.png">Reference comparison sheet</a> · <a href="clapping-square-sheet.png">Square sheet</a></p></header><main>
''' + "\n".join(cards) + "</main></html>\n", encoding="utf-8")
    return sheet_path, square_path, index_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "test/generated/clapping_portraits")
    args = parser.parse_args()
    for output_path in generate(args.output_dir.resolve()):
        print(output_path)

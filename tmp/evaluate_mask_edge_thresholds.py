from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
source = Image.open(ROOT / "docs/archive/old_podium_iterations/02_3d_second_attempt/00x_flat_segmentation_mask.png").convert("RGBA")
current = Image.open(ROOT / "docs/archive/old_podium_iterations/02_3d_second_attempt/00x_flat_segmentation_mask_cleaned.png").convert("RGBA")
w, h = source.size
sp = list(source.getdata())
cp = list(current.getdata())
kernel = (1, 4, 6, 4, 1)
red_signal = [max(0, r - max(g, b)) / 255 for r, g, b, _ in sp]
smooth = [0.0] * len(sp)
for y in range(h):
    for x in range(w):
        total = weight = 0.0
        for ky, wy in enumerate(kernel, -2):
            yy = y + ky
            if not 0 <= yy < h:
                continue
            for kx, wx in enumerate(kernel, -2):
                xx = x + kx
                if 0 <= xx < w:
                    value = wy * wx
                    total += red_signal[yy * w + xx] * value
                    weight += value
        smooth[y * w + x] = total / weight

def variant(threshold):
    out = cp[:]
    changed = 0
    for i, ((r, g, b, a), cleaned) in enumerate(zip(sp, cp)):
        if a < 128 or cleaned[:3] not in ((0, 0, 0), (255, 0, 0)):
            continue
        black_seed = max(r, g, b) <= 40 and max(r, g, b) - min(r, g, b) <= 28
        red_seed = r >= 190 and r - max(g, b) >= 115
        if black_seed or red_seed:
            continue
        target = (255, 0, 0, 255) if smooth[i] >= threshold and r - max(g, b) >= 12 else (0, 0, 0, 255)
        if target != cleaned:
            out[i] = target
            changed += 1
    image = Image.new("RGBA", (w, h)); image.putdata(out)
    return image, changed

boxes = [(180, 568, 1075, 625), (20, 570, 205, 755), (1050, 570, 1245, 755), (180, 700, 1080, 752)]
thresholds = (.22, .28, .34, .40)
panels = []
for threshold in thresholds:
    image, changed = variant(threshold)
    crops = [image.crop(box).resize(((box[2]-box[0])*2, (box[3]-box[1])*2), Image.Resampling.NEAREST) for box in boxes]
    width = max(c.width for c in crops)
    height = 24 + sum(c.height for c in crops)
    panel = Image.new("RGBA", (width, height), (30,30,30,255))
    ImageDraw.Draw(panel).text((6, 6), f"threshold={threshold:.2f}, changed_vs_current={changed}", fill="white")
    y = 24
    for crop in crops:
        panel.paste(crop, (0, y)); y += crop.height
    panels.append(panel)
montage = Image.new("RGBA", (sum(p.width for p in panels), max(p.height for p in panels)), (10,10,10,255))
x = 0
for panel in panels:
    montage.paste(panel, (x,0)); x += panel.width
montage.save(ROOT / "tmp/mask_edge_thresholds.png")

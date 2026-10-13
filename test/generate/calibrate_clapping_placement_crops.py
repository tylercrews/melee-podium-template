"""Fit placement-specific clapping windows to the supplied in-game portraits.

This offline calibration matches silhouettes rather than costume RGB values.
It preserves the existing Ice Climbers member composition. Review the emitted
comparison sheets before adopting a newly fitted profile.
"""

from collections import Counter
from itertools import product
import json
from pathlib import Path
import sys

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from clapping_assets import load_clapping_frame
from clapping_frame_compositor import compose_clapping_member_layers
from models import Character
from portrait_crop_adjustment_for_clapping import ClappingPortraitAdjustment


# Read the number artwork, not the horizontal order, to identify each example.
REFERENCES = {
    "Dr. Mario": ("01 - dr mario.png", (4, 2, 3)),
    "Mario": ("02 - mario.png", (4, 3, 2)),
    "Luigi": ("03 - luigi.png", (4, 3, 2)),
    "Bowser": ("04 - bowser.png", (4, 2, 3)),
    "Peach": ("05 - peach.png", (4, 2, 3)),
    "Yoshi": ("06 - yoshi.png", (4, 3, 2)),
    "Donkey Kong": ("07 - dk.png", (4, 2, 3)),
    "Captain Falcon": ("08 - captain falcon.png", (4, 3, 2)),
    "Ganondorf": ("09 - ganondorf.png", (4, 3, 2)),
    "Falco": ("10 - falco.png", (4, 3, 2)),
    "Fox": ("11 - fox.png", (4, 3, 2)),
    "Ness": ("12 - ness.png", (4, 3, 2)),
    "Ice Climbers": ("13 - ice climbers.png", (2, 3, 4)),
    "Kirby": ("14 - kirby.png", (4, 3, 2)),
    "Samus": ("15 - samus.png", (3, 2, 4)),
    "Zelda": ("16 - zelda.png", (4, 2, 3)),
    "Sheik": ("17 - sheik.png", (3, 2, 4)),
    "Link": ("18 - link.png", (4, 2, 3)),
    "Young Link": ("19 - young link.png", (4, 2, 3)),
    "Pichu": ("20 - pichu.png", (4, 3, 2)),
    "Pikachu": ("21 - pikachu.png", (4, 3, 2)),
    "Jigglypuff": ("22 - jigglypuff.png", (4, 3, 2)),
    "Mewtwo": ("23 - mewtwo.png", (4, 3, 2)),
    "Mr. Game and Watch": ("24 - mr game and watch.png", (4, 3, 2)),
    "Marth": ("25 - marth.png", (4, 3, 2)),
    "Roy": ("26 - roy.png", (4, 3, 2)),
}


def reference_windows(image):
    """Locate the first border and match its strip in the two other columns."""
    rgb = image.convert("RGB")
    pixels = rgb.load()
    candidates = []
    for x in range(25, 65):
        ys = [y for y in range(25, 240) if 120 <= pixels[x, y][0] <= 140
              and max(pixels[x, y]) - min(pixels[x, y]) < 2]
        if len(ys) >= 150:
            candidates.append((x, min(ys)))
    if not candidates:
        raise ValueError("Could not locate portrait border")
    first_x, first_y = candidates[0]
    strip = rgb.crop((first_x - 2, first_y + 5, first_x + 8, first_y + 170)).convert("L")
    windows = []
    for column in range(3):
        if column == 0:
            border_x = first_x
        else:
            predicted = first_x + 337 * column
            def difference(x):
                candidate = rgb.crop((x - 2, first_y + 5, x + 8, first_y + 170)).convert("L")
                return ImageStat.Stat(ImageChops.difference(strip, candidate)).mean[0]
            border_x = min(range(predicted - 8, predicted + 9), key=difference)
        windows.append((border_x + 9, first_y + 9, border_x + 110, first_y + 170))
    return windows


def silhouette(image):
    rgb = image.convert("RGB")
    neutral = [pixel for pixel in rgb.getdata() if 40 <= pixel[0] <= 150 and max(pixel) - min(pixel) < 3]
    background = Counter(neutral).most_common(1)[0][0]
    values = [255 if max(abs(a - b) for a, b in zip(pixel, background)) > 16 else 0
              for pixel in rgb.getdata()]
    mask = Image.new("L", rgb.size)
    mask.putdata(values)
    return mask


def eye_features(image, fighter, *, source=False):
    """Disambiguate an enlarged round head whose silhouette reaches both edges."""
    rgba = image.convert("RGBA")
    values = []
    for index, (red, green, blue, alpha) in enumerate(rgba.getdata()):
        if fighter == "Jigglypuff":
            selected = green > 45 and green > red * 1.12 and green > blue * 1.12
        else:
            selected = max(red, green, blue) < 65
            # Ignore the dark blue/red feet below the face in the source and reference.
            selected = selected and index // rgba.width < (325 if source else 130)
        values.append(255 if selected and alpha > 160 else 0)
    mask = Image.new("L", rgba.size)
    mask.putdata(values)
    return mask


def fit_mask(source, reference, initial, *, levels=8):
    """Fit one uniform scale and translation; no stretching or per-frame crop."""
    target_area = ImageStat.Stat(reference).sum[0] / 255
    cache = {}
    def score(parameters):
        scale, left, top = parameters
        if scale <= .1 or scale > 2:
            return -1
        key = tuple(round(value, 6) for value in parameters)
        if key not in cache:
            transformed = source.transform(reference.size, Image.Transform.AFFINE,
                (1 / scale, 0, left, 0, 1 / scale, top), Image.Resampling.BILINEAR)
            intersection = ImageStat.Stat(ImageChops.multiply(transformed, reference)).sum[0] / 255
            area = ImageStat.Stat(transformed).sum[0] / 255
            cache[key] = intersection / max(1, target_area + area - intersection)
        return cache[key]
    best = initial
    best_score = score(best)
    for factor in (0.68, 1.0, 1.4):
        scale, left, top = initial
        start_scale = scale * factor
        center_x = left + reference.width / (2 * scale)
        current = (start_scale, center_x - reference.width / (2 * start_scale), top)
        current_score = score(current)
        steps = (scale * .18, 16, 24)
        for level in range(levels):
            for repeat in range(6):
                proposals = [tuple(current[i] + delta[i] * steps[i] for i in range(3))
                             for delta in product((-1, 0, 1), repeat=3)]
                candidate = max(proposals, key=score)
                candidate_score = score(candidate)
                if candidate_score <= current_score + 1e-7:
                    break
                current, current_score = candidate, candidate_score
            steps = tuple(step / 2 for step in steps)
        if current_score > best_score:
            best, best_score = current, current_score
    return best, best_score


def refine_round_head_second(profiles, image, fighter):
    """Measure face proportions between references when a head fills the panel."""
    third, second = profiles["3"], profiles["2"]
    third_eyes = eye_features(image.crop(tuple(third["reference_crop"])), fighter)
    second_eyes = eye_features(image.crop(tuple(second["reference_crop"])), fighter)
    (ratio, relative_left, relative_top), quality = fit_mask(third_eyes, second_eyes, (1.2, 8, 12))
    left, top, right, bottom = third["source_crop"]
    scale = 161 / (bottom - top)
    third_left = (left + right) / 2 - 101 / (2 * scale)
    second_scale = scale * ratio
    height = 161 / second_scale
    center_x = third_left + relative_left / scale + 101 / (2 * second_scale)
    second_top = top + relative_top / scale
    second.update({
        "source_crop": [round(center_x - height * .3125, 3), round(second_top, 3),
                        round(center_x + height * .3125, 3), round(second_top + height, 3)],
        "calibration": "reference_eye_proportions", "silhouette_overlap": None,
        "reference_zoom_ratio": round(ratio, 5), "reference_eye_overlap": round(quality, 4),
    })


def calibrate(output):
    original = json.loads((ROOT / "preferences/portraits/clapping.json").read_text(encoding="utf-8"))
    result = {"schema_version": 2, "default_placement": 3,
              "reference_directory": original["reference_directory"], "characters": {}}
    for fighter, old in original["characters"].items():
        filename, ranks = REFERENCES[fighter]
        if set(ranks) != {2, 3, 4}:
            raise ValueError(f"Missing placement reference for {fighter}")
        with Image.open(ROOT / original["reference_directory"] / filename) as image:
            windows = reference_windows(image)
            references = {rank: (window, silhouette(image.crop(window))) for rank, window in zip(ranks, windows)}
        source = load_clapping_frame(Character(fighter, color="default"), old["preview_frame_index"])
        seed = {**old, **old.get("placement_profiles", {}).get("3", {})}
        adjustment = ClappingPortraitAdjustment.from_dict(seed)
        alpha = compose_clapping_member_layers(source, adjustment).getchannel("A")
        left, top, right, bottom = seed["source_crop"]
        scale = 161 / (bottom - top)
        initial = (scale, (left + right) / 2 - 101 / (2 * scale), top)
        profiles = {}
        for rank, (window, reference) in references.items():
            parameters, quality = fit_mask(alpha, reference, initial)
            fitted_scale, source_left, source_top = parameters
            height = 161 / fitted_scale
            center_x = source_left + 101 / (2 * fitted_scale)
            width = height * 100 / 160
            profiles[str(rank)] = {
                "source_crop": [round(center_x - width / 2, 3), round(source_top, 3),
                                round(center_x + width / 2, 3), round(source_top + height, 3)],
                "reference_crop": list(window), "reference_placement": rank,
                "reference_background_color": "#666666FF",
                "calibration": "reference_silhouette", "silhouette_overlap": round(quality, 4),
            }
        if fighter in {"Kirby", "Jigglypuff"}:
            with Image.open(ROOT / original["reference_directory"] / filename) as image:
                refine_round_head_second(profiles, image, fighter)
        row = {"source_size": old["source_size"], "preview_frame_index": old["preview_frame_index"],
               "reference_file": filename, "placement_profiles": profiles}
        if old.get("member_layers"):
            row["member_layers"] = old["member_layers"]
        result["characters"][fighter] = row
        print(f"Fitted {fighter}: " + ", ".join(f"{rank}: {profile['calibration']}" for rank, profile in profiles.items()), flush=True)
    for row in result["characters"].values():
        three = row["placement_profiles"]["3"]["source_crop"]
        height = three[3] - three[1]
        for profile in row["placement_profiles"].values():
            crop = profile["source_crop"]
            profile["zoom_relative_to_3rd"] = round(height / (crop[3] - crop[1]), 5)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    calibrate(ROOT / "tmp/clapping-placement-calibration.json")

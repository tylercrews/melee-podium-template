"""Generate lightweight picker thumbnails for bundled background images."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
SOURCE_FOLDER = ROOT / "backgrounds"
OUTPUT_FOLDER = SOURCE_FOLDER / "thumbnails"
THUMBNAIL_SIZE = (160, 160)


def generate_background_thumbnails() -> list[Path]:
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for source_path in sorted(SOURCE_FOLDER.glob("*.png")):
        output_path = OUTPUT_FOLDER / f"{source_path.stem}.webp"
        with Image.open(source_path) as source:
            thumbnail = source.convert("RGB")
            thumbnail.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            thumbnail.save(output_path, "WEBP", quality=58, method=6)
        outputs.append(output_path)
    return outputs


if __name__ == "__main__":
    generated = generate_background_thumbnails()
    print(f"Generated {len(generated)} background thumbnails in {OUTPUT_FOLDER}")

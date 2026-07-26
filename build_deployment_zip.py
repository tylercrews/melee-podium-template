"""Create a cPanel-compatible deployment ZIP with POSIX archive paths."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "melee-podium-template-deploy.zip"
FILES = (
    "app.py",
    "passenger_wsgi.py",
    "requirements.txt",
    "bracket_import.py",
    "constants.py",
    "DrawPodium.py",
    "models.py",
    "portrait_scale_adjustment_for_each_mode.py",
    "portrait_scale_adjustment_to_character_relativity.py",
    "Impact.ttf",
    "Tyrowo-Inked-Regular.ttf",
    "top_3.png",
    "top_4.png",
    "top_8.png",
)
DIRECTORIES = ("char_assets", "frontend/dist")

with ZipFile(ARCHIVE, "w", compression=ZIP_DEFLATED) as archive:
    for relative_file in FILES:
        path = ROOT / relative_file
        archive.write(path, path.relative_to(ROOT).as_posix())
    for relative_directory in DIRECTORIES:
        directory = ROOT / relative_directory
        for path in directory.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(ROOT).as_posix())

print(f"Created {ARCHIVE}")

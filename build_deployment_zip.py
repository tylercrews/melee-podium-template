"""Create a cPanel-compatible deployment ZIP with POSIX archive paths."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "melee-podium-template-deploy.zip"
FILES = (
    "app.py",
    "passenger_wsgi.py",
    "requirements.txt",
    "background_builder.py",
    "color_values.py",
    "constants.py",
    "content_renderer.py",
    "creation.py",
    "creation_modes.py",
    "DrawPodium.py",
    "DrawEyes.py",
    "DrawSquares.py",
    "eyes_portrait_renderer.py",
    "format_preview.py",
    "formatting_assets.py",
    "geometric_content_renderer.py",
    "geometric_creation.py",
    "geometric_formatting_colors.py",
    "legacy_podium_content_renderer.py",
    "mode_preferences.py",
    "models.py",
    "podium_colors.py",
    "portrait_pose_labels.py",
    "portrait_assets.py",
    "portrait_scale_adjustment_for_each_mode.py",
    "portrait_scale_adjustment_for_eyes.py",
    "portrait_scale_adjustment_for_eyes_doubles.py",
    "portrait_scale_adjustment_to_character_relativity.py",
    "sample_creation_data.py",
    "square_portrait_renderer.py",
    "fonts/Impact.ttf",
    "fonts/Tyrowo-Inked-Regular.ttf",
    "fonts/Ubuntu-Regular.ttf",
)
DIRECTORIES = (
    "backgrounds",
    "bracket_import",
    "char_assets",
    "firebase_services",
    "formatting_assets",
    "frontend/dist",
    "preferences",
)

with ZipFile(ARCHIVE, "w", compression=ZIP_DEFLATED) as archive:
    for relative_file in FILES:
        path = ROOT / relative_file
        archive.write(path, path.relative_to(ROOT).as_posix())
    for relative_directory in DIRECTORIES:
        directory = ROOT / relative_directory
        for path in directory.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                archive.write(path, path.relative_to(ROOT).as_posix())

print(f"Created {ARCHIVE}")

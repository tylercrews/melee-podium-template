# Podium layout previews

This folder keeps comparable legacy and customizable preview generators beside
their generated images. The original generators stop after the formatting
stage. The `*_creation_previews.py` generators additionally use
`sample_creation_data.py` to show portraits, tags, seeds, and tournament text.

The review generators intentionally render preference files even while they
are marked `ready: false`; the production creation pipeline continues to reject
unfinished preferences. `sync_customizable_content_preferences.py` documents
and applies the initial anchor projection: horizontal positions follow each
podium's resized bounds, while portrait feet follow the custom mask's top face.

Run both generators from the repository root:

```powershell
.\.venv\Scripts\python.exe test\podium_layout_previews\generate_legacy_previews.py
.\.venv\Scripts\python.exe test\podium_layout_previews\generate_customizable_previews.py
.\.venv\Scripts\python.exe test\podium_layout_previews\generate_legacy_creation_previews.py
.\.venv\Scripts\python.exe test\podium_layout_previews\generate_customizable_creation_previews.py
.\.venv\Scripts\python.exe test\podium_layout_previews\generate_customizable_color_mode_previews.py
```

Each script writes all six layouts plus a contact sheet beneath `outputs/`.
Full creation previews are kept separately in `outputs/creation/`.
The color-mode generator creates separate contact sheets for the legacy and
medal presets, per-podium colors, and an alternating two-color setup.

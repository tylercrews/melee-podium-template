# Podium layout previews

This folder keeps the comparable legacy and customizable layout generators
beside their generated images. These previews intentionally stop after the
formatting stage: they render the background, podium bodies, and placement
tags from every preference file even when that file is still marked
`ready: false`. Character and text placement should be reviewed separately
before a customizable preference is marked ready for the creation pipeline.

Run both generators from the repository root:

```powershell
.\.venv\Scripts\python.exe test\podium_layout_previews\generate_legacy_previews.py
.\.venv\Scripts\python.exe test\podium_layout_previews\generate_customizable_previews.py
```

Each script writes all six layouts plus a contact sheet beneath `outputs/`.

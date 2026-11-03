# SkyRealm Mod Studio

Official desktop tool for creating SkyRealm modifications.

## Current version

The main screen has two working actions:
- **Создать мод** — opens a project dialog, lets you enter a mod name and choose a destination folder, then creates a starter mod project.
- **Выйти из Studio** — closes the application.

A new mod project contains:
- `mod.json` — basic mod metadata
- `scripts/main.js` — JavaScript entry point
- `README.md` — project description

## Requirements
- Windows 10/11
- Python 3.12+
- PySide6 6.9.3

## Run

```powershell
py -3.12 -m pip install -r requirements.txt
py -3.12 main.py
```

Or double-click `run.bat`.

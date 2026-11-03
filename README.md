# SkyRealm Mod Studio

Desktop tool for creating and editing SkyRealm modifications.

## Current workflow

1. Click **Создать мод** on the start screen.
2. Enter a project name and choose its parent folder.
3. The Studio creates a project and opens the editor automatically.

## Project editor

- **Обзор проекта** — edit mod name, version, author and description.
- **Редактор кода** — edit `scripts/main.js`.
- Project file list — view `mod.json` and `README.md`.
- **Сохранить** — writes metadata and script changes to disk.
- **Открыть папку** — opens the project in Windows Explorer.
- **На главный экран** — returns to the Studio start screen and asks about unsaved changes.

Each new project contains `mod.json`, `scripts/main.js` and `README.md`.

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

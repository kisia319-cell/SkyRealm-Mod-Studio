# SkyRealm Mod Studio

Windows desktop editor for SkyRealm mod projects.

## Features

- Create projects in JavaScript, JSON, or Python.
- Open existing projects and quickly return to recent projects.
- Project file tree with create, rename, and delete actions.
- Code editor with syntax highlighting, line numbers, indentation, completion, and autosave.
- Syntax diagnostics for JavaScript (Node.js), Python (AST), and JSON.
- Click a diagnostic to jump to its line.
- Project checks, ZIP source export, and backup/restore.
- Built-in learning course with nine lessons: project structure, variables, objects, conditions, functions, loops, debugging, practice, and SkyRealm modding limitations.
- First-launch choice to view the course or skip it. The course remains available from the home screen and the editor's Help button.
- GitHub Releases update check. When a newer release is found, the app asks whether to download and install it. The EXE is validated, replaced after the app exits, and the previous executable is retained as a backup.

## Languages and compatibility

JavaScript is the current scripting language used by Mod Studio. JSON stores metadata and data. Python can be edited and syntax-checked, but running Python mods inside SkyRealm is not supported by this statement. A successful syntax check does not grant code access to the game: actual gameplay features require a documented API supported by the matching SkyRealm runtime.

## Requirements for development

- Windows 10/11, 64-bit
- Python 3.12+
- PySide6 6.9.3
- Node.js is optional and required for JavaScript syntax diagnostics

## Run from source

```powershell
py -3.12 -m pip install -r requirements.txt
py -3.12 main.py
```

## Build

```powershell
py -3.12 -m pip install -r requirements.txt pyinstaller
py -3.12 -m compileall -q main.py core editors updater.py tests
py -3.12 -m PyInstaller --noconfirm --clean --onefile --windowed --name SkyRealmModStudio main.py
```

The executable is written to `dist/SkyRealmModStudio.exe`.

## Releases and updates

Pushing a change to the `main` branch builds the EXE and publishes/updates the stable GitHub Release `v1.2.0`. The release asset must be named `SkyRealmModStudio.exe`; the app checks the latest release on startup. For a future version, update `APP_VERSION` in `main.py` and the `tag_name` in `.github/workflows/build-studio.yml` together. Update checks and downloads require an internet connection. Users can decline an update and install it later.

## Safety

Code diagnostics only parse or syntax-check source files; they do not execute mod code. ZIP export packages source files only and does not certify compatibility with a specific SkyRealm game build.

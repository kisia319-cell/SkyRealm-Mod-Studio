# SkyRealm Mod Studio

Windows desktop editor for SkyRealm mod projects.

## Current features

- Create projects in JavaScript, JSON, or Python.
- Open an existing project by selecting its folder (it must contain a valid `mod.json`).
- Recent project list.
- Project file tree with create, rename, and delete actions.
- Code editor with syntax highlighting, line numbers, indentation, and Ctrl+Space completion.
- Automatic save and syntax diagnostics for JavaScript (Node.js), Python (AST), and JSON.
- Click a diagnostic to jump to its line.
- Basic safe formatting (JSON pretty-printing; whitespace cleanup for JS/Python).
- Project syntax check, ZIP export of source files, and one-step backup/restore for edited files.
- Built-in help for the editor and supported languages.
- GitHub Releases update check and one-file EXE replacement on Windows.

## Languages

JavaScript is the current game mod scripting language. JSON is used for project metadata and data files. Python is available as an editor language; running Python mods inside SkyRealm requires separate game-runtime support and is not implied by Studio.

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
py -3.12 -m compileall -q main.py core editors updater.py
py -3.12 -m PyInstaller --noconfirm --clean --onefile --windowed --name SkyRealmModStudio main.py
```

The executable is written to `dist/SkyRealmModStudio.exe`.

## Auto-updates

The application checks the latest GitHub Release in `kisia319-cell/SkyRealm-Mod-Studio`. To publish the first release or a later update, open Actions → Build SkyRealm Mod Studio → Run workflow and enter a version such as `1.1.0` in `release_version`; alternatively, push a version tag such as `v1.1.1`. GitHub Actions builds the EXE and attaches it to the release. The release asset must be named `SkyRealmModStudio.exe`. Update checks are best-effort and require an internet connection.

## Safety notes

Code diagnostics parse or syntax-check source files; they do not execute mod code. ZIP export packages project source files only and does not certify compatibility with a specific SkyRealm game build.

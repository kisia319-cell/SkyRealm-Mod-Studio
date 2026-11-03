# SkyRealm Mod Studio

Windows desktop editor for SkyRealm mod projects.

## Core features

- Create, open and revisit JavaScript, JSON and Python projects.
- Project tree with file creation, rename and delete.
- Code editor with syntax highlighting, line numbers, completion, indentation and autosave.
- Static syntax checks for JavaScript (Node.js), Python (AST) and JSON.
- Background project checks, project search, formatting, backup and version history.
- Learning course, limited SkyRealm API catalog and educational starter templates.
- GitHub Releases update check and portable EXE update flow with SHA-256 verification when the release asset exposes a digest.

## Advanced tools (1.6.0)

Open **Все инструменты** in a project to access:

- **Smart static analyzer:** detects selected risky JavaScript patterns while ignoring strings and ordinary comments; reports TODO/FIXME in comments and malformed JSON/Python. Findings are heuristics and require review; user code is never executed.
- **Strict project validation:** checks manifest field types, ID/version formats, safe entry paths, duplicate mod IDs, missing dependencies and declared conflicts. Missing dependencies are warnings because they may be supplied externally.
- **Visual data designer:** forms for items, weapons, mobs, quests, biomes, NPC dialogues and world events, with raw JSON synchronization, structured list editing and a frame timeline for animations. Files are Studio-side formats until the game implements matching loaders.
- **Asset gallery:** imports sprites, audio and fonts into `assets/`; previews supported images and opens other formats externally.
- **Compatibility check:** compares explicitly declared `gameVersion`, `minGameVersion` and `maxGameVersion` against a selected game version; it cannot certify runtime APIs.
- **Local mod manager:** discovers subprojects in `mods/*/mod.json` and stores Studio-side enable flags in `.studio-mods.json`. These flags do not load or unload mods in the game.
- **ZIP packager:** validates project metadata and dependencies, skips symlinks and excluded folders, writes atomically, then verifies the resulting ZIP.
- **Git viewer:** reads repository status and recent commits without performing destructive Git operations.
- **Live Studio logs:** displays log records emitted by Studio tools. It is not connected to the game's runtime logs.

## Important runtime compatibility note

The visual designers create project data files. They do **not** make those entities appear in SkyRealm automatically. The matching game runtime must implement and document loaders for each data format, event, animation, biome, item, weapon, mob or quest. The current editor does not execute arbitrary mod code, and a successful syntax check does not certify gameplay compatibility.

JavaScript is the current mod scripting language described by Studio. JSON stores metadata and designer data. Python can be edited and syntax-checked, but Python mod execution inside SkyRealm is not supported by this statement.

## Development requirements

- Windows 10/11, 64-bit
- Python 3.12+
- PySide6 6.9.3
- Node.js is optional and required for JavaScript syntax diagnostics
- Git is optional and required for the Git viewer

## Run from source

```powershell
py -3.12 -m pip install -r requirements.txt
py -3.12 main.py
```

## Build

```powershell
py -3.12 -m pip install -r requirements.txt pyinstaller
py -3.12 -m compileall -q main.py core editors updater.py advanced_tools.py tests
py -3.12 -m PyInstaller --noconfirm --clean --onefile --windowed --name SkyRealmModStudio main.py
```

The executable is written to `dist/SkyRealmModStudio.exe`.

## Releases and updates

Pushing supported source changes to `main` triggers the Windows build and updates the stable GitHub Release `v1.6.0`. The release asset is named `SkyRealmModStudio.exe`. Update checks and downloads require an internet connection. Users can decline an update and install it later.

## Safety and packaging

Diagnostics only parse or inspect source text; they do not execute mod code. ZIP export packages project sources and data only; it is not a signed installer and does not certify compatibility with a specific SkyRealm build. Never place API keys, passwords, access tokens or private credentials in a mod project.

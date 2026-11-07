# SkyRealm Mod Studio 1.9.0 — Direct game publishing

- Added a prominent **Опубликовать** button to the project editor.
- New JavaScript and Python projects start with a small valid script template that can be published immediately.
- Publication runs project and syntax checks first. Any errors stop the operation without changing the installed game.
- Valid JavaScript and Python script mods are installed to the local SkyRealm user-data folder, not into replaceable game files.
- The SkyRealm launcher exposes the published mod records to the game; the in-game catalog imports them under **Мои скриптовые моды**.
- Newly imported mods remain disabled until the player enables them in the catalog.
- Updated mods with the same ID replace their prior published version while preserving the in-game enabled state.
- Removed the built-in FaerTestMod test entry and automatic Faer Sword grant from the game.
- Existing movement and walking code was not changed.

## Supported script entry points

- JavaScript: `function onTick(context, state)`
- Python: `def on_tick(context, state):`

Scripts run through the existing isolated runtime and can request only its bounded safe actions. A successful syntax check does not prove that a script's intended gameplay behavior is correct.

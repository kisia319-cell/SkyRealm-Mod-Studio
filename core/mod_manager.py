"""Local mod discovery, dependency resolution and load-order export."""
import json
import os
import tempfile
from pathlib import Path

from core.project_validation import validate_manifest


def _as_ids(value):
    if isinstance(value, dict):
        return set(value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return set(value)
    return set()


def discover_mods(project: Path, state=None):
    root = Path(project).resolve()
    state = state if isinstance(state, dict) else {}
    mods_root = root / "mods"
    mods = {}
    errors, warnings = [], []
    if not mods_root.is_dir():
        return mods, errors, warnings
    for manifest in sorted(mods_root.glob("*/mod.json"), key=lambda p: str(p).casefold()):
        if manifest.is_symlink() or manifest.parent.is_symlink():
            warnings.append(f"Пропущена символическая ссылка: {manifest.parent.name}")
            continue
        metadata, manifest_errors, manifest_warnings = validate_manifest(manifest.parent)
        folder_name = manifest.parent.name
        if manifest_errors:
            errors.extend(f"{folder_name}: {message}" for message in manifest_errors)
            continue
        warnings.extend(f"{folder_name}: {message}" for message in manifest_warnings)
        mod_id = metadata["id"]
        if mod_id in mods:
            errors.append(f"Повторяющийся ID мода: {mod_id}")
            continue
        enabled_value = state.get(mod_id, True)
        if not isinstance(enabled_value, bool):
            warnings.append(f"{folder_name}: некорректный флаг включения; используется включённое состояние.")
            enabled_value = True
        mods[mod_id] = {
            "id": mod_id,
            "name": metadata["name"],
            "version": metadata["version"],
            "entry": metadata["entry"],
            "folder": manifest.parent,
            "relative_path": str(manifest.parent.relative_to(root)).replace("\\", "/"),
            "dependencies": _as_ids(metadata.get("dependencies", {})),
            "conflicts": _as_ids(metadata.get("conflicts", {})),
            "enabled": enabled_value,
        }
    return mods, errors, warnings


def resolve_load_order(mods):
    errors, warnings = [], []
    enabled = {mod_id: mod for mod_id, mod in mods.items() if mod.get("enabled", True)}
    for mod_id, mod in enabled.items():
        for dependency in sorted(mod["dependencies"]):
            if dependency not in mods:
                errors.append(f"{mod_id}: отсутствует обязательная зависимость {dependency}.")
            elif dependency not in enabled:
                errors.append(f"{mod_id}: зависимость {dependency} отключена.")
        for conflict in sorted(mod["conflicts"]):
            if conflict in enabled and conflict != mod_id:
                errors.append(f"{mod_id}: конфликтует с включённым модом {conflict}.")

    order, visiting, visited = [], set(), set()

    def visit(mod_id):
        if mod_id in visited:
            return
        if mod_id in visiting:
            errors.append(f"Обнаружен цикл зависимостей около мода {mod_id}.")
            return
        visiting.add(mod_id)
        for dependency in sorted(enabled[mod_id]["dependencies"]):
            if dependency in enabled:
                visit(dependency)
        visiting.remove(mod_id)
        visited.add(mod_id)
        order.append(mod_id)

    for mod_id in sorted(enabled):
        visit(mod_id)
    if errors:
        return [], list(dict.fromkeys(errors)), warnings
    return order, errors, warnings


def export_load_order(project: Path, mods, order):
    root = Path(project).resolve()
    payload = {
        "schemaVersion": 1,
        "generatedBy": "SkyRealm Mod Studio",
        "mods": [
            {
                "id": mod_id,
                "version": mods[mod_id]["version"],
                "path": mods[mod_id]["relative_path"],
                "entry": mods[mod_id]["entry"],
            }
            for mod_id in order
        ],
    }
    target = root / "mods.loadorder.json"
    fd, temp_name = tempfile.mkstemp(prefix=".mods-loadorder-", suffix=".tmp", dir=str(root))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return target

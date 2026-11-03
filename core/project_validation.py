"""Strict, non-executing validation for SkyRealm mod project manifests."""
import json
import re
from pathlib import Path

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{1,127}$")
_VERSION_RE = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def validate_manifest(folder: Path):
    """Return (metadata, errors, warnings); never execute project code."""
    root = Path(folder).resolve()
    errors, warnings = [], []
    manifest = root / "mod.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, ["Не найден mod.json."], warnings
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, [f"Не удалось прочитать mod.json: {exc}"], warnings

    if not isinstance(data, dict):
        return {}, ["Корень mod.json должен быть JSON-объектом."], warnings

    for key in ("name", "id", "version", "entry"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"Поле '{key}' должно быть непустой строкой.")

    if isinstance(data.get("id"), str) and data["id"].strip() and not _ID_RE.fullmatch(data["id"].strip()):
        errors.append("id должен содержать 2–128 символов: a-z, 0-9, точку, подчёркивание, дефис или двоеточие; первый символ — буква или цифра.")
    if isinstance(data.get("version"), str) and data["version"].strip() and not _VERSION_RE.fullmatch(data["version"].strip()):
        warnings.append("Версия не похожа на SemVer (например, 1.2.3).")

    entry_value = data.get("entry")
    if isinstance(entry_value, str) and entry_value.strip():
        entry_path = Path(entry_value)
        if entry_path.is_absolute():
            errors.append("entry не должен быть абсолютным путём.")
        else:
            resolved = (root / entry_path).resolve()
            if not _inside(root, resolved) or resolved == root:
                errors.append("entry выходит за пределы папки проекта.")
            elif not resolved.is_file():
                errors.append(f"Главный файл не найден: {entry_value}")
            elif resolved.suffix.lower() not in {".js", ".mjs", ".cjs"}:
                warnings.append("Главный файл не JavaScript. Проверь, поддерживает ли его игровой runtime.")

    normalized = {}
    for field in ("dependencies", "conflicts"):
        value = data.get(field)
        if value is not None and not isinstance(value, (dict, list)):
            errors.append(f"Поле '{field}' должно быть объектом или массивом.")
            normalized[field] = set()
            continue
        ids = list(value.keys()) if isinstance(value, dict) else list(value or [])
        if any(not isinstance(item, str) or not _ID_RE.fullmatch(item.strip()) for item in ids):
            errors.append(f"Все ID в поле '{field}' должны соответствовать формату ID мода.")
        if len(ids) != len(set(item for item in ids if isinstance(item, str))):
            warnings.append(f"Поле '{field}' содержит повторяющиеся ID.")
        normalized[field] = {item.strip() for item in ids if isinstance(item, str) and item.strip()}
        if isinstance(value, dict):
            for key, constraint in value.items():
                if constraint is not None and not isinstance(constraint, str):
                    errors.append(f"Ограничение версии для '{key}' в поле '{field}' должно быть строкой.")
    if data.get("id") in normalized.get("dependencies", set()):
        errors.append("Мод не может зависеть сам от себя.")
    overlap = normalized.get("dependencies", set()) & normalized.get("conflicts", set())
    if overlap:
        errors.append("Один ID не может одновременно быть зависимостью и конфликтом: " + ", ".join(sorted(overlap)))

    return data, errors, warnings


def validate_project(folder: Path):
    """Validate the manifest and relationships between mods in mods/."""
    root = Path(folder).resolve()
    data, errors, warnings = validate_manifest(root)
    if not data:
        return errors, warnings

    mods_root = root / "mods"
    installed = {}
    if mods_root.is_symlink():
        warnings.append("Папка mods/ является символической ссылкой и не проверялась.")
        return errors, warnings
    if mods_root.is_dir():
        for manifest in sorted(mods_root.glob("*/mod.json")):
            if manifest.is_symlink() or manifest.parent.is_symlink():
                warnings.append(f"{manifest.parent.name}: символическая ссылка пропущена.")
                continue
            try:
                child = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                warnings.append(f"{manifest.relative_to(root)}: не удалось прочитать manifest подпроекта.")
                continue
            if not isinstance(child, dict):
                warnings.append(f"{manifest.relative_to(root)}: manifest должен быть объектом.")
                continue
            mod_id = child.get("id")
            if not isinstance(mod_id, str) or not mod_id.strip():
                warnings.append(f"{manifest.relative_to(root)}: отсутствует корректный id.")
                continue
            if mod_id in installed:
                errors.append(f"Повторяется id мода '{mod_id}': {installed[mod_id]} и {manifest.parent.relative_to(root)}.")
            else:
                installed[mod_id] = manifest.parent

    dependencies = data.get("dependencies", {})
    if isinstance(dependencies, dict):
        required = set(dependencies)
    elif isinstance(dependencies, list):
        required = set(dependencies)
    else:
        required = set()
    conflicts = data.get("conflicts", {})
    if isinstance(conflicts, dict):
        blocked = set(conflicts)
    elif isinstance(conflicts, list):
        blocked = set(conflicts)
    else:
        blocked = set()

    own_id = data.get("id")
    if own_id in required:
        errors.append("Мод не может зависеть сам от себя.")
    for dep in sorted(required):
        if dep not in installed:
            warnings.append(f"Не найдена зависимость '{dep}' в папке mods/.")
    for conflict in sorted(blocked):
        if conflict in installed:
            errors.append(f"Обнаружен конфликт с установленным модом '{conflict}'.")

    return errors, warnings

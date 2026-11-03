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

    for field in ("dependencies", "conflicts"):
        value = data.get(field)
        if value is not None and not isinstance(value, (dict, list)):
            errors.append(f"Поле '{field}' должно быть объектом или массивом.")
        elif isinstance(value, list) and any(not isinstance(item, str) or not item.strip() for item in value):
            errors.append(f"Все элементы '{field}' должны быть непустыми строками.")
        elif isinstance(value, dict) and any(not isinstance(k, str) or not k.strip() for k in value):
            errors.append(f"Ключи '{field}' должны быть непустыми строками.")

    return data, errors, warnings


def validate_project(folder: Path):
    """Validate the manifest and relationships between mods in mods/."""
    root = Path(folder).resolve()
    data, errors, warnings = validate_manifest(root)
    if not data:
        return errors, warnings

    mods_root = root / "mods"
    installed = {}
    if mods_root.is_dir():
        for manifest in sorted(mods_root.glob("*/mod.json")):
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

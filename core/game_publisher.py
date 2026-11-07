"""Publish a validated Studio script into the local SkyRealm launcher profile."""
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from core.code_analysis import analyze_file
from core.project_validation import validate_manifest, validate_project

_ID_RE = re.compile(r"^[a-z0-9_-]{6,48}$")
_MAX_CODE = 14000


def _data_root():
    base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    return base / "SkyRealm" / "user-mods"


def publish_project(folder):
    root = Path(folder).resolve()
    metadata, errors, warnings = validate_manifest(root)
    project_errors, project_warnings = validate_project(root)
    errors.extend(project_errors)
    if errors:
        raise ValueError("Проверка проекта не пройдена:\\n" + "\\n".join(dict.fromkeys(errors)))

    mod_id = str(metadata.get("id", "")).strip()
    if not _ID_RE.fullmatch(mod_id):
        raise ValueError("Для публикации ID должен содержать 6–48 символов: a-z, 0-9, дефис или подчёркивание.")
    name = str(metadata.get("name", "")).strip()
    if not name or len(name) > 32:
        raise ValueError("Название мода должно содержать от 1 до 32 символов.")
    description = str(metadata.get("description", "") or "").strip()[:140]
    entry = metadata.get("entry")
    if not isinstance(entry, str) or not entry.strip():
        raise ValueError("В mod.json не указан главный файл entry.")
    source_path = (root / entry).resolve()
    try:
        source_path.relative_to(root)
    except ValueError:
        raise ValueError("Главный файл выходит за пределы проекта.") from None
    if source_path == root or not source_path.is_file() or (root / entry).is_symlink():
        raise ValueError("Главный файл мода отсутствует или является недопустимой ссылкой.")
    suffix = source_path.suffix.lower()
    if suffix not in {".js", ".mjs", ".py"}:
        raise ValueError("Для публикации поддерживаются только JavaScript (.js/.mjs) и Python (.py).")
    language = "python" if suffix == ".py" else "javascript"
    source = source_path.read_text(encoding="utf-8")
    if len(source) < 10 or len(source) > _MAX_CODE:
        raise ValueError(f"Код должен содержать от 10 до {_MAX_CODE} символов.")
    required = r"def\\s+on_tick\\s*\\(" if language == "python" else r"function\\s+onTick\\s*\\("
    if not re.search(required, source):
        expected = "def on_tick(context, state):" if language == "python" else "function onTick(context, state)"
        raise ValueError(f"В главном файле должна быть функция {expected}.")
    syntax_issues = analyze_file(source_path, source)
    if syntax_issues:
        details = "\\n".join(f"Строка {line}: {title}: {message}" for line, _col, title, message in syntax_issues)
        raise ValueError("Синтаксическая проверка главного файла не пройдена:\\n" + details)

    record = {
        "format": "skyrealm-studio-mod",
        "schemaVersion": 1,
        "id": mod_id,
        "name": name,
        "description": description,
        "version": str(metadata.get("version", "1.0.0"))[:40],
        "language": language,
        "source": source,
    }
    destination = _data_root()
    destination.mkdir(parents=True, exist_ok=True)
    filename = hashlib.sha256(mod_id.encode("utf-8")).hexdigest() + ".json"
    target = destination / filename
    fd, temporary = tempfile.mkstemp(prefix=".mod-publish-", suffix=".tmp", dir=str(destination))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\\n") as stream:
            json.dump(record, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"path": target, "name": name, "id": mod_id, "language": language}

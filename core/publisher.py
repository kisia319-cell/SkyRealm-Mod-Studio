"""Prepare portable mod release bundles with validation and SHA-256 metadata."""
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from core.archive_builder import create_project_archive
from core.compatibility import check_compatibility
from core.project_validation import validate_manifest, validate_project


def _write_text_atomic(path, content):
    path = Path(path)
    fd, temp_name = tempfile.mkstemp(prefix=".release-info-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def prepare_release(project, destination, game_version="", notes=""):
    root = Path(project).resolve()
    target = Path(destination).expanduser().resolve()
    metadata, errors, warnings = validate_manifest(root)
    project_errors, project_warnings = validate_project(root)
    errors.extend(project_errors)
    warnings.extend(project_warnings)
    errors = list(dict.fromkeys(errors))
    warnings = list(dict.fromkeys(warnings))
    if errors:
        raise ValueError("Исправь ошибки перед публикацией:\n" + "\n".join(errors))
    if game_version.strip():
        compat_errors, compat_warnings, compat_info = check_compatibility(root, game_version.strip())
        errors.extend(compat_errors)
        warnings.extend(compat_warnings)
        if errors:
            raise ValueError("Проверка версии игры не пройдена:\n" + "\n".join(errors))
    else:
        compat_info = []
        warnings.append("Версия SkyRealm не указана; совместимость по версии не проверялась.")
    try:
        target.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("Сохраняй релизный ZIP за пределами папки проекта.")
    if len(notes) > 20000:
        raise ValueError("Описание релиза не должно превышать 20 000 символов.")
    archive_path, file_count = create_project_archive(root, target)
    digest = hashlib.sha256()
    with archive_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    checksum = digest.hexdigest()
    release_info = {
        "schemaVersion": 1,
        "generatedBy": "SkyRealm Mod Studio",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "mod": {
            "id": metadata.get("id"),
            "name": metadata.get("name"),
            "version": metadata.get("version"),
            "author": metadata.get("author", ""),
        },
        "gameVersionChecked": game_version.strip() or None,
        "compatibilityNotes": compat_info,
        "warnings": warnings,
        "releaseNotes": notes.strip(),
        "archive": archive_path.name,
        "fileCount": file_count,
        "sha256": checksum,
    }
    manifest_path = archive_path.with_suffix(archive_path.suffix + ".release.json")
    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    _write_text_atomic(manifest_path, json.dumps(release_info, ensure_ascii=False, indent=2) + "\n")
    _write_text_atomic(checksum_path, f"{checksum}  {archive_path.name}\n")
    return {
        "archive": archive_path,
        "manifest": manifest_path,
        "checksum": checksum_path,
        "file_count": file_count,
        "sha256": checksum,
        "warnings": warnings,
    }

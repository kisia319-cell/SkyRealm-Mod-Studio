import os
import tempfile
import zipfile
from pathlib import Path

EXCLUDED_DIRS = {".git", "__pycache__", ".venv", "venv", ".backups", ".history", "build", "dist", "node_modules", ".pytest_cache"}
EXCLUDED_FILES = {".studio-mods.json"}


def create_project_archive(project, destination):
    root = Path(project).resolve()
    target = Path(destination).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Папка проекта не существует.")
    if target.exists() and target.is_dir():
        raise ValueError("Выбери имя ZIP-файла, а не папку.")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".skyrealm-", suffix=".zip", dir=str(target.parent))
    os.close(fd)
    temp = Path(temp_name)
    count = 0
    try:
        with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as archive:
            for current, dirs, files in os.walk(root, followlinks=False):
                current_path = Path(current)
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not (current_path / d).is_symlink()]
                for name in files:
                    source = current_path / name
                    if name in EXCLUDED_FILES or source.is_symlink() or not source.is_file():
                        continue
                    resolved = source.resolve()
                    try:
                        relative = resolved.relative_to(root)
                    except ValueError:
                        continue
                    if resolved in (target, temp.resolve()) or any(p in EXCLUDED_DIRS for p in relative.parts):
                        continue
                    archive.write(source, relative.as_posix())
                    count += 1
        with zipfile.ZipFile(temp) as archive:
            damaged = archive.testzip()
            if damaged:
                raise zipfile.BadZipFile("Ошибка проверки архива: " + damaged)
        os.replace(temp, target)
        return target, count
    finally:
        temp.unlink(missing_ok=True)

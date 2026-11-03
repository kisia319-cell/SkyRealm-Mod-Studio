"""Safe, atomic ZIP export shared by all Studio packaging actions."""
import os
import tempfile
import zipfile
from pathlib import Path

EXCLUDED_DIRS = {
    ".git", "__pycache__", ".venv", "venv", ".backups", ".history",
    "build", "dist", "node_modules", ".pytest_cache", ".mypy_cache",
}
EXCLUDED_FILES = {".studio-mods.json"}


def create_project_archive(project, destination):
    root = Path(project).resolve()
    target = Path(destination).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Папка проекта не существует.")
    if target.exists() and target.is_dir():
        raise ValueError("Путь архива указывает на папку, а не на ZIP-файл.")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".skyrealm-project-", suffix=".zip", dir=str(target.parent))
    os.close(fd)
    temp_path = Path(temp_name)
    count = 0
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            def walk_error(error):
                raise error
            for current, dirs, files in os.walk(root, topdown=True, followlinks=False, onerror=walk_error):
                current_path = Path(current)
                dirs[:] = sorted(
                    name for name in dirs
                    if name not in EXCLUDED_DIRS and not (current_path / name).is_symlink()
                )
                for name in sorted(files):
                    source = current_path / name
                    if name in EXCLUDED_FILES or source.is_symlink() or not source.is_file():
                        continue
                    resolved = source.resolve()
                    try:
                        relative = resolved.relative_to(root)
                    except ValueError:
                        continue
                    if resolved == target or resolved == temp_path.resolve():
                        continue
                    if any(part in EXCLUDED_DIRS for part in relative.parts):
                        continue
                    archive.write(source, relative.as_posix())
                    count += 1
        with zipfile.ZipFile(temp_path, "r") as check:
            damaged = check.testzip()
            if damaged:
                raise zipfile.BadZipFile(f"Архив повреждён: {damaged}")
        os.replace(temp_path, target)
        return target, count
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass

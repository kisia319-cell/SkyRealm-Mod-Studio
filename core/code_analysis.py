import ast
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def analyze_file(path: Path, text: str):
    """Static syntax checks only: user code is never executed."""
    suffix = path.suffix.lower()
    issues = []
    if suffix == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            issues.append((exc.lineno, exc.colno, "Ошибка JSON", exc.msg))
    elif suffix == ".py":
        try:
            ast.parse(text or "\n", filename=str(path))
        except SyntaxError as exc:
            issues.append((exc.lineno or 1, exc.offset or 1, "Ошибка Python", exc.msg))
    elif suffix in {".js", ".mjs", ".cjs"}:
        node = shutil.which("node")
        if not node:
            issues.append((1, 1, "Проверка JavaScript недоступна",
                           "Node.js не найден. Установи Node.js LTS и перезапусти Mod Studio."))
        else:
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile("w", suffix=suffix, encoding="utf-8",
                                                 newline="\n", delete=False) as temp:
                    temp.write(text)
                    temp_path = Path(temp.name)
                startupinfo = None
                creationflags = 0
                if os.name == "nt":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                result = subprocess.run(
                    [node, "--check", str(temp_path)],
                    text=True, capture_output=True, timeout=6,
                    encoding="utf-8", errors="replace",
                    startupinfo=startupinfo, creationflags=creationflags,
                )
                if result.returncode:
                    message = (result.stderr or result.stdout).strip()
                    import re
                    line = 1
                    col = 1
                    match = re.search(r":(\d+)(?::(\d+))?", message)
                    if match:
                        line = int(match.group(1))
                        if match.group(2):
                            col = int(match.group(2))
                    issues.append((line, col, "Ошибка JavaScript", message[-1200:]))
            except subprocess.TimeoutExpired:
                issues.append((1, 1, "Проверка JavaScript прервана",
                               "Node.js не ответил за 6 секунд. Проверь установку Node.js и попробуй снова."))
            except OSError as exc:
                issues.append((1, 1, "Не удалось проверить JavaScript", str(exc)))
            finally:
                if temp_path:
                    temp_path.unlink(missing_ok=True)
    return issues

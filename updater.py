import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from PySide6.QtCore import QThread, Signal


REPOSITORY = "kisia319-cell/SkyRealm-Mod-Studio"
API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"


def version_tuple(value):
    numbers = re.findall(r"\d+", str(value))
    return tuple(int(part) for part in numbers[:4]) or (0,)


class UpdateWorker(QThread):
    finished_check = Signal(object, str)

    def __init__(self, current_version, parent=None):
        super().__init__(parent)
        self.current_version = current_version

    def run(self):
        request = urllib.request.Request(API_URL, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "SkyRealm-Mod-Studio"
        })
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                release = json.loads(response.read().decode("utf-8"))
            tag = release.get("tag_name", "").lstrip("v")
            if not tag or version_tuple(tag) <= version_tuple(self.current_version):
                self.finished_check.emit(None, "")
                return
            asset = next((a for a in release.get("assets", [])
                          if a.get("name", "").lower() == "skyrealmmodstudio.exe"), None)
            if not asset or not asset.get("browser_download_url"):
                self.finished_check.emit(None, "В релизе нет SkyRealmModStudio.exe.")
                return
            self.finished_check.emit({"version": tag, "url": asset["browser_download_url"]}, "")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                self.finished_check.emit(None, "")
            else:
                self.finished_check.emit(None, f"GitHub вернул HTTP {exc.code}.")
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            self.finished_check.emit(None, str(exc))


class DownloadWorker(QThread):
    finished_download = Signal(str, str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        destination = Path(tempfile.gettempdir()) / "SkyRealmModStudio-update.exe"
        request = urllib.request.Request(self.url, headers={"User-Agent": "SkyRealm-Mod-Studio"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
                total = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > 250 * 1024 * 1024:
                        raise ValueError("Размер обновления превышает 250 МБ.")
                    output.write(chunk)
            if total < 1024 * 1024:
                raise ValueError("Скачанный файл слишком маленький и не похож на EXE.")
            with destination.open("rb") as file:
                if file.read(2) != b"MZ":
                    raise ValueError("GitHub вернул файл, который не является Windows EXE.")
            self.finished_download.emit(str(destination), "")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass
            self.finished_download.emit("", str(exc))


def launch_installer(current_exe: Path, new_exe: Path):
    current = str(current_exe.resolve())
    new = str(new_exe.resolve())
    script = Path(tempfile.gettempdir()) / "skyrealm_mod_studio_update.bat"
    content = (
        "@echo off\r\n"
        "setlocal\r\n"
        "timeout /t 2 /nobreak >nul\r\n"
        f'copy /y "{new}" "{current}" >nul\r\n'
        "if errorlevel 1 (\r\n"
        '  echo Не удалось заменить приложение. Новый файл оставлен в TEMP.\r\n'
        "  pause\r\n"
        "  exit /b 1\r\n"
        ")\r\n"
        f'start "" "{current}"\r\n'
        f'del /f /q "{new}" >nul 2>nul\r\n'
        'del "%~f0" >nul 2>nul\r\n'
    )
    script.write_text(content, encoding="utf-8")
    subprocess.Popen(["cmd.exe", "/c", "start", "", str(script)], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

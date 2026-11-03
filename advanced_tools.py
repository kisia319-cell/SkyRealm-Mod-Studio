"""Advanced, local-only productivity tools for SkyRealm Mod Studio.

The visual designers write JSON data files. They do not claim runtime support:
SkyRealm must implement and document the corresponding data loaders first.
"""
import json
import logging
import os
import re
import subprocess
import shutil
import sys
import zipfile
from pathlib import Path
from core.smart_analysis import scan_javascript
from editors.data_designer import VisualDataDesigner

from PySide6.QtCore import Qt, QProcess, QProcessEnvironment
from PySide6.QtGui import QFont, QPixmap, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel, QPushButton,
    QPlainTextEdit, QComboBox, QLineEdit, QFormLayout, QMessageBox, QFileDialog,
    QListWidget, QListWidgetItem, QCheckBox, QSplitter
)

EXCLUDED_DIRS = {".git", "__pycache__", ".venv", "venv", ".backups", ".history",
                 "build", "dist", "node_modules", ".pytest_cache"}
ALLOWED_SOURCE = {".js", ".mjs", ".cjs", ".json", ".py"}
DATA_TYPES = {
    "Предмет": ("items", {"id": "my_mod:example_item", "name": "Новый предмет",
                           "description": "", "stackSize": 10, "rarity": "common"}),
    "Оружие": ("weapons", {"id": "my_mod:example_weapon", "name": "Новое оружие",
                            "damage": 25, "attackCooldown": 0.7, "rarity": "common"}),
    "Монстр": ("mobs", {"id": "my_mod:example_mob", "name": "Новый монстр",
                         "health": 100, "damage": 10, "speed": 2, "abilities": []}),
    "Квест": ("quests", {"id": "my_mod:example_quest", "title": "Новый квест",
                          "description": "", "objectives": [], "rewards": []}),
    "Анимация": ("animations", {"id": "my_mod:example_animation", "target": "player",
                                 "fps": 12, "loop": False, "frames": []}),
    "Биом": ("biomes", {"id": "my_mod:example_biome", "name": "Новый биом",
                         "temperature": 0.5, "terrain": "default", "spawns": []}),
}


class QtLogHandler(logging.Handler):
    def __init__(self, output):
        super().__init__()
        self.output = output

    def emit(self, record):
        try:
            self.output.appendPlainText(self.format(record))
        except RuntimeError:
            pass


class AdvancedToolsDialog(QDialog):
    def __init__(self, project_folder: Path, parent=None):
        super().__init__(parent)
        self.folder = Path(project_folder).resolve()
        self.setWindowTitle("Дополнительные инструменты — SkyRealm Mod Studio")
        self.resize(1000, 700)
        root = QVBoxLayout(self)
        intro = QLabel("Локальные инструменты проекта. Редакторы создают файлы данных; поддержку этих форматов должна реализовать сама игра.")
        intro.setWordWrap(True)
        root.addWidget(intro)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_analyzer(), "Умный анализатор")
        self.tabs.addTab(self._build_data_editor(), "Визуальные редакторы")
        self.tabs.addTab(self._build_assets(), "Галерея ресурсов")
        self.tabs.addTab(self._build_mod_manager(), "Менеджер модов")
        self.tabs.addTab(self._build_package(), "Сборщик")
        self.tabs.addTab(self._build_git(), "Git")
        self.tabs.addTab(self._build_logs(), "Живые логи")
        root.addWidget(self.tabs, 1)
        close = QPushButton("Закрыть")
        close.clicked.connect(self.accept)
        root.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self._refresh_mods()

    def _build_analyzer(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        row = QHBoxLayout()
        row.addWidget(QLabel("Статический анализ проекта"))
        row.addStretch()
        run = QPushButton("Проверить проект")
        run.clicked.connect(self._run_smart_analysis)
        row.addWidget(run)
        layout.addLayout(row)
        self.analysis_output = QPlainTextEdit()
        self.analysis_output.setReadOnly(True)
        self.analysis_output.setFont(QFont("Consolas", 10))
        layout.addWidget(self.analysis_output, 1)
        layout.addWidget(QLabel("Проверка не исполняет код и не заменяет тестирование в игре. Предупреждения требуют ручной проверки."))
        return page

    def _run_smart_analysis(self):
        findings = []
        checked = 0
        for root, dirs, files in os.walk(self.folder):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            for name in files:
                path = Path(root) / name
                if path.suffix.lower() not in ALLOWED_SOURCE:
                    continue
                try:
                    source = path.read_text(encoding="utf-8")
                except (OSError, UnicodeError) as exc:
                    findings.append(f"ERROR {path.relative_to(self.folder)}: невозможно прочитать: {exc}")
                    continue
                checked += 1
                rel = path.relative_to(self.folder)
                if path.suffix.lower() in {".js", ".mjs", ".cjs"}:
                    for number, message, level in scan_javascript(source):
                        findings.append(f"{level} {rel}:{number}: {message}")
                elif path.suffix.lower() == ".json":
                    try:
                        json.loads(source)
                    except json.JSONDecodeError as exc:
                        findings.append(f"ERROR {rel}:{exc.lineno}:{exc.colno}: {exc.msg}")
                elif path.suffix.lower() == ".py":
                    try:
                        import ast
                        ast.parse(source, filename=str(rel))
                    except SyntaxError as exc:
                        findings.append(f"ERROR {rel}:{exc.lineno}: синтаксическая ошибка Python: {exc.msg}")
        self.analysis_output.setPlainText(
            f"Проверено файлов: {checked}\nНайдено замечаний: {len(findings)}\n"
            "Это эвристический анализ, а не доказательство наличия или отсутствия ошибок.\n\n"
            + ("\n".join(findings) if findings else "Замечаний по выбранным правилам не найдено.")
        )
        logging.info("Smart analysis completed: %s files, %s findings", checked, len(findings))

    def _build_data_editor(self):
        return VisualDataDesigner(self.folder, self)

    def _build_assets(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Локальная библиотека ресурсов проекта. Изображения можно просматривать; аудио открывается внешним проигрывателем."))
        split = QSplitter()
        self.asset_list = QListWidget()
        self.asset_list.currentItemChanged.connect(self._preview_asset)
        split.addWidget(self.asset_list)
        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        self.asset_preview = QLabel("Выбери ресурс")
        self.asset_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.asset_preview.setMinimumSize(260, 220)
        self.asset_preview.setWordWrap(True)
        preview_layout.addWidget(self.asset_preview, 1)
        self.asset_details = QLabel("")
        self.asset_details.setWordWrap(True)
        preview_layout.addWidget(self.asset_details)
        split.addWidget(preview_panel)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)
        layout.addWidget(split, 1)
        row = QHBoxLayout()
        add = QPushButton("Импортировать ресурсы…")
        add.clicked.connect(self._import_assets)
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self._refresh_assets)
        open_file = QPushButton("Открыть ресурс")
        open_file.clicked.connect(self._open_selected_asset)
        row.addWidget(add)
        row.addWidget(refresh)
        row.addStretch()
        row.addWidget(open_file)
        layout.addLayout(row)
        self._refresh_assets()
        return page

    def _refresh_assets(self):
        if not hasattr(self, "asset_list"):
            return
        self.asset_list.clear()
        root = self.folder / "assets"
        if not root.is_dir():
            self.asset_preview.setText("Папка assets/ пока пуста")
            self.asset_details.clear()
            return
        for path in sorted(root.rglob("*"), key=lambda item: str(item).casefold()):
            if not path.is_file() or any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".wav", ".mp3", ".ogg", ".flac", ".ttf", ".otf"}:
                continue
            item = QListWidgetItem(f"{path.relative_to(root)}")
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}:
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    item.setIcon(QIcon(pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
            self.asset_list.addItem(item)

    def _preview_asset(self, item, _previous=None):
        if not item:
            return
        path = Path(item.data(Qt.ItemDataRole.UserRole))
        try:
            size = path.stat().st_size
            self.asset_details.setText(f"{path.name}\n{size:,} байт • {path.suffix.lower()}")
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}:
                pixmap = QPixmap(str(path))
                if pixmap.isNull():
                    self.asset_preview.setText("Не удалось прочитать изображение")
                else:
                    self.asset_preview.setPixmap(pixmap.scaled(520, 420, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                self.asset_preview.setPixmap(QPixmap())
                self.asset_preview.setText("Предпросмотр этого формата не поддерживается. Нажми «Открыть ресурс».")
        except OSError as exc:
            self.asset_preview.setText(str(exc))

    def _import_assets(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Импортировать ресурсы", str(Path.home()), "Ресурсы (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.wav *.mp3 *.ogg *.flac *.ttf *.otf)")
        if not files:
            return
        copied = 0
        errors = []
        for source_name in files:
            source = Path(source_name)
            kind = "sprites" if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"} else "audio" if source.suffix.lower() in {".wav", ".mp3", ".ogg", ".flac"} else "fonts"
            destination_dir = self.folder / "assets" / kind
            try:
                destination_dir.mkdir(parents=True, exist_ok=True)
                destination = destination_dir / source.name
                stem, suffix, index = source.stem, source.suffix, 1
                while destination.exists():
                    destination = destination_dir / f"{stem}_{index}{suffix}"
                    index += 1
                shutil.copy2(source, destination)
                copied += 1
            except OSError as exc:
                errors.append(f"{source.name}: {exc}")
        self._refresh_assets()
        report = f"Импортировано файлов: {copied}"
        if errors:
            report += "\n\nОшибки:\n" + "\n".join(errors)
        QMessageBox.information(self, "Импорт ресурсов", report)
        logging.info("Imported %s project assets", copied)

    def _open_selected_asset(self):
        item = self.asset_list.currentItem()
        if item:
            self._open_path(Path(item.data(Qt.ItemDataRole.UserRole)))

    def _build_mod_manager(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Локальный каталог подпроектов в папке mods/. Флажки сохраняются в .studio-mods.json и сами по себе не включают моды в игре."))
        self.mod_list = QListWidget()
        self.mod_list.itemChanged.connect(self._save_mod_states)
        layout.addWidget(self.mod_list, 1)
        row = QHBoxLayout()
        refresh = QPushButton("Обновить список")
        refresh.clicked.connect(self._refresh_mods)
        open_folder = QPushButton("Открыть папку проекта")
        open_folder.clicked.connect(lambda: self._open_path(self.folder / "mods"))
        row.addWidget(refresh)
        row.addWidget(open_folder)
        row.addStretch()
        layout.addLayout(row)
        return page

    def _refresh_mods(self):
        if not hasattr(self, "mod_list"):
            return
        self.mod_list.clear()
        root = self.folder / "mods"
        state_path = self.folder / ".studio-mods.json"
        try:
            state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
        except (OSError, json.JSONDecodeError):
            state = {}
        if not root.is_dir():
            self.mod_list.addItem("Папка mods/ пока отсутствует.")
            return
        for manifest in sorted(root.glob("*/mod.json")):
            try:
                meta = json.loads(manifest.read_text(encoding="utf-8"))
                mod_id = str(meta.get("id") or manifest.parent.name)
                item = QListWidgetItem(f"{meta.get('name', manifest.parent.name)}  —  {meta.get('version', '?')}  [{mod_id}]")
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if state.get(mod_id, True) else Qt.CheckState.Unchecked)
                item.setData(Qt.ItemDataRole.UserRole, mod_id)
                self.mod_list.addItem(item)
            except (OSError, json.JSONDecodeError):
                self.mod_list.addItem(f"Повреждён manifest: {manifest}")

    def _save_mod_states(self, _item=None):
        state = {}
        for i in range(self.mod_list.count()):
            item = self.mod_list.item(i)
            mod_id = item.data(Qt.ItemDataRole.UserRole)
            if mod_id:
                state[mod_id] = item.checkState() == Qt.CheckState.Checked
        try:
            (self.folder / ".studio-mods.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            logging.error("Cannot save local mod states: %s", exc)

    def _build_package(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Сборщик проверяет manifest и упаковывает исходники без кэша, истории и резервных копий. ZIP не является подписанным установщиком."))
        self.package_report = QPlainTextEdit()
        self.package_report.setReadOnly(True)
        layout.addWidget(self.package_report, 1)
        row = QHBoxLayout()
        check = QPushButton("Проверить перед сборкой")
        check.clicked.connect(self._validate_package)
        build = QPushButton("Собрать ZIP-мод")
        build.clicked.connect(self._build_zip)
        row.addWidget(check)
        row.addStretch()
        row.addWidget(build)
        layout.addLayout(row)
        return page

    def _validate_package(self):
        errors = []
        manifest = self.folder / "mod.json"
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                errors.append("mod.json должен содержать объект.")
            else:
                for key in ("id", "name", "version", "entry"):
                    if not data.get(key):
                        errors.append(f"В mod.json отсутствует {key}.")
                if data.get("entry"):
                    entry = (self.folder / data["entry"]).resolve()
                    if self.folder not in entry.parents:
                        errors.append("entry выходит за пределы папки проекта.")
                    elif not entry.is_file():
                        errors.append(f"Главный файл не найден: {data['entry']}")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Не удалось прочитать mod.json: {exc}")
        self.package_report.setPlainText("Проверка упаковки:\n" + ("\n".join(errors) if errors else "Базовые проверки пройдены. Совместимость с игрой не подтверждена."))
        return not errors

    def _build_zip(self):
        if not self._validate_package():
            QMessageBox.warning(self, "Проверка не пройдена", "Исправь ошибки перед сборкой.")
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Собрать мод", str(self.folder.parent / (self.folder.name + ".zip")), "ZIP (*.zip)")
        if not destination:
            return
        target = Path(destination).resolve()
        try:
            count = 0
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
                for root, dirs, files in os.walk(self.folder):
                    dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                    for name in files:
                        path = Path(root) / name
                        if path.resolve() == target or name == ".studio-mods.json":
                            continue
                        archive.write(path, path.relative_to(self.folder))
                        count += 1
            self.package_report.appendPlainText(f"\nСоздан архив: {target}\nФайлов: {count}")
            QMessageBox.information(self, "Сборка завершена", f"ZIP создан:\n{target}\n\nЭто архив исходников. Проверь его в игре перед публикацией.")
            logging.info("Packaged project into %s (%s files)", target, count)
        except (OSError, zipfile.BadZipFile) as exc:
            QMessageBox.critical(self, "Ошибка сборки", str(exc))

    def _build_git(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Только просмотр статуса и последних коммитов. Изменения в репозитории выполняй осознанно через Git-клиент."))
        self.git_output = QPlainTextEdit()
        self.git_output.setReadOnly(True)
        self.git_output.setFont(QFont("Consolas", 10))
        layout.addWidget(self.git_output, 1)
        row = QHBoxLayout()
        status = QPushButton("Git status")
        status.clicked.connect(lambda: self._run_git(["status", "--short", "--branch"]))
        history = QPushButton("Последние коммиты")
        history.clicked.connect(lambda: self._run_git(["log", "-5", "--oneline"]))
        row.addWidget(status)
        row.addWidget(history)
        row.addStretch()
        layout.addLayout(row)
        self.git_process = QProcess(self)
        self.git_process.setWorkingDirectory(str(self.folder))
        self.git_process.finished.connect(self._git_finished)
        self.git_process.errorOccurred.connect(lambda _err: self.git_output.appendPlainText("Git не найден или не удалось запустить процесс."))
        return page

    def _run_git(self, args):
        if self.git_process.state() != QProcess.ProcessState.NotRunning:
            return
        self.git_output.appendPlainText("$ git " + " ".join(args))
        self.git_process.start("git", args)

    def _git_finished(self, _code, _status):
        output = bytes(self.git_process.readAllStandardOutput()).decode("utf-8", "replace")
        error = bytes(self.git_process.readAllStandardError()).decode("utf-8", "replace")
        self.git_output.appendPlainText(output or error or "(нет вывода)")

    def _build_logs(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Живой журнал событий инструментов Studio. Игровые логи появятся здесь только после отдельного подключения runtime."))
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(2000)
        self.log_output.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_output, 1)
        self.log_handler = QtLogHandler(self.log_output)
        self.log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%H:%M:%S"))
        logging.getLogger().addHandler(self.log_handler)
        clear = QPushButton("Очистить")
        clear.clicked.connect(self.log_output.clear)
        layout.addWidget(clear, alignment=Qt.AlignmentFlag.AlignRight)
        return page

    def _open_path(self, path):
        try:
            if os.name == "nt":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            QMessageBox.warning(self, "Не удалось открыть папку", str(exc))

    def closeEvent(self, event):
        handler = getattr(self, "log_handler", None)
        if handler:
            logging.getLogger().removeHandler(handler)
            handler.close()
        super().closeEvent(event)

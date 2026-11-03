"""Advanced, local-only productivity tools for SkyRealm Mod Studio.

The visual designers write JSON data files. They do not claim runtime support:
SkyRealm must implement and document the corresponding data loaders first.
"""
import json
import logging
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from core.smart_analysis import scan_javascript

from PySide6.QtCore import Qt, QProcess, QProcessEnvironment
from PySide6.QtGui import QFont
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
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.data_type = QComboBox()
        self.data_type.addItems(DATA_TYPES.keys())
        self.data_filename = QLineEdit()
        self.data_filename.setPlaceholderText("например, frost_sword.json")
        form.addRow("Тип данных:", self.data_type)
        form.addRow("Имя файла:", self.data_filename)
        layout.addLayout(form)
        layout.addWidget(QLabel("Редактируй JSON-описание. Это формат проекта Studio, не подтверждённый формат игрового runtime."))
        self.data_editor = QPlainTextEdit()
        self.data_editor.setFont(QFont("Consolas", 10))
        layout.addWidget(self.data_editor, 1)
        self.data_type.currentTextChanged.connect(self._load_data_template)
        self._load_data_template(self.data_type.currentText())
        row = QHBoxLayout()
        validate = QPushButton("Проверить JSON")
        validate.clicked.connect(self._validate_data)
        save = QPushButton("Сохранить файл данных")
        save.clicked.connect(self._save_data_file)
        row.addWidget(validate)
        row.addStretch()
        row.addWidget(save)
        layout.addLayout(row)
        return page

    def _load_data_template(self, kind):
        _, template = DATA_TYPES[kind]
        self.data_editor.setPlainText(json.dumps(template, ensure_ascii=False, indent=4))
        self.data_filename.clear()

    def _validate_data(self):
        try:
            data = json.loads(self.data_editor.toPlainText())
            if not isinstance(data, dict):
                raise ValueError("В корне JSON должен находиться объект.")
            if not data.get("id"):
                raise ValueError("Добавь обязательное поле id.")
            if not data.get("name") and not data.get("title"):
                raise ValueError("Добавь поле name или title.")
            QMessageBox.information(self, "Проверка", "JSON корректен, обязательные поля присутствуют.")
        except (json.JSONDecodeError, ValueError) as exc:
            QMessageBox.warning(self, "Ошибка данных", str(exc))

    def _save_data_file(self):
        try:
            data = json.loads(self.data_editor.toPlainText())
            if not isinstance(data, dict) or not data.get("id"):
                raise ValueError("Ожидается JSON-объект с полем id.")
            if not (data.get("name") or data.get("title")):
                raise ValueError("Добавь поле name или title.")
            default_dir, _ = DATA_TYPES[self.data_type.currentText()]
            safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(data["id"]).split(":")[-1]).strip("._") or "new_data"
            filename = self.data_filename.text().strip() or (safe_id + ".json")
            if Path(filename).name != filename or not filename.lower().endswith(".json"):
                raise ValueError("Имя должно быть простым именем файла с расширением .json.")
            target = self.folder / "data" / default_dir / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                answer = QMessageBox.question(self, "Перезаписать файл?", f"{target.relative_to(self.folder)} уже существует. Перезаписать?")
                if answer != QMessageBox.StandardButton.Yes:
                    return
            target.write_text(json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
            QMessageBox.information(self, "Сохранено", f"Создан файл:\n{target.relative_to(self.folder)}\n\nИгра должна отдельно поддерживать этот формат.")
            logging.info("Created data file %s", target)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Не удалось сохранить", str(exc))

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

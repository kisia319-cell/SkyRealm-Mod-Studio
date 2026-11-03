import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QKeySequence, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMessageBox, QFrame, QDialog, QLineEdit, QFileDialog,
    QFormLayout, QComboBox, QSplitter, QTreeWidget, QTreeWidgetItem,
    QListWidget, QTabWidget, QPlainTextEdit, QInputDialog
)

from core.code_analysis import analyze_file
from editors.code_editor import CodeEditor

APP_VERSION = "1.1.0"
REPOSITORY = "kisia319-cell/SkyRealm-Mod-Studio"
LANGUAGE_EXTENSIONS = {"JavaScript": ".js", "JSON": ".json", "Python": ".py"}
EXTENSION_LANGUAGES = {".js": "JavaScript", ".mjs": "JavaScript", ".json": "JSON", ".py": "Python"}
STYLE = """
QMainWindow,QWidget{background:#0b1020;color:#edf2ff}
QLabel{color:#dce5f7}
QLineEdit,QComboBox,QPlainTextEdit{background:#0a1222;border:1px solid #2b3b59;border-radius:6px;padding:7px;color:#eaf0ff}
QPushButton{background:#1a2740;color:#dce5f7;border:1px solid #344563;border-radius:7px;padding:8px 13px;font-weight:600}
QPushButton:hover{background:#263653}
QPushButton#primary,QPushButton#save{background:#35c987;color:#07150f;border:0}
QPushButton#primary:hover,QPushButton#save:hover{background:#54dda0}
QTreeWidget,QListWidget{background:#101a30;border:1px solid #263552;border-radius:7px}
QTreeWidget::item,QListWidget::item{padding:5px}
QTreeWidget::item:selected,QListWidget::item:selected{background:#1b3b36;color:#67e4a7}
QTabWidget::pane{border:1px solid #263552}
QTabBar::tab{background:#111a30;padding:9px 15px}
QTabBar::tab:selected{background:#1b2b43;color:#5de0a0}
QLabel#muted{color:#8797b6}
QLabel#brand{font-size:30px;font-weight:800;color:#f4f7ff}
QFrame#panel{background:#111a30;border:1px solid #263552;border-radius:14px}
"""

def project_metadata(folder: Path):
    path = folder / "mod.json"
    if not path.is_file():
        raise ValueError("В выбранной папке нет mod.json. Выбери папку проекта SkyRealm Mod Studio.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("name"):
        raise ValueError("Файл mod.json повреждён или в нём отсутствует название проекта.")
    return data


class CreateProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать проект")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText("Например, Magic Mod")
        self.language = QComboBox()
        self.language.addItems(list(LANGUAGE_EXTENSIONS))
        self.folder = QLineEdit(str(Path.home() / "Documents" / "SkyRealmMods"))
        self.folder.setReadOnly(True)
        browse = QPushButton("Выбрать…")
        browse.clicked.connect(self.pick_folder)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder, 1)
        folder_row.addWidget(browse)
        form.addRow("Название:", self.name)
        form.addRow("Язык проекта:", self.language)
        form.addRow("Папка:", folder_row)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        cancel = QPushButton("Отмена")
        create = QPushButton("Создать")
        create.setObjectName("primary")
        cancel.clicked.connect(self.reject)
        create.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(create)
        layout.addLayout(buttons)

    def pick_folder(self):
        selected = QFileDialog.getExistingDirectory(self, "Папка для проекта", self.folder.text())
        if selected:
            self.folder.setText(selected)

    def values(self):
        return self.name.text().strip(), self.language.currentText(), Path(self.folder.text())


class ProjectWindow(QMainWindow):
    def __init__(self, folder: Path, home):
        super().__init__()
        self.folder = folder.resolve()
        self.home = home
        self.metadata = project_metadata(self.folder)
        self.current_file = None
        self.dirty = False
        self.setWindowTitle(f"SkyRealm Mod Studio — {self.metadata['name']}")
        self.resize(1250, 800)
        self.setMinimumSize(950, 620)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 10)
        header = QHBoxLayout()
        title = QLabel(f"SKYREALM MOD STUDIO  /  {self.metadata['name']}")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        header.addWidget(title, 1)
        self.status = QLabel("Готово")
        self.status.setObjectName("muted")
        header.addWidget(self.status)
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("save")
        save_btn.clicked.connect(self.save_file)
        header.addWidget(save_btn)
        format_btn = QPushButton("Форматировать")
        format_btn.clicked.connect(self.format_current_file)
        header.addWidget(format_btn)
        export_btn = QPushButton("Экспорт ZIP")
        export_btn.clicked.connect(self.export_project)
        header.addWidget(export_btn)
        metadata_btn = QPushButton("Настройки мода")
        metadata_btn.clicked.connect(self.edit_metadata)
        header.addWidget(metadata_btn)
        root.addLayout(header)

        split = QSplitter()
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.addWidget(QLabel("ФАЙЛЫ ПРОЕКТА"))
        file_actions = QHBoxLayout()
        add_file = QPushButton("+ Файл")
        add_file.clicked.connect(self.create_file)
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh_tree)
        rename_file = QPushButton("Переименовать")
        rename_file.clicked.connect(self.rename_selected_file)
        delete_file = QPushButton("Удалить")
        delete_file.clicked.connect(self.delete_selected_file)
        file_actions.addWidget(add_file)
        file_actions.addWidget(rename_file)
        file_actions.addWidget(delete_file)
        file_actions.addWidget(refresh)
        left_layout.addLayout(file_actions)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self.open_tree_item)
        left_layout.addWidget(self.tree, 1)
        split.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(6, 0, 0, 0)
        self.file_title = QLabel("Выбери файл слева")
        self.file_title.setObjectName("muted")
        right_layout.addWidget(self.file_title)
        self.editor = CodeEditor("JavaScript")
        self.editor.setReadOnly(True)
        right_layout.addWidget(self.editor, 1)
        self.diagnostics = QListWidget()
        self.diagnostics.setMaximumHeight(145)
        self.diagnostics.itemClicked.connect(self.go_to_diagnostic)
        right_layout.addWidget(QLabel("ПРОВЕРКА КОДА"))
        right_layout.addWidget(self.diagnostics)
        split.addWidget(right)
        split.setSizes([280, 900])
        root.addWidget(split, 1)

        footer = QHBoxLayout()
        back = QPushButton("← К проектам")
        back.clicked.connect(self.return_home)
        check = QPushButton("Проверить проект")
        check.clicked.connect(self.check_project)
        footer.addWidget(back)
        footer.addWidget(check)
        footer.addStretch()
        self.project_path_label = QLabel(str(self.folder))
        self.project_path_label.setObjectName("muted")
        footer.addWidget(self.project_path_label)
        root.addLayout(footer)
        self.setCentralWidget(central)

        self.autosave = QTimer(self)
        self.autosave.setSingleShot(True)
        self.autosave.setInterval(650)
        self.autosave.timeout.connect(self.save_file)
        self.lint_timer = QTimer(self)
        self.lint_timer.setSingleShot(True)
        self.lint_timer.setInterval(500)
        self.lint_timer.timeout.connect(self.check_current_file)
        self.editor.textChanged.connect(self.on_text_changed)
        self.refresh_tree()

        save_action = QAction(self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        self.addAction(save_action)

    def refresh_tree(self):
        self.tree.clear()
        root_item = QTreeWidgetItem([self.folder.name])
        root_item.setData(0, Qt.ItemDataRole.UserRole, str(self.folder))
        self.tree.addTopLevelItem(root_item)
        for path in sorted(self.folder.rglob("*")):
            if any(part in {".git", "__pycache__", ".venv", "venv"} for part in path.parts):
                continue
            if path.is_file() and path.suffix.lower() in {".js", ".mjs", ".json", ".py", ".md", ".txt"}:
                relative = path.relative_to(self.folder)
                parent = root_item
                for part in relative.parts[:-1]:
                    found = None
                    for i in range(parent.childCount()):
                        if parent.child(i).text(0) == part:
                            found = parent.child(i)
                            break
                    if found is None:
                        found = QTreeWidgetItem([part])
                        parent.addChild(found)
                    parent = found
                item = QTreeWidgetItem([relative.name])
                item.setData(0, Qt.ItemDataRole.UserRole, str(path))
                parent.addChild(item)
        root_item.setExpanded(True)

    def open_tree_item(self, item, _column=0):
        value = item.data(0, Qt.ItemDataRole.UserRole)
        if not value:
            return
        path = Path(value)
        if not path.is_file():
            return
        if self.dirty and not self.confirm_discard_or_save():
            return
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            QMessageBox.warning(self, "Не удалось открыть файл", str(exc))
            return
        language = EXTENSION_LANGUAGES.get(path.suffix.lower())
        if not language:
            QMessageBox.information(self, "Файл только для чтения", "Этот тип файла пока нельзя редактировать.")
            return
        self.current_file = path
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)
        self.editor.setReadOnly(False)
        self.editor.set_language(language)
        self.editor.highlighter.rehighlight()
        self.file_title.setText(f"{path.relative_to(self.folder)}  •  {language}")
        self.dirty = False
        self.status.setText("Открыто")
        self.check_current_file()

    def on_text_changed(self):
        self.dirty = True
        self.status.setText("Есть изменения — автосохранение…")
        self.autosave.start()
        self.lint_timer.start()

    def save_file(self):
        self.autosave.stop()
        if self.current_file is None:
            return
        try:
            self.current_file.write_text(self.editor.toPlainText(), encoding="utf-8")
            self.dirty = False
            self.status.setText("Сохранено")
        except OSError as exc:
            self.status.setText("Ошибка сохранения")
            QMessageBox.critical(self, "Ошибка сохранения", str(exc))

    def check_current_file(self):
        self.diagnostics.clear()
        if self.current_file is None:
            return
        issues = analyze_file(self.current_file, self.editor.toPlainText())
        if not issues:
            self.diagnostics.addItem("✓ Ошибок синтаксиса не обнаружено")
            return
        for line, col, title, message in issues:
            self.diagnostics.addItem(f"Строка {line}, столбец {col}: {title} — {message}")
        self.status.setText(f"Найдено проблем: {len(issues)}")

    def go_to_diagnostic(self, item):
        match = re.search(r"Строка (\d+), столбец (\d+)", item.text())
        if not match:
            return
        line, col = map(int, match.groups())
        block = self.editor.document().findBlockByNumber(max(0, line - 1))
        cursor = self.editor.textCursor()
        cursor.setPosition(block.position() + max(0, col - 1))
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def edit_metadata(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Настройки проекта")
        dialog.setMinimumWidth(520)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        name_field = QLineEdit(str(self.metadata.get("name", "")))
        version_field = QLineEdit(str(self.metadata.get("version", "1.0.0")))
        author_field = QLineEdit(str(self.metadata.get("author", "")))
        description_field = QPlainTextEdit(str(self.metadata.get("description", "")))
        description_field.setMaximumHeight(130)
        form.addRow("Название:", name_field)
        form.addRow("Версия:", version_field)
        form.addRow("Автор:", author_field)
        form.addRow("Описание:", description_field)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        cancel = QPushButton("Отмена")
        save = QPushButton("Сохранить")
        save.setObjectName("primary")
        cancel.clicked.connect(dialog.reject)
        save.clicked.connect(dialog.accept)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if not name_field.text().strip():
            QMessageBox.warning(self, "Название", "Название проекта не может быть пустым.")
            return
        self.metadata.update({
            "name": name_field.text().strip(),
            "version": version_field.text().strip() or "1.0.0",
            "author": author_field.text().strip(),
            "description": description_field.toPlainText().strip(),
        })
        try:
            (self.folder / "mod.json").write_text(
                json.dumps(self.metadata, ensure_ascii=False, indent=4), encoding="utf-8")
            self.setWindowTitle(f"SkyRealm Mod Studio — {self.metadata['name']}")
            self.status.setText("Настройки проекта сохранены")
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка сохранения", str(exc))

    def format_current_file(self):
        if self.current_file is None:
            return
        source = self.editor.toPlainText()
        try:
            if self.current_file.suffix.lower() == ".json":
                formatted = json.dumps(json.loads(source), ensure_ascii=False, indent=4)
            else:
                formatted = "\n".join(line.rstrip().replace("\t", "    ") for line in source.splitlines())
            if formatted != source:
                self.editor.setPlainText(formatted)
                self.status.setText("Форматирование применено")
        except json.JSONDecodeError as exc:
            QMessageBox.warning(self, "Нельзя форматировать JSON", f"Строка {exc.lineno}: {exc.msg}")

    def export_project(self):
        self.save_file()
        suggested = str(self.folder.parent / (self.folder.name + ".zip"))
        destination, _ = QFileDialog.getSaveFileName(self, "Экспорт проекта", suggested, "ZIP архив (*.zip)")
        if not destination:
            return
        try:
            destination_path = Path(destination).resolve()
            with zipfile.ZipFile(destination_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in self.folder.rglob("*"):
                    if (path.is_file() and path.resolve() != destination_path
                            and not any(part in {".git", "__pycache__", ".venv", "venv"} for part in path.parts)):
                        archive.write(path, path.relative_to(self.folder))
            QMessageBox.information(self, "Экспорт завершён",
                f"ZIP-архив исходников создан:\n{destination}\n\nЭто архив проекта, а не гарантированно совместимый установщик игры.")
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка экспорта", str(exc))

    def check_project(self):
        self.save_file()
        problems = []
        try:
            data = project_metadata(self.folder)
            entry = (self.folder / data.get("entry", "")).resolve()
            if self.folder not in entry.parents:
                problems.append("Путь главного файла выходит за пределы папки проекта.")
            elif not entry.is_file():
                problems.append(f"Не найден главный файл: {data.get('entry', '(не указан)')}")
            if not data.get("id"):
                problems.append("В mod.json отсутствует id мода.")
            for code_path in self.folder.rglob("*"):
                if not code_path.is_file() or any(part in {".git", "__pycache__", ".venv", "venv"} for part in code_path.parts):
                    continue
                if code_path.suffix.lower() in EXTENSION_LANGUAGES:
                    try:
                        source = code_path.read_text(encoding="utf-8")
                        problems.extend(f"{code_path.relative_to(self.folder)}:{line}:{col}: {title}: {msg}"
                                        for line, col, title, msg in analyze_file(code_path, source))
                    except (OSError, UnicodeError) as exc:
                        problems.append(f"{code_path.name}: {exc}")
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            problems.append(str(exc))
        if problems:
            QMessageBox.warning(self, "Проверка проекта", "Найдены проблемы:\n\n" + "\n".join(problems))
        else:
            QMessageBox.information(self, "Проверка проекта", "Все исходные файлы проекта прошли синтаксическую проверку.")

    def selected_file_path(self):
        item = self.tree.currentItem()
        value = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        return Path(value) if value else None

    def rename_selected_file(self):
        path = self.selected_file_path()
        if not path or not path.is_file():
            QMessageBox.information(self, "Выбери файл", "Сначала выбери файл в дереве проекта.")
            return
        name, ok = QInputDialog.getText(self, "Переименовать файл", "Новое имя:", text=path.name)
        if not ok or not name.strip():
            return
        name = name.strip()
        if Path(name).name != name or Path(name).suffix.lower() not in EXTENSION_LANGUAGES:
            QMessageBox.warning(self, "Недопустимое имя", "Разрешены только расширения .js, .json и .py.")
            return
        target = path.with_name(name)
        if target.exists():
            QMessageBox.warning(self, "Файл существует", "Файл с таким именем уже существует.")
            return
        if self.current_file == path and self.dirty and not self.confirm_discard_or_save():
            return
        try:
            path.rename(target)
            if self.current_file == path:
                self.current_file = target
                self.file_title.setText(f"{target.relative_to(self.folder)} • {EXTENSION_LANGUAGES[target.suffix.lower()]}")
                self.editor.set_language(EXTENSION_LANGUAGES[target.suffix.lower()])
            self.refresh_tree()
        except OSError as exc:
            QMessageBox.warning(self, "Не удалось переименовать", str(exc))

    def delete_selected_file(self):
        path = self.selected_file_path()
        if not path or not path.is_file():
            QMessageBox.information(self, "Выбери файл", "Сначала выбери файл в дереве проекта.")
            return
        answer = QMessageBox.question(self, "Удалить файл", f"Удалить {path.name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self.current_file == path and self.dirty and not self.confirm_discard_or_save():
            return
        try:
            path.unlink()
            if self.current_file == path:
                self.current_file = None
                self.editor.clear()
                self.editor.setReadOnly(True)
                self.file_title.setText("Выбери файл слева")
                self.dirty = False
            self.refresh_tree()
        except OSError as exc:
            QMessageBox.warning(self, "Не удалось удалить", str(exc))

    def create_file(self):
        name, ok = QInputDialog.getText(self, "Новый файл", "Имя файла (.js, .json или .py):")
        if not ok or not name.strip():
            return
        name = name.strip()
        if Path(name).name != name or Path(name).suffix.lower() not in EXTENSION_LANGUAGES:
            QMessageBox.warning(self, "Недопустимое имя", "Используй имя файла с расширением .js, .json или .py.")
            return
        path = self.folder / name
        if path.exists():
            QMessageBox.warning(self, "Файл существует", "Файл с таким именем уже существует.")
            return
        try:
            path.write_text("", encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка создания файла", str(exc))
            return
        self.refresh_tree()
        items = self.tree.findItems(name, Qt.MatchFlag.MatchRecursive | Qt.MatchFlag.MatchExactly, 0)
        if items:
            self.open_tree_item(items[0])

    def confirm_discard_or_save(self):
        answer = QMessageBox.question(
            self, "Несохранённые изменения", "Сохранить изменения перед переключением?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            self.save_file()
            return not self.dirty
        self.autosave.stop()
        self.dirty = False
        return True

    def return_home(self):
        if self.dirty and not self.confirm_discard_or_save():
            return
        self.home.show()
        self.close()

    def closeEvent(self, event):
        if self.dirty and not self.confirm_discard_or_save():
            event.ignore()
            return
        self.home.show()
        event.accept()


class StudioWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SkyRealm Mod Studio")
        self.resize(900, 620)
        self.setMinimumSize(760, 520)
        self.setStyleSheet(STYLE)
        self.settings_path = Path.home() / ".skyrealm_mod_studio.json"
        self.settings = self.load_settings()
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(48, 34, 48, 28)
        eyebrow = QLabel("SKYREALM • CREATOR TOOLS")
        eyebrow.setObjectName("muted")
        brand = QLabel("MOD STUDIO")
        brand.setObjectName("brand")
        subtitle = QLabel("Создавай, редактируй и проверяй модификации SkyRealm")
        subtitle.setObjectName("muted")
        layout.addWidget(eyebrow)
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addStretch()
        panel = QFrame()
        panel.setObjectName("panel")
        box = QVBoxLayout(panel)
        box.setContentsMargins(36, 32, 36, 32)
        box.setSpacing(14)
        welcome = QLabel("Добро пожаловать в SkyRealm Mod Studio")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        box.addWidget(welcome)
        create = QPushButton("＋  Создать проект")
        create.setObjectName("primary")
        create.clicked.connect(self.create_project)
        open_btn = QPushButton("Открыть / выбрать проект")
        open_btn.clicked.connect(self.open_project)
        box.addWidget(create)
        box.addWidget(open_btn)
        box.addWidget(QLabel("Недавние проекты"))
        self.recent = QListWidget()
        self.recent.itemDoubleClicked.connect(lambda item: self.open_project_path(Path(item.data(Qt.ItemDataRole.UserRole))))
        box.addWidget(self.recent)
        layout.addWidget(panel, 2)
        bottom = QHBoxLayout()
        self.update_status = QLabel(f"Версия {APP_VERSION} • Проверка обновлений…")
        self.update_status.setObjectName("muted")
        bottom.addWidget(self.update_status, 1)
        update_btn = QPushButton("Проверить обновления")
        update_btn.clicked.connect(self.check_updates)
        bottom.addWidget(update_btn)
        exit_btn = QPushButton("Выход")
        exit_btn.clicked.connect(self.close)
        bottom.addWidget(exit_btn)
        layout.addLayout(bottom)
        self.setCentralWidget(root)
        self.project_window = None
        self.refresh_recent()
        QTimer.singleShot(900, self.check_updates)

    def load_settings(self):
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {"recent_projects": []}

    def save_settings(self):
        try:
            self.settings_path.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def refresh_recent(self):
        self.recent.clear()
        for value in self.settings.get("recent_projects", []):
            path = Path(value)
            if path.is_dir() and (path / "mod.json").is_file():
                from PySide6.QtWidgets import QListWidgetItem
                item = QListWidgetItem(f"{path.name}  —  {path}")
                item.setData(Qt.ItemDataRole.UserRole, str(path))
                self.recent.addItem(item)

    def remember_project(self, folder):
        items = [str(folder)] + [p for p in self.settings.get("recent_projects", []) if p != str(folder)]
        self.settings["recent_projects"] = items[:12]
        self.save_settings()
        self.refresh_recent()

    def create_project(self):
        dialog = CreateProjectDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, language, parent = dialog.values()
        if not name:
            QMessageBox.warning(self, "Название", "Введи название проекта.")
            return
        safe = re.sub(r'[<>:"/\\|?*]', "_", name).strip(" .")
        if not safe:
            QMessageBox.warning(self, "Название", "Выбери другое название.")
            return
        folder = parent / safe
        if folder.exists():
            QMessageBox.warning(self, "Папка существует", "Выбери другое имя или место.")
            return
        entry = "scripts/main" + LANGUAGE_EXTENSIONS[language]
        try:
            (folder / "scripts").mkdir(parents=True)
            metadata = {"name": name, "id": re.sub(r"[^a-z0-9]+", "-", safe.lower()).strip("-") or "my-mod",
                        "version": "1.0.0", "game": "SkyRealm", "entry": entry,
                        "language": language, "author": "", "description": ""}
            (folder / "mod.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=4), encoding="utf-8")
            (folder / entry).write_text("", encoding="utf-8")
            (folder / "README.md").write_text(f"# {name}\n\nМодификация для SkyRealm.\n", encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка создания", str(exc))
            return
        self.open_project_path(folder)

    def open_project(self):
        selected = QFileDialog.getExistingDirectory(self, "Выбери папку проекта", str(Path.home() / "Documents"))
        if selected:
            self.open_project_path(Path(selected))

    def open_project_path(self, folder):
        try:
            project_metadata(folder)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Не удалось открыть проект", str(exc))
            return
        self.remember_project(folder.resolve())
        self.hide()
        self.project_window = ProjectWindow(folder, self)
        self.project_window.show()

    def check_updates(self):
        if getattr(self, "_update_thread", None) and self._update_thread.isRunning():
            return
        from updater import UpdateWorker
        self.update_status.setText("Проверяю обновления…")
        self._update_thread = UpdateWorker(APP_VERSION, self)
        self._update_thread.finished_check.connect(self.on_update_check)
        self._update_thread.start()

    def on_update_check(self, info, error):
        if error:
            self.update_status.setText("Не удалось проверить обновления")
            return
        if not info:
            self.update_status.setText(f"Версия {APP_VERSION} • обновлений пока нет")
            return
        self.update_status.setText(f"Доступна версия {info['version']}")
        answer = QMessageBox.question(self, "Доступно обновление",
            f"Найдена версия {info['version']}. Скачать и установить обновление?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        if answer == QMessageBox.StandardButton.Yes:
            self.download_update(info)

    def download_update(self, info):
        from updater import DownloadWorker
        self.update_status.setText("Скачиваю обновление…")
        self._download_thread = DownloadWorker(info["url"], self)
        self._download_thread.finished_download.connect(self.on_update_downloaded)
        self._download_thread.start()

    def on_update_downloaded(self, path, error):
        if error:
            self.update_status.setText("Ошибка загрузки обновления")
            QMessageBox.warning(self, "Обновление не установлено", error)
            return
        if not getattr(sys, "frozen", False):
            QMessageBox.information(self, "Обновление скачано", f"Новый EXE сохранён:\n{path}\nЗапусти его вручную.")
            self.update_status.setText("Обновление скачано")
            return
        from updater import launch_installer
        launch_installer(Path(sys.executable), Path(path))
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("SkyRealm Mod Studio")
    app.setOrganizationName("SkyRealm")
    app.setStyle("Fusion")
    window = StudioWindow()
    window.show()
    sys.exit(app.exec())

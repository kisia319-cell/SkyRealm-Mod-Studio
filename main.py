import json
import os
import re
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QFrame, QDialog, QLineEdit,
    QFileDialog, QFormLayout, QTabWidget, QPlainTextEdit, QListWidget,
    QListWidgetItem, QSplitter, QTextEdit
)


STYLE = """
QMainWindow, QWidget { background: #0b1020; color: #edf2ff; }
QLabel { color: #dce5f7; }
QLineEdit, QPlainTextEdit, QTextEdit {
    background: #0a1222; border: 1px solid #2b3b59; border-radius: 7px;
    padding: 9px; color: #eaf0ff; selection-background-color: #237b5b;
}
QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid #35c987; }
QPushButton { border-radius: 8px; padding: 10px 18px; font-weight: 650; }
QPushButton#primary, QPushButton#save {
    background: #35c987; color: #07150f; border: 0;
}
QPushButton#primary:hover, QPushButton#save:hover { background: #54dda0; }
QPushButton#secondary { background: #1a2740; color: #dce5f7; border: 1px solid #344563; }
QPushButton#secondary:hover { background: #263653; }
QTabWidget::pane { border: 1px solid #263552; border-radius: 10px; top: -1px; }
QTabBar::tab { background: #111a30; color: #91a0bd; padding: 12px 22px;
    border-top-left-radius: 7px; border-top-right-radius: 7px; margin-right: 4px; }
QTabBar::tab:selected { background: #1b2b43; color: #5de0a0; }
QListWidget { background: #101a30; border: 1px solid #263552; border-radius: 8px; padding: 5px; }
QListWidget::item { padding: 11px; border-radius: 5px; color: #b8c5dd; }
QListWidget::item:selected { background: #1b3b36; color: #67e4a7; }
QLabel#muted { color: #8797b6; }
QLabel#brand { color: #f4f7ff; font-size: 34px; font-weight: 800; letter-spacing: 1px; }
QLabel#eyebrow { color: #66e3a4; font-size: 11px; font-weight: 700; letter-spacing: 3px; }
QFrame#panel { background: #111a30; border: 1px solid #263552; border-radius: 22px; }
QLabel#status { color: #68dfa5; padding: 5px; }
"""


STARTER_CODE = ""


class CreateModDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать мод")
        self.setMinimumWidth(540)
        self.setModal(True)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(16)

        title = QLabel("Новая модификация")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        subtitle = QLabel("Создадим папку проекта и откроем редактор.")
        subtitle.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(12)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например: My First Mod")
        self.folder_input = QLineEdit(str(Path.home() / "Documents" / "SkyRealmMods"))
        self.folder_input.setReadOnly(True)
        folder_row = QHBoxLayout()
        browse = QPushButton("Обзор…")
        browse.setObjectName("secondary")
        browse.clicked.connect(self.choose_folder)
        folder_row.addWidget(self.folder_input, 1)
        folder_row.addWidget(browse)
        form.addRow("Название мода:", self.name_input)
        form.addRow("Папка сохранения:", folder_row)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Отмена")
        cancel.setObjectName("secondary")
        cancel.clicked.connect(self.reject)
        create = QPushButton("Создать и открыть")
        create.setObjectName("primary")
        create.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(create)
        layout.addLayout(buttons)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Папка для модов", self.folder_input.text())
        if folder:
            self.folder_input.setText(folder)

    def values(self):
        return self.name_input.text().strip(), self.folder_input.text().strip()



class CodeEditorWindow(QMainWindow):
    def __init__(self, script_path: Path, parent=None):
        super().__init__(parent)
        self.script_path = script_path
        self.setWindowTitle(f"Редактор кода — {script_path.parent.parent.name}")
        self.resize(1050, 720)
        self.setMinimumSize(760, 500)
        self.setStyleSheet(STYLE)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("РЕДАКТОР КОДА")
        title.setObjectName("eyebrow")
        subtitle = QLabel("scripts/main.js")
        subtitle.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)
        self.language_label = QLabel("Язык: JavaScript")
        self.language_label.setObjectName("status")
        header.addWidget(self.language_label)
        save = QPushButton("Сохранить")
        save.setObjectName("save")
        save.clicked.connect(self.save_code)
        header.addWidget(save)
        layout.addLayout(header)

        # Кодовая область намеренно пустая: никаких приветствий и шаблонного текста.
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("codeArea")
        self.editor.setFont(QFont("Consolas", 12))
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setTabStopDistance(4 * self.editor.fontMetrics().horizontalAdvance(" "))
        self.editor.setPlainText(self.script_path.read_text(encoding="utf-8") if self.script_path.exists() else "")
        layout.addWidget(self.editor, 1)

        footer = QHBoxLayout()
        self.status = QLabel("Готово")
        self.status.setObjectName("muted")
        footer.addWidget(self.status)
        footer.addStretch(1)
        close = QPushButton("Закрыть")
        close.setObjectName("secondary")
        close.clicked.connect(self.close)
        footer.addWidget(close)
        layout.addLayout(footer)
        self.setCentralWidget(central)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(700)
        self.autosave_timer.timeout.connect(self.save_code)
        self.editor.textChanged.connect(self.schedule_autosave)

    def schedule_autosave(self):
        self.status.setText("Изменения… автосохранение через секунду")
        self.autosave_timer.start()

    def save_code(self):
        self.autosave_timer.stop()
        try:
            self.script_path.parent.mkdir(parents=True, exist_ok=True)
            self.script_path.write_text(self.editor.toPlainText(), encoding="utf-8")
            self.status.setText("Автосохранено")
        except OSError as error:
            self.status.setText(f"Ошибка автосохранения: {error}")

    def closeEvent(self, event):
        if self.autosave_timer.isActive():
            self.save_code()
        if self.status.text().startswith("Ошибка автосохранения"): 
            answer = QMessageBox.question(
                self, "Несохранённый код",
                "Сохранить изменения перед закрытием?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if answer == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.StandardButton.Save:
                self.save_code()
                if self.status.text() == "Есть несохранённые изменения":
                    event.ignore()
                    return
        event.accept()


class ModEditorWindow(QMainWindow):
    def __init__(self, project_dir: Path, home_window):
        super().__init__()
        self.project_dir = project_dir
        self.home_window = home_window
        self.metadata_path = project_dir / "mod.json"
        self.script_path = project_dir / "scripts" / "main.js"
        self.setWindowTitle(f"SkyRealm Mod Studio — {project_dir.name}")
        self.resize(1180, 760)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(STYLE)

        metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(26, 20, 26, 18)
        root.setSpacing(14)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        eyebrow = QLabel("SKYREALM MOD STUDIO  /  PROJECT")
        eyebrow.setObjectName("eyebrow")
        self.project_title = QLabel(metadata.get("name", project_dir.name))
        self.project_title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.project_path_label = QLabel(str(project_dir))
        self.project_path_label.setObjectName("muted")
        titles.addWidget(eyebrow)
        titles.addWidget(self.project_title)
        titles.addWidget(self.project_path_label)
        header.addLayout(titles, 1)

        self.status = QLabel("Все изменения сохранены")
        self.status.setObjectName("status")
        header.addWidget(self.status)
        save_button = QPushButton("Сохранить")
        save_button.setObjectName("save")
        save_button.clicked.connect(self.save_project)
        header.addWidget(save_button)
        open_button = QPushButton("Открыть папку")
        open_button.setObjectName("secondary")
        open_button.clicked.connect(self.open_project_folder)
        header.addWidget(open_button)
        root.addLayout(header)

        self.tabs = QTabWidget()
        overview = QWidget()
        overview_layout = QVBoxLayout(overview)
        overview_layout.setContentsMargins(22, 22, 22, 22)
        overview_layout.setSpacing(15)
        intro = QLabel("Настройки модификации")
        intro.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        intro_hint = QLabel("Заполни информацию о моде. Нажми «Сохранить», чтобы записать её в mod.json.")
        intro_hint.setObjectName("muted")
        overview_layout.addWidget(intro)
        overview_layout.addWidget(intro_hint)

        form = QFormLayout()
        form.setSpacing(14)
        self.name_field = QLineEdit(metadata.get("name", ""))
        self.version_field = QLineEdit(metadata.get("version", "1.0.0"))
        self.author_field = QLineEdit(metadata.get("author", ""))
        self.description_field = QTextEdit()
        self.description_field.setFixedHeight(120)
        self.description_field.setPlainText(metadata.get("description", ""))
        form.addRow("Название:", self.name_field)
        form.addRow("Версия:", self.version_field)
        form.addRow("Автор:", self.author_field)
        form.addRow("Описание:", self.description_field)
        overview_layout.addLayout(form)
        overview_layout.addStretch(1)
        self.tabs.addTab(overview, "Обзор проекта")

        files_page = QWidget()
        files_layout = QVBoxLayout(files_page)
        files_layout.setContentsMargins(22, 22, 22, 22)
        files_layout.setSpacing(14)
        files_title = QLabel("Файлы проекта")
        files_title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        files_hint = QLabel("Редактор кода открывается в отдельном окне. Основное окно проекта остаётся независимым.")
        files_hint.setObjectName("muted")
        files_layout.addWidget(files_title)
        files_layout.addWidget(files_hint)
        file_list = QListWidget()
        file_list.addItem("📄  scripts/main.js  — JavaScript")
        file_list.addItem("📄  mod.json  — параметры мода")
        file_list.addItem("📄  README.md  — описание проекта")
        file_list.setMaximumHeight(170)
        files_layout.addWidget(file_list)
        open_code = QPushButton("Открыть отдельный редактор кода")
        open_code.setObjectName("primary")
        open_code.clicked.connect(self.open_code_editor)
        files_layout.addWidget(open_code, alignment=Qt.AlignmentFlag.AlignLeft)
        files_layout.addStretch(1)
        self.tabs.addTab(files_page, "Файлы проекта")
        root.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        back = QPushButton("← На главный экран")
        back.setObjectName("secondary")
        back.clicked.connect(self.return_home)
        footer.addWidget(back)
        footer.addStretch(1)
        footer_note = QLabel("Проект хранится локально на твоём компьютере")
        footer_note.setObjectName("muted")
        footer.addWidget(footer_note)
        root.addLayout(footer)
        self.setCentralWidget(central)

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(700)
        self.autosave_timer.timeout.connect(self.save_project)
        self.name_field.textChanged.connect(self.schedule_autosave)
        self.version_field.textChanged.connect(self.schedule_autosave)
        self.author_field.textChanged.connect(self.schedule_autosave)
        self.description_field.textChanged.connect(self.schedule_autosave)
        self.code_editor_window = None

    def open_code_editor(self):
        if self.code_editor_window is None or not self.code_editor_window.isVisible():
            self.code_editor_window = CodeEditorWindow(self.script_path, self)
        self.code_editor_window.show()
        self.code_editor_window.raise_()
        self.code_editor_window.activateWindow()

    def schedule_autosave(self, *_):
        self.status.setText("Изменения… автосохранение через секунду")
        self.autosave_timer.start()

    def save_project(self):
        self.autosave_timer.stop()
        try:
            metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            metadata.update({
                "name": self.name_field.text().strip(),
                "version": self.version_field.text().strip() or "1.0.0",
                "author": self.author_field.text().strip(),
                "description": self.description_field.toPlainText().strip(),
            })
            if not metadata["name"]:
                QMessageBox.warning(self, "Не заполнено название", "Укажи название мода.")
                return
            self.metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=4), encoding="utf-8")
            self.project_title.setText(metadata["name"])
            self.setWindowTitle(f"SkyRealm Mod Studio — {metadata['name']}")
            self.status.setText("Автосохранено")
        except (OSError, json.JSONDecodeError) as error:
            self.status.setText(f"Ошибка автосохранения: {error}")

    def open_project_folder(self):
        try:
            os.startfile(str(self.project_dir))
        except OSError as error:
            QMessageBox.warning(self, "Не удалось открыть папку", str(error))

    def return_home(self):
        self.close()

    def closeEvent(self, event):
        if self.autosave_timer.isActive():
            self.save_project()
        if self.status.text().startswith("Ошибка автосохранения"):
            answer = QMessageBox.question(
                self, "Ошибка сохранения",
                "Не удалось сохранить проект. Всё равно закрыть окно?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if answer == QMessageBox.StandardButton.No:
                event.ignore()
                return
        if self.code_editor_window is not None and self.code_editor_window.isVisible():
            self.code_editor_window.close()
            if self.code_editor_window.isVisible():
                event.ignore()
                return
        self.home_window.show()
        event.accept()


class StudioWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.editor_window = None
        self.setWindowTitle("SkyRealm Mod Studio")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        self.setStyleSheet(STYLE)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(54, 38, 54, 28)
        layout.setSpacing(0)
        top = QVBoxLayout()
        top.setSpacing(5)
        eyebrow = QLabel("SKYREALM • CREATOR TOOLS")
        eyebrow.setObjectName("eyebrow")
        brand = QLabel("MOD STUDIO")
        brand.setObjectName("brand")
        subtitle = QLabel("Инструмент для создания модификаций SkyRealm")
        subtitle.setObjectName("muted")
        top.addWidget(eyebrow)
        top.addWidget(brand)
        top.addWidget(subtitle)
        layout.addLayout(top)
        layout.addStretch(1)

        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(48, 54, 48, 54)
        panel_layout.setSpacing(18)
        panel_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome = QLabel("Добро пожаловать в SkyRealm Mod Studio")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        hint = QLabel("Создай собственную модификацию для своего мира")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setObjectName("muted")
        create_button = QPushButton("＋   Создать мод")
        create_button.setObjectName("primary")
        create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        create_button.setMinimumWidth(250)
        create_button.clicked.connect(self.create_mod)
        panel_layout.addWidget(welcome)
        panel_layout.addWidget(hint)
        panel_layout.addSpacing(18)
        panel_layout.addWidget(create_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(panel)
        layout.addStretch(1)

        exit_button = QPushButton("Выйти из Studio")
        exit_button.setObjectName("secondary")
        exit_button.clicked.connect(self.close)
        layout.addWidget(exit_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        footer = QLabel("SKYREALM MOD STUDIO  •  EARLY DEVELOPMENT")
        footer.setObjectName("muted")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)
        self.setCentralWidget(root)

    def create_mod(self):
        dialog = CreateModDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        mod_name, parent_folder = dialog.values()
        if not mod_name:
            QMessageBox.warning(self, "Не указано название", "Введи название мода.")
            return
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", mod_name).strip(" .")
        if not safe_name:
            QMessageBox.warning(self, "Некорректное название", "Укажи другое название мода.")
            return
        project_dir = Path(parent_folder).expanduser() / safe_name
        if project_dir.exists():
            QMessageBox.warning(self, "Папка уже существует",
                                f"Папка уже существует:\n{project_dir}\n\nВыбери другое название или место.")
            return
        try:
            (project_dir / "scripts").mkdir(parents=True, exist_ok=False)
            metadata = {
                "name": mod_name,
                "id": re.sub(r"[^a-z0-9]+", "-", safe_name.lower()).strip("-"),
                "version": "1.0.0",
                "game": "SkyRealm",
                "entry": "scripts/main.js",
                "author": "",
                "description": ""
            }
            (project_dir / "mod.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=4), encoding="utf-8")
            (project_dir / "scripts" / "main.js").write_text("", encoding="utf-8")
            (project_dir / "README.md").write_text(
                f"# {mod_name}\n\nМодификация для игры SkyRealm.\n", encoding="utf-8"
            )
        except OSError as error:
            QMessageBox.critical(self, "Ошибка создания", f"Не удалось создать проект:\n{error}")
            return

        self.hide()
        self.editor_window = ModEditorWindow(project_dir, self)
        self.editor_window.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("SkyRealm Mod Studio")
    app.setStyle("Fusion")
    window = StudioWindow()
    window.show()
    sys.exit(app.exec())

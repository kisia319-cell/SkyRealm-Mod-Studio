[Reading 231 lines from start (total: 231 lines, 0 remaining)]

import json
import re
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QFrame, QDialog, QLineEdit,
    QFileDialog, QFormLayout
)


class CreateModDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать мод")
        self.setMinimumWidth(520)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog, QWidget { background: #101a30; color: #edf2ff; }
            QLabel { color: #dce5f7; font-size: 13px; }
            QLabel#muted { color: #8797b6; }
            QLineEdit { background: #0b1222; border: 1px solid #344563;
                border-radius: 8px; padding: 11px; color: #ffffff; }
            QLineEdit:focus { border: 1px solid #35c987; }
            QPushButton { border-radius: 8px; padding: 10px 18px; font-weight: 650; }
            QPushButton#make { background: #35c987; color: #07150f; border: 0; }
            QPushButton#make:hover { background: #54dda0; }
            QPushButton#cancel { background: #1a2740; color: #dce5f7; border: 1px solid #344563; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(16)

        title = QLabel("Новая модификация")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        description = QLabel("Укажи название и место, где будет храниться проект мода.")
        description.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(description)

        form = QFormLayout()
        form.setSpacing(12)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например: My First Mod")
        self.folder_input = QLineEdit(str(Path.home() / "Documents" / "SkyRealmMods"))
        self.folder_input.setReadOnly(True)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        folder_row.addWidget(self.folder_input, 1)
        browse = QPushButton("Обзор…")
        browse.setObjectName("cancel")
        browse.clicked.connect(self.choose_folder)
        folder_row.addWidget(browse)

        form.addRow("Название мода:", self.name_input)
        form.addRow("Папка сохранения:", folder_row)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Отмена")
        cancel.setObjectName("cancel")
        cancel.clicked.connect(self.reject)
        create = QPushButton("Создать проект")
        create.setObjectName("make")
        create.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(create)
        layout.addLayout(buttons)

    def choose_folder(self):
        selected = QFileDialog.getExistingDirectory(
            self, "Выбери папку для модов", self.folder_input.text()
        )
        if selected:
            self.folder_input.setText(selected)

    def values(self):
        return self.name_input.text().strip(), self.folder_input.text().strip()


class StudioWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SkyRealm Mod Studio")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #0b1020; color: #edf2ff; }
            QLabel#brand { color: #f4f7ff; font-size: 38px; font-weight: 800; letter-spacing: 1px; }
            QLabel#subtitle { color: #8d9ab8; font-size: 14px; }
            QLabel#eyebrow { color: #66e3a4; font-size: 11px; font-weight: 700; letter-spacing: 3px; }
            QFrame#panel { background: #111a30; border: 1px solid #263552; border-radius: 22px; }
            QPushButton#primary { background: #35c987; color: #07150f; border: 0; border-radius: 12px; padding: 17px 34px; font-size: 17px; font-weight: 750; }
            QPushButton#primary:hover { background: #54dda0; }
            QPushButton#primary:pressed { background: #27ad73; }
            QPushButton#exit { background: transparent; color: #9aa8c4; border: 1px solid #34415d; border-radius: 10px; padding: 12px 28px; font-size: 13px; }
            QPushButton#exit:hover { background: #1b2740; color: #ffffff; }
            QLabel#footer { color: #586783; font-size: 11px; }
        """)

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
        subtitle.setObjectName("subtitle")
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
        welcome.setStyleSheet("color: #f2f6ff;")
        hint = QLabel("Создай собственную модификацию для своего мира")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #91a0bd; font-size: 13px;")
        create_button = QPushButton("＋   Создать мод")
        create_button.setObjectName("primary")
        create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        create_button.setMinimumWidth(250)
        create_button.clicked.connect(self.create_mod)
        panel_layout.addWidget(welcome)
        panel_layout.addWidget(hint)
        panel_layout.addSpacing(18)
        panel_layout.addWidget(create_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(panel, stretch=0)
        layout.addStretch(1)

        bottom = QVBoxLayout()
        bottom.setSpacing(14)
        exit_button = QPushButton("Выйти из Studio")
        exit_button.setObjectName("exit")
        exit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_button.clicked.connect(self.close)
        bottom.addWidget(exit_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        footer = QLabel("SKYREALM MOD STUDIO  •  EARLY DEVELOPMENT")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom.addWidget(footer)
        layout.addLayout(bottom)
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
            QMessageBox.warning(
                self, "Папка уже существует",
                f"Папка уже существует:\n{project_dir}\n\nВыбери другое название или место."
            )
            return

        try:
            (project_dir / "scripts").mkdir(parents=True, exist_ok=False)
            metadata = {
                "name": mod_name,
                "id": re.sub(r"[^a-z0-9]+", "-", safe_name.lower()).strip("-"),
                "version": "1.0.0",
                "game": "SkyRealm",
                "entry": "scripts/main.js"
            }
            (project_dir / "mod.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=4), encoding="utf-8"
            )
            (project_dir / "scripts" / "main.js").write_text(
                "// SkyRealm Mod entry point\n"
                "// Your mod logic will be added here.\n\n"
                "function onTick(context) {\n"
                "    // Called by the mod runtime.\n"
                "}\n",
                encoding="utf-8"
            )
            (project_dir / "README.md").write_text(
                f"# {mod_name}\n\nA SkyRealm mod project created with SkyRealm Mod Studio.\n",
                encoding="utf-8"
            )
        except OSError as error:
            QMessageBox.critical(self, "Ошибка создания", f"Не удалось создать проект:\n{error}")
            return

        QMessageBox.information(
            self, "Мод создан",
            f"Проект «{mod_name}» успешно создан.\n\nПапка: {project_dir}\n\n"
            "Созданы файлы mod.json, scripts/main.js и README.md."
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("SkyRealm Mod Studio")
    app.setStyle("Fusion")
    window = StudioWindow()
    window.show()
    sys.exit(app.exec())

[executed on device: DESKTOP-J3FNV3N (393b286a-047d-423b-ad40-4dc164e17a6c)]
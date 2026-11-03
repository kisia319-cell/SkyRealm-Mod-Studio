"""Extra productivity tools for SkyRealm Mod Studio."""
import json
import re
from pathlib import Path

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QKeySequence, QAction
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QPlainTextEdit, QMessageBox, QComboBox,
    QFormLayout, QDialogButtonBox, QSplitter, QWidget, QGraphicsOpacityEffect
)


def fade_in(widget, duration=240):
    """Subtle entrance animation; harmless if the platform cannot animate opacity."""
    try:
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", widget)
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        widget._entrance_animation = animation
        animation.start()
    except Exception:
        pass


class AnimatedDialog(QDialog):
    def showEvent(self, event):
        super().showEvent(event)
        fade_in(self)


class ApiCatalogDialog(AnimatedDialog):
    """Only documents the limited host surface known to this Studio build."""
    ITEMS = [
        ("Контекст игрока", "health, stamina, hunger, level, XP — значения состояния игрока. "
         "day, night, difficulty, inHouse, wallet — контекст мира. Доступность зависит от версии runtime."),
        ("Разрешённые действия", "heal, stamina, hunger, XP, gold, message — ограниченный набор действий, "
         "который встречается в базовом SkyRealm custom-mod host. Проверяй реализацию runtime перед использованием."),
        ("Важно", "Это не полный API и не обещание поддержки произвольных игровых команд. "
         "Не выдумывай методы для мобов, предметов, оружия или событий: для них нужна отдельная реализация в игре."),
        ("Безопасность", "Studio проверяет синтаксис и структуру. Она не запускает пользовательский код "
         "и не может подтвердить, что конкретный игровой вызов поддерживается установленной версией SkyRealm.")
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Каталог API SkyRealm")
        self.resize(760, 520)
        layout = QVBoxLayout(self)
        intro = QLabel("Справочник ограниченного API. Сверяйся с runtime игры перед использованием.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        split = QSplitter()
        self.list = QListWidget()
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        for title, _ in self.ITEMS:
            self.list.addItem(title)
        self.list.currentRowChanged.connect(self.show_item)
        split.addWidget(self.list)
        split.addWidget(self.details)
        split.setSizes([210, 520])
        layout.addWidget(split, 1)
        close = QPushButton("Закрыть")
        close.clicked.connect(self.accept)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self.list.setCurrentRow(0)

    def show_item(self, row):
        if 0 <= row < len(self.ITEMS):
            self.details.setPlainText(self.ITEMS[row][1])


class ProjectSearchDialog(AnimatedDialog):
    def __init__(self, folder: Path, open_callback, parent=None):
        super().__init__(parent)
        self.folder = Path(folder)
        self.open_callback = open_callback
        self.setWindowTitle("Поиск по проекту")
        self.resize(820, 560)
        layout = QVBoxLayout(self)
        self.query = QLineEdit()
        self.query.setPlaceholderText("Найти текст во всех файлах проекта…")
        self.query.textChanged.connect(self.search)
        layout.addWidget(self.query)
        self.results = QListWidget()
        self.results.itemDoubleClicked.connect(self.open_result)
        layout.addWidget(self.results, 1)
        self.hint = QLabel("Поиск не выполняет и не запускает код.")
        self.hint.setObjectName("muted")
        layout.addWidget(self.hint)

    def search(self, value):
        self.results.clear()
        needle = value.casefold().strip()
        if len(needle) < 2:
            self.hint.setText("Введи минимум 2 символа.")
            return
        count = 0
        ignored = {".git", "__pycache__", ".venv", "venv", ".backups", ".history", "build", "dist"}
        for path in self.folder.rglob("*"):
            if not path.is_file() or any(part in ignored for part in path.relative_to(self.folder).parts):
                continue
            if path.suffix.lower() not in {".js", ".mjs", ".json", ".py", ".md", ".txt"}:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError):
                continue
            for number, line in enumerate(lines, 1):
                if needle in line.casefold():
                    item = QListWidgetItem(f"{path.relative_to(self.folder)}  •  строка {number}: {line.strip()[:180]}")
                    item.setData(Qt.ItemDataRole.UserRole, (str(path), number))
                    self.results.addItem(item)
                    count += 1
                    if count >= 500:
                        self.hint.setText("Показаны первые 500 совпадений.")
                        return
        self.hint.setText(f"Найдено совпадений: {count}")

    def open_result(self, item):
        path, line = item.data(Qt.ItemDataRole.UserRole)
        self.open_callback(Path(path), line)
        self.accept()


class TemplateWizard(AnimatedDialog):
    TEMPLATES = {
        "Предмет (учебный шаблон)": {
            "filename": "item-template.js",
            "source": '''// Учебная структура данных предмета.
// Это не активирует предмет в игре без соответствующего API/runtime.
const item = {
    id: "my_mod:example_item",
    name: "Новый предмет",
    description: "Описание предмета",
    stackSize: 10,
    rarity: "common"
};

console.log("Подготовлены данные предмета:", item);
'''
        },
        "Оружие (учебный шаблон)": {
            "filename": "weapon-template.js",
            "source": '''// Учебная структура оружия.
// Реальное появление оружия в SkyRealm требует поддержки со стороны игры.
const weapon = {
    id: "my_mod:example_weapon",
    name: "Новое оружие",
    damage: 25,
    attackCooldown: 0.7,
    rarity: "rare"
};

console.log("Подготовлены данные оружия:", weapon);
'''
        },
        "Моб (учебный шаблон)": {
            "filename": "mob-template.js",
            "source": '''// Учебная структура моба.
// Спавн, AI, атаки и награды должны быть реализованы в игровом runtime.
const mob = {
    id: "my_mod:example_mob",
    name: "Новый моб",
    health: 100,
    damage: 10,
    movementSpeed: 2
};

console.log("Подготовлены данные моба:", mob);
'''
        },
        "Способность (учебный шаблон)": {
            "filename": "ability-template.js",
            "source": '''// Учебная структура способности.
// Для реального применения нужен поддерживаемый обработчик событий в игре.
const ability = {
    id: "my_mod:example_ability",
    name: "Новая способность",
    cooldownSeconds: 5,
    description: "Опиши эффект способности"
};

console.log("Подготовлены данные способности:", ability);
'''
        }
    }

    def __init__(self, folder: Path, refresh_callback, parent=None):
        super().__init__(parent)
        self.folder = Path(folder)
        self.refresh_callback = refresh_callback
        self.setWindowTitle("Генератор шаблонов")
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.kind = QComboBox()
        self.kind.addItems(self.TEMPLATES.keys())
        self.name = QLineEdit()
        self.name.setPlaceholderText("Например, frost_sword.js")
        form.addRow("Тип шаблона:", self.kind)
        form.addRow("Имя файла:", self.name)
        layout.addLayout(form)
        note = QLabel("Генератор создаёт учебный JavaScript-файл с данными. Он не добавляет игровые сущности без API-поддержки в SkyRealm.")
        note.setWordWrap(True)
        note.setObjectName("muted")
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.create)
        layout.addWidget(buttons)

    def create(self):
        template = self.TEMPLATES[self.kind.currentText()]
        filename = self.name.text().strip() or template["filename"]
        if Path(filename).name != filename or not filename.lower().endswith(".js"):
            QMessageBox.warning(self, "Имя файла", "Укажи простое имя файла с расширением .js.")
            return
        target = self.folder / "scripts" / filename
        if target.exists():
            QMessageBox.warning(self, "Файл уже существует", "Выбери другое имя, чтобы не перезаписать существующий файл.")
            return
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(template["source"], encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))
            return
        self.refresh_callback()
        QMessageBox.information(self, "Шаблон создан", f"Файл создан:\n{target.relative_to(self.folder)}")
        self.accept()


class ConsoleDialog(AnimatedDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Консоль и журнал Studio")
        self.resize(850, 500)
        layout = QVBoxLayout(self)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        layout.addWidget(self.output, 1)
        row = QHBoxLayout()
        clear = QPushButton("Очистить")
        clear.clicked.connect(self.output.clear)
        close = QPushButton("Закрыть")
        close.clicked.connect(self.accept)
        row.addWidget(clear)
        row.addStretch()
        row.addWidget(close)
        layout.addLayout(row)

    def append(self, text):
        self.output.appendPlainText(str(text))


def add_fade_animation(widget, duration=260):
    fade_in(widget, duration)


class HistoryDialog(AnimatedDialog):
    def __init__(self, source_file: Path, project_folder: Path, parent=None):
        super().__init__(parent)
        self.source_file = Path(source_file)
        self.project_folder = Path(project_folder)
        self.history_dir = self.project_folder / ".history" / self.source_file.relative_to(self.project_folder)
        self.setWindowTitle("История версий файла")
        self.resize(720, 480)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"История: {self.source_file.relative_to(self.project_folder)}"))
        self.items = QListWidget()
        layout.addWidget(self.items, 1)
        if self.history_dir.is_dir():
            for path in sorted(self.history_dir.glob("*.bak"), key=lambda p: p.stat().st_mtime, reverse=True):
                from datetime import datetime
                stamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d.%m.%Y %H:%M:%S")
                item = QListWidgetItem(f"{stamp}  —  {path.name}")
                item.setData(Qt.ItemDataRole.UserRole, str(path))
                self.items.addItem(item)
        if self.items.count() == 0:
            self.items.addItem("История пока пуста. Она начнёт собираться после сохранений.")
        row = QHBoxLayout()
        restore = QPushButton("Восстановить выбранную версию")
        restore.clicked.connect(self.restore)
        close = QPushButton("Закрыть")
        close.clicked.connect(self.reject)
        row.addWidget(restore)
        row.addStretch()
        row.addWidget(close)
        layout.addLayout(row)

    def restore(self):
        item = self.items.currentItem()
        value = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not value:
            return
        answer = QMessageBox.question(self, "Восстановить версию",
            "Текущий файл будет заменён выбранной версией. Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            content = Path(value).read_text(encoding="utf-8")
            self.source_file.write_text(content, encoding="utf-8")
            QMessageBox.information(self, "Готово", "Выбранная версия восстановлена.")
            self.accept()
        except (OSError, UnicodeError) as exc:
            QMessageBox.critical(self, "Ошибка восстановления", str(exc))

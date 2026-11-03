"""Visual data designer for mod metadata and animation frames."""
import json
import os
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QLabel,
    QLineEdit, QComboBox, QPlainTextEdit, QPushButton, QSpinBox,
    QDoubleSpinBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QHeaderView
)

DATA_TYPES = {
    "Предмет": ("items", {"id": "my_mod:example_item", "name": "Новый предмет", "description": "", "stackSize": 10, "rarity": "common"}),
    "Оружие": ("weapons", {"id": "my_mod:example_weapon", "name": "Новое оружие", "damage": 25, "attackCooldown": 0.7, "rarity": "common"}),
    "Монстр": ("mobs", {"id": "my_mod:example_mob", "name": "Новый монстр", "health": 100, "damage": 10, "speed": 2, "abilities": []}),
    "Квест": ("quests", {"id": "my_mod:example_quest", "title": "Новый квест", "description": "", "objectives": [], "rewards": []}),
    "Анимация": ("animations", {"id": "my_mod:example_animation", "target": "player", "fps": 12, "loop": False, "frames": []}),
    "Биом": ("biomes", {"id": "my_mod:example_biome", "name": "Новый биом", "temperature": 0.5, "terrain": "default", "spawns": []}),
    "Диалог NPC": ("dialogs", {"id": "my_mod:example_dialog", "title": "Диалог NPC", "npc": "villager", "nodes": [{"id": "start", "text": "Привет!", "options": []}]}),
    "Игровое событие": ("events", {"id": "my_mod:example_event", "name": "Новое событие", "trigger": "on_day_start", "conditions": [], "actions": []}),
}

class VisualDataDesigner(QWidget):
    """Form + raw JSON editor. Formats are Studio-side until the game loads them."""
    def __init__(self, project_folder: Path, parent=None):
        super().__init__(parent)
        self.folder = Path(project_folder).resolve()
        self._loading = False
        self._controls = {}
        self._array_controls = {}
        root = QVBoxLayout(self)
        intro = QLabel("Заполняй поля формы или редактируй JSON напрямую. Форматы данных должны быть реализованы в игровом runtime отдельно.")
        intro.setWordWrap(True)
        root.addWidget(intro)
        top = QHBoxLayout()
        self.kind = QComboBox()
        self.kind.addItems(DATA_TYPES.keys())
        self.filename = QLineEdit()
        self.filename.setPlaceholderText("имя_файла.json")
        top.addWidget(QLabel("Тип:"))
        top.addWidget(self.kind)
        top.addWidget(QLabel("Файл:"))
        top.addWidget(self.filename, 1)
        root.addLayout(top)
        self.tabs = QTabWidget()
        self.form_page = QWidget()
        self.form_layout = QFormLayout(self.form_page)
        self.tabs.addTab(self.form_page, "Визуальная форма")
        self.raw = QPlainTextEdit()
        self.raw.setPlaceholderText("JSON проекта")
        self.tabs.addTab(self.raw, "JSON")
        self.animation_page = QWidget()
        anim_layout = QVBoxLayout(self.animation_page)
        anim_layout.addWidget(QLabel("Кадры анимации: спрайт/имя кадра, длительность и координаты"))
        self.frames = QTableWidget(0, 6)
        self.frames.setHorizontalHeaderLabels(["Спрайт / ID", "мс", "X", "Y", "Масштаб", "Прозрачность"])
        self.frames.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        anim_layout.addWidget(self.frames, 1)
        frame_buttons = QHBoxLayout()
        add_frame = QPushButton("＋ Добавить кадр")
        remove_frame = QPushButton("Удалить выбранный")
        add_frame.clicked.connect(self.add_frame)
        remove_frame.clicked.connect(self.remove_frame)
        frame_buttons.addWidget(add_frame)
        frame_buttons.addWidget(remove_frame)
        frame_buttons.addStretch()
        anim_layout.addLayout(frame_buttons)
        self.tabs.addTab(self.animation_page, "Кадры анимации")
        root.addWidget(self.tabs, 1)
        bottom = QHBoxLayout()
        load = QPushButton("Сбросить к шаблону")
        validate = QPushButton("Проверить")
        save = QPushButton("Сохранить данные")
        save.setObjectName("primary")
        load.clicked.connect(lambda: self.load_template(self.kind.currentText()))
        validate.clicked.connect(self.validate_data)
        save.clicked.connect(self.save_data)
        bottom.addWidget(load)
        bottom.addStretch()
        bottom.addWidget(validate)
        bottom.addWidget(save)
        root.addLayout(bottom)
        self.kind.currentTextChanged.connect(self.load_template)
        self.raw.textChanged.connect(self._raw_changed)
        self.frames.itemChanged.connect(self._frames_changed)
        self.load_template(self.kind.currentText())

    def _clear_form(self):
        while self.form_layout.rowCount():
            self.form_layout.removeRow(0)
        self._controls.clear()
        self._array_controls.clear()

    def load_template(self, kind):
        self._loading = True
        self._clear_form()
        _, template = DATA_TYPES[kind]
        for key, value in template.items():
            if key == "frames":
                continue
            if isinstance(value, bool):
                control = QCheckBox()
                control.setChecked(value)
            elif isinstance(value, int):
                control = QSpinBox()
                control.setRange(-1000000000, 1000000000)
                control.setValue(value)
            elif isinstance(value, float):
                control = QDoubleSpinBox()
                control.setRange(-1000000000, 1000000000)
                control.setDecimals(4)
                control.setValue(value)
            elif isinstance(value, (list, dict)):
                control = QPlainTextEdit()
                control.setMaximumHeight(100)
                control.setPlainText(json.dumps(value, ensure_ascii=False, indent=2))
                self._array_controls[key] = control
            else:
                control = QLineEdit(str(value))
            self._controls[key] = control
            if isinstance(control, QCheckBox):
                control.toggled.connect(self._sync_raw)
            elif isinstance(control, (QSpinBox, QDoubleSpinBox)):
                control.valueChanged.connect(self._sync_raw)
            elif isinstance(control, QPlainTextEdit):
                control.textChanged.connect(self._sync_raw)
            elif isinstance(control, QLineEdit):
                control.textChanged.connect(self._sync_raw)
            self.form_layout.addRow(key, control)
        self.filename.setText(template["id"].split(":")[-1] + ".json")
        self.frames.setRowCount(0)
        if kind == "Анимация":
            self.tabs.setTabEnabled(2, True)
        else:
            self.tabs.setTabEnabled(2, False)
        self._loading = False
        self._sync_raw()

    def _form_data(self):
        data = {}
        for key, control in self._controls.items():
            if isinstance(control, QCheckBox):
                data[key] = control.isChecked()
            elif isinstance(control, QSpinBox):
                data[key] = control.value()
            elif isinstance(control, QDoubleSpinBox):
                data[key] = control.value()
            elif isinstance(control, QPlainTextEdit):
                value = json.loads(control.toPlainText() or "[]")
                if not isinstance(value, (list, dict)):
                    raise ValueError(f"Поле {key} должно быть JSON-массивом или объектом.")
                data[key] = value
            else:
                data[key] = control.text().strip()
        if self.kind.currentText() == "Анимация":
            data["frames"] = self._read_frames()
        return data

    def _read_frames(self):
        frames = []
        for row in range(self.frames.rowCount()):
            def cell(column, default):
                item = self.frames.item(row, column)
                return item.text().strip() if item else str(default)
            try:
                frame = {
                    "sprite": cell(0, ""),
                    "durationMs": int(cell(1, 100)),
                    "x": float(cell(2, 0)),
                    "y": float(cell(3, 0)),
                    "scale": float(cell(4, 1)),
                    "opacity": float(cell(5, 1)),
                }
            except ValueError as exc:
                raise ValueError(f"Неверное число в строке кадра {row + 1}.") from exc
            if frame["durationMs"] < 1:
                raise ValueError(f"Длительность кадра {row + 1} должна быть больше нуля.")
            if not 0 <= frame["opacity"] <= 1 or frame["scale"] <= 0:
                raise ValueError(f"Масштаб должен быть > 0, прозрачность — от 0 до 1 (кадр {row + 1}).")
            frames.append(frame)
        return frames

    def _sync_raw(self):
        if self._loading:
            return
        try:
            data = self._form_data()
            self.raw.blockSignals(True)
            self.raw.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))
            self.raw.blockSignals(False)
        except (ValueError, json.JSONDecodeError):
            self.raw.blockSignals(False)

    def _raw_changed(self):
        if self._loading:
            return
        try:
            data = json.loads(self.raw.toPlainText())
            if not isinstance(data, dict):
                return
            self._loading = True
            for key, value in data.items():
                control = self._controls.get(key)
                if control is None:
                    continue
                if isinstance(control, QCheckBox):
                    control.setChecked(bool(value))
                elif isinstance(control, QSpinBox):
                    control.setValue(int(value))
                elif isinstance(control, QDoubleSpinBox):
                    control.setValue(float(value))
                elif isinstance(control, QPlainTextEdit):
                    control.setPlainText(json.dumps(value, ensure_ascii=False, indent=2))
                elif isinstance(control, QLineEdit):
                    control.setText(str(value))
            if self.kind.currentText() == "Анимация":
                self.frames.setRowCount(0)
                for frame in data.get("frames", []):
                    self._insert_frame(frame)
            self._loading = False
        except (ValueError, TypeError, json.JSONDecodeError):
            self._loading = False

    def _frames_changed(self, _item):
        if not self._loading:
            self._sync_raw()

    def _insert_frame(self, frame=None):
        frame = frame or {"sprite": "", "durationMs": 100, "x": 0, "y": 0, "scale": 1, "opacity": 1}
        row = self.frames.rowCount()
        self.frames.insertRow(row)
        values = [frame.get("sprite", ""), frame.get("durationMs", 100), frame.get("x", 0),
                  frame.get("y", 0), frame.get("scale", 1), frame.get("opacity", 1)]
        for col, value in enumerate(values):
            self.frames.setItem(row, col, QTableWidgetItem(str(value)))

    def add_frame(self):
        self._insert_frame()
        self._sync_raw()

    def remove_frame(self):
        rows = sorted({index.row() for index in self.frames.selectedIndexes()}, reverse=True)
        for row in rows:
            self.frames.removeRow(row)
        self._sync_raw()

    def validate_data(self):
        try:
            data = json.loads(self.raw.toPlainText())
            if not isinstance(data, dict):
                raise ValueError("Корень JSON должен быть объектом.")
            if not isinstance(data.get("id"), str) or not data["id"].strip():
                raise ValueError("Поле id должно быть непустой строкой.")
            label = data.get("name") or data.get("title")
            if not isinstance(label, str) or not label.strip():
                raise ValueError("Нужно непустое текстовое поле name или title.")
            if self.kind.currentText() == "Анимация":
                self._read_frames()
            QMessageBox.information(self, "Проверка", "JSON корректен, основные поля проверены. Поддержка игровым runtime не подтверждена.")
            return True
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Ошибка данных", str(exc))
            return False

    def save_data(self):
        if not self.validate_data():
            return
        try:
            data = json.loads(self.raw.toPlainText())
            directory, _ = DATA_TYPES[self.kind.currentText()]
            filename = self.filename.text().strip() or (data["id"].split(":")[-1] + ".json")
            if Path(filename).name != filename or not filename.lower().endswith(".json"):
                raise ValueError("Имя файла должно быть простым именем с расширением .json.")
            target = (self.folder / "data" / directory / filename).resolve()
            base = (self.folder / "data" / directory).resolve()
            if base not in target.parents:
                raise ValueError("Путь сохранения выходит за пределы папки данных.")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                answer = QMessageBox.question(self, "Перезаписать?", f"{target.name} уже существует. Перезаписать?")
                if answer != QMessageBox.StandardButton.Yes:
                    return
            payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
            fd, temp_name = tempfile.mkstemp(prefix=".studio-", suffix=".tmp", dir=str(target.parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp_name, target)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
            QMessageBox.information(self, "Сохранено", f"Создан файл:\n{target.relative_to(self.folder)}")
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Не удалось сохранить", str(exc))

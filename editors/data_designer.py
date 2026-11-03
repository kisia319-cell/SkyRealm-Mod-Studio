"""Visual data designer for mod metadata and animation frames."""
import json
import os
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QLabel,
    QLineEdit, QComboBox, QPlainTextEdit, QPushButton, QSpinBox,
    QDoubleSpinBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QHeaderView
)

DATA_TYPES = {
    "Предмет": ("items", {"id": "my_mod:example_item", "name": "Новый предмет", "description": "", "stackSize": 10, "rarity": "common", "sprite": "assets/sprites/example.png"}),
    "Оружие": ("weapons", {"id": "my_mod:example_weapon", "name": "Новое оружие", "damage": 25, "attackCooldown": 0.7, "rarity": "common", "sprite": "assets/sprites/example.png"}),
    "Монстр": ("mobs", {"id": "my_mod:example_mob", "name": "Новый монстр", "health": 100, "damage": 10, "speed": 2, "abilities": [], "sprite": "assets/sprites/example.png"}),
    "Квест": ("quests", {"id": "my_mod:example_quest", "title": "Новый квест", "description": "", "objectives": [], "rewards": []}),
    "Анимация": ("animations", {"id": "my_mod:example_animation", "target": "player", "fps": 12, "loop": False, "frames": []}),
    "Биом": ("biomes", {"id": "my_mod:example_biome", "name": "Новый биом", "temperature": 0.5, "terrain": "default", "spawns": [], "sprite": "assets/sprites/example.png"}),
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
        self.list_page = QWidget()
        list_layout = QVBoxLayout(self.list_page)
        list_layout.addWidget(QLabel("Конструктор целей квестов, наград, способностей, узлов диалогов и действий событий. Каждый элемент хранится как отдельный JSON-объект или значение."))
        self.list_field = QComboBox()
        self.list_table = QTableWidget(0, 1)
        self.list_table.setHorizontalHeaderLabels(["JSON элемента списка"])
        self.list_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        list_layout.addWidget(self.list_field)
        list_layout.addWidget(self.list_table, 1)
        list_buttons = QHBoxLayout()
        add_list = QPushButton("＋ Добавить элемент")
        remove_list = QPushButton("Удалить выбранный")
        add_list.clicked.connect(self._add_list_item)
        remove_list.clicked.connect(self._remove_list_item)
        list_buttons.addWidget(add_list)
        list_buttons.addWidget(remove_list)
        list_buttons.addStretch()
        list_layout.addLayout(list_buttons)
        self.tabs.addTab(self.list_page, "Квесты / диалоги / события")
        preview_panel = QWidget()
        preview_layout = QHBoxLayout(preview_panel)
        self.preview_image = QLabel("Спрайт не выбран")
        self.preview_image.setFixedSize(100, 100)
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image.setStyleSheet("background:#101a30;border:1px solid #263552;border-radius:8px")
        self.preview = QLabel("Предпросмотр данных")
        self.preview.setWordWrap(True)
        self.preview.setObjectName("muted")
        preview_layout.addWidget(self.preview_image)
        preview_layout.addWidget(self.preview, 1)
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
        root.addWidget(preview_panel)
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
        self.list_table.itemChanged.connect(self._list_table_changed)
        self.list_field.currentTextChanged.connect(self._load_list_table)
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
        self._refresh_list_fields()
        self.tabs.setTabEnabled(3, kind == "Анимация")
        self.tabs.setTabEnabled(2, bool(self._array_controls))
        self._loading = False
        self._sync_raw()

    def _form_data(self):
        current_text = self.raw.toPlainText().strip()
        if current_text:
            data = json.loads(current_text)
            if not isinstance(data, dict):
                raise ValueError("Корень JSON должен быть объектом.")
        else:
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
            self._update_preview(data)
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
                frame_data = data.get("frames", [])
                if isinstance(frame_data, list):
                    for frame in frame_data:
                        if isinstance(frame, dict):
                            self._insert_frame(frame)
            self._load_list_table(self.list_field.currentText())
            self._update_preview(data)
            self._loading = False
        except (ValueError, TypeError, json.JSONDecodeError):
            self._loading = False

    def _frames_changed(self, _item):
        if not self._loading:
            self._sync_raw()

    def _refresh_list_fields(self):
        current = self.list_field.currentText()
        self.list_field.blockSignals(True)
        self.list_field.clear()
        self.list_field.addItems(list(self._array_controls))
        if current in self._array_controls:
            self.list_field.setCurrentText(current)
        self.list_field.blockSignals(False)
        self._load_list_table(self.list_field.currentText())

    def _load_list_table(self, field):
        if not hasattr(self, "list_table"):
            return
        self._loading = True
        self.list_table.setRowCount(0)
        control = self._array_controls.get(field)
        if control:
            try:
                values = json.loads(control.toPlainText() or "[]")
                if isinstance(values, list):
                    for value in values:
                        self._insert_list_row(value)
            except json.JSONDecodeError:
                pass
        self._loading = False

    def _insert_list_row(self, value=None):
        row = self.list_table.rowCount()
        self.list_table.insertRow(row)
        self.list_table.setItem(row, 0, QTableWidgetItem(json.dumps(value if value is not None else {}, ensure_ascii=False)))

    def _add_list_item(self):
        self._insert_list_row({})
        self._list_table_changed(None)

    def _remove_list_item(self):
        rows = sorted({index.row() for index in self.list_table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.list_table.removeRow(row)
        self._list_table_changed(None)

    def _list_table_changed(self, _item):
        if self._loading:
            return
        field = self.list_field.currentText()
        control = self._array_controls.get(field)
        if not control:
            return
        values = []
        try:
            for row in range(self.list_table.rowCount()):
                item = self.list_table.item(row, 0)
                values.append(json.loads(item.text()) if item else {})
        except json.JSONDecodeError:
            return
        control.blockSignals(True)
        control.setPlainText(json.dumps(values, ensure_ascii=False, indent=2))
        control.blockSignals(False)
        self._sync_raw()

    def _update_preview(self, data):
        if not hasattr(self, "preview"):
            return
        label = data.get("name") or data.get("title") or "(без названия)"
        details = [f"{self.kind.currentText()} • {label}", f"ID: {data.get('id', '—')}"]
        for key, value in data.items():
            if key in {"id", "name", "title", "sprite", "frames"} or isinstance(value, (dict, list)):
                continue
            details.append(f"{key}: {value}")
        self.preview.setText("\n".join(details[:7]))
        self.preview_image.setPixmap(QPixmap())
        sprite = data.get("sprite")
        if isinstance(sprite, str) and sprite.strip():
            candidate = (self.folder / sprite).resolve()
            try:
                candidate.relative_to(self.folder)
                pixmap = QPixmap(str(candidate))
                if not pixmap.isNull():
                    self.preview_image.setPixmap(pixmap.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    self.preview_image.setText("")
                else:
                    self.preview_image.setText("Нет спрайта")
            except (ValueError, OSError):
                self.preview_image.setText("Путь вне проекта")


    def _insert_frame(self, frame=None):
        if not isinstance(frame, dict):
            frame = {}
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
            if (Path(filename).name != filename or "/" in filename or "\\" in filename
                    or not filename.lower().endswith(".json")):
                raise ValueError("Имя файла должно быть простым именем с расширением .json.")
            base = (self.folder / "data" / directory).resolve()
            try:
                base.relative_to(self.folder)
            except ValueError as exc:
                raise ValueError("Папка данных не должна вести за пределы проекта.") from exc
            target = (base / filename).resolve()
            try:
                target.relative_to(base)
            except ValueError as exc:
                raise ValueError("Путь сохранения выходит за пределы папки данных.") from exc
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

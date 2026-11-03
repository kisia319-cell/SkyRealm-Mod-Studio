"""Simple pixel-art sprite editor for mod assets."""
from pathlib import Path

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QCheckBox, QSpinBox, QColorDialog, QFileDialog, QMessageBox
)


class SpriteCanvas(QWidget):
    def __init__(self, width=32, height=32, parent=None):
        super().__init__(parent)
        self.image = QImage(width, height, QImage.Format.Format_ARGB32)
        self.image.fill(Qt.GlobalColor.transparent)
        self.color = QColor("#ffffff")
        self.tool = "Карандаш"
        self.show_grid = True
        self.setMinimumSize(320, 320)
        self.setMouseTracking(True)

    def set_image(self, image):
        self.image = image.convertToFormat(QImage.Format.Format_ARGB32)
        self.update()

    def resize_image(self, width, height):
        resized = QImage(width, height, QImage.Format.Format_ARGB32)
        resized.fill(Qt.GlobalColor.transparent)
        painter = QPainter(resized)
        painter.drawImage(0, 0, self.image)
        painter.end()
        self.image = resized
        self.update()

    def _geometry(self):
        cell = min(self.width() / self.image.width(), self.height() / self.image.height())
        side_w, side_h = cell * self.image.width(), cell * self.image.height()
        left = (self.width() - side_w) / 2
        top = (self.height() - side_h) / 2
        return cell, left, top

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#182238"))
        cell, left, top = self._geometry()
        target = QRectF(left, top, cell * self.image.width(), cell * self.image.height())
        painter.fillRect(target, QColor("#d5d9e0"))
        painter.drawImage(target, self.image)
        if self.show_grid and cell >= 5:
            pen = QPen(QColor(30, 40, 58, 90))
            pen.setWidthF(0.6)
            painter.setPen(pen)
            for x in range(self.image.width() + 1):
                px = left + x * cell
                painter.drawLine(QPointF(px, top), QPointF(px, top + self.image.height() * cell))
            for y in range(self.image.height() + 1):
                py = top + y * cell
                painter.drawLine(QPointF(left, py), QPointF(left + self.image.width() * cell, py))
        painter.setPen(QPen(QColor("#7183a5"), 1))
        painter.drawRect(target)
        painter.end()

    def _pixel_at(self, position):
        cell, left, top = self._geometry()
        x = int((position.x() - left) / cell)
        y = int((position.y() - top) / cell)
        if 0 <= x < self.image.width() and 0 <= y < self.image.height():
            return x, y
        return None

    def _paint_pixel(self, x, y, erase=False):
        painter = QPainter(self.image)
        if erase:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(x, y, 1, 1, Qt.GlobalColor.transparent)
        else:
            painter.fillRect(x, y, 1, 1, self.color)
        painter.end()
        self.update()

    def _fill(self, x, y):
        target = self.image.pixelColor(x, y)
        replacement = self.color
        if target == replacement:
            return
        pending = [(x, y)]
        visited = set()
        while pending:
            px, py = pending.pop()
            if (px, py) in visited or not (0 <= px < self.image.width() and 0 <= py < self.image.height()):
                continue
            visited.add((px, py))
            if self.image.pixelColor(px, py) != target:
                continue
            self.image.setPixelColor(px, py, replacement)
            pending.extend(((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)))
        self.update()

    def _apply_tool(self, position, erase_button=False):
        pixel = self._pixel_at(position)
        if pixel is None:
            return
        x, y = pixel
        if self.tool == "Заливка" and not erase_button:
            self._fill(x, y)
        else:
            self._paint_pixel(x, y, erase=erase_button or self.tool == "Ластик")

    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self._apply_tool(event.position(), event.button() == Qt.MouseButton.RightButton)

    def mouseMoveEvent(self, event):
        if event.buttons() & (Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton):
            self._apply_tool(event.position(), bool(event.buttons() & Qt.MouseButton.RightButton))


class SpriteEditorDialog(QDialog):
    def __init__(self, project_folder: Path, image_path=None, parent=None):
        super().__init__(parent)
        self.folder = Path(project_folder).resolve()
        self.setWindowTitle("Редактор спрайтов — SkyRealm Mod Studio")
        self.resize(820, 720)
        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.tool = QComboBox()
        self.tool.addItems(["Карандаш", "Ластик", "Заливка"])
        self.tool.currentTextChanged.connect(self._set_tool)
        self.color_button = QPushButton("Цвет")
        self.color_button.clicked.connect(self._choose_color)
        self.grid = QCheckBox("Сетка")
        self.grid.setChecked(True)
        self.grid.toggled.connect(self._toggle_grid)
        self.width_box = QSpinBox()
        self.width_box.setRange(8, 256)
        self.width_box.setValue(32)
        self.height_box = QSpinBox()
        self.height_box.setRange(8, 256)
        self.height_box.setValue(32)
        resize_button = QPushButton("Размер")
        resize_button.clicked.connect(self._resize_canvas)
        for widget in (QLabel("Инструмент:"), self.tool, self.color_button, self.grid,
                       QLabel("Ширина:"), self.width_box, QLabel("Высота:"), self.height_box, resize_button):
            toolbar.addWidget(widget)
        root.addLayout(toolbar)
        self.canvas = SpriteCanvas()
        root.addWidget(self.canvas, 1)
        self.status = QLabel("ЛКМ — рисовать, ПКМ — стирать. Заливка работает по связанным пикселям.")
        root.addWidget(self.status)
        bottom = QHBoxLayout()
        open_button = QPushButton("Открыть PNG…")
        open_button.clicked.connect(self.open_image)
        save_button = QPushButton("Сохранить PNG…")
        save_button.setObjectName("primary")
        save_button.clicked.connect(self.save_image)
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.reject)
        bottom.addWidget(open_button)
        bottom.addStretch()
        bottom.addWidget(save_button)
        bottom.addWidget(close_button)
        root.addLayout(bottom)
        if image_path:
            self.load_image(image_path)

    def _set_tool(self, value):
        self.canvas.tool = value

    def _toggle_grid(self, value):
        self.canvas.show_grid = bool(value)
        self.canvas.update()

    def _choose_color(self):
        color = QColorDialog.getColor(self.canvas.color, self, "Цвет пикселя")
        if color.isValid():
            self.canvas.color = color
            self.color_button.setStyleSheet(f"background:{color.name()};color:#111")

    def _resize_canvas(self):
        self.canvas.resize_image(self.width_box.value(), self.height_box.value())

    def load_image(self, filename):
        path = Path(filename).resolve()
        try:
            path.relative_to(self.folder)
        except ValueError as exc:
            raise ValueError("Изображение должно находиться внутри папки проекта.") from exc
        image = QImage(str(path))
        if image.isNull():
            raise ValueError("Не удалось открыть изображение.")
        self.canvas.set_image(image)
        self.width_box.setValue(image.width())
        self.height_box.setValue(image.height())
        self.status.setText(f"Открыт спрайт: {path.name} • {image.width()}×{image.height()}")

    def open_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Открыть спрайт", str(self.folder / "assets" / "sprites"), "Изображения (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if filename:
            try:
                self.load_image(filename)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "Не удалось открыть спрайт", str(exc))

    def save_image(self):
        folder = self.folder / "assets" / "sprites"
        folder.mkdir(parents=True, exist_ok=True)
        filename, _ = QFileDialog.getSaveFileName(self, "Сохранить спрайт", str(folder / "new_sprite.png"), "PNG (*.png)")
        if not filename:
            return
        target = Path(filename).resolve()
        try:
            target.relative_to(folder.resolve())
        except ValueError:
            QMessageBox.warning(self, "Недопустимый путь", "Сохраняй спрайты внутри assets/sprites/.")
            return
        if target.suffix.lower() != ".png":
            target = target.with_suffix(".png")
        if not self.canvas.image.save(str(target), "PNG"):
            QMessageBox.warning(self, "Ошибка сохранения", "Не удалось сохранить PNG.")
            return
        self.status.setText(f"Сохранено: {target.relative_to(self.folder)}")

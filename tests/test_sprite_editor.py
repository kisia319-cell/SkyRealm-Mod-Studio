import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor
from editors.sprite_editor import SpriteCanvas

app = QApplication.instance() or QApplication([])


class SpriteEditorTests(unittest.TestCase):
    def test_draw_and_erase_pixel(self):
        canvas = SpriteCanvas(8, 8)
        canvas.color = QColor("#ff0000")
        canvas._paint_pixel(2, 3)
        self.assertEqual(canvas.image.pixelColor(2, 3), QColor("#ff0000"))
        canvas._paint_pixel(2, 3, erase=True)
        self.assertEqual(canvas.image.pixelColor(2, 3).alpha(), 0)

    def test_bucket_fills_connected_transparent_area(self):
        canvas = SpriteCanvas(8, 8)
        canvas.color = QColor("#00ff00")
        canvas._fill(0, 0)
        self.assertEqual(canvas.image.pixelColor(7, 7), QColor("#00ff00"))

    def test_resize_preserves_existing_pixels(self):
        canvas = SpriteCanvas(8, 8)
        canvas.color = QColor("#0000ff")
        canvas._paint_pixel(1, 1)
        canvas.resize_image(16, 16)
        self.assertEqual(canvas.image.pixelColor(1, 1), QColor("#0000ff"))
        self.assertEqual(canvas.image.width(), 16)


if __name__ == "__main__":
    unittest.main()

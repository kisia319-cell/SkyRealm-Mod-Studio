import json
import os
import sys
import unittest
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication, QLineEdit, QDoubleSpinBox
from editors.data_designer import VisualDataDesigner

app = QApplication.instance() or QApplication([])


class VisualDesignerTests(unittest.TestCase):
    def test_form_updates_raw_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            widget = VisualDataDesigner(Path(tmp))
            widget._controls["name"].setText("Crystal")
            data = json.loads(widget.raw.toPlainText())
            self.assertEqual(data["name"], "Crystal")
            widget.close()

    def test_animation_frames_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            widget = VisualDataDesigner(Path(tmp))
            widget.kind.setCurrentText("Анимация")
            widget.add_frame()
            widget.frames.item(0, 0).setText("walk_01")
            widget.frames.item(0, 1).setText("120")
            data = json.loads(widget.raw.toPlainText())
            self.assertEqual(data["frames"][0]["sprite"], "walk_01")
            self.assertEqual(data["frames"][0]["durationMs"], 120)
            widget.close()

    def test_invalid_frame_values_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            widget = VisualDataDesigner(Path(tmp))
            widget.kind.setCurrentText("Анимация")
            widget.add_frame()
            widget.frames.item(0, 1).setText("0")
            with self.assertRaises(ValueError):
                widget._read_frames()
            widget.close()


if __name__ == "__main__":
    unittest.main()

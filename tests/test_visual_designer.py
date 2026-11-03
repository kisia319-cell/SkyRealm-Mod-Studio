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

    def test_form_keeps_unknown_custom_json_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            widget = VisualDataDesigner(Path(tmp))
            data = json.loads(widget.raw.toPlainText())
            data["customRuntimeFlag"] = True
            widget.raw.setPlainText(json.dumps(data))
            widget._controls["name"].setText("Edited")
            saved = json.loads(widget.raw.toPlainText())
            self.assertTrue(saved["customRuntimeFlag"])
            self.assertEqual(saved["name"], "Edited")
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

    def test_load_existing_json_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "data" / "items"
            folder.mkdir(parents=True)
            source = folder / "gem.json"
            source.write_text(json.dumps({
                "id": "demo:gem", "name": "Gem", "description": "",
                "stackSize": 5, "rarity": "rare", "sprite": ""
            }), encoding="utf-8")
            widget = VisualDataDesigner(root)
            self.assertTrue(widget.load_data_file(source))
            self.assertEqual(widget.filename.text(), "gem.json")
            self.assertEqual(json.loads(widget.raw.toPlainText())["name"], "Gem")
            widget.close()

    def test_animation_preview_starts_and_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            widget = VisualDataDesigner(Path(tmp))
            widget.kind.setCurrentText("Анимация")
            widget.add_frame()
            widget.frames.item(0, 0).setText("")
            widget.frames.item(0, 1).setText("80")
            widget.start_animation_preview()
            self.assertTrue(widget._preview_timer.isActive())
            widget.stop_animation_preview()
            self.assertFalse(widget._preview_timer.isActive())
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

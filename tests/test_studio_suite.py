import json
import tempfile
import unittest
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from editors.studio_suite import StudioSuiteWidget, _atomic_json, _safe_project_path


class StudioSuiteTests(unittest.TestCase):
    def test_atomic_json_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / ".studio" / "graph.json"
            _atomic_json(target, {"nodes": [{"id": "a"}]})
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"nodes": [{"id": "a"}]})
            self.assertFalse(target.with_name(target.name + ".tmp").exists())

    def test_safe_path_rejects_parent_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                _safe_project_path(Path(folder), "../outside.json")

    def test_safe_path_accepts_project_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(_safe_project_path(root, "assets/frame.png"), (root / "assets" / "frame.png").resolve())


    def test_suite_widget_initializes(self):
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            widget = StudioSuiteWidget(Path(folder))
            self.assertEqual(widget.tabs.count(), 10)
            self.assertIn("Введи название функции", widget.api_output.toPlainText())
            widget.close()
        self.assertIsNotNone(app)


if __name__ == "__main__":
    unittest.main()

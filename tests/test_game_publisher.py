import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.game_publisher import publish_project


class GamePublisherTests(unittest.TestCase):
    def make_project(self, root, language="JavaScript", source=None):
        suffix = ".py" if language == "Python" else ".js"
        root.mkdir(parents=True)
        (root / "scripts").mkdir()
        entry = "scripts/main" + suffix
        if source is None:
            source = (
                "def on_tick(context, state):\n    return {\"state\": state, \"actions\": []}\n"
                if language == "Python"
                else "function onTick(context, state) { return { state, actions: [] }; }\n"
            )
        (root / entry).write_text(source, encoding="utf-8")
        (root / "mod.json").write_text(json.dumps({
            "id": "demo-mod", "name": "Demo Mod", "version": "1.0.0",
            "entry": entry, "language": language, "description": "Test script mod"
        }), encoding="utf-8")
        return root

    def test_publishes_javascript_to_local_skyrealm_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_project(Path(tmp) / "project")
            with patch.dict(os.environ, {"LOCALAPPDATA": str(Path(tmp) / "appdata")}):
                result = publish_project(root)
                data = json.loads(result["path"].read_text(encoding="utf-8"))
            self.assertEqual(result["id"], "demo-mod")
            self.assertEqual(data["format"], "skyrealm-studio-mod")
            self.assertEqual(data["language"], "javascript")
            self.assertIn("function onTick", data["source"])

    def test_publishes_python_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_project(Path(tmp) / "project", language="Python")
            with patch.dict(os.environ, {"LOCALAPPDATA": str(Path(tmp) / "appdata")}):
                result = publish_project(root)
                data = json.loads(result["path"].read_text(encoding="utf-8"))
            self.assertEqual(data["language"], "python")
            self.assertIn("def on_tick", data["source"])

    def test_rejects_script_without_runtime_entry_point(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_project(Path(tmp) / "project", source="const value = 5;\n")
            with patch.dict(os.environ, {"LOCALAPPDATA": str(Path(tmp) / "appdata")}):
                with self.assertRaisesRegex(ValueError, "function onTick"):
                    publish_project(root)


if __name__ == "__main__":
    unittest.main()

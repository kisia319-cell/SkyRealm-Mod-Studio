import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.project_validation import validate_manifest, validate_project


class ProjectValidationTests(unittest.TestCase):
    def make_project(self, root, manifest=None):
        root.mkdir(parents=True, exist_ok=True)
        (root / "scripts").mkdir(exist_ok=True)
        (root / "scripts" / "main.js").write_text("const ok = true;\n", encoding="utf-8")
        data = manifest or {"name": "Demo", "id": "demo.mod", "version": "1.0.0", "entry": "scripts/main.js"}
        (root / "mod.json").write_text(json.dumps(data), encoding="utf-8")
        return root

    def test_valid_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_project(Path(tmp) / "Demo")
            _, errors, warnings = validate_manifest(root)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_non_object_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mod.json").write_text("[]", encoding="utf-8")
            _, errors, _ = validate_manifest(root)
            self.assertTrue(errors)

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_project(Path(tmp) / "Demo", {
                "name": "Demo", "id": "demo", "version": "1.0.0", "entry": "../outside.js"
            })
            _, errors, _ = validate_manifest(root)
            self.assertTrue(any("выходит за пределы" in error for error in errors))

    def test_rejects_non_string_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_project(Path(tmp) / "Demo", {
                "name": "Demo", "id": "demo", "version": "1.0.0", "entry": []
            })
            _, errors, _ = validate_manifest(root)
            self.assertTrue(any("entry" in error for error in errors))

    def test_malformed_dependency_value_returns_validation_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_project(Path(tmp) / "Demo", {
                "name": "Demo", "id": "demo.mod", "version": "1.0.0",
                "entry": "scripts/main.js", "dependencies": [{"invalid": "value"}]
            })
            errors, warnings = validate_project(root)
            self.assertTrue(any("ID" in error for error in errors))
    def test_detects_duplicate_ids_and_missing_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_project(Path(tmp) / "Demo", {
                "name": "Demo", "id": "demo", "version": "1.0.0", "entry": "scripts/main.js",
                "dependencies": ["missing.mod"]
            })
            for name in ("one", "two"):
                child = root / "mods" / name
                child.mkdir(parents=True)
                (child / "mod.json").write_text(json.dumps({"id": "same.mod"}), encoding="utf-8")
            errors, warnings = validate_project(root)
            self.assertTrue(any("Повторяется id" in error for error in errors))
            self.assertTrue(any("missing.mod" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()

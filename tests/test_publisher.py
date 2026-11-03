import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.publisher import prepare_release


class PublisherTests(unittest.TestCase):
    def make_project(self, root):
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "main.js").write_text("void 0;\n", encoding="utf-8")
        (root / "mod.json").write_text(json.dumps({
            "id": "demo.mod", "name": "Demo", "version": "1.0.0",
            "entry": "scripts/main.js"
        }), encoding="utf-8")
        return root

    def test_prepares_archive_manifest_and_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_project(Path(tmp) / "project")
            output = Path(tmp) / "release.zip"
            result = prepare_release(root, output, notes="First release")
            self.assertTrue(result["archive"].is_file())
            self.assertTrue(result["manifest"].is_file())
            self.assertTrue(result["checksum"].is_file())
            data = json.loads(result["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(data["releaseNotes"], "First release")
            self.assertEqual(data["sha256"], result["sha256"])
            self.assertEqual(result["file_count"], 2)

    def test_rejects_output_inside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_project(Path(tmp) / "project")
            with self.assertRaises(ValueError):
                prepare_release(root, root / "release.zip")

    def test_rejects_non_text_release_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_project(Path(tmp) / "project")
            with self.assertRaises(ValueError):
                prepare_release(root, Path(tmp) / "release.zip", game_version=123)
            with self.assertRaises(ValueError):
                prepare_release(root, Path(tmp) / "release.zip", notes=None)

    def test_rejects_invalid_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "mod.json").write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                prepare_release(root, Path(tmp) / "release.zip")


if __name__ == "__main__":
    unittest.main()

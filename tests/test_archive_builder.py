import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.archive_builder import create_project_archive


class ArchiveTests(unittest.TestCase):
    def test_excludes_history_and_private_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            (root / "scripts").mkdir(parents=True)
            (root / ".history").mkdir()
            (root / "scripts" / "main.js").write_text("void 0;", encoding="utf-8")
            (root / ".studio-mods.json").write_text("{}", encoding="utf-8")
            (root / ".history" / "old.bak").write_text("old", encoding="utf-8")
            target = Path(tmp) / "out.zip"
            _, count = create_project_archive(root, target)
            self.assertEqual(count, 1)
            with zipfile.ZipFile(target) as archive:
                self.assertEqual(archive.namelist(), ["scripts/main.js"])
                self.assertIsNone(archive.testzip())


if __name__ == "__main__":
    unittest.main()

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.compatibility import check_compatibility, parse_version


class CompatibilityTests(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(parse_version("v1.2.3"), (1, 2, 3))
        self.assertIsNone(parse_version("latest"))

    def test_minimum_and_maximum_constraints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mod.json").write_text(json.dumps({
                "id": "demo", "name": "Demo", "version": "1.0.0", "entry": "main.js",
                "minGameVersion": "0.20.0", "maxGameVersion": "0.21.0"
            }), encoding="utf-8")
            errors, warnings, info = check_compatibility(root, "0.20.37")
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])
            errors, _, _ = check_compatibility(root, "0.22.0")
            self.assertTrue(any("максимум" in item for item in errors))

    def test_missing_constraints_are_unknown_not_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mod.json").write_text(json.dumps({"id": "demo"}), encoding="utf-8")
            errors, warnings, _ = check_compatibility(root, "0.20.37")
            self.assertEqual(errors, [])
            self.assertTrue(any("не определена" in item for item in warnings))


if __name__ == "__main__":
    unittest.main()

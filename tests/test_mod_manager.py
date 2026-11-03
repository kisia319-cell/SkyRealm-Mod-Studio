import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.mod_manager import discover_mods, resolve_load_order, export_load_order


class ModManagerTests(unittest.TestCase):
    def make_mod(self, root, name, mod_id, dependencies=None, conflicts=None):
        folder = root / "mods" / name
        (folder / "scripts").mkdir(parents=True)
        (folder / "scripts" / "main.js").write_text("void 0;\n", encoding="utf-8")
        data = {"id": mod_id, "name": name, "version": "1.0.0",
                "entry": "scripts/main.js", "dependencies": dependencies or [],
                "conflicts": conflicts or []}
        (folder / "mod.json").write_text(json.dumps(data), encoding="utf-8")

    def test_dependency_order_and_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_mod(root, "A", "mod.a", ["mod.b"])
            self.make_mod(root, "B", "mod.b")
            mods, errors, warnings = discover_mods(root)
            order, errors, warnings = resolve_load_order(mods)
            self.assertEqual(order, ["mod.b", "mod.a"])
            result = json.loads(export_load_order(root, mods, order).read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in result["mods"]], order)

    def test_disabled_dependency_and_cycle_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_mod(root, "A", "mod.a", ["mod.b"])
            self.make_mod(root, "B", "mod.b", ["mod.a"], ["mod.a"])
            mods, _, _ = discover_mods(root, {"mod.b": False})
            _, errors, _ = resolve_load_order(mods)
            self.assertTrue(any("отключена" in error for error in errors))
            mods, _, _ = discover_mods(root)
            _, errors, _ = resolve_load_order(mods)
            self.assertTrue(any("цикл" in error for error in errors))
            self.assertTrue(any("конфликтует" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from core.code_analysis import analyze_file
from main import StudioWindow, ProjectWindow

app = QApplication([])
with tempfile.TemporaryDirectory() as tmp:
    folder = Path(tmp) / "Demo"
    (folder / "scripts").mkdir(parents=True)
    metadata = {"name": "Demo", "id": "demo", "version": "1.0.0",
                "game": "SkyRealm", "entry": "scripts/main.js",
                "language": "JavaScript"}
    (folder / "mod.json").write_text(json.dumps(metadata), encoding="utf-8")
    js = folder / "scripts" / "main.js"
    js.write_text("const ok = true;\n", encoding="utf-8")
    (folder / "README.md").write_text("# Demo", encoding="utf-8")

    assert analyze_file(folder / "test.json", '{"broken": }')
    assert analyze_file(folder / "test.py", "def broken(:\n pass")
    assert analyze_file(folder / "test.js", "function ( {")
    assert not analyze_file(folder / "test.json", '{"ok": true}')
    assert not analyze_file(folder / "test.py", "def ok():\n    return 1")
    assert not analyze_file(folder / "test.js", "const ok = true;")

    home = StudioWindow()
    win = ProjectWindow(folder, home)
    item = win.tree.findItems("main.js", Qt.MatchFlag.MatchRecursive, 0)[0]
    win.open_tree_item(item)
    assert win.current_file == js.resolve()
    win.editor.setPlainText("const updated = 42;")
    deadline = time.time() + 2
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)
    assert js.read_text(encoding="utf-8") == "const updated = 42;"
    assert not win.dirty
    backup = win.backup_path_for(js)
    assert backup.is_file()
    assert "const ok = true" in backup.read_text(encoding="utf-8")
    from PySide6.QtWidgets import QMessageBox
    original_question = QMessageBox.question
    QMessageBox.question = lambda *args, **kwargs: QMessageBox.StandardButton.Yes
    try:
        js.write_text("const damaged = ;", encoding="utf-8")
        win.restore_backup()
    finally:
        QMessageBox.question = original_question
    assert "const ok = true" in js.read_text(encoding="utf-8")
    win.close()
    home.close()

print("STUDIO_CORE_TESTS_OK")


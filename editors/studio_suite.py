"""Additional local-first editors and QA tools for SkyRealm Mod Studio.

These tools author portable JSON assets and inspect project metadata. They do not
pretend to add loaders to the SkyRealm game runtime or provide a hosted marketplace.
"""
import ast
import json
import os
import re
import time
from pathlib import Path

from PySide6.QtCore import Qt, QFileSystemWatcher, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QPlainTextEdit, QLineEdit, QComboBox, QListWidget, QListWidgetItem,
    QTabWidget, QMessageBox, QFileDialog, QSplitter, QInputDialog
)

EXCLUDED = {".git", ".venv", "venv", "__pycache__", "node_modules", "build", "dist", ".backups", ".history"}


def _safe_project_path(root, relative):
    root = Path(root).resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Путь выходит за пределы проекта.") from exc
    if candidate == root:
        raise ValueError("Нужно указать файл внутри проекта.")
    return candidate


def _atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    try:
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


class StudioSuiteWidget(QWidget):
    """A lazy, project-scoped toolbox for authoring and validating mod assets."""
    def __init__(self, project_folder, parent=None):
        super().__init__(parent)
        self.root = Path(project_folder).resolve()
        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(self._directory_changed)
        self.watcher.fileChanged.connect(self._file_changed)
        self._watch_refresh = QTimer(self)
        self._watch_refresh.setSingleShot(True)
        self._watch_refresh.setInterval(250)
        self._watch_refresh.timeout.connect(self._refresh_watched_paths)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Дополнительная мастерская: анимации, миры, визуальная логика, "
            "тесты, зависимости, Hot Reload-наблюдение, плагины и локальный каталог. "
            "Форматы данных требуют соответствующей поддержки в игровом runtime."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._animation_page(), "Анимации")
        self.tabs.addTab(self._world_page(), "Миры")
        self.tabs.addTab(self._node_page(), "Node Editor")
        self.tabs.addTab(self._tests_page(), "Тестирование")
        self.tabs.addTab(self._dependency_page(), "Зависимости")
        self.tabs.addTab(self._hot_reload_page(), "Hot Reload")
        self.tabs.addTab(self._plugins_page(), "Плагины Studio")
        self.tabs.addTab(self._catalog_page(), "Каталог модов")
        self.tabs.addTab(self._assistant_page(), "Помощник кода")
        self.tabs.addTab(self._api_page(), "API Explorer")
        layout.addWidget(self.tabs, 1)

    def _animation_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.anim_id = QLineEdit("my_mod:idle")
        self.anim_target = QComboBox()
        self.anim_target.addItems(["player", "mob", "boss", "npc", "object"])
        self.anim_fps = QLineEdit("12")
        self.anim_loop = QComboBox()
        self.anim_loop.addItems(["Да", "Нет"])
        self.anim_frames = QPlainTextEdit('[{"sprite":"assets/sprites/frame_01.png","duration":1}]')
        self.anim_frames.setMaximumHeight(150)
        form.addRow("ID анимации:", self.anim_id)
        form.addRow("Цель:", self.anim_target)
        form.addRow("FPS:", self.anim_fps)
        form.addRow("Зацикливать:", self.anim_loop)
        form.addRow("Кадры (JSON):", self.anim_frames)
        layout.addLayout(form)
        hint = QLabel("Каждый кадр: объект с sprite и необязательным duration. Проверяется JSON и наличие указанных файлов.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        save = QPushButton("Проверить и сохранить анимацию")
        save.clicked.connect(self._save_animation)
        layout.addWidget(save)
        layout.addStretch(1)
        return page

    def _save_animation(self):
        try:
            fps = int(self.anim_fps.text())
            frames = json.loads(self.anim_frames.toPlainText())
            if not re.fullmatch(r"[a-zA-Z0-9_.:-]{2,128}", self.anim_id.text().strip()):
                raise ValueError("Некорректный ID анимации.")
            if not 1 <= fps <= 120:
                raise ValueError("FPS должен быть от 1 до 120.")
            if not isinstance(frames, list) or not frames:
                raise ValueError("Нужен непустой массив кадров.")
            for frame in frames:
                if not isinstance(frame, dict) or not isinstance(frame.get("sprite"), str):
                    raise ValueError("Каждый кадр должен содержать строковое поле sprite.")
                asset = _safe_project_path(self.root, frame["sprite"])
                if not asset.is_file():
                    raise ValueError(f"Файл кадра не найден: {frame['sprite']}")
                duration = frame.get("duration", 1)
                if not isinstance(duration, (int, float)) or duration <= 0:
                    raise ValueError("duration кадра должен быть положительным числом.")
            data = {"id": self.anim_id.text().strip(), "target": self.anim_target.currentText(),
                    "fps": fps, "loop": self.anim_loop.currentIndex() == 0, "frames": frames}
            _atomic_json(self.root / "assets" / "animations" / (re.sub(r"[^a-zA-Z0-9_.-]", "_", data["id"]) + ".json"), data)
            QMessageBox.information(self, "Анимация сохранена", "JSON-файл анимации сохранён в assets/animations/. Для отображения в игре нужен загрузчик анимаций.")
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Ошибка анимации", str(exc))

    def _world_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.world_name = QLineEdit("Новый биом")
        self.world_id = QLineEdit("my_mod:new_biome")
        self.world_width = QLineEdit("64")
        self.world_height = QLineEdit("64")
        self.world_tile = QComboBox()
        self.world_tile.addItems(["grass", "snow", "sand", "stone", "forest", "water"])
        self.world_spawns = QPlainTextEdit('["my_mod:forest_mob"]')
        self.world_spawns.setMaximumHeight(90)
        form.addRow("Название биома:", self.world_name)
        form.addRow("ID:", self.world_id)
        form.addRow("Ширина карты:", self.world_width)
        form.addRow("Высота карты:", self.world_height)
        form.addRow("Тип поверхности:", self.world_tile)
        form.addRow("Список спавна (JSON):", self.world_spawns)
        layout.addLayout(form)
        save = QPushButton("Проверить и сохранить шаблон мира")
        save.clicked.connect(self._save_world)
        layout.addWidget(save)
        note = QLabel("Создаётся декларативный шаблон биома/мира. Генерация карты и спавн заработают только при поддержке этих полей самой игрой.")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return page

    def _save_world(self):
        try:
            width, height = int(self.world_width.text()), int(self.world_height.text())
            spawns = json.loads(self.world_spawns.toPlainText())
            if not self.world_name.text().strip():
                raise ValueError("Название не может быть пустым.")
            if not re.fullmatch(r"[a-zA-Z0-9_.:-]{2,128}", self.world_id.text().strip()):
                raise ValueError("Некорректный ID.")
            if not (8 <= width <= 4096 and 8 <= height <= 4096):
                raise ValueError("Размеры должны быть от 8 до 4096 блоков.")
            if not isinstance(spawns, list) or any(not isinstance(item, str) for item in spawns):
                raise ValueError("Список спавна должен быть массивом строк.")
            data = {"id": self.world_id.text().strip(), "name": self.world_name.text().strip(),
                    "size": {"width": width, "height": height}, "terrain": self.world_tile.currentText(),
                    "spawns": spawns}
            _atomic_json(self.root / "assets" / "worlds" / (re.sub(r"[^a-zA-Z0-9_.-]", "_", data["id"]) + ".json"), data)
            QMessageBox.information(self, "Шаблон мира сохранён", "Файл сохранён в assets/worlds/. Проверь его в игре после добавления runtime-загрузчика.")
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Ошибка шаблона мира", str(exc))

    def _node_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Визуальная логика хранится как граф узлов JSON. Узлы: event, condition, action, value. Связи задаются парами source → target."))
        split = QSplitter()
        self.node_list = QListWidget()
        self.node_details = QPlainTextEdit()
        self.node_details.setPlainText(json.dumps({
            "nodes": [
                {"id": "start", "type": "event", "name": "onEnemyDefeated", "params": {}},
                {"id": "check", "type": "condition", "name": "enemy.isBoss", "params": {}},
                {"id": "reward", "type": "action", "name": "giveItem", "params": {"item": "my_mod:reward"}}
            ],
            "edges": [{"source": "start", "target": "check"}, {"source": "check", "target": "reward"}]
        }, ensure_ascii=False, indent=2))
        self.node_list.addItems(["Событие", "Условие", "Действие", "Значение"])
        split.addWidget(self.node_list)
        split.addWidget(self.node_details)
        split.setStretchFactor(1, 3)
        layout.addWidget(split, 1)
        row = QHBoxLayout()
        add = QPushButton("Добавить узел")
        add.clicked.connect(self._add_node)
        save = QPushButton("Проверить и сохранить граф")
        save.clicked.connect(self._save_nodes)
        row.addWidget(add)
        row.addStretch()
        row.addWidget(save)
        layout.addLayout(row)
        return page

    def _add_node(self):
        kind, ok = QInputDialog.getItem(self, "Новый узел", "Тип:", ["event", "condition", "action", "value"], 0, False)
        if not ok:
            return
        name, ok = QInputDialog.getText(self, "Новый узел", "Имя события/условия/действия:")
        if not ok or not name.strip():
            return
        try:
            graph = json.loads(self.node_details.toPlainText())
            nodes = graph.setdefault("nodes", [])
            node_id = f"node_{len(nodes) + 1}"
            nodes.append({"id": node_id, "type": kind, "name": name.strip(), "params": {}})
            self.node_details.setPlainText(json.dumps(graph, ensure_ascii=False, indent=2))
        except json.JSONDecodeError as exc:
            QMessageBox.warning(self, "Граф повреждён", str(exc))

    def _save_nodes(self):
        try:
            graph = json.loads(self.node_details.toPlainText())
            if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("edges", []), list):
                raise ValueError("Граф должен содержать массивы nodes и edges.")
            ids = [n.get("id") for n in graph["nodes"] if isinstance(n, dict)]
            if len(ids) != len(graph["nodes"]) or len(ids) != len(set(ids)) or any(not isinstance(i, str) or not i for i in ids):
                raise ValueError("У каждого узла должен быть уникальный строковый id.")
            known = set(ids)
            for edge in graph.get("edges", []):
                if not isinstance(edge, dict) or edge.get("source") not in known or edge.get("target") not in known:
                    raise ValueError("Связь ссылается на неизвестный узел.")
            _atomic_json(self.root / ".studio" / "visual_graph.json", graph)
            QMessageBox.information(self, "Граф сохранён", "Граф сохранён в .studio/visual_graph.json. Для исполнения нужен интерпретатор графов в игре.")
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Ошибка графа", str(exc))

    def _tests_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Безопасная статическая проверка проекта: JSON, Python AST и базовые проверки JavaScript. Код проекта не запускается."))
        self.test_output = QPlainTextEdit()
        self.test_output.setReadOnly(True)
        layout.addWidget(self.test_output, 1)
        run = QPushButton("Запустить статические тесты")
        run.clicked.connect(self._run_static_tests)
        layout.addWidget(run)
        return page

    def _run_static_tests(self):
        checked, issues = 0, []
        for base, dirs, files in os.walk(self.root, followlinks=False):
            current = Path(base)
            dirs[:] = [d for d in dirs if d not in EXCLUDED and not (current / d).is_symlink()]
            for name in files:
                path = current / name
                if path.is_symlink() or path.suffix.lower() not in {".json", ".py", ".js", ".mjs", ".cjs"}:
                    continue
                try:
                    source = path.read_text(encoding="utf-8")
                    checked += 1
                    rel = path.relative_to(self.root)
                    if path.suffix.lower() == ".json":
                        try:
                            json.loads(source)
                        except json.JSONDecodeError as exc:
                            issues.append(f"{rel}:{exc.lineno}:{exc.colno}: JSON: {exc.msg}")
                    elif path.suffix.lower() == ".py":
                        try:
                            ast.parse(source, filename=str(rel))
                        except SyntaxError as exc:
                            issues.append(f"{rel}:{exc.lineno}: Python: {exc.msg}")
                    else:
                        if source.count("{") != source.count("}"):
                            issues.append(f"{rel}: возможно, не совпадает число фигурных скобок")
                except (OSError, UnicodeError) as exc:
                    issues.append(f"{path.name}: {exc}")
        self.test_output.setPlainText(f"Проверено файлов: {checked}\nНайдено замечаний: {len(issues)}\n\n" + ("\n".join(issues) if issues else "Статические проверки пройдены. Это не заменяет запуск в игре."))
    
    def _dependency_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Граф зависимостей строится по dependencies/conflicts в mod.json подпроектов mods/."))
        self.dep_output = QPlainTextEdit()
        self.dep_output.setReadOnly(True)
        layout.addWidget(self.dep_output, 1)
        refresh = QPushButton("Построить граф зависимостей")
        refresh.clicked.connect(self._build_dependency_graph)
        layout.addWidget(refresh)
        return page

    def _build_dependency_graph(self):
        mods_root = self.root / "mods"
        found, lines = {}, []
        if mods_root.is_dir() and not mods_root.is_symlink():
            for manifest in mods_root.glob("*/mod.json"):
                if manifest.is_symlink() or manifest.parent.is_symlink():
                    continue
                try:
                    data = json.loads(manifest.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and isinstance(data.get("id"), str):
                        found[data["id"]] = data
                except (OSError, UnicodeError, json.JSONDecodeError):
                    lines.append(f"Некорректный manifest: {manifest}")
        for mod_id, data in sorted(found.items()):
            deps = data.get("dependencies", [])
            deps = list(deps) if isinstance(deps, (list, dict)) else []
            if not deps:
                lines.append(f"{mod_id}  (нет объявленных зависимостей)")
            for dep in deps:
                lines.append(f"{mod_id}  →  {dep}" + ("" if dep in found else "  [НЕ НАЙДЕН]"))
            conflicts = data.get("conflicts", [])
            conflicts = list(conflicts) if isinstance(conflicts, (list, dict)) else []
            for conflict in conflicts:
                if conflict in found:
                    lines.append(f"{mod_id}  ⚠ конфликт с {conflict}")
        self.dep_output.setPlainText("\n".join(lines) if lines else "Папка mods/ пуста или зависимости не объявлены.")

    def _hot_reload_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Наблюдение за файлами проекта. При изменении Studio обновляет список событий; автоматическая перезагрузка кода в игре возможна только при подключённом runtime bridge."))
        self.watch_output = QPlainTextEdit()
        self.watch_output.setReadOnly(True)
        layout.addWidget(self.watch_output, 1)
        row = QHBoxLayout()
        start = QPushButton("Начать наблюдение")
        start.clicked.connect(self._start_watching)
        stop = QPushButton("Остановить")
        stop.clicked.connect(self._stop_watching)
        row.addWidget(start)
        row.addWidget(stop)
        layout.addLayout(row)
        return page

    def _start_watching(self):
        self._stop_watching()
        dirs = []
        for base, names, _files in os.walk(self.root, followlinks=False):
            current = Path(base)
            names[:] = [n for n in names if n not in EXCLUDED and not (current / n).is_symlink()]
            dirs.append(str(current))
            if len(dirs) >= 500:
                break
        self.watcher.addPaths(dirs)
        self.watch_output.appendPlainText(f"Наблюдение включено: {len(dirs)} папок. Изменения отслеживаются локально.")

    def _stop_watching(self):
        paths = self.watcher.directories() + self.watcher.files()
        if paths:
            self.watcher.removePaths(paths)
        self.watch_output.appendPlainText("Наблюдение остановлено.")

    def _directory_changed(self, path):
        self.watch_output.appendPlainText(f"Изменилась папка: {Path(path).name}")
        self._watch_refresh.start()

    def _file_changed(self, path):
        self.watch_output.appendPlainText(f"Изменён файл: {Path(path).name} — требуется обновить ресурс в runtime bridge.")
        self._watch_refresh.start()

    def _refresh_watched_paths(self):
        existing = set(self.watcher.directories() + self.watcher.files())
        dirs = []
        for base, names, _files in os.walk(self.root, followlinks=False):
            current = Path(base)
            names[:] = [n for n in names if n not in EXCLUDED and not (current / n).is_symlink()]
            if str(current) not in existing:
                dirs.append(str(current))
            if len(dirs) >= 500:
                break
        if dirs:
            self.watcher.addPaths(dirs)

    def _plugins_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Список локальных расширений Studio. Для безопасности читаются только plugin.json; произвольный Python-код плагинов автоматически не запускается."))
        self.plugin_output = QPlainTextEdit()
        self.plugin_output.setReadOnly(True)
        layout.addWidget(self.plugin_output, 1)
        refresh = QPushButton("Обновить список расширений")
        refresh.clicked.connect(self._scan_plugins)
        layout.addWidget(refresh)
        self._scan_plugins()
        return page

    def _scan_plugins(self):
        root = self.root / ".studio" / "plugins"
        rows = []
        if root.is_dir() and not root.is_symlink():
            for manifest in sorted(root.glob("*/plugin.json")):
                try:
                    data = json.loads(manifest.read_text(encoding="utf-8"))
                    if not isinstance(data, dict) or not isinstance(data.get("name"), str):
                        raise ValueError("ожидается объект с name")
                    rows.append(f"{data['name']} — {data.get('version', 'без версии')} [{manifest.parent.name}]")
                except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                    rows.append(f"ОШИБКА {manifest}: {exc}")
        self.plugin_output.setPlainText("\n".join(rows) if rows else "Расширения пока не установлены. Создай .studio/plugins/<id>/plugin.json.")

    def _catalog_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Локальный каталог проектов и модов. Онлайн-каталог, загрузки и публичная статистика требуют отдельного серверного API."))
        self.catalog_list = QListWidget()
        layout.addWidget(self.catalog_list, 1)
        row = QHBoxLayout()
        refresh = QPushButton("Обновить каталог")
        refresh.clicked.connect(self._scan_catalog)
        import_btn = QPushButton("Импортировать ZIP-мод…")
        import_btn.clicked.connect(self._import_catalog_zip)
        row.addWidget(refresh)
        row.addWidget(import_btn)
        layout.addLayout(row)
        self._scan_catalog()
        return page

    def _scan_catalog(self):
        self.catalog_list.clear()
        root = self.root / "mods"
        if root.is_dir() and not root.is_symlink():
            for manifest in sorted(root.glob("*/mod.json")):
                try:
                    data = json.loads(manifest.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        self.catalog_list.addItem(f"{data.get('name', manifest.parent.name)} | {data.get('version', '?')} | {data.get('author', 'неизвестен')}")
                except (OSError, UnicodeError, json.JSONDecodeError):
                    self.catalog_list.addItem(f"Повреждён: {manifest.parent.name}")
        if self.catalog_list.count() == 0:
            self.catalog_list.addItem("Локальные моды не найдены.")

    def _import_catalog_zip(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Выбрать ZIP мода", str(Path.home()), "ZIP (*.zip)")
        if not filename:
            return
        import zipfile
        import tempfile
        import shutil
        try:
            with zipfile.ZipFile(filename) as archive:
                for info in archive.infolist():
                    target = Path(info.filename)
                    if target.is_absolute() or ".." in target.parts or info.is_dir():
                        if target.is_absolute() or ".." in target.parts:
                            raise ValueError("В архиве найден небезопасный путь.")
                temp = Path(tempfile.mkdtemp(prefix="skyrealm-mod-import-"))
                try:
                    archive.extractall(temp)
                    manifests = list(temp.rglob("mod.json"))
                    if len(manifests) != 1 or manifests[0].is_symlink():
                        raise ValueError("В ZIP должен находиться ровно один mod.json.")
                    data = json.loads(manifests[0].read_text(encoding="utf-8"))
                    mod_id = data.get("id") if isinstance(data, dict) else None
                    if not isinstance(mod_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._:-]{1,127}", mod_id):
                        raise ValueError("В mod.json указан некорректный id.")
                    destination = self.root / "mods" / re.sub(r"[^a-zA-Z0-9_.-]", "_", mod_id)
                    if destination.exists():
                        raise ValueError("Мод с таким ID уже установлен.")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(manifests[0].parent, destination)
                finally:
                    shutil.rmtree(temp, ignore_errors=True)
            self._scan_catalog()
            QMessageBox.information(self, "Импорт завершён", "Мод помещён в mods/. Он не активируется в игре автоматически.")
        except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
            QMessageBox.warning(self, "Не удалось импортировать мод", str(exc))

    def _assistant_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Локальный помощник без облачного ИИ: объясняет типовые замечания и подсказывает, какие проверки выполнить."))
        self.assistant_input = QPlainTextEdit()
        self.assistant_input.setPlaceholderText("Вставь текст ошибки или фрагмент кода…")
        layout.addWidget(self.assistant_input, 1)
        self.assistant_output = QPlainTextEdit()
        self.assistant_output.setReadOnly(True)
        layout.addWidget(self.assistant_output, 1)
        run = QPushButton("Проанализировать")
        run.clicked.connect(self._assist)
        layout.addWidget(run)
        return page

    def _assist(self):
        source = self.assistant_input.toPlainText()
        if not source.strip():
            return
        hints = []
        checks = [
            (r"SyntaxError|Unexpected token", "Проверь скобки, запятые, кавычки и синтаксис рядом с указанной строкой."),
            (r"ReferenceError|is not defined", "Проверь написание имени и область видимости переменной."),
            (r"TypeError|undefined|null", "Проверь, что объект существует до обращения к его свойствам."),
            (r"ModuleNotFoundError|ImportError", "Проверь установленную зависимость и активное Python-окружение."),
            (r"JSONDecodeError|JSON", "Проверь запятые, двойные кавычки и отсутствие комментариев в JSON."),
            (r"timeout|freeze|завис", "Ищи блокирующие циклы и тяжёлые операции в главном потоке; переноси анализ в фон."),
        ]
        for pattern, hint in checks:
            if re.search(pattern, source, re.IGNORECASE):
                hints.append("• " + hint)
        if not hints:
            hints.append("• Укажи полный текст ошибки, файл и строку. Сначала воспроизведи проблему на минимальном примере.")
        self.assistant_output.setPlainText("Предварительные рекомендации (эвристика, не генеративная модель):\n\n" + "\n".join(hints))

    def _api_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Каталог API проекта и локальных документаций. Неизвестные игровые функции не выдумываются."))
        self.api_search = QLineEdit()
        self.api_search.setPlaceholderText("Поиск по API / docs / README…")
        self.api_search.textChanged.connect(self._search_api_docs)
        layout.addWidget(self.api_search)
        self.api_output = QPlainTextEdit()
        self.api_output.setReadOnly(True)
        layout.addWidget(self.api_output, 1)
        self._search_api_docs("")
        return page

    def _search_api_docs(self, query):
        terms = query.casefold().strip()
        results = []
        for base, dirs, files in os.walk(self.root, followlinks=False):
            current = Path(base)
            dirs[:] = [d for d in dirs if d not in EXCLUDED and not (current / d).is_symlink()]
            for name in files:
                if name.lower() not in {"api.md", "api.json", "readme.md", "docs.md"}:
                    continue
                path = current / name
                if path.is_symlink():
                    continue
                try:
                    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                        if not terms or terms in line.casefold():
                            results.append(f"{path.relative_to(self.root)}:{number}: {line[:240]}")
                            if len(results) >= 300:
                                break
                except (OSError, UnicodeError):
                    pass
            if len(results) >= 300:
                break
        self.api_output.setPlainText("\n".join(results) if results else "В проекте пока нет локальной документации API по найденному запросу.")

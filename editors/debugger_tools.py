"""Opt-in Node.js debugger and profiler for trusted local project code."""
import json
import queue
import re
import threading
import time
from pathlib import Path

from PySide6.QtCore import Qt, QProcess, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QPlainTextEdit, QCheckBox, QMessageBox
)


def parse_breakpoints(value):
    result = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit() or int(part) < 1:
            raise ValueError("Номера точек останова должны быть положительными номерами строк через запятую.")
        line = int(part)
        if line not in result:
            result.append(line)
    return result


class InspectorWorker(QThread):
    output = Signal(str)

    def __init__(self, websocket_url, script_url, breakpoints, parent=None):
        super().__init__(parent)
        self.websocket_url = websocket_url
        self.script_url = script_url
        self.breakpoints = list(breakpoints)
        self.commands = queue.Queue()
        self.stopping = threading.Event()
        self._next_id = 1
        self.current_call_frame_id = None
        self._scope_requests = {}

    def command(self, method, params=None):
        self.commands.put({"method": method, "params": params or {}})

    def evaluate(self, expression):
        self.commands.put({"method": "__evaluate_watch", "params": {"expression": expression}})

    def stop(self):
        self.stopping.set()

    def run(self):
        try:
            import websocket
            socket = websocket.create_connection(self.websocket_url, timeout=5, suppress_origin=True)
            socket.settimeout(0.25)
        except Exception as exc:
            self.output.emit(f"Не удалось подключиться к Node Inspector: {exc}")
            return
        self.output.emit("Node Inspector подключён.")
        try:
            def send(method, params=None):
                command_id = self._next_id
                socket.send(json.dumps({"id": command_id, "method": method, "params": params or {}}))
                self._next_id += 1
                return command_id

            send("Runtime.enable")
            send("Debugger.enable")
            for line in self.breakpoints:
                send("Debugger.setBreakpointByUrl", {
                    "url": self.script_url,
                    "lineNumber": line - 1
                })
            send("Runtime.runIfWaitingForDebugger")
            while not self.stopping.is_set():
                try:
                    while True:
                        command = self.commands.get_nowait()
                        if command["method"] == "__evaluate_watch":
                            if self.current_call_frame_id:
                                send("Debugger.evaluateOnCallFrame", {
                                    "callFrameId": self.current_call_frame_id,
                                    "expression": command["params"].get("expression", ""),
                                    "returnByValue": True
                                })
                            else:
                                self.output.emit("Сначала останови выполнение на точке останова.")
                        else:
                            send(command["method"], command.get("params"))
                except queue.Empty:
                    pass
                try:
                    raw = socket.recv()
                except Exception as exc:
                    if "timed out" in str(exc).lower() or "timeout" in str(exc).lower():
                        continue
                    if not self.stopping.is_set():
                        self.output.emit(f"Соединение отладчика закрыто: {exc}")
                    break
                if not raw:
                    continue
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                method = message.get("method")
                params = message.get("params", {})
                if method == "Debugger.paused":
                    frames = params.get("callFrames") or []
                    if frames:
                        frame = frames[0]
                        self.current_call_frame_id = frame.get("callFrameId")
                        location = frame.get("location", {})
                        line = location.get("lineNumber", 0) + 1
                        function = frame.get("functionName") or "(анонимная функция)"
                        scopes = frame.get("scopeChain", [])
                        scope_names = ", ".join(scope.get("type", "scope") for scope in scopes)
                        self.output.emit(f"⏸ Пауза: {function}, строка {line}. Области видимости: {scope_names or 'нет данных'}.")
                        for scope in scopes[:8]:
                            object_id = (scope.get("object") or {}).get("objectId")
                            if object_id:
                                request_id = send("Runtime.getProperties", {
                                    "objectId": object_id,
                                    "ownProperties": True,
                                    "generatePreview": True
                                })
                                self._scope_requests[request_id] = scope.get("type", "scope")
                    else:
                        self.output.emit(f"⏸ Выполнение приостановлено: {params.get('reason', 'breakpoint')}")
                elif method == "Debugger.resumed":
                    self.current_call_frame_id = None
                    self.output.emit("▶ Выполнение продолжено.")
                elif method == "Runtime.consoleAPICalled":
                    args = params.get("args", [])
                    values = [arg.get("value", arg.get("description", arg.get("type", "?"))) for arg in args]
                    self.output.emit("[console] " + " ".join(map(str, values)))
                elif method == "Runtime.exceptionThrown":
                    details = params.get("exceptionDetails", {})
                    self.output.emit("[исключение] " + str(details.get("text", "JavaScript exception")))
                elif message.get("id") and message.get("error"):
                    self.output.emit("[Inspector] " + str(message["error"].get("message", "ошибка протокола")))
                elif message.get("id") and "result" in message:
                    result = message["result"]
                    request_id = message["id"]
                    if "breakpointId" in result:
                        self.output.emit("[точка останова] установлена: " + str(result.get("breakpointId")))
                    if request_id in self._scope_requests:
                        scope_name = self._scope_requests.pop(request_id)
                        properties = result.get("result", [])
                        values = []
                        for prop in properties[:30]:
                            value = prop.get("value") or {}
                            rendered = value.get("value", value.get("description", value.get("type", "undefined")))
                            values.append(f"{prop.get('name')} = {rendered}")
                        if values:
                            self.output.emit(f"[переменные {scope_name}] " + "; ".join(values))
                    elif result.get("result") and isinstance(result.get("result"), dict):
                        value = result["result"]
                        self.output.emit("[выражение] " + str(value.get("value", value.get("description", value.get("type", "undefined")))))
        finally:
            try:
                socket.close()
            except Exception:
                pass


class NodeDebuggerWidget(QWidget):
    """The user explicitly opts in before any local JavaScript is executed."""
    def __init__(self, project_folder: Path, parent=None):
        super().__init__(parent)
        self.folder = Path(project_folder).resolve()
        self.debug_process = QProcess(self)
        self.debug_process.setWorkingDirectory(str(self.folder))
        self.debug_process.readyReadStandardError.connect(self._debug_stderr)
        self.debug_process.readyReadStandardOutput.connect(self._debug_stdout)
        self.debug_process.finished.connect(self._debug_finished)
        self.debug_process.errorOccurred.connect(self._process_error)
        self.profiler_process = QProcess(self)
        self.profiler_process.setWorkingDirectory(str(self.folder))
        self.profiler_process.readyReadStandardOutput.connect(lambda: self._append_process_output(self.profiler_process))
        self.profiler_process.readyReadStandardError.connect(lambda: self._append_process_output(self.profiler_process))
        self.profiler_process.finished.connect(self._profiler_finished)
        self.profiler_process.errorOccurred.connect(self._process_error)
        self.worker = None
        self._inspector_url_seen = False
        self._processing_profile = False
        self._profile_started_at = 0.0
        self._profile_log_path = None

        root = QVBoxLayout(self)
        warning = QLabel("ВНИМАНИЕ: отладчик и профилировщик реально запускают выбранный JavaScript-файл через Node.js с правами текущего пользователя. Запускай только код, которому доверяешь. Это не песочница.")
        warning.setWordWrap(True)
        warning.setStyleSheet("color:#ffbf69;font-weight:700")
        root.addWidget(warning)
        row = QHBoxLayout()
        self.file_combo = QComboBox()
        self.breakpoints = QLineEdit()
        self.breakpoints.setPlaceholderText("Точки останова, строки: 12, 25")
        refresh = QPushButton("Обновить файлы")
        refresh.clicked.connect(self.refresh_files)
        row.addWidget(QLabel("Файл:"))
        row.addWidget(self.file_combo, 2)
        row.addWidget(self.breakpoints, 2)
        row.addWidget(refresh)
        root.addLayout(row)
        self.confirm = QCheckBox("Я доверяю выбранному файлу и разрешаю выполнить его на этом компьютере.")
        self.confirm.toggled.connect(self._update_enabled)
        root.addWidget(self.confirm)
        controls = QHBoxLayout()
        self.run_button = QPushButton("Запустить отладчик")
        self.run_button.clicked.connect(self.start_debugger)
        self.continue_button = QPushButton("Продолжить")
        self.continue_button.clicked.connect(lambda: self._send("Debugger.resume"))
        self.over_button = QPushButton("Шаг через")
        self.over_button.clicked.connect(lambda: self._send("Debugger.stepOver"))
        self.into_button = QPushButton("Шаг внутрь")
        self.into_button.clicked.connect(lambda: self._send("Debugger.stepInto"))
        self.out_button = QPushButton("Шаг наружу")
        self.out_button.clicked.connect(lambda: self._send("Debugger.stepOut"))
        self.stop_button = QPushButton("Остановить")
        self.stop_button.clicked.connect(self.stop_debugger)
        self.profile_button = QPushButton("Профилировать")
        self.profile_button.clicked.connect(self.start_profiler)
        for button in (self.run_button, self.continue_button, self.over_button, self.into_button, self.out_button, self.stop_button, self.profile_button):
            controls.addWidget(button)
        root.addLayout(controls)
        watch_row = QHBoxLayout()
        self.watch_expression = QLineEdit()
        self.watch_expression.setPlaceholderText("Выражение для вычисления на паузе, например player.health")
        evaluate = QPushButton("Вычислить")
        evaluate.clicked.connect(self._evaluate_watch)
        watch_row.addWidget(self.watch_expression, 1)
        watch_row.addWidget(evaluate)
        root.addLayout(watch_row)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(5000)
        root.addWidget(self.output, 1)
        self.refresh_files()
        self._update_enabled(False)

    def _append(self, message):
        self.output.appendPlainText(str(message))

    def refresh_files(self):
        current = self.file_combo.currentData()
        self.file_combo.clear()
        excluded = {".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist"}
        for path in sorted(self.folder.rglob("*"), key=lambda item: str(item).casefold()):
            if path.is_symlink() or not path.is_file() or path.suffix.lower() not in {".js", ".mjs", ".cjs"}:
                continue
            if any(part in excluded for part in path.relative_to(self.folder).parts):
                continue
            try:
                path.resolve().relative_to(self.folder)
            except ValueError:
                continue
            self.file_combo.addItem(str(path.relative_to(self.folder)), str(path))
        if current:
            index = self.file_combo.findData(current)
            if index >= 0:
                self.file_combo.setCurrentIndex(index)

    def _update_enabled(self, checked):
        idle = self.debug_process.state() == QProcess.ProcessState.NotRunning and self.profiler_process.state() == QProcess.ProcessState.NotRunning
        self.run_button.setEnabled(bool(checked and idle and self.file_combo.count()))
        self.profile_button.setEnabled(bool(checked and idle and self.file_combo.count()))
        for button in (self.continue_button, self.over_button, self.into_button, self.out_button):
            button.setEnabled(self.worker is not None and self.worker.isRunning())
        self.stop_button.setEnabled(
            self.debug_process.state() != QProcess.ProcessState.NotRunning
            or self.profiler_process.state() != QProcess.ProcessState.NotRunning
        )

    def _selected_file(self):
        value = self.file_combo.currentData()
        if not value:
            return None
        path = Path(value)
        if path.is_symlink() or not path.is_file():
            return None
        try:
            path.resolve().relative_to(self.folder)
        except ValueError:
            return None
        return path

    def start_debugger(self):
        if not self.confirm.isChecked():
            return
        if self.debug_process.state() != QProcess.ProcessState.NotRunning or self.profiler_process.state() != QProcess.ProcessState.NotRunning:
            return
        path = self._selected_file()
        if not path or not path.is_file():
            QMessageBox.warning(self, "Файл не выбран", "Выбери существующий JavaScript-файл.")
            return
        try:
            lines = parse_breakpoints(self.breakpoints.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Точки останова", str(exc))
            return
        self._inspector_url_seen = False
        self._append(f"Запуск отладчика: {path.relative_to(self.folder)}")
        self.debug_process.start("node", ["--inspect-brk=127.0.0.1:0", str(path)])

    def _debug_stderr(self):
        text = bytes(self.debug_process.readAllStandardError()).decode("utf-8", "replace")
        if text:
            self._append(text.rstrip())
        if self.worker is None:
            match = re.search(r"(ws://127\.0\.0\.1:\d+/[A-Za-z0-9_-]+)", text)
            if match:
                path = self._selected_file()
                try:
                    lines = parse_breakpoints(self.breakpoints.text())
                except ValueError:
                    lines = []
                self._inspector_url_seen = True
                self.worker = InspectorWorker(match.group(1), path.as_uri(), lines, self)
                self.worker.output.connect(self._append)
                self.worker.finished.connect(lambda: self._update_enabled(self.confirm.isChecked()))
                self.worker.start()
                self._update_enabled(self.confirm.isChecked())

    def _debug_stdout(self):
        text = bytes(self.debug_process.readAllStandardOutput()).decode("utf-8", "replace")
        if text:
            self._append(text.rstrip())

    def _debug_finished(self, code, _status):
        self._append(f"Процесс отладки завершён, код: {code}")
        if self.worker:
            self.worker.stop()
            self.worker.wait(1500)
            self.worker = None
        self._update_enabled(self.confirm.isChecked())

    def _send(self, method):
        if self.worker and self.worker.isRunning():
            self.worker.command(method)
        else:
            self._append("Отладчик ещё не подключён.")

    def _evaluate_watch(self):
        expression = self.watch_expression.text().strip()
        if not expression:
            return
        if self.worker and self.worker.isRunning():
            self.worker.evaluate(expression)
        else:
            self._append("Отладчик ещё не подключён.")

    def stop_debugger(self):
        if self.worker:
            self.worker.stop()
        if self.debug_process.state() != QProcess.ProcessState.NotRunning:
            self.debug_process.kill()
            self.debug_process.waitForFinished(1500)
        if self.profiler_process.state() != QProcess.ProcessState.NotRunning:
            self.profiler_process.kill()
            self.profiler_process.waitForFinished(1500)
        if self.worker:
            self.worker.wait(1500)
            self.worker = None
        self._processing_profile = False
        self._profile_log_path = None
        self._update_enabled(self.confirm.isChecked())

    def stop_all(self):
        self.stop_debugger()

    def start_profiler(self):
        if not self.confirm.isChecked():
            return
        if self.debug_process.state() != QProcess.ProcessState.NotRunning or self.profiler_process.state() != QProcess.ProcessState.NotRunning:
            return
        path = self._selected_file()
        if not path or not path.is_file():
            QMessageBox.warning(self, "Файл не выбран", "Выбери существующий JavaScript-файл.")
            return
        self._append(f"Профилирование: {path.relative_to(self.folder)}")
        self._processing_profile = False
        self._profile_started_at = time.time()
        self._profile_log_path = None
        self.profiler_process.start("node", ["--prof", str(path)])
        self._update_enabled(self.confirm.isChecked())

    def _append_process_output(self, process):
        stdout = bytes(process.readAllStandardOutput()).decode("utf-8", "replace")
        stderr = bytes(process.readAllStandardError()).decode("utf-8", "replace")
        if stdout:
            self._append(stdout.rstrip())
        if stderr:
            self._append(stderr.rstrip())

    def _profiler_finished(self, code, _status):
        if self._processing_profile:
            self._append(f"Обработка профиля завершена, код: {code}")
            if self._profile_log_path and self._profile_log_path.exists():
                try:
                    self._profile_log_path.unlink()
                except OSError:
                    pass
            self._profile_log_path = None
            self._processing_profile = False
            self._update_enabled(self.confirm.isChecked())
            return
        self._append(f"Профилирование завершено, код: {code}")
        logs = sorted(
            (path for path in self.folder.glob("isolate-*.log") if path.stat().st_mtime >= self._profile_started_at - 1),
            key=lambda path: path.stat().st_mtime,
            reverse=True
        )
        if code == 0 and logs:
            self._profile_log_path = logs[0]
            self._processing_profile = True
            self._append(f"Отчёт V8 создаётся из {logs[0].name}…")
            self.profiler_process.start("node", ["--prof-process", str(logs[0])])
        else:
            self._append("Файл профиля V8 не найден. Проверь, что Node.js поддерживает --prof.")
            self._update_enabled(self.confirm.isChecked())

    def _process_error(self, _error):
        self._append("Не удалось запустить Node.js. Установи Node.js и добавь node в PATH.")
        self._update_enabled(self.confirm.isChecked())

    def closeEvent(self, event):
        self.stop_debugger()
        if self.profiler_process.state() != QProcess.ProcessState.NotRunning:
            self.profiler_process.kill()
            self.profiler_process.waitForFinished(1000)
        super().closeEvent(event)

from PySide6.QtCore import QRect, QSize, Qt, QStringListModel
from PySide6.QtGui import QColor, QFont, QPainter, QSyntaxHighlighter, QTextCharFormat, QKeySequence
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QCompleter, QTextEdit


COMPLETIONS = {
    "JavaScript": ["function", "const", "let", "var", "return", "if", "else",
                   "for", "while", "true", "false", "null", "undefined",
                   "onTick", "onStart", "context", "health", "hunger", "stamina", "level", "xp", "day", "night", "difficulty", "inHouse", "wallet", "heal", "gold", "message", "console", "Math", "JSON", "Array", "Object", "Number", "String", "Promise", "map", "filter", "forEach", "find", "includes"],
    "Python": ["def", "class", "return", "if", "elif", "else", "for", "while",
               "import", "from", "True", "False", "None", "try", "except"],
    "JSON": ["true", "false", "null"],
}


class SyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document, language):
        super().__init__(document)
        self.language = language
        self.rules = []

        def rule(pattern, color, bold=False):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            self.rules.append((pattern, fmt))

        if language == "JavaScript":
            rule(r"\b(function|return|const|let|var|if|else|for|while|new|class|this|throw|try|catch|async|await)\b", "#72a7ff", True)
            rule(r"\b(true|false|null|undefined|NaN)\b", "#c792ea")
            rule(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'|\x60[^\x60]*\x60', "#b5d99c")
            rule(r"//[^\n]*", "#71839f")
        elif language == "Python":
            rule(r"\b(def|class|return|if|elif|else|for|while|in|import|from|as|try|except|with|lambda|pass|break|continue|async|await)\b", "#72a7ff", True)
            rule(r"\b(True|False|None)\b", "#c792ea")
            rule(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', "#b5d99c")
            rule(r"#[^\n]*", "#71839f")
        else:
            rule(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', "#b5d99c")
            rule(r"\b(true|false|null)\b", "#c792ea")
        rule(r"\b\d+(?:\.\d+)?\b", "#f4b86a")

    def highlightBlock(self, text):
        import re
        for pattern, fmt in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, language="JavaScript", parent=None):
        super().__init__(parent)
        self.language = language
        self.setFont(QFont("Consolas", 11))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.setStyleSheet("QPlainTextEdit { background:#0a1222; color:#eaf0ff; border:0; padding:8px; selection-background-color:#244d67; }")
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)
        self.highlighter = SyntaxHighlighter(self.document(), language)
        self.completer = QCompleter(self)
        self.completer.setWidget(self)
        self.completer.setModel(QStringListModel(COMPLETIONS.get(language, []), self.completer))
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.activated.connect(self.insert_completion)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.highlight_current_line()

    def highlight_current_line(self):
        from PySide6.QtGui import QTextFormat
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#111d32"))
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection] if not self.isReadOnly() else [])

    def set_language(self, language):
        self.language = language
        self.highlighter.setDocument(None)
        self.highlighter = SyntaxHighlighter(self.document(), language)
        self.completer.setModel(QStringListModel(COMPLETIONS.get(language, []), self.completer))

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 14 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        rect = self.contentsRect()
        self.line_number_area.setGeometry(QRect(rect.left(), rect.top(), self.line_number_area_width(), rect.height()))

    def paint_line_numbers(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#101a30"))
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#71839f"))
                painter.drawText(0, top, self.line_number_area.width() - 7,
                                 self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight,
                                 str(number + 1))
            block = block.next()
            top = bottom
            if block.isValid():
                bottom = top + int(self.blockBoundingRect(block).height())
            number += 1

    def insert_completion(self, completion):
        cursor = self.textCursor()
        prefix = self.completer.completionPrefix()
        cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.MoveAnchor, len(prefix))
        cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.KeepAnchor, len(prefix))
        cursor.insertText(completion)
        self.setTextCursor(cursor)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.InsertParagraphSeparator):
            cursor = self.textCursor()
            line = cursor.block().text()
            indent = line[:len(line) - len(line.lstrip(" \t"))]
            super().keyPressEvent(event)
            self.textCursor().insertText(indent)
            return
        if event.key() == Qt.Key.Key_Tab and not event.modifiers():
            self.insertPlainText("    ")
            return
        if event.key() == Qt.Key.Key_Space and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            cursor = self.textCursor()
            cursor.select(cursor.SelectionType.WordUnderCursor)
            prefix = cursor.selectedText()
            self.completer.setCompletionPrefix(prefix)
            popup = self.completer.popup()
            self.completer.complete()
            if self.completer.completionCount():
                popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
            return
        super().keyPressEvent(event)
        if (event.text() and (event.text().isalnum() or event.text() == "_")
                and not event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)):
            cursor = self.textCursor()
            cursor.select(cursor.SelectionType.WordUnderCursor)
            prefix = cursor.selectedText()
            if len(prefix) >= 2:
                self.completer.setCompletionPrefix(prefix)
                popup = self.completer.popup()
                self.completer.complete()
                if self.completer.completionCount() == 0:
                    popup.hide()

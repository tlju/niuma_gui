import sys
import re
import json
import traceback
import math
from PyQt5.QtWidgets import QPlainTextEdit, QCompleter, QWidget
from PyQt5.QtGui import (
    QFont, QColor, QSyntaxHighlighter, QTextCharFormat, 
    QTextCursor, QPainter, QTextBlock, QKeySequence
)
from PyQt5.QtCore import Qt, QRegExp, QRect, QEvent, QStringListModel
from core.logger import get_logger

logger = get_logger(__name__)


class BaseHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._formats = {}
        self._rules = []

    def _create_format(self, color, style=""):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if "bold" in style:
            fmt.setFontWeight(QFont.Bold)
        if "italic" in style:
            fmt.setFontItalic(True)
        return fmt

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            index = pattern.indexIn(text)
            while index >= 0:
                length = pattern.matchedLength()
                self.setFormat(index, length, fmt)
                index = pattern.indexIn(text, index + length)


class PythonHighlighter(BaseHighlighter):
    KEYWORDS = [
        "and", "as", "assert", "break", "class", "continue", "def",
        "del", "elif", "else", "except", "finally", "for", "from",
        "global", "if", "import", "in", "is", "lambda", "nonlocal",
        "not", "or", "pass", "raise", "return", "try", "while",
        "with", "yield", "True", "False", "None"
    ]

    BUILTINS = [
        "abs", "all", "any", "bin", "bool", "bytearray", "bytes",
        "callable", "chr", "classmethod", "compile", "complex",
        "delattr", "dict", "dir", "divmod", "enumerate", "eval",
        "exec", "filter", "float", "format", "frozenset", "getattr",
        "globals", "hasattr", "hash", "help", "hex", "id", "input",
        "int", "isinstance", "issubclass", "iter", "len", "list",
        "locals", "map", "max", "memoryview", "min", "next", "object",
        "oct", "open", "ord", "pow", "print", "property", "range",
        "repr", "reversed", "round", "set", "setattr", "slice",
        "sorted", "staticmethod", "str", "sum", "super", "tuple",
        "type", "vars", "zip"
    ]

    def __init__(self, document):
        super().__init__(document)
        self._init_formats()
        self._init_rules()

    def _init_formats(self):
        self._formats["keyword"] = self._create_format("#0000ff", "bold")
        self._formats["builtin"] = self._create_format("#267f99")
        self._formats["comment"] = self._create_format("#008000")
        self._formats["string"] = self._create_format("#a31515")
        self._formats["number"] = self._create_format("#098658")
        self._formats["operator"] = self._create_format("#000000")
        self._formats["class"] = self._create_format("#267f99", "bold")
        self._formats["function"] = self._create_format("#795e26")
        self._formats["decorator"] = self._create_format("#795e26")

    def _init_rules(self):
        keyword_pattern = r"\b(" + "|".join(self.KEYWORDS) + r")\b"
        self._rules.append((QRegExp(keyword_pattern), self._formats["keyword"]))

        builtin_pattern = r"\b(" + "|".join(self.BUILTINS) + r")\b"
        self._rules.append((QRegExp(builtin_pattern), self._formats["builtin"]))

        self._rules.append((QRegExp(r"#[^\n]*"), self._formats["comment"]))
        self._rules.append((QRegExp(r'"[^"\\]*(\\.[^"\\]*)*"'), self._formats["string"]))
        self._rules.append((QRegExp(r"'[^'\\]*(\\.[^'\\]*)*'"), self._formats["string"]))
        self._rules.append((QRegExp(r'\b[0-9]+\.?[0-9]*\b'), self._formats["number"]))
        self._rules.append((QRegExp(r"\bclass\s+(\w+)"), self._formats["class"]))
        self._rules.append((QRegExp(r"\bdef\s+(\w+)"), self._formats["function"]))
        self._rules.append((QRegExp(r"@\w+"), self._formats["decorator"]))


class BashHighlighter(BaseHighlighter):
    KEYWORDS = [
        "if", "then", "else", "elif", "fi", "case", "esac", "for",
        "while", "do", "done", "in", "function", "select", "until",
        "time", "coproc", "declare", "typeset", "export", "readonly",
        "local", "return", "exit", "break", "continue", "eval",
        "exec", "source", "alias", "unalias", "set", "unset", "shift"
    ]

    BUILTINS = [
        "echo", "printf", "read", "cd", "pwd", "pushd", "popd",
        "ls", "cat", "grep", "sed", "awk", "cut", "sort", "uniq",
        "wc", "head", "tail", "find", "xargs", "mkdir", "rmdir",
        "rm", "cp", "mv", "touch", "chmod", "chown", "ln", "tar",
        "gzip", "gunzip", "zip", "unzip", "ssh", "scp", "rsync",
        "curl", "wget", "ping", "netstat", "ps", "kill", "top",
        "df", "du", "free", "mount", "umount", "date", "cal",
        "which", "whereis", "type", "man", "info", "help", "true", "false"
    ]

    def __init__(self, document):
        super().__init__(document)
        self._init_formats()
        self._init_rules()

    def _init_formats(self):
        self._formats["keyword"] = self._create_format("#0000ff", "bold")
        self._formats["builtin"] = self._create_format("#267f99")
        self._formats["comment"] = self._create_format("#008000")
        self._formats["string"] = self._create_format("#a31515")
        self._formats["number"] = self._create_format("#098658")
        self._formats["variable"] = self._create_format("#795e26")
        self._formats["operator"] = self._create_format("#000000")

    def _init_rules(self):
        keyword_pattern = r"\b(" + "|".join(self.KEYWORDS) + r")\b"
        self._rules.append((QRegExp(keyword_pattern), self._formats["keyword"]))

        builtin_pattern = r"\b(" + "|".join(self.BUILTINS) + r")\b"
        self._rules.append((QRegExp(builtin_pattern), self._formats["builtin"]))

        self._rules.append((QRegExp(r"#[^\n]*"), self._formats["comment"]))
        self._rules.append((QRegExp(r'"[^"\\]*(\\.[^"\\]*)*"'), self._formats["string"]))
        self._rules.append((QRegExp(r"'[^']*'"), self._formats["string"]))
        self._rules.append((QRegExp(r'\b[0-9]+\.?[0-9]*\b'), self._formats["number"]))
        self._rules.append((QRegExp(r"\$\{?[a-zA-Z_][a-zA-Z0-9_]*\}?"), self._formats["variable"]))
        self._rules.append((QRegExp(r"\$\([^\)]*\)"), self._formats["variable"]))


class SQLHighlighter(BaseHighlighter):
    KEYWORDS = [
        "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "IN", "LIKE",
        "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE", "CREATE",
        "TABLE", "DROP", "ALTER", "ADD", "COLUMN", "INDEX", "VIEW",
        "JOIN", "INNER", "LEFT", "RIGHT", "OUTER", "ON", "AS", "ORDER",
        "BY", "GROUP", "HAVING", "LIMIT", "OFFSET", "UNION", "ALL",
        "DISTINCT", "COUNT", "SUM", "AVG", "MIN", "MAX", "NULL", "IS",
        "BETWEEN", "EXISTS", "CASE", "WHEN", "THEN", "ELSE", "END",
        "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "CONSTRAINT",
        "UNIQUE", "DEFAULT", "CHECK", "AUTO_INCREMENT", "DATABASE",
        "DATABASES", "USE", "SHOW", "DESCRIBE", "EXPLAIN", "GRANT",
        "REVOKE", "COMMIT", "ROLLBACK", "TRANSACTION", "BEGIN", "TRUNCATE"
    ]

    TYPES = [
        "INT", "INTEGER", "VARCHAR", "CHAR", "TEXT", "BOOLEAN", "BOOL",
        "DATE", "DATETIME", "TIMESTAMP", "TIME", "YEAR", "FLOAT",
        "DOUBLE", "DECIMAL", "NUMERIC", "BIGINT", "SMALLINT", "TINYINT",
        "BLOB", "CLOB", "JSON", "ENUM", "SET"
    ]

    def __init__(self, document):
        super().__init__(document)
        self._init_formats()
        self._init_rules()

    def _init_formats(self):
        self._formats["keyword"] = self._create_format("#0000ff", "bold")
        self._formats["type"] = self._create_format("#267f99")
        self._formats["comment"] = self._create_format("#008000")
        self._formats["string"] = self._create_format("#a31515")
        self._formats["number"] = self._create_format("#098658")
        self._formats["operator"] = self._create_format("#000000")
        self._formats["function"] = self._create_format("#795e26")

    def _init_rules(self):
        keyword_pattern = r"\b(" + "|".join(self.KEYWORDS) + r")\b"
        self._rules.append((QRegExp(keyword_pattern, Qt.CaseInsensitive), self._formats["keyword"]))

        type_pattern = r"\b(" + "|".join(self.TYPES) + r")\b"
        self._rules.append((QRegExp(type_pattern, Qt.CaseInsensitive), self._formats["type"]))

        self._rules.append((QRegExp(r"--[^\n]*"), self._formats["comment"]))
        self._rules.append((QRegExp(r"/\*[^*]*\*+(?:[^/*][^*]*\*+)*/"), self._formats["comment"]))
        self._rules.append((QRegExp(r"'[^']*'"), self._formats["string"]))
        self._rules.append((QRegExp(r'"[^"]*"'), self._formats["string"]))
        self._rules.append((QRegExp(r'\b[0-9]+\.?[0-9]*\b'), self._formats["number"]))
        self._rules.append((QRegExp(r"\b\w+(?=\s*\()"), self._formats["function"]))


class VariableCompleter(QCompleter):
    def __init__(self, parent=None):
        super().__init__([], parent)
        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterMode(Qt.MatchContains)
        self.setCompletionMode(QCompleter.PopupCompletion)
        self._completion_words = []

    def update_completions(self, words):
        self._completion_words = words
        model = QStringListModel(words, self)
        self.setModel(model)

    def get_completions(self):
        return self._completion_words


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QRect(0, 0, self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint_event(event)


class FoldingArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QRect(0, 0, self._editor.folding_area_width(), 0)

    def paintEvent(self, event):
        self._editor.folding_area_paint_event(event)

    def mousePressEvent(self, event):
        self._editor.folding_area_mouse_press_event(event)


class CodeEditor(QPlainTextEdit):
    LEXER_MAP = {
        "python": PythonHighlighter,
        "shell": BashHighlighter,
        "sql": SQLHighlighter,
    }

    FOLD_START_MARKERS = {
        "python": [":", "{"],
        "shell": ["then", "do", "{", "in"],
        "sql": ["BEGIN", "CASE", "IF"],
    }

    FOLD_END_MARKERS = {
        "python": [],
        "shell": ["fi", "done", "esac", "}"],
        "sql": ["END", "END CASE", "END IF"],
    }

    @staticmethod
    def _get_monospace_font(size: int = 10) -> QFont:
        if sys.platform == "win32":
            font = QFont("Consolas", size)
        else:
            font = QFont("DejaVu Sans Mono", size)
            if not font.exactMatch():
                font = QFont("Liberation Mono", size)
            if not font.exactMatch():
                font = QFont("Ubuntu Mono", size)
            if not font.exactMatch():
                font = QFont("Monospace", size)
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        return font

    def __init__(self, parent=None, param_service=None, dict_service=None):
        super().__init__(parent)
        self._param_service = param_service
        self._dict_service = dict_service
        self._current_highlighter = None
        self._current_language = None
        self._completion_words = []
        self._completer = VariableCompleter()
        self._completer.setWidget(self)
        self._completer.activated.connect(self._insert_completion)
        
        self._line_number_area = LineNumberArea(self)
        self._folding_area = FoldingArea(self)
        
        self._folded_blocks = set()
        self._indentation_levels = {}
        
        self._setup_editor()
        self._load_completion_words()
        
        self.blockCountChanged.connect(self._update_viewport_margins)
        self.updateRequest.connect(self._update_line_number_area)
        self.updateRequest.connect(self._update_folding_area)

    def _setup_editor(self):
        self.setObjectName("codeEditor")
        font = self._get_monospace_font(15)
        self.setFont(font)

        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)
        
        self._update_viewport_margins()

    def line_number_area_width(self):
        digits = 1
        max_value = max(1, self.blockCount())
        while max_value >= 10:
            max_value //= 10
            digits += 1
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def folding_area_width(self):
        return 20

    def _update_viewport_margins(self):
        left_margin = self.line_number_area_width() + self.folding_area_width()
        self.setViewportMargins(left_margin, 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self._update_viewport_margins()

    def _update_folding_area(self, rect, dy):
        if dy:
            self._folding_area.scroll(0, dy)
        else:
            self._folding_area.update(0, rect.y(), self._folding_area.width(), rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        line_number_width = self.line_number_area_width()
        folding_width = self.folding_area_width()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), line_number_width, cr.height())
        )
        self._folding_area.setGeometry(
            QRect(cr.left() + line_number_width, cr.top(), folding_width, cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#f5f5f5"))
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        painter.setPen(QColor("#888888"))
        font = self.font()
        painter.setFont(font)
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(
                    0, int(top), self._line_number_area.width() - 5, 
                    self.fontMetrics().height(),
                    Qt.AlignRight, number
                )
            
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def folding_area_paint_event(self, event):
        painter = QPainter(self._folding_area)
        painter.fillRect(event.rect(), QColor("#f5f5f5"))
        
        block = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        painter.setPen(QColor("#888888"))
        font = self.font()
        font.setPointSize(10)
        painter.setFont(font)
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                block_number = block.blockNumber()
                text = block.text()
                
                if self._can_fold_block(block):
                    indicator = "▼" if block_number not in self._folded_blocks else "▶"
                    painter.drawText(
                        2, int(top), self._folding_area.width() - 2,
                        self.fontMetrics().height(),
                        Qt.AlignLeft, indicator
                    )
            
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()

    def folding_area_mouse_press_event(self, event):
        block = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        while block.isValid():
            if block.isVisible():
                if top <= event.y() <= bottom:
                    if self._can_fold_block(block):
                        self._toggle_fold(block)
                    break
            
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()

    def _can_fold_block(self, block):
        if not block.isValid():
            return False
        
        text = block.text().rstrip()
        if not text:
            return False
        
        current_indent = len(text) - len(text.lstrip())
        next_block = block.next()
        
        if not next_block.isValid():
            return False
        
        next_text = next_block.text().rstrip()
        if not next_text:
            next_block = next_block.next()
            if not next_block.isValid():
                return False
            next_text = next_block.text().rstrip()
        
        if not next_text:
            return False
        
        next_indent = len(next_text) - len(next_text.lstrip())
        
        return next_indent > current_indent

    def _toggle_fold(self, block):
        block_number = block.blockNumber()
        
        if block_number in self._folded_blocks:
            self._unfold_block(block)
            self._folded_blocks.discard(block_number)
        else:
            self._fold_block(block)
            self._folded_blocks.add(block_number)
        
        self._folding_area.update()

    def _fold_block(self, start_block):
        start_indent = len(start_block.text()) - len(start_block.text().lstrip())
        block = start_block.next()
        
        while block.isValid():
            text = block.text().rstrip()
            if not text:
                block.setVisible(False)
                block = block.next()
                continue
            
            current_indent = len(text) - len(text.lstrip())
            if current_indent <= start_indent:
                break
            
            block.setVisible(False)
            block = block.next()
        
        self.document().markContentsDirty(start_block.position(), block.position() - start_block.position())

    def _unfold_block(self, start_block):
        start_indent = len(start_block.text()) - len(start_block.text().lstrip())
        block = start_block.next()
        
        while block.isValid():
            text = block.text().rstrip()
            if not text:
                block.setVisible(True)
                block = block.next()
                continue
            
            current_indent = len(text) - len(text.lstrip())
            if current_indent <= start_indent:
                break
            
            block.setVisible(True)
            block = block.next()
        
        self.document().markContentsDirty(start_block.position(), block.position() - start_block.position())

    def _load_completion_words(self):
        logger.debug(f"_load_completion_words called, param_service={self._param_service}, dict_service={self._dict_service}")
        self._completion_words = []
        if self._param_service:
            try:
                params = self._param_service.get_params()
                logger.debug(f"Loaded {len(params) if params else 0} params")
                for param in params:
                    if param.status == 1:
                        self._completion_words.append(f"@param.{param.param_code}")
            except Exception as e:
                logger.warning(f"Failed to load params for completion: {e}")
        
        if self._dict_service:
            try:
                dicts = self._dict_service.get_dicts()
                logger.debug(f"Loaded {len(dicts) if dicts else 0} dicts")
                for d in dicts:
                    self._completion_words.append(f"@dict.{d.code}")
                    items = self._dict_service.get_dict_items(d.code)
                    for item in items:
                        self._completion_words.append(f"@dict.{d.code}.{item.item_name}")
            except Exception as e:
                logger.warning(f"Failed to load dicts for completion: {e}")
        
        self._completer.update_completions(self._completion_words)
        logger.debug(f"Total completion words: {len(self._completion_words)}")

    def _get_word_before_cursor(self):
        cursor = self.textCursor()
        text = cursor.block().text()
        pos_in_block = cursor.positionInBlock()
        start = pos_in_block
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] in "._"):
            start -= 1
        if start > 0 and text[start - 1] == '@':
            start -= 1
        return text[start:pos_in_block], start, pos_in_block

    def _show_completion(self, word):
        logger.debug(f"_show_completion called with word='{word}'")
        if not self._completion_words:
            return
        if word.startswith("@"):
            self._completer.setCompletionPrefix(word)
            cursor_rect = self.cursorRect()
            popup = self._completer.popup()
            popup.setFixedWidth(300)
            popup.setFixedHeight(200)
            point = self.viewport().mapToGlobal(cursor_rect.bottomLeft())
            self._completer.complete()
            popup.move(point)
            popup.show()

    def set_language(self, language: str):
        if self._current_language == language:
            return
        
        self._current_language = language
        
        if self._current_highlighter:
            self._current_highlighter.setDocument(None)
        
        highlighter_class = self.LEXER_MAP.get(language)
        if highlighter_class:
            self._current_highlighter = highlighter_class(self.document())
        else:
            self._current_highlighter = None

    def _insert_completion(self, completion):
        cursor = self.textCursor()
        word, start, end = self._get_word_before_cursor()
        cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len(word))
        cursor.insertText(completion)
        self.setTextCursor(cursor)

    def keyPressEvent(self, event):
        if self._completer.popup().isVisible():
            if event.key() == Qt.Key_Escape:
                self._completer.popup().hide()
                return
            if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab):
                event.ignore()
                self._completer.popup().hide()
                if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab):
                    return
            elif event.key() == Qt.Key_Backtab:
                self._completer.popup().hide()

        if event.key() == Qt.Key_Tab:
            self._handle_tab_key()
            return
        
        if event.key() == Qt.Key_Backtab:
            self._handle_backtab_key()
            return
        
        if event.key() == Qt.Key_Return:
            self._handle_return_key()
            return

        super().keyPressEvent(event)

        text = event.text()
        if text == "@":
            word, start, end = self._get_word_before_cursor()
            self._show_completion(word)
        elif text and (text.isalnum() or text in "._"):
            if self._completer.popup().isVisible():
                word, start, end = self._get_word_before_cursor()
                if word.startswith("@"):
                    self._show_completion(word)

    def _handle_tab_key(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            self._indent_selection()
        else:
            cursor.insertText("    ")

    def _handle_backtab_key(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            self._unindent_selection()
        else:
            line = cursor.block().text()
            pos = cursor.positionInBlock()
            if pos >= 4 and line[pos-4:pos] == "    ":
                cursor.deletePreviousChar()
                cursor.deletePreviousChar()
                cursor.deletePreviousChar()
                cursor.deletePreviousChar()

    def _handle_return_key(self):
        cursor = self.textCursor()
        line = cursor.block().text()
        indent = ""
        for char in line:
            if char == " ":
                indent += " "
            elif char == "\t":
                indent += "\t"
            else:
                break
        
        cursor.insertText("\n" + indent)
        self.setTextCursor(cursor)

    def _indent_selection(self):
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        
        cursor.setPosition(start)
        cursor.beginEditBlock()
        
        while cursor.position() <= end:
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.insertText("    ")
            cursor.movePosition(QTextCursor.NextBlock)
            if cursor.atEnd():
                break
        
        cursor.endEditBlock()

    def _unindent_selection(self):
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        
        cursor.setPosition(start)
        cursor.beginEditBlock()
        
        while cursor.position() <= end:
            cursor.movePosition(QTextCursor.StartOfBlock)
            line = cursor.block().text()
            if line.startswith("    "):
                for _ in range(4):
                    cursor.deleteChar()
            cursor.movePosition(QTextCursor.NextBlock)
            if cursor.atEnd():
                break
        
        cursor.endEditBlock()

    def get_content(self) -> str:
        return self.toPlainText()

    def set_content(self, content: str):
        self.setPlainText(content)

    def set_text(self, text: str):
        self.setPlainText(text)

    def get_text(self) -> str:
        return self.toPlainText()

    def set_read_only(self, read_only: bool):
        self.setReadOnly(read_only)

    def get_language(self) -> str:
        return self._current_language

    def refresh_completions(self):
        self._load_completion_words()

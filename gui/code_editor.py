import sys
import re
import json
import traceback
from PyQt6.QtWidgets import QPlainTextEdit, QCompleter, QWidget
from PyQt6.QtGui import (
    QFont, QColor, QSyntaxHighlighter, QTextCharFormat, 
    QTextCursor, QPainter, QTextBlock, QKeySequence
)
from PyQt6.QtCore import Qt, QRegularExpression, QRect, QEvent
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
            fmt.setFontWeight(QFont.Weight.Bold)
        if "italic" in style:
            fmt.setFontItalic(True)
        return fmt

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            match_iter = pattern.globalMatch(text)
            while match_iter.hasNext():
                match = match_iter.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


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
        self._rules.append((QRegularExpression(keyword_pattern), self._formats["keyword"]))

        builtin_pattern = r"\b(" + "|".join(self.BUILTINS) + r")\b"
        self._rules.append((QRegularExpression(builtin_pattern), self._formats["builtin"]))

        self._rules.append((QRegularExpression(r"#[^\n]*"), self._formats["comment"]))
        self._rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), self._formats["string"]))
        self._rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), self._formats["string"]))
        self._rules.append((QRegularExpression(r'\b[0-9]+\.?[0-9]*\b'), self._formats["number"]))
        self._rules.append((QRegularExpression(r"\bclass\s+(\w+)"), self._formats["class"]))
        self._rules.append((QRegularExpression(r"\bdef\s+(\w+)"), self._formats["function"]))
        self._rules.append((QRegularExpression(r"@\w+"), self._formats["decorator"]))


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
        self._rules.append((QRegularExpression(keyword_pattern), self._formats["keyword"]))

        builtin_pattern = r"\b(" + "|".join(self.BUILTINS) + r")\b"
        self._rules.append((QRegularExpression(builtin_pattern), self._formats["builtin"]))

        self._rules.append((QRegularExpression(r"#[^\n]*"), self._formats["comment"]))
        self._rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), self._formats["string"]))
        self._rules.append((QRegularExpression(r"'[^']*'"), self._formats["string"]))
        self._rules.append((QRegularExpression(r'\b[0-9]+\.?[0-9]*\b'), self._formats["number"]))
        self._rules.append((QRegularExpression(r"\$\{?[a-zA-Z_][a-zA-Z0-9_]*\}?"), self._formats["variable"]))
        self._rules.append((QRegularExpression(r"\$\([^\)]*\)"), self._formats["variable"]))


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
        self._rules.append((QRegularExpression(keyword_pattern, QRegularExpression.PatternOption.CaseInsensitiveOption), self._formats["keyword"]))

        type_pattern = r"\b(" + "|".join(self.TYPES) + r")\b"
        self._rules.append((QRegularExpression(type_pattern, QRegularExpression.PatternOption.CaseInsensitiveOption), self._formats["type"]))

        self._rules.append((QRegularExpression(r"--[^\n]*"), self._formats["comment"]))
        self._rules.append((QRegularExpression(r"/\*[^*]*\*+(?:[^/*][^*]*\*+)*/"), self._formats["comment"]))
        self._rules.append((QRegularExpression(r"'[^']*'"), self._formats["string"]))
        self._rules.append((QRegularExpression(r'"[^"]*"'), self._formats["string"]))
        self._rules.append((QRegularExpression(r'\b[0-9]+\.?[0-9]*\b'), self._formats["number"]))
        self._rules.append((QRegularExpression(r"\b\w+(?=\s*\()"), self._formats["function"]))


class VariableCompleter(QCompleter):
    def __init__(self, parent=None):
        super().__init__([], parent)
        self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterMode(Qt.MatchFlag.MatchContains)
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completion_words = []

    def update_completions(self, words):
        self._completion_words = words
        from PyQt6.QtCore import QStringListModel
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
        font.setStyleHint(QFont.StyleHint.Monospace)
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

        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
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
                    Qt.AlignmentFlag.AlignRight, number
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
                        Qt.AlignmentFlag.AlignLeft, indicator
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
                if top <= event.position().y() <= bottom:
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
        logger.info(f"_load_completion_words called, param_service={self._param_service}, dict_service={self._dict_service}")
        self._completion_words = []
        if self._param_service:
            try:
                params = self._param_service.get_params()
                logger.info(f"Loaded {len(params) if params else 0} params")
                for param in params:
                    if param.status == 1:
                        self._completion_words.append(f"@param.{param.param_code}")
            except Exception as e:
                logger.error(f"Error loading params: {e}\n{traceback.format_exc()}")
        if self._dict_service:
            try:
                dicts = self._dict_service.get_dicts()
                logger.info(f"Loaded {len(dicts) if dicts else 0} dicts")
                for d in dicts:
                    if d.is_active == "Y":
                        self._completion_words.append(f"@dict.{d.code}")
                        items = self._dict_service.get_dict_items(d.code)
                        for item in items:
                            if item.is_active == "Y":
                                self._completion_words.append(f"@dict.{d.code}.{item.item_name}")
            except Exception as e:
                logger.error(f"Error loading dicts: {e}\n{traceback.format_exc()}")
        logger.info(f"Total completion words: {len(self._completion_words)}")
        self._completer.update_completions(self._completion_words)

    def _get_word_before_cursor(self):
        cursor = self.textCursor()
        text = cursor.block().text()
        pos_in_block = cursor.positionInBlock()
        start = pos_in_block
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] in "._@"):
            start -= 1
        return text[start:pos_in_block], start, pos_in_block

    def _show_completion(self, word):
        logger.info(f"_show_completion called with word='{word}', completion_words_count={len(self._completion_words)}")
        if not self._completion_words:
            logger.info("No completion words available, returning")
            return
        if word.startswith("@"):
            self._completer.setCompletionPrefix(word)
            logger.info(f"Set completion prefix to: '{word}'")
            try:
                cursor_rect = self.cursorRect()
                popup = self._completer.popup()
                popup.setFixedWidth(300)
                popup.setFixedHeight(200)
                point = self.viewport().mapToGlobal(cursor_rect.bottomLeft())
                logger.info(f"Popup position: {point}")
                logger.info("Calling completer.complete()")
                self._completer.complete()
                popup.move(point)
                popup.show()
                logger.info("Popup shown successfully")
            except Exception as e:
                logger.error(f"Error showing completion: {e}\n{traceback.format_exc()}")

    def _insert_completion(self, completion):
        cursor = self.textCursor()
        word, start, end = self._get_word_before_cursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, start)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, end - start)
        cursor.insertText(completion)
        self.setTextCursor(cursor)

    def keyPressEvent(self, e):
        logger.info(f"keyPressEvent: key={e.key()}, text='{e.text()}'")
        try:
            if self._completer.popup().isVisible():
                if e.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Enter,
                              Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab):
                    logger.info(f"Forwarding key {e.key()} to completer popup")
                    self._completer.popup().keyPressEvent(e)
                    return
                if e.key() == Qt.Key.Key_Escape:
                    logger.info("Hiding completer popup via Escape")
                    self._completer.popup().hide()
                    return

            if e.key() == Qt.Key.Key_Tab:
                self._handle_tab_key()
                return
            
            if e.key() == Qt.Key.Key_Backtab:
                self._handle_backtab_key()
                return
            
            if e.key() == Qt.Key.Key_Return:
                self._handle_return_key()
                return

            super().keyPressEvent(e)

            text = e.text()
            if text and (text == "@" or text.isalnum() or text in "._"):
                word, start, end = self._get_word_before_cursor()
                logger.info(f"Word before cursor: '{word}'")
                if word.startswith("@"):
                    self._show_completion(word)
        except Exception as e:
            logger.error(f"Error in keyPressEvent: {e}\n{traceback.format_exc()}")

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
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.insertText("    ")
            cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
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
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            line = cursor.block().text()
            if line.startswith("    "):
                for _ in range(4):
                    cursor.deleteChar()
            cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
            if cursor.atEnd():
                break
        
        cursor.endEditBlock()

    def resolve_variables(self, content: str) -> str:
        if not content:
            return content
        pattern = r'@(param|dict)\.([a-zA-Z0-9_]+)(?:\.([a-zA-Z0-9_\u4e00-\u9fa5]+))?'
        def replace_var(match):
            var_type = match.group(1)
            if var_type == "param":
                param_code = match.group(2)
                if self._param_service:
                    param = self._param_service.get_param_by_code(param_code)
                    if param and param.status == 1:
                        return param.param_value or ""
            elif var_type == "dict":
                dict_code = match.group(2)
                item_name = match.group(3)
                if self._dict_service and dict_code:
                    if item_name:
                        item_code = self._dict_service.get_item_code_by_name(dict_code, item_name)
                        if item_code:
                            return item_code
                    else:
                        items = self._dict_service.get_dict_items(dict_code)
                        result = [{"code": item.item_code, "name": item.item_name} for item in items if item.is_active == "Y"]
                        return json.dumps(result, ensure_ascii=False)
            return match.group(0)
        return re.sub(pattern, replace_var, content)

    def set_language(self, language: str):
        self._current_language = language
        highlighter_class = self.LEXER_MAP.get(language)
        if highlighter_class:
            self._current_highlighter = highlighter_class(self.document())
        else:
            self._current_highlighter = None

    def set_read_only(self, read_only: bool):
        self.setReadOnly(read_only)

    def set_text(self, text: str):
        self.setPlainText(text)

    def text(self):
        return self.toPlainText()

    def show_completion_list(self, words, replace_len=0):
        if words:
            self._completer.update_completions(words)

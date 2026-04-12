from PyQt6.Qsci import QsciScintilla, QsciLexerPython, QsciLexerBash, QsciLexerSQL
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt


class CodeEditor(QsciScintilla):
    LEXER_MAP = {
        "python": QsciLexerPython,
        "shell": QsciLexerBash,
        "sql": QsciLexerSQL,
    }

    def __init__(self, parent=None, param_service=None, dict_service=None):
        super().__init__(parent)
        self._param_service = param_service
        self._dict_service = dict_service
        self._setup_editor()
        self._current_lexer = None
        self._completion_words = []
        self._setup_completion()

    def _setup_editor(self):
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        self.setMarginLineNumbers(1, True)
        self.setMarginWidth(1, "00000")
        self.setMarginsForegroundColor(QColor("#888888"))
        self.setMarginsBackgroundColor(QColor("#f5f5f5"))

        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setTabIndents(True)
        self.setAutoIndent(True)

        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#f0f0f0"))

        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setMatchedBraceBackgroundColor(QColor("#c0ffc0"))
        self.setUnmatchedBraceBackgroundColor(QColor("#ffc0c0"))

        self.setWhitespaceVisibility(QsciScintilla.WhitespaceVisibility.WsInvisible)

        self.SendScintilla(QsciScintilla.SCI_SETHSCROLLBAR, 1)

    def _setup_completion(self):
        self.setAutoCompletionThreshold(-1)
        self.setAutoCompletionCaseSensitivity(False)
        self.setAutoCompletionReplaceWord(True)
        self.setAutoCompletionShowSingle(True)
        self._load_completion_words()

    def _load_completion_words(self):
        self._completion_words = []
        if self._param_service:
            try:
                params = self._param_service.get_params()
                for param in params:
                    if param.status == 1:
                        self._completion_words.append(f"@param.{param.param_code}")
            except Exception:
                pass
        if self._dict_service:
            try:
                dicts = self._dict_service.get_dicts()
                for d in dicts:
                    if d.is_active == "Y":
                        self._completion_words.append(f"@dict.{d.code}")
                        items = self._dict_service.get_dict_items(d.code)
                        for item in items:
                            if item.is_active == "Y":
                                self._completion_words.append(f"@dict.{d.code}.{item.item_name}")
            except Exception:
                pass

    def _get_word_before_cursor(self):
        line, index = self.getCursorPosition()
        text = self.text(line)
        start = index
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] in "._@"):
            start -= 1
        return text[start:index], start, index

    def _show_at_completion(self):
        if not self._completion_words:
            return
        word, start, end = self._get_word_before_cursor()
        if word.startswith("@"):
            self.SendScintilla(QsciScintilla.SCI_AUTOCSETFILLUPS, b" \t\n")
            self.SendScintilla(QsciScintilla.SCI_AUTOCSETIGNORECASE, 1)
            filtered = [w for w in self._completion_words if w.startswith(word)] if word != "@" else self._completion_words
            if filtered:
                self.show_completion_list(filtered, len(word))

    def show_completion_list(self, words, replace_len=0):
        if words:
            self.SendScintilla(QsciScintilla.SCI_AUTOCSETSEPARATOR, ord(" "))
            words_str = " ".join(sorted(words))
            self.SendScintilla(QsciScintilla.SCI_AUTOCSHOW, replace_len, words_str.encode("utf-8"))

    def keyPressEvent(self, e):
        from PyQt6.QtCore import Qt
        auto_active = self.SendScintilla(QsciScintilla.SCI_AUTOCACTIVE)
        if auto_active:
            if e.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Enter, 
                          Qt.Key.Key_Return, Qt.Key.Key_Escape, Qt.Key.Key_Tab):
                super().keyPressEvent(e)
                return
        if e.text() == "@":
            super().keyPressEvent(e)
            self._show_at_completion()
        elif e.text().isalnum() or e.text() in "._":
            super().keyPressEvent(e)
            word, start, end = self._get_word_before_cursor()
            if word.startswith("@"):
                self._show_at_completion()
        else:
            super().keyPressEvent(e)

    def resolve_variables(self, content: str) -> str:
        if not content:
            return content
        import re
        import json
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

    def _setup_python_lexer(self, lexer):
        font = QFont("Consolas", 10)
        lexer.setFont(font, QsciLexerPython.Default)
        lexer.setFont(font, QsciLexerPython.Comment)
        lexer.setFont(font, QsciLexerPython.Number)
        lexer.setFont(font, QsciLexerPython.DoubleQuotedString)
        lexer.setFont(font, QsciLexerPython.SingleQuotedString)
        lexer.setFont(font, QsciLexerPython.Keyword)
        lexer.setFont(font, QsciLexerPython.TripleSingleQuotedString)
        lexer.setFont(font, QsciLexerPython.TripleDoubleQuotedString)
        lexer.setFont(font, QsciLexerPython.ClassName)
        lexer.setFont(font, QsciLexerPython.FunctionMethodName)
        lexer.setFont(font, QsciLexerPython.Operator)

        lexer.setColor(QColor("#000000"), QsciLexerPython.Default)
        lexer.setColor(QColor("#008000"), QsciLexerPython.Comment)
        lexer.setColor(QColor("#098658"), QsciLexerPython.Number)
        lexer.setColor(QColor("#a31515"), QsciLexerPython.DoubleQuotedString)
        lexer.setColor(QColor("#a31515"), QsciLexerPython.SingleQuotedString)
        lexer.setColor(QColor("#0000ff"), QsciLexerPython.Keyword)
        lexer.setColor(QColor("#a31515"), QsciLexerPython.TripleSingleQuotedString)
        lexer.setColor(QColor("#a31515"), QsciLexerPython.TripleDoubleQuotedString)
        lexer.setColor(QColor("#267f99"), QsciLexerPython.ClassName)
        lexer.setColor(QColor("#795e26"), QsciLexerPython.FunctionMethodName)
        lexer.setColor(QColor("#000000"), QsciLexerPython.Operator)

        lexer.setPaper(QColor("#ffffff"), QsciLexerPython.Default)

    def _setup_bash_lexer(self, lexer):
        font = QFont("Consolas", 10)
        lexer.setFont(font, QsciLexerBash.Default)
        lexer.setFont(font, QsciLexerBash.Comment)
        lexer.setFont(font, QsciLexerBash.Number)
        lexer.setFont(font, QsciLexerBash.DoubleQuotedString)
        lexer.setFont(font, QsciLexerBash.SingleQuotedString)
        lexer.setFont(font, QsciLexerBash.Keyword)
        lexer.setFont(font, QsciLexerBash.Operator)

        lexer.setColor(QColor("#000000"), QsciLexerBash.Default)
        lexer.setColor(QColor("#008000"), QsciLexerBash.Comment)
        lexer.setColor(QColor("#098658"), QsciLexerBash.Number)
        lexer.setColor(QColor("#a31515"), QsciLexerBash.DoubleQuotedString)
        lexer.setColor(QColor("#a31515"), QsciLexerBash.SingleQuotedString)
        lexer.setColor(QColor("#0000ff"), QsciLexerBash.Keyword)
        lexer.setColor(QColor("#000000"), QsciLexerBash.Operator)

        lexer.setPaper(QColor("#ffffff"), QsciLexerBash.Default)

    def _setup_sql_lexer(self, lexer):
        font = QFont("Consolas", 10)
        lexer.setFont(font, QsciLexerSQL.Default)
        lexer.setFont(font, QsciLexerSQL.Comment)
        lexer.setFont(font, QsciLexerSQL.CommentLine)
        lexer.setFont(font, QsciLexerSQL.Number)
        lexer.setFont(font, QsciLexerSQL.DoubleQuotedString)
        lexer.setFont(font, QsciLexerSQL.SingleQuotedString)
        lexer.setFont(font, QsciLexerSQL.Keyword)
        lexer.setFont(font, QsciLexerSQL.Operator)

        lexer.setColor(QColor("#000000"), QsciLexerSQL.Default)
        lexer.setColor(QColor("#008000"), QsciLexerSQL.Comment)
        lexer.setColor(QColor("#008000"), QsciLexerSQL.CommentLine)
        lexer.setColor(QColor("#098658"), QsciLexerSQL.Number)
        lexer.setColor(QColor("#a31515"), QsciLexerSQL.DoubleQuotedString)
        lexer.setColor(QColor("#a31515"), QsciLexerSQL.SingleQuotedString)
        lexer.setColor(QColor("#0000ff"), QsciLexerSQL.Keyword)
        lexer.setColor(QColor("#000000"), QsciLexerSQL.Operator)

        lexer.setPaper(QColor("#ffffff"), QsciLexerSQL.Default)

    def set_language(self, language: str):
        lexer_class = self.LEXER_MAP.get(language)
        if lexer_class:
            lexer = lexer_class(self)
            if language == "python":
                self._setup_python_lexer(lexer)
            elif language == "shell":
                self._setup_bash_lexer(lexer)
            elif language == "sql":
                self._setup_sql_lexer(lexer)
            self.setLexer(lexer)
            self._current_lexer = lexer
        else:
            self.setLexer(None)
            self._current_lexer = None

    def set_read_only(self, read_only: bool):
        self.setReadOnly(read_only)
        if read_only:
            self.setCaretLineVisible(False)

    def set_text(self, text: str):
        self.setText(text)

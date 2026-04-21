import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import json


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class TestCodeEditorVariableResolution:
    def test_resolve_variables_with_param(self, qapp):
        from gui.code_editor import CodeEditor
        mock_param_service = Mock()
        mock_param = Mock()
        mock_param.param_code = "DB_HOST"
        mock_param.param_value = "localhost"
        mock_param.status = 1
        mock_param_service.get_param_by_code.return_value = mock_param

        editor = CodeEditor(param_service=mock_param_service, dict_service=None)
        result = editor.resolve_variables("connect to @param.DB_HOST")
        assert result == "connect to localhost"

    def test_resolve_variables_with_dict_item_name(self, qapp):
        from gui.code_editor import CodeEditor
        mock_dict_service = Mock()
        mock_dict_service.get_item_code_by_name.return_value = "prod"

        editor = CodeEditor(param_service=None, dict_service=mock_dict_service)
        result = editor.resolve_variables("Environment: @dict.env_type.生产环境")
        assert result == "Environment: prod"

    def test_resolve_variables_with_dict_full_list(self, qapp):
        from gui.code_editor import CodeEditor
        mock_dict_service = Mock()
        mock_item1 = Mock()
        mock_item1.item_code = "prod"
        mock_item1.item_name = "生产环境"
        mock_item1.is_active = "Y"
        mock_item2 = Mock()
        mock_item2.item_code = "dev"
        mock_item2.item_name = "开发环境"
        mock_item2.is_active = "Y"
        mock_dict_service.get_dict_items.return_value = [mock_item1, mock_item2]

        editor = CodeEditor(param_service=None, dict_service=mock_dict_service)
        result = editor.resolve_variables("items = @dict.env_type")
        expected = json.dumps([{"code": "prod", "name": "生产环境"}, {"code": "dev", "name": "开发环境"}], ensure_ascii=False)
        assert result == f"items = {expected}"

    def test_resolve_variables_multiple_params(self, qapp):
        from gui.code_editor import CodeEditor
        mock_param_service = Mock()

        def get_param_by_code(code):
            param = Mock()
            param.status = 1
            if code == "DB_HOST":
                param.param_value = "localhost"
            elif code == "DB_PORT":
                param.param_value = "3306"
            elif code == "DB_USER":
                param.param_value = "root"
            return param

        mock_param_service.get_param_by_code.side_effect = get_param_by_code

        editor = CodeEditor(param_service=mock_param_service, dict_service=None)
        result = editor.resolve_variables(
            "mysql -h @param.DB_HOST -P @param.DB_PORT -u @param.DB_USER"
        )
        assert result == "mysql -h localhost -P 3306 -u root"

    def test_resolve_variables_disabled_param(self, qapp):
        from gui.code_editor import CodeEditor
        mock_param_service = Mock()
        mock_param = Mock()
        mock_param.param_code = "DB_HOST"
        mock_param.param_value = "localhost"
        mock_param.status = 0
        mock_param_service.get_param_by_code.return_value = mock_param

        editor = CodeEditor(param_service=mock_param_service, dict_service=None)
        result = editor.resolve_variables("connect to @param.DB_HOST")
        assert result == "connect to @param.DB_HOST"

    def test_resolve_variables_nonexistent_param(self, qapp):
        from gui.code_editor import CodeEditor
        mock_param_service = Mock()
        mock_param_service.get_param_by_code.return_value = None

        editor = CodeEditor(param_service=mock_param_service, dict_service=None)
        result = editor.resolve_variables("connect to @param.NONEXISTENT")
        assert result == "connect to @param.NONEXISTENT"

    def test_resolve_variables_mixed(self, qapp):
        from gui.code_editor import CodeEditor
        mock_param_service = Mock()
        mock_dict_service = Mock()

        def get_param_by_code(code):
            param = Mock()
            param.status = 1
            param.param_value = "localhost"
            return param

        mock_param_service.get_param_by_code.side_effect = get_param_by_code
        mock_dict_service.get_item_code_by_name.return_value = "prod"

        editor = CodeEditor(param_service=mock_param_service, dict_service=mock_dict_service)
        result = editor.resolve_variables(
            "Host: @param.DB_HOST, Env: @dict.env_type.生产环境"
        )
        assert result == "Host: localhost, Env: prod"

    def test_resolve_variables_empty_content(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor(param_service=None, dict_service=None)
        result = editor.resolve_variables("")
        assert result == ""

    def test_resolve_variables_no_services(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor(param_service=None, dict_service=None)
        result = editor.resolve_variables("echo @param.DB_HOST")
        assert result == "echo @param.DB_HOST"

    def test_resolve_variables_dict_missing_item_name(self, qapp):
        from gui.code_editor import CodeEditor
        mock_dict_service = Mock()
        mock_dict_service.get_item_code_by_name.return_value = None

        editor = CodeEditor(param_service=None, dict_service=mock_dict_service)
        result = editor.resolve_variables("Env: @dict.env_type.不存在")
        assert result == "Env: @dict.env_type.不存在"


class TestCodeEditorCompletionWords:
    def test_load_completion_words_with_params(self, qapp):
        from gui.code_editor import CodeEditor
        mock_param_service = Mock()
        mock_param1 = Mock()
        mock_param1.param_code = "DB_HOST"
        mock_param1.status = 1
        mock_param2 = Mock()
        mock_param2.param_code = "DB_PORT"
        mock_param2.status = 1
        mock_param_service.get_params.return_value = [mock_param1, mock_param2]

        editor = CodeEditor(param_service=mock_param_service, dict_service=None)
        assert "@param.DB_HOST" in editor._completion_words
        assert "@param.DB_PORT" in editor._completion_words

    def test_load_completion_words_filters_disabled_params(self, qapp):
        from gui.code_editor import CodeEditor
        mock_param_service = Mock()
        mock_param1 = Mock()
        mock_param1.param_code = "DB_HOST"
        mock_param1.status = 1
        mock_param2 = Mock()
        mock_param2.param_code = "DB_PORT"
        mock_param2.status = 0
        mock_param_service.get_params.return_value = [mock_param1, mock_param2]

        editor = CodeEditor(param_service=mock_param_service, dict_service=None)
        assert "@param.DB_HOST" in editor._completion_words
        assert "@param.DB_PORT" not in editor._completion_words

    def test_load_completion_words_with_dicts(self, qapp):
        from gui.code_editor import CodeEditor
        mock_dict_service = Mock()
        mock_dict = Mock()
        mock_dict.code = "env_type"
        mock_dict.is_active = "Y"
        mock_item = Mock()
        mock_item.item_code = "prod"
        mock_item.item_name = "生产环境"
        mock_item.is_active = "Y"
        mock_dict_service.get_dicts.return_value = [mock_dict]
        mock_dict_service.get_dict_items.return_value = [mock_item]

        editor = CodeEditor(param_service=None, dict_service=mock_dict_service)
        assert "@dict.env_type" in editor._completion_words
        assert "@dict.env_type.生产环境" in editor._completion_words

    def test_load_completion_words_filters_inactive_dicts(self, qapp):
        from gui.code_editor import CodeEditor
        mock_dict_service = Mock()
        mock_dict = Mock()
        mock_dict.code = "env_type"
        mock_dict.is_active = "N"
        mock_dict_service.get_dicts.return_value = [mock_dict]

        editor = CodeEditor(param_service=None, dict_service=mock_dict_service)
        assert len(editor._completion_words) == 0

    def test_load_completion_words_no_services(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor(param_service=None, dict_service=None)
        assert len(editor._completion_words) == 0


class TestCodeEditorBasicOperations:
    def test_set_text(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_text("Hello World")
        assert editor.text() == "Hello World"

    def test_set_text_empty(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_text("")
        assert editor.text() == ""

    def test_set_text_multiline(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_text("Line 1\nLine 2\nLine 3")
        assert editor.text() == "Line 1\nLine 2\nLine 3"

    def test_set_read_only(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_text("Test")
        editor.set_read_only(True)
        assert editor.isReadOnly() == True

    def test_set_read_only_false(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_read_only(True)
        editor.set_read_only(False)
        assert editor.isReadOnly() == False


class TestCodeEditorLanguageSupport:
    def test_set_language_python(self, qapp):
        from gui.code_editor import CodeEditor, PythonHighlighter
        editor = CodeEditor()
        editor.set_language("python")
        assert editor._current_highlighter is not None
        assert isinstance(editor._current_highlighter, PythonHighlighter)

    def test_set_language_shell(self, qapp):
        from gui.code_editor import CodeEditor, BashHighlighter
        editor = CodeEditor()
        editor.set_language("shell")
        assert editor._current_highlighter is not None
        assert isinstance(editor._current_highlighter, BashHighlighter)

    def test_set_language_sql(self, qapp):
        from gui.code_editor import CodeEditor, SQLHighlighter
        editor = CodeEditor()
        editor.set_language("sql")
        assert editor._current_highlighter is not None
        assert isinstance(editor._current_highlighter, SQLHighlighter)

    def test_set_language_unknown(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_language("unknown")
        assert editor._current_highlighter is None

    def test_set_language_none(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_language("python")
        editor.set_language(None)
        assert editor._current_highlighter is None


class TestCodeEditorLineNumberArea:
    def test_line_number_area_width(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_text("Line 1\nLine 2\nLine 3")
        width = editor.line_number_area_width()
        assert width > 0

    def test_line_number_area_width_increases(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_text("\n".join(["Line"] * 9))
        width_9 = editor.line_number_area_width()
        editor.set_text("\n".join(["Line"] * 10))
        width_10 = editor.line_number_area_width()
        editor.set_text("\n".join(["Line"] * 100))
        width_100 = editor.line_number_area_width()
        assert width_100 > width_10 >= width_9


class TestCodeEditorFolding:
    def test_can_fold_block_simple(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_language("python")
        editor.set_text("def foo():\n    pass\n")
        block = editor.document().firstBlock()
        assert editor._can_fold_block(block) == True

    def test_can_fold_block_no_indent(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_language("python")
        editor.set_text("x = 1\ny = 2\n")
        block = editor.document().firstBlock()
        assert editor._can_fold_block(block) == False

    def test_fold_and_unfold_block(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_language("python")
        editor.set_text("def foo():\n    x = 1\n    y = 2\nz = 3\n")
        
        block = editor.document().firstBlock()
        editor._fold_block(block)
        
        next_block = block.next()
        assert next_block.isVisible() == False
        
        editor._unfold_block(block)
        assert next_block.isVisible() == True

    def test_toggle_fold(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_language("python")
        editor.set_text("def foo():\n    x = 1\n    y = 2\nz = 3\n")
        
        block = editor.document().firstBlock()
        block_number = block.blockNumber()
        
        editor._toggle_fold(block)
        assert block_number in editor._folded_blocks
        
        editor._toggle_fold(block)
        assert block_number not in editor._folded_blocks


class TestCodeEditorIndentation:
    def test_handle_return_key_preserves_indent(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_text("    def foo():")
        
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.EndOfLine)
        editor.setTextCursor(cursor)
        
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QKeyEvent
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        editor.keyPressEvent(event)
        
        lines = editor.text().split("\n")
        assert lines[1].startswith("    ")

    def test_handle_tab_key_inserts_spaces(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_text("")
        
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QKeyEvent
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier)
        editor.keyPressEvent(event)
        
        assert editor.text() == "    "


class TestCodeEditorHighlighters:
    def test_python_highlighter_keywords(self, qapp):
        from gui.code_editor import PythonHighlighter
        from PyQt6.QtGui import QTextDocument
        
        doc = QTextDocument()
        highlighter = PythonHighlighter(doc)
        doc.setPlainText("def foo():\n    pass")
        
        assert highlighter._formats["keyword"] is not None

    def test_bash_highlighter_variables(self, qapp):
        from gui.code_editor import BashHighlighter
        from PyQt6.QtGui import QTextDocument
        
        doc = QTextDocument()
        highlighter = BashHighlighter(doc)
        doc.setPlainText("echo $HOME")
        
        assert highlighter._formats["variable"] is not None

    def test_sql_highlighter_keywords(self, qapp):
        from gui.code_editor import SQLHighlighter
        from PyQt6.QtGui import QTextDocument
        
        doc = QTextDocument()
        highlighter = SQLHighlighter(doc)
        doc.setPlainText("SELECT * FROM users")
        
        assert highlighter._formats["keyword"] is not None


class TestCodeEditorCompleter:
    def test_completer_initialization(self, qapp):
        from gui.code_editor import CodeEditor, VariableCompleter
        editor = CodeEditor()
        
        assert editor._completer is not None
        assert isinstance(editor._completer, VariableCompleter)

    def test_completer_with_params(self, qapp):
        from gui.code_editor import CodeEditor
        mock_param_service = Mock()
        mock_param = Mock()
        mock_param.param_code = "TEST_PARAM"
        mock_param.status = 1
        mock_param_service.get_params.return_value = [mock_param]
        
        editor = CodeEditor(param_service=mock_param_service)
        
        assert "@param.TEST_PARAM" in editor._completer.get_completions()

    def test_show_completion_list_updates_completer(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        
        editor.show_completion_list(["@param.TEST", "@dict.ENV"])
        
        completions = editor._completer.get_completions()
        assert "@param.TEST" in completions
        assert "@dict.ENV" in completions

    def test_get_word_before_cursor(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_text("@param.TEST")
        
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.EndOfLine)
        editor.setTextCursor(cursor)
        
        word, start, end = editor._get_word_before_cursor()
        assert word == "@param.TEST"

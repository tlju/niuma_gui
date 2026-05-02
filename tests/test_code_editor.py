import pytest
from unittest.mock import Mock, MagicMock, patch
import sys


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


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
        mock_item = Mock()
        mock_item.item_code = "prod"
        mock_item.item_name = "生产环境"
        mock_dict_service.get_dicts.return_value = [mock_dict]
        mock_dict_service.get_dict_items.return_value = [mock_item]

        editor = CodeEditor(param_service=None, dict_service=mock_dict_service)
        assert "@dict.env_type" in editor._completion_words

    def test_load_completion_words_no_services(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor(param_service=None, dict_service=None)
        assert len(editor._completion_words) == 0


class TestCodeEditorBasicOperations:
    def test_set_text(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.setPlainText("Hello World")
        assert editor.toPlainText() == "Hello World"

    def test_set_text_empty(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.setPlainText("")
        assert editor.toPlainText() == ""

    def test_set_text_multiline(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.setPlainText("Line 1\nLine 2\nLine 3")
        assert editor.toPlainText() == "Line 1\nLine 2\nLine 3"

    def test_set_read_only(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.setPlainText("Test")
        editor.setReadOnly(True)
        assert editor.isReadOnly() == True

    def test_set_read_only_false(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.setReadOnly(True)
        editor.setReadOnly(False)
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
        editor.setPlainText("Line 1\nLine 2\nLine 3")
        width = editor.line_number_area_width()
        assert width > 0

    def test_line_number_area_width_increases(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.setPlainText("\n".join(["Line"] * 9))
        width_9 = editor.line_number_area_width()
        editor.setPlainText("\n".join(["Line"] * 10))
        width_10 = editor.line_number_area_width()
        editor.setPlainText("\n".join(["Line"] * 100))
        width_100 = editor.line_number_area_width()
        assert width_100 > width_10 >= width_9


class TestCodeEditorFolding:
    def test_can_fold_block_simple(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_language("python")
        editor.setPlainText("def foo():\n    pass\n")
        block = editor.document().firstBlock()
        assert editor._can_fold_block(block) == True

    def test_can_fold_block_no_indent(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_language("python")
        editor.setPlainText("x = 1\ny = 2\n")
        block = editor.document().firstBlock()
        assert editor._can_fold_block(block) == False

    def test_fold_and_unfold_block(self, qapp):
        from gui.code_editor import CodeEditor
        editor = CodeEditor()
        editor.set_language("python")
        editor.setPlainText("def foo():\n    x = 1\n    y = 2\nz = 3\n")
        
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
        editor.setPlainText("def foo():\n    x = 1\n    y = 2\nz = 3\n")
        
        block = editor.document().firstBlock()
        block_number = block.blockNumber()
        
        editor._toggle_fold(block)
        assert block_number in editor._folded_blocks
        
        editor._toggle_fold(block)
        assert block_number not in editor._folded_blocks


class TestCodeEditorHighlighters:
    def test_python_highlighter_keywords(self, qapp):
        from gui.code_editor import PythonHighlighter
        from PyQt5.QtGui import QTextDocument
        
        doc = QTextDocument()
        highlighter = PythonHighlighter(doc)
        doc.setPlainText("def foo():\n    pass")
        
        assert highlighter._formats["keyword"] is not None

    def test_bash_highlighter_variables(self, qapp):
        from gui.code_editor import BashHighlighter
        from PyQt5.QtGui import QTextDocument
        
        doc = QTextDocument()
        highlighter = BashHighlighter(doc)
        doc.setPlainText("echo $HOME")
        
        assert highlighter._formats["variable"] is not None

    def test_sql_highlighter_keywords(self, qapp):
        from gui.code_editor import SQLHighlighter
        from PyQt5.QtGui import QTextDocument
        
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
        
        editor._completer.update_completions(["@param.TEST", "@dict.ENV"])
        
        completions = editor._completer.get_completions()
        assert "@param.TEST" in completions
        assert "@dict.ENV" in completions

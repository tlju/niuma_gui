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

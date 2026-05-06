import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtWidgets import QDialog, QMenu
from core.bastion_manager import BastionManager
from services.bastion_service import ConnectionStatus


class TestBastionManagerServerListStorage:
    """测试堡垒机管理器服务器列表存储功能"""

    @pytest.fixture
    def bastion_manager(self, db_session):
        return BastionManager(db_session)

    def test_initial_server_list_empty(self, bastion_manager):
        """测试初始服务器列表为空"""
        assert bastion_manager._server_list == []
        assert bastion_manager._raw_output == ""

    def test_has_server_list_initially_false(self, bastion_manager):
        """测试初始状态下has_server_list返回False"""
        assert bastion_manager.has_server_list() == False

    def test_get_server_list_initially_empty(self, bastion_manager):
        """测试初始状态下获取服务器列表为空"""
        server_list, raw_output = bastion_manager.get_server_list()
        assert server_list == []
        assert raw_output == ""

    def test_on_server_list_available_stores_data(self, bastion_manager):
        """测试服务器列表可用时存储数据"""
        mock_worker = Mock()
        mock_worker.isRunning.return_value = False
        bastion_manager._auth_worker = mock_worker

        server_list = [
            {"index": "1", "ip": "10.9.50.52", "name": "server1"},
            {"index": "2", "ip": "10.9.50.53", "name": "server2"},
        ]
        raw_output = "目标资产列表\n1: 10.9.50.52 server1\n2: 10.9.50.53 server2"

        bastion_manager._on_server_list_available(server_list, raw_output)

        assert bastion_manager.has_server_list() == True
        stored_list, stored_output = bastion_manager.get_server_list()
        assert len(stored_list) == 2
        assert stored_list[0]["ip"] == "10.9.50.52"
        assert stored_output == raw_output

    def test_disconnect_clears_server_list(self, bastion_manager):
        """测试断开连接时清除服务器列表"""
        bastion_manager._server_list = [{"index": "1", "ip": "10.9.50.52", "name": "server1"}]
        bastion_manager._raw_output = "some output"

        with patch.object(bastion_manager.bastion_service, 'disconnect'):
            bastion_manager.disconnect()

        assert bastion_manager._server_list == []
        assert bastion_manager._raw_output == ""
        assert bastion_manager.has_server_list() == False


class TestMainWindowServerSelectNonModal:
    """测试主窗口服务器选择对话框非模态显示"""

    @pytest.fixture
    def db_with_user(self, db_session):
        from models.user import User
        user = User(username="testuser", hashed_password="hash")
        db_session.add(user)
        db_session.commit()
        return db_session

    @pytest.fixture
    def main_window(self, db_with_user, qapp):
        from gui.main_window import MainWindow
        window = MainWindow(user_id=1, username="testuser", db=db_with_user)
        yield window
        window.close()

    def test_server_select_dialog_reference_initialized(self, main_window):
        """测试服务器选择对话框引用初始化为None"""
        assert hasattr(main_window, '_server_select_dialog')
        assert main_window._server_select_dialog is None

    def test_cleanup_server_select_dialog_when_none(self, main_window):
        """测试清理空的服务器选择对话框不报错"""
        main_window._cleanup_server_select_dialog()
        assert main_window._server_select_dialog is None

    def test_cleanup_server_select_dialog_with_dialog(self, main_window, qapp):
        """测试清理服务器选择对话框"""
        from gui.bastion_dialog import ServerSelectDialog
        dialog = ServerSelectDialog([], "", main_window)
        main_window._server_select_dialog = dialog

        main_window._cleanup_server_select_dialog()

        assert main_window._server_select_dialog is None

    def test_on_server_select_cancelled_does_not_disconnect(self, main_window):
        """测试取消服务器选择不会断开堡垒机连接"""
        with patch.object(main_window.bastion_manager, 'disconnect') as mock_disconnect:
            main_window._on_server_select_cancelled()
            mock_disconnect.assert_not_called()

    def test_on_auth_dialog_finished_always_cleans_up(self, main_window):
        """测试认证对话框结束后总是清理"""
        from gui.bastion_dialog import SecondaryAuthDialog
        auth_info = {"needs_otp": True}
        dialog = SecondaryAuthDialog(auth_info, 0, 5, main_window)
        main_window._auth_dialog = dialog

        main_window._on_auth_dialog_finished(QDialog.Accepted)

        assert main_window._auth_dialog is None

    def test_show_bastion_menu_has_select_server_when_list_available(self, main_window, qapp):
        """测试有服务器列表时堡垒机菜单包含'选择服务器'选项"""
        main_window.bastion_manager._server_list = [
            {"index": "1", "ip": "10.9.50.52", "name": "server1"}
        ]

        with patch.object(main_window.bastion_manager, 'get_status') as mock_status:
            mock_status.return_value = {
                "authenticated": True,
                "host": "10.92.202.40",
                "connected": True
            }

            with patch('PyQt5.QtWidgets.QMenu.exec'):
                menu = QMenu(main_window)
                menu.setObjectName("bastionMenu")

                status = main_window.bastion_manager.get_status()
                if status.get("authenticated"):
                    if main_window.bastion_manager.has_server_list():
                        select_action = menu.addAction("选择服务器")
                    disconnect_action = menu.addAction("断开连接")

                action_texts = [action.text() for action in menu.actions()]
                assert "选择服务器" in action_texts
                assert "断开连接" in action_texts

    def test_show_bastion_menu_no_select_server_when_list_empty(self, main_window, qapp):
        """测试无服务器列表时堡垒机菜单不包含'选择服务器'选项"""
        from PyQt5.QtWidgets import QMenu

        with patch.object(main_window.bastion_manager, 'get_status') as mock_status:
            mock_status.return_value = {
                "authenticated": True,
                "host": "10.92.202.40",
                "connected": True
            }

            menu = QMenu(main_window)
            menu.setObjectName("bastionMenu")

            status = main_window.bastion_manager.get_status()
            if status.get("authenticated"):
                if main_window.bastion_manager.has_server_list():
                    menu.addAction("选择服务器")
                menu.addAction("断开连接")

            action_texts = [action.text() for action in menu.actions()]
            assert "选择服务器" not in action_texts
            assert "断开连接" in action_texts

    def test_close_event_cleans_up_dialogs(self, main_window):
        """测试关闭窗口时清理对话框"""
        from gui.bastion_dialog import SecondaryAuthDialog, ServerSelectDialog

        auth_info = {"needs_otp": True}
        main_window._auth_dialog = SecondaryAuthDialog(auth_info, 0, 5, main_window)
        main_window._server_select_dialog = ServerSelectDialog([], "", main_window)

        with patch.object(main_window.bastion_manager, 'disconnect'):
            with patch('gui.main_window.AuthService'):
                from PyQt5.QtGui import QCloseEvent
                event = QCloseEvent()
                main_window.closeEvent(event)

        assert main_window._auth_dialog is None
        assert main_window._server_select_dialog is None

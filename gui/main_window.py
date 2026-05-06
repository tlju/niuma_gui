from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QMessageBox, QStatusBar, QFrame, QStackedWidget, QApplication,
    QPushButton, QMenu, QAction, QToolButton, QSizePolicy, QDialog
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QColor
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet
from gui.bastion_dialog import SecondaryAuthDialog, BastionConnectingDialog
from services.asset_service import AssetService
from services.script_service import ScriptService
from services.audit_service import AuditService
from services.param_service import ParamService
from services.dict_service import DictService
from services.todo_service import TodoService
from services.document_service import DocumentService
from services.workflow_service import WorkflowService
from services.auth_service import AuthService
from core.bastion_manager import BastionManager
from services.bastion_service import ConnectionStatus
from core.logger import get_logger

logger = get_logger(__name__)


class BastionStatusWidget(QFrame):
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bastionStatusWidget")
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        
        self.status_indicator = QLabel()
        self.status_indicator.setObjectName("bastionStatusIndicator")
        self.status_indicator.setFixedSize(10, 10)
        layout.addWidget(self.status_indicator)
        
        self.status_label = QLabel("堡垒机: 未配置")
        self.status_label.setObjectName("bastionStatusLabel")
        layout.addWidget(self.status_label)
        
        self.set_status(ConnectionStatus.DISCONNECTED.value, "未配置")
    
    def set_status(self, status: str, message: str = ""):
        status_map = {
            ConnectionStatus.DISCONNECTED.value: ("disconnected", "断开"),
            ConnectionStatus.CONNECTING.value: ("connecting", "连接中"),
            ConnectionStatus.CONNECTED.value: ("connected", "已连接"),
            ConnectionStatus.AUTHENTICATING.value: ("authenticating", "认证中"),
            ConnectionStatus.AUTHENTICATED.value: ("authenticated", "已连接"),
            ConnectionStatus.FAILED.value: ("failed", "失败"),
        }
        
        status_key, default_text = status_map.get(status, ("disconnected", status))
        
        self.status_indicator.setProperty("status", status_key)
        self.status_indicator.style().unpolish(self.status_indicator)
        self.status_indicator.style().polish(self.status_indicator)
        
        display_text = f"堡垒机: {message}" if message else f"堡垒机: {default_text}"
        self.status_label.setText(display_text)
        self.status_label.setProperty("status", status_key)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, user_id: int, username: str):
        super().__init__()
        self.current_user_id = user_id
        self.current_username = username
        self.setWindowIcon(icons.app_icon())
        logger.info(f"启动运维辅助工具主窗口，用户: {username}")

        self.asset_service = AssetService()
        self.script_service = ScriptService()
        self.audit_service = AuditService()
        self.param_service = ParamService()
        self.dict_service = DictService()
        self.todo_service = TodoService()
        self.document_service = DocumentService()

        self.bastion_manager = BastionManager()
        self.workflow_service = WorkflowService(self.script_service, self.dict_service, self.param_service, self.bastion_manager)
        self._auth_dialog = None
        self._server_select_dialog = None

        self.init_ui()
        self.status_bar.showMessage(f"当前用户: {username}  |  状态: 在线")
        self.create_main_tabs()

    def init_ui(self):
        self.setWindowTitle("运维辅助工具")
        self.resize(1400, 900)
        self.setMinimumSize(1280, 800)

        load_combined_stylesheet(QApplication.instance(), ["common", "main_window"])

        self.create_menu_bar()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)
        self.central_widget.setLayout(self.layout)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self._create_bastion_status_widget()

        self.stacked_widget = None
        self.assets_page = None
        self.scripts_page = None
        self.audit_page = None
        self.params_page = None
        self.dicts_page = None
        self.todos_page = None
        self.documents_page = None
        self.workflow_page = None

    def _create_bastion_status_widget(self):
        self.bastion_status_widget = BastionStatusWidget()
        self.bastion_status_widget.clicked.connect(self._show_bastion_menu)
        self.status_bar.addPermanentWidget(self.bastion_status_widget)
        
        self.bastion_manager.status_changed.connect(self._on_bastion_status_changed)
        self.bastion_manager.connection_success.connect(self._on_bastion_connected)
        self.bastion_manager.connection_failed.connect(self._on_bastion_failed)
        self.bastion_manager.auth_required.connect(self._on_bastion_auth_required)
        self.bastion_manager.otp_retry_required.connect(self._on_otp_retry_required)
        self.bastion_manager.server_list_available.connect(self._on_server_list_available)

    def _show_bastion_menu(self):
        menu = QMenu(self)
        menu.setObjectName("bastionMenu")
        
        status = self.bastion_manager.get_status()
        
        if status.get("authenticated"):
            if self.bastion_manager.has_server_list():
                select_action = menu.addAction("选择服务器")
                select_action.triggered.connect(self._show_server_select_dialog)
            
            disconnect_action = menu.addAction("断开连接")
            disconnect_action.triggered.connect(self._disconnect_bastion)
            
            info_action = menu.addAction(f"已连接: {status.get('host', '')}")
            info_action.setEnabled(False)
        else:
            connect_action = menu.addAction("连接堡垒机")
            connect_action.triggered.connect(self._manual_connect_bastion)
        
        config_action = menu.addAction("配置堡垒机参数")
        config_action.triggered.connect(lambda: self.switch_page("params"))
        
        menu.exec(self.bastion_status_widget.mapToGlobal(
            self.bastion_status_widget.rect().bottomLeft()
        ))
    
    def _show_server_select_dialog(self):
        server_list, raw_output = self.bastion_manager.get_server_list()
        if not server_list and not raw_output:
            self.bastion_status_widget.set_status(ConnectionStatus.AUTHENTICATED.value, "无可用服务器列表")
            return
        self._on_server_list_available(server_list, raw_output)

    def _init_bastion_auto_login(self):
        if self.bastion_manager.has_bastion_config():
            self.bastion_status_widget.set_status(ConnectionStatus.CONNECTING.value, "连接中...")
            QTimer.singleShot(1000, self._start_bastion_auto_login)

    def _start_bastion_auto_login(self):
        self.bastion_manager.start_auto_login(max_retries=3, retry_interval=5)

    def _manual_connect_bastion(self):
        if not self.bastion_manager.has_bastion_config():
            QMessageBox.warning(self, "提示", "请先在系统参数中配置堡垒机参数\n\n"
                               "需要配置:\n"
                               "- BASTION_HOST: 堡垒机地址\n"
                               "- BASTION_USER: 堡垒机用户名\n"
                               "- BASTION_PASSWORD: 堡垒机密码")
            self.switch_page("params")
            return
        
        self.bastion_manager.start_auto_login(max_retries=3, retry_interval=5)

    def _disconnect_bastion(self):
        reply = QMessageBox.question(
            self, "确认", "确定要断开堡垒机连接吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.bastion_manager.disconnect()
            self.bastion_status_widget.set_status(ConnectionStatus.DISCONNECTED.value, "已断开")

    def _on_bastion_status_changed(self, status: str, message: str):
        self.bastion_status_widget.set_status(status, message)

    def _on_bastion_connected(self):
        self._cleanup_auth_dialog()
        status = self.bastion_manager.get_status()
        self.bastion_status_widget.set_status(
            ConnectionStatus.AUTHENTICATED.value, 
            f"{status.get('host', '')}"
        )
        self.status_bar.showMessage(f"堡垒机连接成功: {status.get('host', '')}", 3000)
        logger.info("堡垒机自动登录成功")

    def _on_bastion_failed(self, error: str):
        self.bastion_status_widget.set_status(ConnectionStatus.FAILED.value, "连接失败")
        logger.error(f"堡垒机连接失败: {error}")

    def _on_bastion_auth_required(self, auth_info: dict, retry_count: int):
        self._cleanup_auth_dialog()
        
        self._auth_dialog = SecondaryAuthDialog(auth_info, retry_count, BastionManager.MAX_AUTH_RETRIES, self)
        self._auth_dialog.auth_submitted.connect(self._on_auth_submitted)
        self._auth_dialog.rejected.connect(self._on_auth_cancelled)
        self._auth_dialog.finished.connect(self._on_auth_dialog_finished)
        self._auth_dialog.show()
    
    def _cleanup_auth_dialog(self):
        if hasattr(self, '_auth_dialog') and self._auth_dialog is not None:
            try:
                self._auth_dialog.auth_submitted.disconnect(self._on_auth_submitted)
                self._auth_dialog.rejected.disconnect(self._on_auth_cancelled)
                self._auth_dialog.finished.disconnect(self._on_auth_dialog_finished)
            except TypeError:
                pass
            self._auth_dialog.deleteLater()
            self._auth_dialog = None
    
    def _on_auth_dialog_finished(self, result):
        self._cleanup_auth_dialog()
    
    def _on_auth_submitted(self, otp_code: str):
        self.bastion_manager.submit_auth(otp_code=otp_code)
    
    def _on_auth_cancelled(self):
        self.bastion_manager.disconnect()
        self.bastion_status_widget.set_status(ConnectionStatus.DISCONNECTED.value, "已取消")
        self._cleanup_auth_dialog()

    def _on_otp_retry_required(self, retry_count: int):
        self._cleanup_auth_dialog()
        
        auth_info = {"needs_otp": True, "retry_error": True}
        self._auth_dialog = SecondaryAuthDialog(auth_info, retry_count, BastionManager.MAX_AUTH_RETRIES, self)
        self._auth_dialog.auth_submitted.connect(self._on_auth_submitted)
        self._auth_dialog.rejected.connect(self._on_auth_cancelled)
        self._auth_dialog.finished.connect(self._on_auth_dialog_finished)
        self._auth_dialog.show()

    def _on_server_list_available(self, server_list: list, raw_output: str):
        self._cleanup_server_select_dialog()
        
        from gui.bastion_dialog import ServerSelectDialog
        self._server_select_dialog = ServerSelectDialog(server_list, raw_output, self)
        self._server_select_dialog.server_selected.connect(self._on_server_selected)
        self._server_select_dialog.rejected.connect(self._on_server_select_cancelled)
        self._server_select_dialog.finished.connect(self._on_server_select_finished)
        self._server_select_dialog.show()
    
    def _cleanup_server_select_dialog(self):
        if hasattr(self, '_server_select_dialog') and self._server_select_dialog is not None:
            try:
                self._server_select_dialog.server_selected.disconnect(self._on_server_selected)
                self._server_select_dialog.rejected.disconnect(self._on_server_select_cancelled)
                self._server_select_dialog.finished.disconnect(self._on_server_select_finished)
            except TypeError:
                pass
            self._server_select_dialog.deleteLater()
            self._server_select_dialog = None
    
    def _on_server_select_finished(self, result):
        self._cleanup_server_select_dialog()
    
    def _on_server_selected(self, menu_selection: str):
        self.bastion_manager.select_server(menu_selection)
    
    def _on_server_select_cancelled(self):
        self.bastion_status_widget.set_status(ConnectionStatus.AUTHENTICATED.value, "已认证-未选择服务器")

    def create_menu_bar(self):
        menubar = self.menuBar()

        system_menu = menubar.addMenu("系统")

        audit_action = QAction("审计日志", self)
        audit_action.setIcon(icons.audit_icon())
        audit_action.setShortcut("Ctrl+U")
        audit_action.triggered.connect(lambda: self.switch_page("audit"))
        system_menu.addAction(audit_action)

        params_action = QAction("系统参数", self)
        params_action.setIcon(icons.settings_icon())
        params_action.setShortcut("Ctrl+P")
        params_action.triggered.connect(lambda: self.switch_page("params"))
        system_menu.addAction(params_action)

        dicts_action = QAction("数据字典", self)
        dicts_action.setIcon(icons.dict_icon())
        dicts_action.setShortcut("Ctrl+D")
        dicts_action.triggered.connect(lambda: self.switch_page("dicts"))
        system_menu.addAction(dicts_action)

        system_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.setIcon(icons.cancel_icon())
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        system_menu.addAction(exit_action)

        function_menu = menubar.addMenu("功能")

        assets_action = QAction("资产管理", self)
        assets_action.setIcon(icons.asset_icon())
        assets_action.setShortcut("Ctrl+A")
        assets_action.triggered.connect(lambda: self.switch_page("assets"))
        function_menu.addAction(assets_action)

        scripts_action = QAction("脚本管理", self)
        scripts_action.setIcon(icons.script_icon())
        scripts_action.setShortcut("Ctrl+S")
        scripts_action.triggered.connect(lambda: self.switch_page("scripts"))
        function_menu.addAction(scripts_action)

        todos_action = QAction("待办事项", self)
        todos_action.setIcon(icons.todo_icon())
        todos_action.setShortcut("Ctrl+T")
        todos_action.triggered.connect(lambda: self.switch_page("todos"))
        function_menu.addAction(todos_action)

        docs_action = QAction("文档管理", self)
        docs_action.setIcon(icons.document_icon())
        docs_action.setShortcut("Ctrl+W")
        docs_action.triggered.connect(lambda: self.switch_page("documents"))
        function_menu.addAction(docs_action)

        workflow_action = QAction("工作流", self)
        workflow_action.setIcon(icons.script_icon())
        workflow_action.setShortcut("Ctrl+L")
        workflow_action.triggered.connect(lambda: self.switch_page("workflow"))
        function_menu.addAction(workflow_action)

        help_menu = menubar.addMenu("帮助")

        help_action = QAction("功能说明", self)
        help_action.setIcon(icons.about_icon())
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

        help_menu.addSeparator()

        about_action = QAction("关于", self)
        about_action.setIcon(icons.about_icon())
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_main_tabs(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.stacked_widget = QStackedWidget()

        from gui.pages.assets_page import AssetsPage
        from gui.pages.scripts_page import ScriptsPage
        from gui.pages.audit_page import AuditPage
        from gui.pages.system_params_page import SystemParamsPage
        from gui.pages.data_dicts_page import DataDictsPage
        from gui.pages.todos_page import TodosPage
        from gui.pages.documents_page import DocumentsPage
        from gui.pages.workflow_page import WorkflowPage

        self.assets_page = AssetsPage(self.asset_service, self.current_user_id, self.dict_service, self.bastion_manager)
        self.scripts_page = ScriptsPage(self.script_service, self.current_user_id, self.dict_service, self.param_service)
        self.audit_page = AuditPage(self.audit_service)
        self.params_page = SystemParamsPage(self.param_service)
        self.dicts_page = DataDictsPage(self.dict_service)
        self.todos_page = TodosPage(self.todo_service, self.current_user_id)
        self.documents_page = DocumentsPage(self.document_service, self.current_user_id)
        self.workflow_page = WorkflowPage(self.workflow_service, self.current_user_id, self.script_service, self.bastion_manager)

        self.stacked_widget.addWidget(self.assets_page)
        self.stacked_widget.addWidget(self.scripts_page)
        self.stacked_widget.addWidget(self.audit_page)
        self.stacked_widget.addWidget(self.params_page)
        self.stacked_widget.addWidget(self.dicts_page)
        self.stacked_widget.addWidget(self.todos_page)
        self.stacked_widget.addWidget(self.documents_page)
        self.stacked_widget.addWidget(self.workflow_page)

        self.layout.addWidget(self.stacked_widget)

    def switch_page(self, page_name: str):
        if not self.stacked_widget:
            return

        page_map = {
            "assets": (self.assets_page, "资产管理"),
            "scripts": (self.scripts_page, "脚本管理"),
            "audit": (self.audit_page, "审计日志"),
            "params": (self.params_page, "系统参数"),
            "dicts": (self.dicts_page, "数据字典"),
            "todos": (self.todos_page, "待办事项"),
            "documents": (self.documents_page, "文档管理"),
            "workflow": (self.workflow_page, "工作流"),
        }

        if page_name in page_map:
            page, name = page_map[page_name]
            self.stacked_widget.setCurrentWidget(page)
            logger.debug(f"切换到{name}页面")

    def show_help(self):
        from gui.pages.help_page import HelpPage
        dialog = HelpPage(self)
        dialog.exec()

    def show_about(self):
        QMessageBox.about(
            self,
            "关于 运维辅助工具",
            "<h3>运维辅助工具 v1.0.0</h3>"
            "<p>纯 Python GUI 版本，基于 PyQt5</p>"
            "<p><b>技术栈:</b> PyQt5, SQLAlchemy, Paramiko</p>"
            "<hr>"
            "<p style='color: #7f8c8d;'>© 2026 Niuma Team</p>"
        )

    def get_bastion_manager(self) -> BastionManager:
        return self.bastion_manager

    def closeEvent(self, event):
        if self.current_user_id:
            auth_service = AuthService()
            auth_service.logout(self.current_user_id, self.current_username)

        self._cleanup_auth_dialog()
        self._cleanup_server_select_dialog()
        self.bastion_manager.disconnect()

        self.current_user_id = None
        self.current_username = None
        self.status_bar.clearMessage()

        if self.stacked_widget:
            self.layout.removeWidget(self.stacked_widget)
            self.stacked_widget.deleteLater()
            self.stacked_widget = None
            self.assets_page = None
            self.scripts_page = None
            self.audit_page = None
            self.params_page = None
            self.dicts_page = None
            self.todos_page = None
            self.documents_page = None
            self.workflow_page = None

        super().closeEvent(event)

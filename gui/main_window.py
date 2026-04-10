from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QMessageBox, QStatusBar, QFrame, QStackedWidget, QApplication
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction
from gui.login_dialog import LoginDialog
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet
from core.database import init_db, get_db_session
from services.auth_service import AuthService
from services.asset_service import AssetService
from services.script_service import ScriptService
from services.audit_service import AuditService
from services.param_service import ParamService
from services.dict_service import DictService
from services.todo_service import TodoService
from services.document_service import DocumentService
from services.workflow_service import WorkflowService
from core.logger import get_logger

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_user_id = None
        self.current_username = None
        self.setWindowIcon(icons.app_icon())
        logger.info("启动运维辅助工具主窗口")

        init_db()

        self.db = get_db_session()
        self.auth_service = AuthService(self.db)
        self.asset_service = AssetService(self.db)
        self.script_service = ScriptService(self.db)
        self.audit_service = AuditService(self.db)
        self.param_service = ParamService(self.db)
        self.dict_service = DictService(self.db)
        self.todo_service = TodoService(self.db)
        self.document_service = DocumentService(self.db)
        self.workflow_service = WorkflowService(self.db)

        self.init_ui()

        self.show_login()

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

        self.stacked_widget = None
        self.assets_page = None
        self.scripts_page = None
        self.audit_page = None
        self.params_page = None
        self.dicts_page = None
        self.todos_page = None
        self.documents_page = None
        self.workflows_page = None

    def create_menu_bar(self):
        menubar = self.menuBar()

        system_menu = menubar.addMenu("系统")

        audit_action = QAction("审计日志", self)
        audit_action.setIcon(icons.audit_icon())
        audit_action.setShortcut("Ctrl+U")
        audit_action.triggered.connect(lambda: self.switch_page("audit"))
        system_menu.addAction(audit_action)

        params_action = QAction("系统参数", self)
        params_action.setShortcut("Ctrl+P")
        params_action.triggered.connect(lambda: self.switch_page("params"))
        system_menu.addAction(params_action)

        dicts_action = QAction("数据字典", self)
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
        todos_action.setShortcut("Ctrl+T")
        todos_action.triggered.connect(lambda: self.switch_page("todos"))
        function_menu.addAction(todos_action)

        docs_action = QAction("文档管理", self)
        docs_action.setShortcut("Ctrl+W")
        docs_action.triggered.connect(lambda: self.switch_page("documents"))
        function_menu.addAction(docs_action)

        workflows_action = QAction("工作流", self)
        workflows_action.setShortcut("Ctrl+F")
        workflows_action.triggered.connect(lambda: self.switch_page("workflows"))
        function_menu.addAction(workflows_action)

        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_login(self):
        login_dialog = LoginDialog(self.auth_service, self)
        login_dialog.login_success.connect(self.on_login_success)
        login_dialog.exec()

        if not self.current_user_id:
            self.close()

    def on_login_success(self, user_id: int, username: str):
        self.current_user_id = user_id
        self.current_username = username
        self.status_bar.showMessage(f"当前用户: {username}  |  状态: 在线")
        self.create_main_tabs()

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
        from gui.pages.workflows_page import WorkflowsPage

        self.assets_page = AssetsPage(self.asset_service, self.current_user_id, self.dict_service)
        self.scripts_page = ScriptsPage(self.script_service, self.current_user_id)
        self.audit_page = AuditPage(self.audit_service)
        self.params_page = SystemParamsPage(self.param_service)
        self.dicts_page = DataDictsPage(self.dict_service)
        self.todos_page = TodosPage(self.todo_service, self.current_user_id)
        self.documents_page = DocumentsPage(self.document_service, self.current_user_id)
        self.workflows_page = WorkflowsPage(self.workflow_service, self.current_user_id)

        self.stacked_widget.addWidget(self.assets_page)
        self.stacked_widget.addWidget(self.scripts_page)
        self.stacked_widget.addWidget(self.audit_page)
        self.stacked_widget.addWidget(self.params_page)
        self.stacked_widget.addWidget(self.dicts_page)
        self.stacked_widget.addWidget(self.todos_page)
        self.stacked_widget.addWidget(self.documents_page)
        self.stacked_widget.addWidget(self.workflows_page)

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
            "workflows": (self.workflows_page, "工作流"),
        }

        if page_name in page_map:
            page, name = page_map[page_name]
            self.stacked_widget.setCurrentWidget(page)
            logger.info(f"切换到{name}页面")

    def show_about(self):
        QMessageBox.about(
            self,
            "关于 运维辅助工具",
            "<h3>运维辅助工具 v1.0.0</h3>"
            "<p>纯 Python GUI 版本，基于 PyQt6</p>"
            "<p><b>技术栈:</b> PyQt6, SQLAlchemy, Paramiko</p>"
            "<hr>"
            "<p style='color: #7f8c8d;'>© 2026 Niuma Team</p>"
        )

    def closeEvent(self, event):
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
            self.workflows_page = None

        if self.db:
            self.db.close()
        super().closeEvent(event)

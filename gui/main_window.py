from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QMessageBox, QStatusBar
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction
from gui.login_dialog import LoginDialog
from gui.icons import icons
from core.database import init_db, get_db_session
from services.auth_service import AuthService
from services.asset_service import AssetService
from services.script_service import ScriptService
from services.audit_service import AuditService
from core.logger import get_logger

logger = get_logger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_user_id = None
        self.current_username = None
        self.setWindowIcon(icons.app_icon())
        logger.info("启动Niuma堡垒机主窗口")

        # 初始化数据库
        init_db()

        # 初始化服务
        self.db = get_db_session()
        self.auth_service = AuthService(self.db)
        self.asset_service = AssetService(self.db)
        self.script_service = ScriptService(self.db)
        self.audit_service = AuditService(self.db)

        self.init_ui()

        # 显示登录对话框
        self.show_login()

    def init_ui(self):
        self.setWindowTitle("Niuma 堡垒机")
        self.resize(1400, 900)

        # 创建菜单栏
        self.create_menu_bar()

        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 初始化为空（登录后创建标签页）
        self.tabs = None

    def create_menu_bar(self):
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        logout_action = QAction("登出", self)
        logout_action.setIcon(icons.user_icon())
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)

        exit_action = QAction("退出", self)
        exit_action.setIcon(icons.cancel_icon())
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_login(self):
        login_dialog = LoginDialog(self.auth_service, self)
        login_dialog.login_success.connect(self.on_login_success)
        login_dialog.exec()

        if not self.current_user_id:
            # 登录失败或取消，关闭应用
            self.close()

    def on_login_success(self, user_id: int, username: str):
        self.current_user = user_id
        self.current_username = username
        self.status_bar.showMessage(f"欢迎, {username}")
        self.create_main_tabs()

    def create_main_tabs(self):
        # 清除现有内容
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 创建标签页
        self.tabs = QTabWidget()

        # 添加各功能模块页面
        from gui.pages.assets_page import AssetsPage
        from gui.pages.scripts_page import ScriptsPage
        from gui.pages.audit_page import AuditPage

        self.assets_page = AssetsPage(self.asset_service, self.current_user_id)
        self.scripts_page = ScriptsPage(self.script_service, self.current_user_id)
        self.audit_page = AuditPage(self.audit_service)

        self.tabs.addTab(self.assets_page, icons.asset_icon(), "资产管理")
        self.tabs.addTab(self.scripts_page, icons.script_icon(), "脚本管理")
        self.tabs.addTab(self.audit_page, icons.audit_icon(), "审计日志")

        self.layout.addWidget(self.tabs)

    def logout(self):
        self.current_user_id = None
        self.current_username = None
        self.status_bar.clearMessage()

        # 清除标签页
        if self.tabs:
            self.layout.removeWidget(self.tabs)
            self.tabs.deleteLater()
            self.tabs = None

        self.show_login()

    def show_about(self):
        QMessageBox.about(
            self,
            "关于 Niuma 堡垒机",
            "牛马运维辅助系统 v2.0.0\n"
            "纯 Python GUI 版本，基于 PyQt6\n\n"
            "技术栈: PyQt6, SQLAlchemy, Paramiko"
        )

    def closeEvent(self, event):
        # 清理数据库会话
        if self.db:
            self.db.close()
        super().closeEvent(event)

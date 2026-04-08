from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIntValidator
from gui.icons import icons
from core.logger import get_logger

logger = get_logger(__name__)

class LoginDialog(QDialog):
    login_success = pyqtSignal(int, str)  # user_id, username

    def __init__(self, auth_service, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.user_id = None
        self.username = None
        self.setWindowIcon(icons.user_icon())
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("登录 - Niuma 堡垒机")
        self.setFixedSize(400, 250)

        layout = QVBoxLayout()

        # 标题
        title_label = QLabel("牛马运维辅助系统")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title_label)

        # 用户名
        layout.addWidget(QLabel("用户名:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        layout.addWidget(self.username_input)

        # 密码
        layout.addWidget(QLabel("密码:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        # 登录按钮
        self.login_btn = QPushButton("登录")
        self.login_btn.setIcon(icons.ok_icon())
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)

        # 注册按钮
        self.register_btn = QPushButton("注册")
        self.register_btn.setIcon(icons.add_icon())
        self.register_btn.clicked.connect(self.handle_register)
        layout.addWidget(self.register_btn)

        self.setLayout(layout)

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码")
            return

        user = self.auth_service.authenticate(username, password)
        if user:
            self.user_id = user.id
            self.username = username
            self.login_success.emit(user.id, username)
            self.accept()
        else:
            QMessageBox.warning(self, "错误", "用户名或密码错误")

    def handle_register(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "提示", "密码至少6位")
            return

        user_id = self.auth_service.register(username, password, username)
        if user_id:
            QMessageBox.information(self, "成功", "注册成功，请登录")
        else:
            QMessageBox.warning(self, "错误", "用户名已存在")

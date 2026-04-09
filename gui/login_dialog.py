from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QFrame, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
from gui.icons import icons
from core.logger import get_logger

logger = get_logger(__name__)


class LoginDialog(QDialog):
    login_success = pyqtSignal(int, str)

    def __init__(self, auth_service, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.user_id = None
        self.username = None
        self.setWindowIcon(icons.user_icon())
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("登录 - 运维辅助工具")
        self.setFixedSize(420, 380)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(120)
        header.setStyleSheet("""
            QFrame#header {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1abc9c, stop:1 #3498db);
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel("运维辅助工具")
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet("""
            QLabel#titleLabel {
                font-size: 28px;
                font-weight: bold;
                color: white;
                background: transparent;
            }
        """)
        header_layout.addWidget(title_label)

        subtitle_label = QLabel("运维辅助工具")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setStyleSheet("""
            QLabel#subtitleLabel {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.8);
                background: transparent;
                margin-top: 5px;
            }
        """)
        header_layout.addWidget(subtitle_label)

        main_layout.addWidget(header)

        form_frame = QFrame()
        form_frame.setStyleSheet("QFrame { background-color: white; }")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(40, 30, 40, 30)

        username_label = QLabel("用户名")
        username_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        form_layout.addWidget(username_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setMinimumHeight(42)
        form_layout.addWidget(self.username_input)

        password_label = QLabel("密码")
        password_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        form_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(42)
        self.password_input.returnPressed.connect(self.handle_login)
        form_layout.addWidget(self.password_input)

        form_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.login_btn = QPushButton("登 录")
        self.login_btn.setObjectName("loginBtn")
        self.login_btn.setMinimumHeight(48)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton#loginBtn {
                background-color: #1abc9c;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton#loginBtn:hover {
                background-color: #16a085;
            }
            QPushButton#loginBtn:pressed {
                background-color: #14967a;
            }
        """)
        self.login_btn.clicked.connect(self.handle_login)
        form_layout.addWidget(self.login_btn)

        main_layout.addWidget(form_frame)
        self.setLayout(main_layout)

    def handle_login(self):
        username = self.username_input.text().strip()
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
            self.password_input.clear()
            self.password_input.setFocus()

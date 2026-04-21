from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QSpacerItem, QSizePolicy,
    QApplication, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QRegularExpression
from PyQt6.QtGui import QFont, QRegularExpressionValidator
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet
from core.logger import get_logger

logger = get_logger(__name__)


class SecondaryAuthDialog(QDialog):
    auth_submitted = pyqtSignal(str)
    
    def __init__(self, auth_info: dict = None, retry_count: int = 0, max_retries: int = 5, parent=None):
        super().__init__(parent)
        self.auth_info = auth_info or {}
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.setWindowIcon(icons.settings_icon())
        self.init_ui()
        
    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "bastion_dialog"])
        
        self.setWindowTitle("堡垒机二次认证")
        self.setFixedSize(420, 280)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        header = QFrame()
        header.setObjectName("authHeader")
        header.setFixedHeight(80)
        header_layout = QVBoxLayout(header)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_label = QLabel("堡垒机二次认证")
        title_label.setObjectName("authTitle")
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel("请输入6位数字动态口令")
        subtitle_label.setObjectName("authSubtitle")
        header_layout.addWidget(subtitle_label)
        
        main_layout.addWidget(header)
        
        form_frame = QFrame()
        form_frame.setObjectName("authFormFrame")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(30, 25, 30, 25)
        
        if self.retry_count > 0:
            error_label = QLabel(f"动态口令验证失败，请重新输入")
            error_label.setObjectName("authError")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            form_layout.addWidget(error_label)
        
        retry_info = QLabel(f"剩余尝试次数: {self.max_retries - self.retry_count} 次")
        retry_info.setObjectName("authRetryInfo")
        retry_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(retry_info)
        
        otp_label = QLabel("动态口令 (OTP):")
        form_layout.addWidget(otp_label)
        
        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("请输入6位数字动态口令")
        self.otp_input.setMinimumHeight(42)
        self.otp_input.setMaxLength(6)
        self.otp_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.otp_input.setFont(font)
        
        validator = QRegularExpressionValidator(QRegularExpression(r'^[0-9]{0,6}$'))
        self.otp_input.setValidator(validator)
        self.otp_input.textChanged.connect(self._on_text_changed)
        form_layout.addWidget(self.otp_input)
        
        form_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setProperty("class", "success")
        self.ok_btn.setMinimumHeight(40)
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.clicked.connect(self.submit_auth)
        self.ok_btn.setEnabled(False)
        btn_layout.addWidget(self.ok_btn)
        
        form_layout.addLayout(btn_layout)
        main_layout.addWidget(form_frame)
        
        self.setLayout(main_layout)
        
        self.otp_input.setFocus()
    
    def _on_text_changed(self, text: str):
        self.ok_btn.setEnabled(len(text) == 6)
    
    def submit_auth(self):
        otp_code = self.otp_input.text()
        
        if len(otp_code) != 6 or not otp_code.isdigit():
            QMessageBox.warning(self, "提示", "请输入6位数字动态口令")
            return
        
        self.auth_submitted.emit(otp_code)
        self.accept()
    
    def get_otp_code(self) -> str:
        return self.otp_input.text()


class BastionConnectingDialog(QDialog):
    cancel_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowIcon(icons.settings_icon())
        self.init_ui()
        
    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "bastion_dialog"])
        
        self.setWindowTitle("连接堡垒机")
        self.setFixedSize(380, 180)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        title_label = QLabel("正在连接堡垒机...")
        title_label.setObjectName("connectingTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        self.status_label = QLabel("初始化连接...")
        self.status_label.setObjectName("connectingStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        self.retry_label = QLabel("")
        self.retry_label.setObjectName("connectingRetry")
        self.retry_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.retry_label)
        
        main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setMinimumHeight(36)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.on_cancel)
        main_layout.addWidget(cancel_btn)
        
        self.setLayout(main_layout)
    
    def update_status(self, status: str):
        self.status_label.setText(status)
        QApplication.processEvents()
    
    def update_retry(self, attempt: int, max_retries: int, error: str):
        self.retry_label.setText(f"重试 {attempt}/{max_retries}: {error}")
        QApplication.processEvents()
    
    def clear_retry(self):
        self.retry_label.setText("")
        QApplication.processEvents()
    
    def on_cancel(self):
        self.cancel_requested.emit()
        self.reject()

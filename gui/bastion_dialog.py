from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QSpacerItem, QSizePolicy,
    QApplication, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QRegExp
from PyQt5.QtGui import QFont, QRegExpValidator
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
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        header = QFrame()
        header.setObjectName("authHeader")
        header.setFixedHeight(80)
        header_layout = QVBoxLayout(header)
        header_layout.setAlignment(Qt.AlignCenter)
        
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
            error_label.setAlignment(Qt.AlignCenter)
            form_layout.addWidget(error_label)
        
        retry_info = QLabel(f"剩余尝试次数: {self.max_retries - self.retry_count} 次")
        retry_info.setObjectName("authRetryInfo")
        retry_info.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(retry_info)
        
        otp_label = QLabel("动态口令 (OTP):")
        form_layout.addWidget(otp_label)
        
        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("请输入6位数字动态口令")
        self.otp_input.setMinimumHeight(42)
        self.otp_input.setMaxLength(6)
        self.otp_input.setAlignment(Qt.AlignCenter)
        
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.otp_input.setFont(font)
        
        validator = QRegExpValidator(QRegExp(r'^[0-9]{0,6}$'))
        self.otp_input.setValidator(validator)
        self.otp_input.textChanged.connect(self._on_text_changed)
        form_layout.addWidget(self.otp_input)
        
        form_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setProperty("class", "success")
        self.ok_btn.setMinimumHeight(40)
        self.ok_btn.setCursor(Qt.PointingHandCursor)
        self.ok_btn.clicked.connect(self.submit_auth)
        self.ok_btn.setEnabled(False)
        btn_layout.addWidget(self.ok_btn)
        
        form_layout.addLayout(btn_layout)
        main_layout.addWidget(form_frame)
        
        self.setLayout(main_layout)
        
        self.otp_input.setFocus()
    
    def _on_text_changed(self, text: str):
        enabled = len(text) == 6
        self.ok_btn.setEnabled(enabled)
    
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
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        title_label = QLabel("正在连接堡垒机...")
        title_label.setObjectName("connectingTitle")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        self.status_label = QLabel("初始化连接...")
        self.status_label.setObjectName("connectingStatus")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        self.retry_label = QLabel("")
        self.retry_label.setObjectName("connectingRetry")
        self.retry_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.retry_label)
        
        main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setMinimumHeight(36)
        cancel_btn.setCursor(Qt.PointingHandCursor)
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


class ServerSelectDialog(QDialog):
    server_selected = pyqtSignal(str)
    
    def __init__(self, server_list: list, raw_output: str = "", parent=None):
        super().__init__(parent)
        self.server_list = server_list
        self.raw_output = raw_output
        self.selected_index = None
        self.setWindowIcon(icons.settings_icon())
        self.init_ui()
    
    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "bastion_dialog"])
        
        self.setWindowTitle("选择目标服务器")
        self.setMinimumSize(600, 450)
        self.resize(700, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        header = QFrame()
        header.setObjectName("authHeader")
        header.setFixedHeight(70)
        header_layout = QVBoxLayout(header)
        header_layout.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel("选择目标服务器")
        title_label.setObjectName("authTitle")
        header_layout.addWidget(title_label)
        
        if self.server_list:
            subtitle_label = QLabel(f"共 {len(self.server_list)} 台服务器可选")
            subtitle_label.setObjectName("authSubtitle")
            header_layout.addWidget(subtitle_label)
        
        main_layout.addWidget(header)
        
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(20, 15, 20, 15)
        
        if self.server_list:
            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText("搜索: 输入IP或名称过滤...")
            self.search_input.setMinimumHeight(36)
            self.search_input.textChanged.connect(self._on_search)
            content_layout.addWidget(self.search_input)
            
            self.server_table = QTableWidget()
            self.server_table.setColumnCount(3)
            self.server_table.setHorizontalHeaderLabels(["序号", "IP地址", "名称"])
            self.server_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.server_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self.server_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            self.server_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.server_table.setSelectionMode(QAbstractItemView.SingleSelection)
            self.server_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.server_table.verticalHeader().setVisible(False)
            self.server_table.doubleClicked.connect(self._on_table_double_clicked)
            
            self._populate_table(self.server_list)
            content_layout.addWidget(self.server_table)
        else:
            info_label = QLabel("未解析到服务器列表，请手动输入序号:")
            info_label.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(info_label)
            
            self.manual_input = QLineEdit()
            self.manual_input.setPlaceholderText("输入服务器序号")
            self.manual_input.setMinimumHeight(42)
            self.manual_input.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(self.manual_input)
            
            if self.raw_output:
                from PyQt5.QtWidgets import QTextEdit
                raw_label = QLabel("堡垒机原始输出:")
                content_layout.addWidget(raw_label)
                
                raw_text = QTextEdit()
                raw_text.setReadOnly(True)
                raw_text.setMaximumHeight(200)
                raw_text.setPlainText(self.raw_output)
                content_layout.addWidget(raw_text)
        
        content_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.ok_btn = QPushButton("连接")
        self.ok_btn.setProperty("class", "success")
        self.ok_btn.setMinimumHeight(40)
        self.ok_btn.setCursor(Qt.PointingHandCursor)
        self.ok_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(self.ok_btn)
        
        content_layout.addLayout(btn_layout)
        main_layout.addWidget(content_frame)
        
        self.setLayout(main_layout)
        
        if self.server_list:
            self.search_input.setFocus()
    
    def _populate_table(self, servers: list):
        self.server_table.setRowCount(len(servers))
        for row, server in enumerate(servers):
            index_item = QTableWidgetItem(server.get("index", ""))
            index_item.setTextAlignment(Qt.AlignCenter)
            self.server_table.setItem(row, 0, index_item)
            
            ip_item = QTableWidgetItem(server.get("ip", ""))
            ip_item.setTextAlignment(Qt.AlignCenter)
            self.server_table.setItem(row, 1, ip_item)
            
            name_item = QTableWidgetItem(server.get("name", ""))
            self.server_table.setItem(row, 2, name_item)
    
    def _on_search(self, text: str):
        if not text.strip():
            self._populate_table(self.server_list)
            return
        
        text_lower = text.lower()
        filtered = [
            s for s in self.server_list
            if text_lower in s.get("ip", "").lower() or text_lower in s.get("name", "").lower()
        ]
        self._populate_table(filtered)
    
    def _on_table_double_clicked(self, index):
        row = index.row()
        index_item = self.server_table.item(row, 0)
        if index_item:
            self.selected_index = index_item.text()
            self.server_selected.emit(self.selected_index)
            self.accept()
    
    def _on_confirm(self):
        if self.server_list:
            selected_rows = self.server_table.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "提示", "请选择一台服务器")
                return
            row = selected_rows[0].row()
            index_item = self.server_table.item(row, 0)
            if index_item:
                self.selected_index = index_item.text()
                self.server_selected.emit(self.selected_index)
                self.accept()
        else:
            if hasattr(self, 'manual_input'):
                index_text = self.manual_input.text().strip()
                if not index_text:
                    QMessageBox.warning(self, "提示", "请输入服务器序号")
                    return
                self.selected_index = index_text
                self.server_selected.emit(self.selected_index)
                self.accept()

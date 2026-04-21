from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QComboBox, QLabel,
    QMessageBox, QFrame, QApplication
)
from PyQt6.QtCore import Qt
from core.workers import AuditLogLoadWorker
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet

logger = get_logger(__name__)

ACTION_TYPE_NAMES = {
    "login": "登录",
    "logout": "登出",
    "create": "创建",
    "update": "更新",
    "delete": "删除",
    "execute": "执行"
}

class AuditPage(QWidget):
    def __init__(self, audit_service, parent=None):
        super().__init__(parent)
        self.audit_service = audit_service
        self.loading_worker = None
        self.init_ui()
        self.load_logs()

    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "audit_page"])

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        toolbar_frame = QFrame()
        toolbar_frame.setProperty("class", "toolbar")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)

        toolbar_layout.addWidget(QLabel("操作类型:"))
        self.action_combo = QComboBox()
        self.action_combo.addItem("全部", "")
        self.action_combo.addItem("登录", "login")
        self.action_combo.addItem("登出", "logout")
        self.action_combo.addItem("创建", "create")
        self.action_combo.addItem("更新", "update")
        self.action_combo.addItem("删除", "delete")
        self.action_combo.addItem("执行", "execute")
        self.action_combo.setMinimumHeight(34)
        self.action_combo.currentIndexChanged.connect(self.load_logs)
        toolbar_layout.addWidget(self.action_combo)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setIcon(icons.refresh_icon())
        self.refresh_btn.setMinimumHeight(34)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_logs)
        toolbar_layout.addWidget(self.refresh_btn)

        toolbar_layout.addStretch()
        layout.addWidget(toolbar_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            "操作类型", "详情", "时间"
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(42)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_logs(self):
        action_type = self.action_combo.currentData()

        if self.loading_worker and self.loading_worker.isRunning():
            logger.warning("审计日志加载任务正在进行中，跳过")
            return

        self.loading_worker = AuditLogLoadWorker(self.audit_service, action_type)
        self.loading_worker.finished.connect(self._on_logs_loaded)
        self.loading_worker.error.connect(self._on_load_error)
        self.loading_worker.start()
        logger.debug(f"开始加载审计日志，操作类型: {action_type or '全部'}")

    def _on_logs_loaded(self, logs):
        logger.debug(f"成功加载 {len(logs)} 条审计日志")
        self._populate_table(logs)

    def _on_load_error(self, error_msg):
        logger.error(f"加载审计日志失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"加载审计日志失败:\n{error_msg}")

    def _populate_table(self, logs):
        self.table.setRowCount(len(logs))

        for row, log in enumerate(logs):
            action_name = ACTION_TYPE_NAMES.get(log.action_type, log.action_type)
            self.table.setItem(row, 0, QTableWidgetItem(action_name))
            self.table.setItem(row, 1, QTableWidgetItem(log.details or ""))

            from datetime import datetime
            dt = log.created_at or datetime.now()
            self.table.setItem(row, 2, QTableWidgetItem(
                dt.strftime("%Y-%m-%d %H:%M:%S")
            ))

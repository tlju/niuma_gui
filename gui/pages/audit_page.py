from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QComboBox, QLabel,
    QMessageBox, QApplication
)
from PyQt6.QtCore import Qt
from core.workers import AuditLogLoadWorker
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet

logger = get_logger(__name__)

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

        # 工具栏
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("操作类型:"))
        self.action_combo = QComboBox()
        self.action_combo.addItem("全部", "")
        self.action_combo.addItems(["login", "create", "update", "delete", "execute"])
        self.action_combo.currentIndexChanged.connect(self.load_logs)
        toolbar.addWidget(self.action_combo)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setIcon(icons.refresh_icon())
        self.refresh_btn.clicked.connect(self.load_logs)
        toolbar.addWidget(self.refresh_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 日志表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "用户ID", "操作类型", "资源类型", "资源ID", "时间"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_logs(self):
        """在后台线程加载审计日志"""
        action_type = self.action_combo.currentData()

        if self.loading_worker and self.loading_worker.isRunning():
            logger.warning("审计日志加载任务正在进行中，跳过")
            return

        self.loading_worker = AuditLogLoadWorker(self.audit_service, action_type)
        self.loading_worker.finished.connect(self._on_logs_loaded)
        self.loading_worker.error.connect(self._on_load_error)
        self.loading_worker.start()
        logger.info(f"开始加载审计日志，操作类型: {action_type or '全部'}")

    def _on_logs_loaded(self, logs):
        """审计日志加载完成回调"""
        logger.info(f"成功加载 {len(logs)} 条审计日志")
        self._populate_table(logs)

    def _on_load_error(self, error_msg):
        """加载错误回调"""
        logger.error(f"加载审计日志失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"加载审计日志失败:\n{error_msg}")

    def _populate_table(self, logs):
        """填充表格数据"""
        self.table.setRowCount(len(logs))

        for row, log in enumerate(logs):
            self.table.setItem(row, 0, QTableWidgetItem(str(log.id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(log.user_id)))
            self.table.setItem(row, 2, QTableWidgetItem(log.action_type))
            self.table.setItem(row, 3, QTableWidgetItem(log.resource_type or ""))
            self.table.setItem(row, 4, QTableWidgetItem(str(log.resource_id) if log.resource_id else ""))

            from datetime import datetime
            dt = log.created_at or datetime.now()
            self.table.setItem(row, 5, QTableWidgetItem(
                dt.strftime("%Y-%m-%d %H:%M:%S")
            ))

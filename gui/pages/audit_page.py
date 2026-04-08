from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QComboBox, QLabel
)
from PyQt6.QtCore import Qt

class AuditPage(QWidget):
    def __init__(self, audit_service, parent=None):
        super().__init__(parent)
        self.audit_service = audit_service
        self.init_ui()
        self.load_logs()

    def init_ui(self):
        layout = QVBoxLayout()

        # 工具栏
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("操作类型:"))
        self.action_combo = QComboBox()
        self.action_combo.addItem("全部", "")
        self.action_combo.addItems(["login", "create", "update", "delete", "execute"])
        toolbar.addWidget(self.action_combo)

        self.refresh_btn = QPushButton("刷新")
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
        action_type = self.action_combo.currentData()

        if action_type:
            logs = self.audit_service.get_logs(action_type=action_type)
        else:
            logs = self.audit_service.get_logs()

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

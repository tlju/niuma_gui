from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QComboBox, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt

class AssetsPage(QWidget):
    def __init__(self, asset_service, current_user_id, parent=None):
        super().__init__(parent)
        self.asset_service = asset_service
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_assets()

    def init_ui(self):
        layout = QVBoxLayout()

        # 工具栏
        toolbar = QHBoxLayout()

        self.add_btn = QPushButton("添加资产")
        self.add_btn.clicked.connect(self.show_add_dialog)
        toolbar.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_assets)
        toolbar.addWidget(self.refresh_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 资产表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "名称", "主机名", "IP", "端口", "OS", "操作"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_assets(self):
        assets = self.asset_service.get_all()

        self.table.setRowCount(len(assets))

        for row, asset in enumerate(assets):
            self.table.setItem(row, 0, QTableWidgetItem(str(asset.id)))
            self.table.setItem(row, 1, QTableWidgetItem(asset.name))
            self.table.setItem(row, 2, QTableWidgetItem(asset.hostname or ""))
            self.table.setItem(row, 3, QTableWidgetItem(asset.ip))
            self.table.setItem(row, 4, QTableWidgetItem(str(asset.port)))
            self.table.setItem(row, 5, QTableWidgetItem(asset.os_type or ""))

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()

            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(
                lambda checked, a=asset.id: self.delete_asset(a)
            )
            btn_layout.addWidget(delete_btn)

            btn_layout.setContentsMargins(5, 0, 5, 0)
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row, 6, btn_widget)

    def show_add_dialog(self):
        dialog = AssetDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.asset_service.create(**data, created_by=self.current_user_id)
            self.load_assets()

    def delete_asset(self, asset_id: int):
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除该资产吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.asset_service.delete(asset_id, self.current_user_id)
            self.load_assets()

class AssetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加资产")
        self.setFixedSize(400, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 表单字段
        self.name_input = self._create_field(layout, "名称:")
        self.ip_input = self._create_field(layout, "IP:")
        self.port_input = self._create_field(layout, "端口:")
        self.port_input.setText("22")
        self.hostname_input = self._create_field(layout, "主机名:")
        self.username_input = self._create_field(layout, "用户名:")
        self.password_input = self._create_field(layout, "密码:")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        # OS 类型
        layout.addWidget(QLabel("操作系统:"))
        self.os_combo = QComboBox()
        self.os_combo.addItems(["Linux", "Windows", "macOS"])
        layout.addWidget(self.os_combo)

        # 按钮
        buttons = QWidget()
        btn_layout = QHBoxLayout()

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        buttons.setLayout(btn_layout)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _create_field(self, layout, label: str):
        layout.addWidget(QLabel(label))
        input_field = QLineEdit()
        layout.addWidget(input_field)
        return input_field

    def get_data(self):
        return {
            "name": self.name_input.text(),
            "ip": self.ip_input.text(),
            "port": int(self.port_input.text()) if self.port_input.text() else 22,
            "hostname": self.hostname_input.text(),
            "os_type": self.os_combo.currentText(),
            "username": self.username_input.text(),
            "password": self.password_input.text()
        }

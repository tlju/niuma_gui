from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QComboBox, QMessageBox, QHeaderView,
    QFrame, QSpacerItem, QSizePolicy, QGroupBox,
    QFormLayout, QSpinBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from core.workers import AssetLoadWorker
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet

logger = get_logger(__name__)


class AssetsPage(QWidget):
    def __init__(self, asset_service, current_user_id, parent=None):
        super().__init__(parent)
        self.asset_service = asset_service
        self.current_user_id = current_user_id
        self.loading_worker = None
        self.all_assets = []
        self.init_ui()
        self.load_assets()

    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "assets_page"])
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        toolbar_frame = QFrame()
        toolbar_frame.setProperty("class", "toolbar")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)

        self.add_btn = QPushButton("  添加资产")
        self.add_btn.setIcon(icons.add_icon())
        self.add_btn.setMinimumHeight(36)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toolbar_layout.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("  刷新")
        self.refresh_btn.setIcon(icons.refresh_icon())
        self.refresh_btn.setMinimumHeight(36)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toolbar_layout.addWidget(self.refresh_btn)

        toolbar_layout.addSpacing(20)

        search_label = QLabel("搜索:")
        toolbar_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入名称、IP或主机名搜索...")
        self.search_input.setMinimumWidth(250)
        self.search_input.setMinimumHeight(36)
        self.search_input.textChanged.connect(self._filter_assets)
        toolbar_layout.addWidget(self.search_input)

        toolbar_layout.addStretch()

        self.count_label = QLabel("共 0 条记录")
        toolbar_layout.addWidget(self.count_label)

        layout.addWidget(toolbar_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "名称", "主机名", "IP地址", "端口", "系统", "状态", "操作"
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 150)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.add_btn.clicked.connect(self.show_add_dialog)
        self.refresh_btn.clicked.connect(self.load_assets)

    def load_assets(self):
        if self.loading_worker and self.loading_worker.isRunning():
            logger.warning("资产加载任务正在进行中，跳过")
            return

        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("  加载中...")
        self.loading_worker = AssetLoadWorker(self.asset_service)
        self.loading_worker.finished.connect(self._on_assets_loaded)
        self.loading_worker.error.connect(self._on_load_error)
        self.loading_worker.start()
        logger.info("开始加载资产列表")

    def _on_assets_loaded(self, assets):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("  刷新")
        self.all_assets = assets
        self._populate_table(assets)
        self._update_count_label()
        logger.info(f"成功加载 {len(assets)} 个资产")

    def _on_load_error(self, error_msg):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("  刷新")
        logger.error(f"加载资产失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"加载资产失败:\n{error_msg}")

    def _filter_assets(self, text):
        if not text:
            self._populate_table(self.all_assets)
        else:
            text = text.lower()
            filtered = [
                a for a in self.all_assets
                if text in (a.name or "").lower()
                or text in (a.ip or "").lower()
                or text in (a.hostname or "").lower()
            ]
            self._populate_table(filtered)
        self._update_count_label()

    def _update_count_label(self):
        count = self.table.rowCount()
        total = len(self.all_assets)
        if count == total:
            self.count_label.setText(f"共 {count} 条记录")
        else:
            self.count_label.setText(f"显示 {count} / {total} 条记录")

    def _populate_table(self, assets):
        self.table.setRowCount(len(assets))

        for row, asset in enumerate(assets):
            id_item = QTableWidgetItem(str(asset.id))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, id_item)

            self.table.setItem(row, 1, QTableWidgetItem(asset.name or ""))
            self.table.setItem(row, 2, QTableWidgetItem(asset.hostname or ""))
            self.table.setItem(row, 3, QTableWidgetItem(asset.ip or ""))

            port_item = QTableWidgetItem(str(asset.port or 22))
            port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, port_item)

            os_item = QTableWidgetItem(asset.os_type or "-")
            os_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, os_item)

            status_item = QTableWidgetItem("在线" if asset.is_active else "离线")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if asset.is_active:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                status_item.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, 6, status_item)

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)

            edit_btn = QPushButton("编辑")
            edit_btn.setFixedSize(50, 28)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            edit_btn.clicked.connect(lambda checked, a=asset: self.show_edit_dialog(a))
            btn_layout.addWidget(edit_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setFixedSize(50, 28)
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            delete_btn.clicked.connect(lambda checked, a=asset.id: self.delete_asset(a))
            btn_layout.addWidget(delete_btn)

            self.table.setCellWidget(row, 7, btn_widget)

    def show_add_dialog(self):
        dialog = AssetDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.asset_service.create(**data, created_by=self.current_user_id)
                self.load_assets()
                QMessageBox.information(self, "成功", "资产添加成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加资产失败: {e}")

    def show_edit_dialog(self, asset):
        dialog = AssetDialog(self, asset)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.asset_service.update(asset.id, **data, updated_by=self.current_user_id)
                self.load_assets()
                QMessageBox.information(self, "成功", "资产更新成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新资产失败: {e}")

    def delete_asset(self, asset_id: int):
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除该资产吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.asset_service.delete(asset_id, self.current_user_id)
                self.load_assets()
                QMessageBox.information(self, "成功", "资产删除成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除资产失败: {e}")


class AssetDialog(QDialog):
    def __init__(self, parent=None, asset=None):
        super().__init__(parent)
        self.asset = asset
        self.setWindowTitle("编辑资产" if asset else "添加资产")
        self.setFixedSize(480, 520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()
        if asset:
            self._populate_data()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 20, 25, 20)

        title_label = QLabel("编辑资产信息" if self.asset else "添加新资产")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title_label)

        form_group = QGroupBox("基本信息")
        form_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #2c3e50;
            }
        """)
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(15, 20, 15, 15)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入资产名称")
        self.name_input.setMinimumHeight(36)
        form_layout.addRow("名称 *:", self.name_input)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("例如: 192.168.1.100")
        self.ip_input.setMinimumHeight(36)
        form_layout.addRow("IP地址 *:", self.ip_input)

        port_layout = QHBoxLayout()
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(22)
        self.port_input.setMinimumHeight(36)
        self.port_input.setMinimumWidth(120)
        port_layout.addWidget(self.port_input)
        port_layout.addStretch()
        form_layout.addRow("端口:", port_layout)

        self.hostname_input = QLineEdit()
        self.hostname_input.setPlaceholderText("可选")
        self.hostname_input.setMinimumHeight(36)
        form_layout.addRow("主机名:", self.hostname_input)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        auth_group = QGroupBox("认证信息")
        auth_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #2c3e50;
            }
        """)
        auth_layout = QFormLayout()
        auth_layout.setSpacing(12)
        auth_layout.setContentsMargins(15, 20, 15, 15)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("SSH 登录用户名")
        self.username_input.setMinimumHeight(36)
        auth_layout.addRow("用户名:", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("SSH 登录密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(36)
        auth_layout.addRow("密码:", self.password_input)

        os_layout = QHBoxLayout()
        self.os_combo = QComboBox()
        self.os_combo.addItems(["Linux", "Windows", "macOS", "Other"])
        self.os_combo.setMinimumHeight(36)
        self.os_combo.setMinimumWidth(150)
        os_layout.addWidget(self.os_combo)
        os_layout.addStretch()
        auth_layout.addRow("操作系统:", os_layout)

        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumHeight(42)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #bdc3c7;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #95a5a6;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.setMinimumHeight(42)
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #1abc9c;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16a085;
            }
        """)
        self.ok_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(self.ok_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _populate_data(self):
        self.name_input.setText(self.asset.name or "")
        self.ip_input.setText(self.asset.ip or "")
        self.port_input.setValue(self.asset.port or 22)
        self.hostname_input.setText(self.asset.hostname or "")
        self.username_input.setText(self.asset.username or "")
        self.password_input.setText(self.asset.password or "")
        os_type = self.asset.os_type or "Linux"
        index = self.os_combo.findText(os_type)
        if index >= 0:
            self.os_combo.setCurrentIndex(index)

    def _validate_and_accept(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入资产名称")
            self.name_input.setFocus()
            return
        if not self.ip_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入IP地址")
            self.ip_input.setFocus()
            return
        self.accept()

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "ip": self.ip_input.text().strip(),
            "port": self.port_input.value(),
            "hostname": self.hostname_input.text().strip() or None,
            "os_type": self.os_combo.currentText(),
            "username": self.username_input.text().strip() or None,
            "password": self.password_input.text() or None
        }

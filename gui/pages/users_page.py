from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QComboBox, QMessageBox, QHeaderView,
    QFrame, QFormLayout, QApplication
)
from PyQt6.QtCore import Qt
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet

logger = get_logger(__name__)


class UsersPage(QWidget):
    def __init__(self, user_service, current_user_id, parent=None):
        super().__init__(parent)
        self.user_service = user_service
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_users()

    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "users_page"])

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        toolbar_frame = QFrame()
        toolbar_frame.setProperty("class", "toolbar")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)

        self.add_btn = QPushButton("  添加用户")
        self.add_btn.setIcon(icons.add_icon())
        self.add_btn.setProperty("class", "success")
        self.add_btn.setMinimumHeight(34)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.show_add_dialog)
        toolbar_layout.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("  刷新")
        self.refresh_btn.setIcon(icons.refresh_icon())
        self.refresh_btn.setMinimumHeight(34)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_users)
        toolbar_layout.addWidget(self.refresh_btn)

        toolbar_layout.addStretch()

        self.count_label = QLabel("共 0 条记录")
        toolbar_layout.addWidget(self.count_label)

        layout.addWidget(toolbar_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "用户名", "角色", "状态", "操作"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_users(self):
        try:
            users = self.user_service.get_users(limit=1000)
            self._populate_table(users)
            self.count_label.setText(f"共 {len(users)} 条记录")
            logger.info(f"加载了 {len(users)} 个用户")
        except Exception as e:
            logger.error(f"加载用户列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载用户列表失败:\n{e}")

    def _populate_table(self, users):
        self.table.setRowCount(len(users))
        for row, user in enumerate(users):
            self.table.setItem(row, 0, QTableWidgetItem(str(user.id)))
            self.table.setItem(row, 1, QTableWidgetItem(user.username or ""))
            self.table.setItem(row, 2, QTableWidgetItem(user.role or ""))
            self.table.setItem(row, 3, QTableWidgetItem(user.status or ""))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            edit_btn = QPushButton("编辑")
            edit_btn.setProperty("class", "table-edit")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda checked, u=user: self.show_edit_dialog(u))
            btn_layout.addWidget(edit_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setProperty("class", "table-delete")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.clicked.connect(lambda checked, uid=user.id: self.delete_user(uid))
            btn_layout.addWidget(delete_btn)

            self.table.setCellWidget(row, 4, btn_widget)

    def show_add_dialog(self):
        dialog = UserDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.user_service.create_user(**data)
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def show_edit_dialog(self, user):
        dialog = UserDialog(self, user)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.user_service.update_user(user.id, **data)
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def delete_user(self, user_id):
        if user_id == self.current_user_id:
            QMessageBox.warning(self, "提示", "不能删除当前登录用户")
            return
        reply = QMessageBox.question(self, "确认删除", "确定要删除此用户吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.user_service.delete_user(user_id)
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))


class UserDialog(QDialog):
    def __init__(self, parent=None, user=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("编辑用户" if user else "添加用户")
        self.setMinimumSize(400, 280)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()
        if user:
            self._populate_data()

    def init_ui(self):
        layout = QFormLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        self.username_input = QLineEdit()
        self.username_input.setMinimumHeight(34)
        layout.addRow("用户名:", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(34)
        if self.user:
            self.password_input.setPlaceholderText("留空则不修改密码")
        layout.addRow("密码:", self.password_input)

        self.role_combo = QComboBox()
        self.role_combo.setMinimumHeight(34)
        self.role_combo.addItem("普通用户", "user")
        self.role_combo.addItem("管理员", "admin")
        layout.addRow("角色:", self.role_combo)

        self.status_combo = QComboBox()
        self.status_combo.setMinimumHeight(34)
        self.status_combo.addItem("活跃", "active")
        self.status_combo.addItem("禁用", "disabled")
        layout.addRow("状态:", self.status_combo)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        ok_btn = QPushButton("确定")
        ok_btn.setProperty("class", "success")
        ok_btn.setMinimumHeight(38)
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        self.setLayout(layout)

    def _populate_data(self):
        self.username_input.setText(self.user.username or "")
        index = self.role_combo.findData(self.user.role)
        if index >= 0:
            self.role_combo.setCurrentIndex(index)
        index = self.status_combo.findData(self.user.status)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)

    def get_data(self):
        data = {
            "username": self.username_input.text(),
            "role": self.role_combo.currentData(),
            "status": self.status_combo.currentData()
        }
        if self.password_input.text():
            data["password"] = self.password_input.text()
        return data

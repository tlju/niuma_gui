from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QComboBox, QMessageBox, QHeaderView,
    QFrame, QFormLayout, QTextEdit, QDateEdit, QApplication
)
from PyQt6.QtCore import Qt
from datetime import datetime
from models.todo import TodoStatus
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet

logger = get_logger(__name__)


class TodosPage(QWidget):
    def __init__(self, todo_service, current_user_id, parent=None):
        super().__init__(parent)
        self.todo_service = todo_service
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_todos()

    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "todos_page"])
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        toolbar_frame = QFrame()
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)

        self.add_btn = QPushButton("  添加待办")
        self.add_btn.setIcon(icons.add_icon())
        self.add_btn.setMinimumHeight(36)
        self.add_btn.clicked.connect(self.show_add_dialog)
        toolbar_layout.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("  刷新")
        self.refresh_btn.setIcon(icons.refresh_icon())
        self.refresh_btn.setMinimumHeight(36)
        self.refresh_btn.clicked.connect(self.load_todos)
        toolbar_layout.addWidget(self.refresh_btn)

        toolbar_layout.addSpacing(20)

        status_label = QLabel("状态:")
        toolbar_layout.addWidget(status_label)

        self.status_combo = QComboBox()
        self.status_combo.addItem("全部", "")
        self.status_combo.addItem("待处理", TodoStatus.PENDING)
        self.status_combo.addItem("进行中", TodoStatus.IN_PROGRESS)
        self.status_combo.addItem("已完成", TodoStatus.COMPLETED)
        self.status_combo.currentIndexChanged.connect(self.load_todos)
        toolbar_layout.addWidget(self.status_combo)

        toolbar_layout.addStretch()

        self.count_label = QLabel("共 0 条记录")
        toolbar_layout.addWidget(self.count_label)

        layout.addWidget(toolbar_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "标题", "描述", "状态", "优先级", "截止日期", "操作"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.all_todos = []

    def load_todos(self):
        try:
            status = self.status_combo.currentData()
            if status:
                self.all_todos = self.todo_service.get_todos(status=status, limit=1000)
            else:
                self.all_todos = self.todo_service.get_todos(limit=1000)
            self._populate_table(self.all_todos)
            self.count_label.setText(f"共 {len(self.all_todos)} 条记录")
            logger.info(f"加载了 {len(self.all_todos)} 个待办事项")
        except Exception as e:
            logger.error(f"加载待办事项失败: {e}")
            QMessageBox.critical(self, "错误", f"加载待办事项失败:\n{e}")

    def _populate_table(self, todos):
        self.table.setRowCount(len(todos))
        for row, todo in enumerate(todos):
            self.table.setItem(row, 0, QTableWidgetItem(str(todo.id)))
            self.table.setItem(row, 1, QTableWidgetItem(todo.title or ""))
            self.table.setItem(row, 2, QTableWidgetItem((todo.description or "")[:50]))
            self.table.setItem(row, 3, QTableWidgetItem(todo.status or ""))
            self.table.setItem(row, 4, QTableWidgetItem(str(todo.priority or 5)))
            due_date = todo.due_date.strftime("%Y-%m-%d") if todo.due_date else ""
            self.table.setItem(row, 5, QTableWidgetItem(due_date))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 4, 4, 4)

            complete_btn = QPushButton("完成")
            complete_btn.clicked.connect(lambda checked, tid=todo.id: self.complete_todo(tid))
            edit_btn = QPushButton("编辑")
            edit_btn.clicked.connect(lambda checked, t=todo: self.show_edit_dialog(t))
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda checked, tid=todo.id: self.delete_todo(tid))

            btn_layout.addWidget(complete_btn)
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            self.table.setCellWidget(row, 6, btn_widget)

    def show_add_dialog(self):
        dialog = TodoDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.todo_service.create_todo(**data, assigned_to=self.current_user_id)
                self.load_todos()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def show_edit_dialog(self, todo):
        dialog = TodoDialog(self, todo)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.todo_service.update_todo(todo.id, **data)
                self.load_todos()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def complete_todo(self, todo_id):
        try:
            self.todo_service.complete_todo(todo_id)
            self.load_todos()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def delete_todo(self, todo_id):
        reply = QMessageBox.question(self, "确认删除", "确定要删除此待办事项吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.todo_service.delete_todo(todo_id)
                self.load_todos()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))


class TodoDialog(QDialog):
    def __init__(self, parent=None, todo=None):
        super().__init__(parent)
        self.todo = todo
        self.setWindowTitle("编辑待办" if todo else "添加待办")
        self.setFixedSize(450, 350)
        self.init_ui()
        if todo:
            self._populate_data()

    def init_ui(self):
        layout = QFormLayout()

        self.title_input = QLineEdit()
        layout.addRow("标题:", self.title_input)

        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(80)
        layout.addRow("描述:", self.desc_input)

        self.status_combo = QComboBox()
        self.status_combo.addItem("待处理", TodoStatus.PENDING)
        self.status_combo.addItem("进行中", TodoStatus.IN_PROGRESS)
        self.status_combo.addItem("已完成", TodoStatus.COMPLETED)
        layout.addRow("状态:", self.status_combo)

        self.priority_input = QLineEdit()
        self.priority_input.setPlaceholderText("1-10, 数字越大优先级越高")
        layout.addRow("优先级:", self.priority_input)

        self.due_date_input = QDateEdit()
        self.due_date_input.setCalendarPopup(True)
        self.due_date_input.setDateTime(datetime.now())
        layout.addRow("截止日期:", self.due_date_input)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        self.setLayout(layout)

    def _populate_data(self):
        self.title_input.setText(self.todo.title or "")
        self.desc_input.setPlainText(self.todo.description or "")
        index = self.status_combo.findData(self.todo.status)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)
        self.priority_input.setText(str(self.todo.priority or 5))
        if self.todo.due_date:
            self.due_date_input.setDateTime(self.todo.due_date)

    def get_data(self):
        priority = 5
        try:
            priority = int(self.priority_input.text())
        except ValueError:
            pass
        return {
            "title": self.title_input.text(),
            "description": self.desc_input.toPlainText(),
            "status": self.status_combo.currentData(),
            "priority": priority,
            "due_date": self.due_date_input.dateTime().toPyDateTime()
        }

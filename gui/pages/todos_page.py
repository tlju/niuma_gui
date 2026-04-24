from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QComboBox, QMessageBox, QHeaderView,
    QFrame, QFormLayout, QTextEdit, QDateEdit, QApplication,
    QSpinBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush, QFont
from datetime import datetime
from models.todo import TodoStatus, RecurrenceType
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet

logger = get_logger(__name__)

STATUS_DISPLAY = {
    TodoStatus.PENDING: "待处理",
    TodoStatus.IN_PROGRESS: "进行中",
    TodoStatus.COMPLETED: "已完成"
}

STATUS_COLORS = {
    TodoStatus.PENDING: "#f39c12",
    TodoStatus.IN_PROGRESS: "#3498db",
    TodoStatus.COMPLETED: "#27ae60"
}

RECURRENCE_DISPLAY = {
    RecurrenceType.NONE: "无",
    RecurrenceType.DAILY: "每日",
    RecurrenceType.WEEKLY: "每周",
    RecurrenceType.MONTHLY: "每月"
}


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
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        toolbar_frame = QFrame()
        toolbar_frame.setProperty("class", "toolbar")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)

        self.add_btn = QPushButton("添加待办")
        self.add_btn.setIcon(icons.add_icon())
        self.add_btn.setProperty("class", "success")
        self.add_btn.setMinimumHeight(34)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.show_add_dialog)
        toolbar_layout.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setIcon(icons.refresh_icon())
        self.refresh_btn.setMinimumHeight(34)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_todos)
        toolbar_layout.addWidget(self.refresh_btn)

        toolbar_layout.addSpacing(20)

        status_label = QLabel("状态:")
        toolbar_layout.addWidget(status_label)

        self.status_combo = QComboBox()
        self.status_combo.setMinimumHeight(34)
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
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "标题", "描述", "状态", "优先级", "截止日期", "循环", "操作"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(42)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.all_todos = []
        self._bold_font = QFont()
        self._bold_font.setBold(True)

    def _get_bold_font(self):
        return self._bold_font

    def load_todos(self):
        try:
            status = self.status_combo.currentData()
            if status:
                self.all_todos = self.todo_service.get_todos(status=status, limit=1000)
            else:
                self.all_todos = self.todo_service.get_todos(limit=1000)
            self._populate_table(self.all_todos)
            self.count_label.setText(f"共 {len(self.all_todos)} 条记录")
            logger.debug(f"加载了 {len(self.all_todos)} 个待办事项")
        except Exception as e:
            logger.error(f"加载待办事项失败: {e}")
            QMessageBox.critical(self, "错误", f"加载待办事项失败:\n{e}")

    def _populate_table(self, todos):
        self.table.setRowCount(len(todos))
        for row, todo in enumerate(todos):
            self.table.setItem(row, 0, QTableWidgetItem(str(todo.id)))
            self.table.setItem(row, 1, QTableWidgetItem(todo.title or ""))
            self.table.setItem(row, 2, QTableWidgetItem((todo.description or "")[:50]))
            
            status_text = STATUS_DISPLAY.get(todo.status, todo.status or "")
            status_item = QTableWidgetItem(status_text)
            status_color = STATUS_COLORS.get(todo.status, "#666666")
            status_item.setForeground(QBrush(QColor(status_color)))
            status_item.setFont(self._get_bold_font())
            self.table.setItem(row, 3, status_item)
            
            self.table.setItem(row, 4, QTableWidgetItem(str(todo.priority or 5)))
            due_date = todo.due_date.strftime("%Y-%m-%d") if todo.due_date else ""
            self.table.setItem(row, 5, QTableWidgetItem(due_date))
            
            recurrence_text = RECURRENCE_DISPLAY.get(todo.recurrence_type, "无")
            if todo.recurrence_type and todo.recurrence_type != RecurrenceType.NONE and todo.recurrence_interval > 1:
                recurrence_text = f"{recurrence_text}({todo.recurrence_interval})"
            self.table.setItem(row, 6, QTableWidgetItem(recurrence_text))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            btn_layout.setAlignment(Qt.AlignCenter)

            complete_btn = QPushButton("完成")
            complete_btn.setProperty("class", "table-complete")
            complete_btn.setCursor(Qt.PointingHandCursor)
            complete_btn.clicked.connect(lambda checked, tid=todo.id: self.complete_todo(tid))
            btn_layout.addWidget(complete_btn)

            edit_btn = QPushButton("编辑")
            edit_btn.setProperty("class", "table-edit")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.clicked.connect(lambda checked, t=todo: self.show_edit_dialog(t))
            btn_layout.addWidget(edit_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setProperty("class", "table-delete")
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.clicked.connect(lambda checked, tid=todo.id: self.delete_todo(tid))
            btn_layout.addWidget(delete_btn)

            self.table.setCellWidget(row, 7, btn_widget)

    def show_add_dialog(self):
        dialog = TodoDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.todo_service.create_todo(**data, assigned_to=self.current_user_id, created_by=self.current_user_id)
                self.load_todos()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def show_edit_dialog(self, todo):
        dialog = TodoDialog(self, todo)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.todo_service.update_todo(todo.id, user_id=self.current_user_id, **data)
                self.load_todos()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def complete_todo(self, todo_id):
        try:
            self.todo_service.complete_todo(todo_id, user_id=self.current_user_id)
            self.load_todos()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def delete_todo(self, todo_id):
        reply = QMessageBox.question(self, "确认删除", "确定要删除此待办事项吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.todo_service.delete_todo(todo_id, user_id=self.current_user_id)
                self.load_todos()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))


class TodoDialog(QDialog):
    def __init__(self, parent=None, todo=None):
        super().__init__(parent)
        self.todo = todo
        self.setWindowTitle("编辑待办" if todo else "添加待办")
        self.setMinimumSize(450, 450)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.init_ui()
        if todo:
            self._populate_data()

    def init_ui(self):
        layout = QFormLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        self.title_input = QLineEdit()
        self.title_input.setMinimumHeight(34)
        layout.addRow("标题:", self.title_input)

        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(80)
        layout.addRow("描述:", self.desc_input)

        self.status_combo = QComboBox()
        self.status_combo.setMinimumHeight(34)
        self.status_combo.addItem("待处理", TodoStatus.PENDING)
        self.status_combo.addItem("进行中", TodoStatus.IN_PROGRESS)
        self.status_combo.addItem("已完成", TodoStatus.COMPLETED)
        layout.addRow("状态:", self.status_combo)

        self.priority_input = QLineEdit()
        self.priority_input.setPlaceholderText("1-10, 数字越大优先级越高")
        self.priority_input.setMinimumHeight(34)
        layout.addRow("优先级:", self.priority_input)

        self.due_date_input = QDateEdit()
        self.due_date_input.setCalendarPopup(True)
        self.due_date_input.setMinimumHeight(34)
        self.due_date_input.setDateTime(datetime.now())
        layout.addRow("截止日期:", self.due_date_input)

        recurrence_layout = QHBoxLayout()
        self.recurrence_combo = QComboBox()
        self.recurrence_combo.setMinimumHeight(34)
        self.recurrence_combo.addItem("无", RecurrenceType.NONE)
        self.recurrence_combo.addItem("每日", RecurrenceType.DAILY)
        self.recurrence_combo.addItem("每周", RecurrenceType.WEEKLY)
        self.recurrence_combo.addItem("每月", RecurrenceType.MONTHLY)
        recurrence_layout.addWidget(self.recurrence_combo)
        
        interval_label = QLabel("间隔:")
        interval_label.setContentsMargins(10, 0, 5, 0)
        recurrence_layout.addWidget(interval_label)
        
        self.recurrence_interval = QSpinBox()
        self.recurrence_interval.setMinimumHeight(34)
        self.recurrence_interval.setMinimum(1)
        self.recurrence_interval.setMaximum(99)
        self.recurrence_interval.setValue(1)
        self.recurrence_interval.setFixedWidth(60)
        recurrence_layout.addWidget(self.recurrence_interval)
        recurrence_layout.addStretch()
        layout.addRow("循环:", recurrence_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        ok_btn = QPushButton("确定")
        ok_btn.setProperty("class", "success")
        ok_btn.setMinimumHeight(38)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.setCursor(Qt.PointingHandCursor)
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
        
        recurrence_index = self.recurrence_combo.findData(self.todo.recurrence_type or RecurrenceType.NONE)
        if recurrence_index >= 0:
            self.recurrence_combo.setCurrentIndex(recurrence_index)
        self.recurrence_interval.setValue(self.todo.recurrence_interval or 1)

    def get_data(self):
        priority = 5
        try:
            priority = int(self.priority_input.text())
        except ValueError:
            pass
        
        recurrence_type = self.recurrence_combo.currentData()
        return {
            "title": self.title_input.text(),
            "description": self.desc_input.toPlainText(),
            "status": self.status_combo.currentData(),
            "priority": priority,
            "due_date": self.due_date_input.dateTime().toPyDateTime(),
            "recurrence_type": recurrence_type,
            "recurrence_interval": self.recurrence_interval.value() if recurrence_type != RecurrenceType.NONE else 1
        }

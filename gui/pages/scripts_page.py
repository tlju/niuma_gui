from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QPlainTextEdit, QMessageBox, QHeaderView,
    QComboBox
)
from PyQt6.QtCore import Qt

class ScriptsPage(QWidget):
    def __init__(self, script_service, current_user_id, parent=None):
        super().__init__(parent)
        self.script_service = script_service
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_scripts()

    def init_ui(self):
        layout = QVBoxLayout()

        # 工具栏
        toolbar = QHBoxLayout()

        self.add_btn = QPushButton("添加脚本")
        self.add_btn.clicked.connect(self.show_add_dialog)
        toolbar.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_scripts)
        toolbar.addWidget(self.refresh_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 脚本表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "ID", "名称", "描述", "语言", "操作"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_scripts(self):
        scripts = self.script_service.get_all()

        self.table.setRowCount(len(scripts))

        for row, script in enumerate(scripts):
            self.table.setItem(row, 0, QTableWidgetItem(str(script.id)))
            self.table.setItem(row, 1, QTableWidgetItem(script.name))
            self.table.setItem(row, 2, QTableWidgetItem(script.description or ""))
            self.table.setItem(row, 3, QTableWidgetItem(script.language or "bash"))

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()

            execute_btn = QPushButton("执行")
            execute_btn.clicked.connect(
                lambda checked, s=script: self.show_execute_dialog(s)
            )
            btn_layout.addWidget(execute_btn)

            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(
                lambda checked, s=script.id: self.delete_script(s)
            )
            btn_layout.addWidget(delete_btn)

            btn_layout.setContentsMargins(5, 0, 5, 0)
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row, 4, btn_widget)

    def show_add_dialog(self):
        dialog = ScriptDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, content, description = dialog.get_data()
            self.script_service.create(
                name=name,
                content=content,
                description=description,
                created_by=self.current_user_id
            )
            self.load_scripts()

    def show_execute_dialog(self, script):
        dialog = ExecuteScriptDialog(self.script_service, script, self.current_user_id, self)
        dialog.exec()

    def delete_script(self, script_id: int):
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除该脚本吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.script_service.delete(script_id, self.current_user_id)
            self.load_scripts()


class ScriptDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加脚本")
        self.setFixedSize(600, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 名称
        layout.addWidget(QLabel("名称:"))
        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)

        # 描述
        layout.addWidget(QLabel("描述:"))
        self.desc_input = QLineEdit()
        layout.addWidget(self.desc_input)

        # 内容
        layout.addWidget(QLabel("脚本内容:"))
        self.content_input = QPlainTextEdit()
        layout.addWidget(self.content_input)

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

    def get_data(self):
        return (
            self.name_input.text(),
            self.content_input.toPlainText(),
            self.desc_input.text()
        )


class ExecuteScriptDialog(QDialog):
    def __init__(self, script_service, script, current_user_id, parent=None):
        super().__init__(parent)
        self.script_service = script_service
        self.script = script
        self.current_user_id = current_user_id
        self.setWindowTitle(f"执行脚本: {script.name}")
        self.setFixedSize(600, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 显示脚本内容
        layout.addWidget(QLabel("脚本内容:"))
        self.script_display = QPlainTextEdit()
        self.script_display.setReadOnly(True)
        self.script_display.setPlainText(self.script.content)
        layout.addWidget(self.script_display)

        # 选择服务器
        layout.addWidget(QLabel("选择服务器:"))
        from gui.pages.assets_page import AssetsPage
        # 这里需要更好的方式获取服务器列表
        # 简化实现：手动输入服务器ID
        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("输入服务器ID")
        layout.addWidget(self.server_input)

        # 输出
        layout.addWidget(QLabel("执行输出:"))
        self.output_display = QPlainTextEdit()
        self.output_display.setReadOnly(True)
        layout.addWidget(self.output_display)

        # 按钮
        buttons = QWidget()
        btn_layout = QHBoxLayout()

        execute_btn = QPushButton("执行")
        execute_btn.clicked.connect(self.execute_script)
        btn_layout.addWidget(execute_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        buttons.setLayout(btn_layout)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def execute_script(self):
        try:
            server_id = int(self.server_input.text())
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的服务器ID")
            return

        self.output_display.appendPlainText("开始执行...")

        exec_log_id = self.script_service.execute(
            self.script,
            server_id,
            self.current_user_id
        )

        if exec_log_id:
            self.output_display.appendPlainText("\n执行完成")
            # 获取执行日志
            from models.exec_log import ExecLog
            from core.database import get_db_session
            db = get_db_session()
            log = db.query(ExecLog).filter(ExecLog.id == exec_log_id).first()
            if log:
                self.output_display.appendPlainText(f"\n状态: {log.status}")
                if log.output:
                    self.output_display.appendPlainText(f"\n输出:\n{log.output}")
                if log.error:
                    self.output_display.appendPlainText(f"\n错误:\n{log.error}")
            db.close()
        else:
            self.output_display.appendPlainText("\n执行失败")

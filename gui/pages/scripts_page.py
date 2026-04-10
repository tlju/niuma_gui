from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QPlainTextEdit, QMessageBox, QHeaderView,
    QComboBox, QFrame, QApplication
)
from PyQt6.QtCore import Qt
from core.workers import ScriptLoadWorker, ScriptExecutionWorker
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet

logger = get_logger(__name__)

class ScriptsPage(QWidget):
    def __init__(self, script_service, current_user_id, parent=None):
        super().__init__(parent)
        self.script_service = script_service
        self.current_user_id = current_user_id
        self.loading_worker = None
        self.init_ui()
        self.load_scripts()

    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "scripts_page"])

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        toolbar_frame = QFrame()
        toolbar_frame.setProperty("class", "toolbar")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)

        self.add_btn = QPushButton("  添加脚本")
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
        self.refresh_btn.clicked.connect(self.load_scripts)
        toolbar_layout.addWidget(self.refresh_btn)

        toolbar_layout.addStretch()
        layout.addWidget(toolbar_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "ID", "名称", "描述", "语言", "操作"
        ])
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

    def load_scripts(self):
        if self.loading_worker and self.loading_worker.isRunning():
            logger.warning("脚本加载任务正在进行中，跳过")
            return

        self.loading_worker = ScriptLoadWorker(self.script_service)
        self.loading_worker.finished.connect(self._on_scripts_loaded)
        self.loading_worker.error.connect(self._on_load_error)
        self.loading_worker.start()
        logger.info("开始加载脚本列表")

    def _on_scripts_loaded(self, scripts):
        logger.info(f"成功加载 {len(scripts)} 个脚本")
        self._populate_table(scripts)

    def _on_load_error(self, error_msg):
        logger.error(f"加载脚本失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"加载脚本失败:\n{error_msg}")

    def _populate_table(self, scripts):
        self.table.setRowCount(len(scripts))

        for row, script in enumerate(scripts):
            self.table.setItem(row, 0, QTableWidgetItem(str(script.id)))
            self.table.setItem(row, 1, QTableWidgetItem(script.name))
            self.table.setItem(row, 2, QTableWidgetItem(script.description or ""))
            self.table.setItem(row, 3, QTableWidgetItem(script.language or "bash"))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            execute_btn = QPushButton("执行")
            execute_btn.setProperty("class", "table-run")
            execute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            execute_btn.clicked.connect(
                lambda checked, s=script: self.show_execute_dialog(s)
            )
            btn_layout.addWidget(execute_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setProperty("class", "table-delete")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.clicked.connect(
                lambda checked, s=script.id: self.delete_script(s)
            )
            btn_layout.addWidget(delete_btn)

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
        self.setMinimumSize(600, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        layout.addWidget(QLabel("名称:"))
        self.name_input = QLineEdit()
        self.name_input.setMinimumHeight(34)
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("描述:"))
        self.desc_input = QLineEdit()
        self.desc_input.setMinimumHeight(34)
        layout.addWidget(self.desc_input)

        layout.addWidget(QLabel("脚本内容:"))
        self.content_input = QPlainTextEdit()
        layout.addWidget(self.content_input)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        ok_btn = QPushButton("确定")
        ok_btn.setProperty("class", "success")
        ok_btn.setMinimumHeight(38)
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
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
        self.execution_worker = None
        self.setWindowTitle(f"执行脚本: {script.name}")
        self.setMinimumSize(600, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        layout.addWidget(QLabel("脚本内容:"))
        self.script_display = QPlainTextEdit()
        self.script_display.setReadOnly(True)
        self.script_display.setPlainText(self.script.content)
        layout.addWidget(self.script_display)

        layout.addWidget(QLabel("选择服务器:"))
        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("输入服务器ID")
        self.server_input.setMinimumHeight(34)
        layout.addWidget(self.server_input)

        layout.addWidget(QLabel("执行输出:"))
        self.output_display = QPlainTextEdit()
        self.output_display.setReadOnly(True)
        layout.addWidget(self.output_display)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.execute_btn = QPushButton("执行")
        self.execute_btn.setProperty("class", "warning")
        self.execute_btn.setMinimumHeight(38)
        self.execute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.execute_btn.clicked.connect(self.execute_script)
        btn_layout.addWidget(self.execute_btn)

        close_btn = QPushButton("关闭")
        close_btn.setProperty("class", "secondary")
        close_btn.setMinimumHeight(38)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def execute_script(self):
        try:
            server_id = int(self.server_input.text())
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的服务器ID")
            return

        if self.execution_worker and self.execution_worker.isRunning():
            QMessageBox.warning(self, "提示", "脚本正在执行中，请稍候")
            return

        self.output_display.appendPlainText("开始执行...")
        self.execute_btn.setEnabled(False)

        self.execution_worker = ScriptExecutionWorker(
            self.script_service,
            self.script,
            server_id,
            self.current_user_id
        )
        self.execution_worker.finished.connect(self._on_execution_finished)
        self.execution_worker.progress.connect(self._on_execution_progress)
        self.execution_worker.error.connect(self._on_execution_error)
        self.execution_worker.start()
        logger.info(f"开始执行脚本 {self.script.name} 在服务器 {server_id}")

    def _on_execution_finished(self, exec_log_id):
        logger.info(f"脚本执行完成，日志ID: {exec_log_id}")
        self.execute_btn.setEnabled(True)
        self.output_display.appendPlainText("\n执行完成")

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

    def _on_execution_progress(self, message):
        self.output_display.appendPlainText(message)

    def _on_execution_error(self, error_msg):
        logger.error(f"脚本执行失败: {error_msg}")
        self.execute_btn.setEnabled(True)
        self.output_display.appendPlainText(f"\n执行失败:\n{error_msg}")
        QMessageBox.critical(self, "错误", f"脚本执行失败:\n{error_msg}")

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QTextEdit, QMessageBox, QHeaderView,
    QFrame, QApplication, QComboBox, QSplitter,
    QListWidget, QListWidgetItem, QGroupBox, QTabWidget,
    QPlainTextEdit, QProgressBar, QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QDateTime
from PyQt6.QtGui import QColor, QFont, QIcon
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from gui.workflow_canvas import WorkflowCanvas, NodePaletteWidget
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet
from core.logger import get_logger
from core.node_types import get_all_node_types
from core.workers import BaseWorker

logger = get_logger(__name__)


class WorkflowLoadWorker(BaseWorker):
    def __init__(self, workflow_service):
        super().__init__()
        self.workflow_service = workflow_service

    def execute(self) -> list:
        return self.workflow_service.get_all()


class WorkflowExecutionWorker(BaseWorker):
    progress = pyqtSignal(dict)
    log = pyqtSignal(dict)

    def __init__(self, workflow_service, workflow_id: int, user_id: int = None, max_workers: int = 4):
        super().__init__()
        self.workflow_service = workflow_service
        self.workflow_id = workflow_id
        self.user_id = user_id
        self.max_workers = max_workers

    def execute(self) -> dict:
        def on_execution_update(update):
            self.progress.emit(update)

        def on_log(log_entry):
            self.log.emit(log_entry)

        return self.workflow_service.execute_workflow(
            self.workflow_id,
            user_id=self.user_id,
            max_workers=self.max_workers,
            execution_callback=on_execution_update,
            log_callback=on_log
        )


class WorkflowEditDialog(QDialog):
    MODE_EDIT = "edit"
    MODE_EXECUTE = "execute"

    def __init__(self, workflow_service, workflow=None, mode="edit", current_user_id=None, parent=None):
        super().__init__(parent)
        self.workflow_service = workflow_service
        self.workflow = workflow
        self.mode = mode
        self.current_user_id = current_user_id

        if mode == self.MODE_EXECUTE:
            self.setWindowTitle(f"执行工作流 - {workflow.name}" if workflow else "执行工作流")
        else:
            self.setWindowTitle("编辑工作流" if workflow else "新建工作流")

        self.setMinimumSize(1200, 800)
        self.init_ui()

        if workflow and workflow.graph_data:
            self.canvas.load_graph_data(workflow.graph_data)

    def init_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("工作流名称")
        self.name_edit.setMaximumWidth(200)
        if self.workflow:
            self.name_edit.setText(self.workflow.name)
        toolbar.addWidget(QLabel("名称:"))
        toolbar.addWidget(self.name_edit)

        if self.mode == self.MODE_EXECUTE:
            self.name_edit.setReadOnly(True)

        toolbar.addStretch()

        self.save_btn = QPushButton("保存")
        self.save_btn.setIcon(icons.save_icon())
        self.save_btn.clicked.connect(self.save)

        if self.mode == self.MODE_EDIT:
            toolbar.addWidget(self.save_btn)

        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.node_palette = NodePaletteWidget()
        self.node_palette.node_selected.connect(self._on_node_type_selected)
        splitter.addWidget(self.node_palette)

        self.canvas = WorkflowCanvas()
        splitter.addWidget(self.canvas)

        self.log_panel = QWidget()
        log_layout = QVBoxLayout(self.log_panel)
        log_layout.setContentsMargins(5, 5, 5, 5)

        log_label = QLabel("执行日志")
        log_label.setStyleSheet("font-weight: bold;")
        log_layout.addWidget(log_label)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(500)
        self.log_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        log_layout.addWidget(self.log_text)

        splitter.addWidget(self.log_panel)

        if self.mode == self.MODE_EDIT:
            self.log_panel.hide()
            splitter.setSizes([200, 1000, 0])
        else:
            self.node_palette.hide()
            splitter.setSizes([0, 700, 500])

        layout.addWidget(splitter)

        self.canvas.node_added.connect(self._log_node_added)
        self.canvas.node_removed.connect(self._log_node_removed)
        self.canvas.connection_added.connect(self._log_connection_added)

    def _on_node_type_selected(self, node_type: str):
        center = self.canvas.mapToScene(self.canvas.viewport().rect().center())
        self.canvas.add_node(node_type, center.x() - 80, center.y() - 40)

    def _log_node_added(self, node):
        self._append_log("INFO", f"添加节点: {node.name} [{node.node_type}]")

    def _log_node_removed(self, node_id):
        self._append_log("INFO", f"删除节点: {node_id}")

    def _log_connection_added(self, conn):
        self._append_log("INFO", f"添加连接: {conn.source_node.name} -> {conn.target_node.name}")

    def _append_log(self, level: str, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "INFO": "#4FC3F7",
            "WARN": "#FFB74D",
            "ERROR": "#EF5350",
            "SUCCESS": "#81C784"
        }
        color = color_map.get(level, "#FFFFFF")
        self.log_text.appendHtml(
            f'<span style="color: #888;">[{timestamp}]</span> '
            f'<span style="color: {color};">[{level}]</span> '
            f'<span>{message}</span>'
        )

    def save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "请输入工作流名称")
            return

        graph_data = self.canvas.get_graph_data()

        if not graph_data["nodes"]:
            QMessageBox.warning(self, "警告", "请添加至少一个节点")
            return

        if self.workflow:
            self.workflow_service.update(
                self.workflow.id,
                user_id=self.current_user_id,
                name=name,
                graph_data=graph_data
            )
        else:
            self.workflow = self.workflow_service.create(name=name, user_id=self.current_user_id, graph_data=graph_data)

        QMessageBox.information(self, "成功", "工作流保存成功")
        self.accept()


class WorkflowPage(QWidget):
    def __init__(self, workflow_service, current_user_id, parent=None):
        super().__init__(parent)
        self.workflow_service = workflow_service
        self.current_user_id = current_user_id
        self.loading_worker = None
        self.execution_worker = None
        self.workflows_data = []
        self.init_ui()
        self.load_workflows()

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

        self.add_btn = QPushButton("新建工作流")
        self.add_btn.setIcon(icons.add_icon())
        self.add_btn.setProperty("class", "success")
        self.add_btn.setMinimumHeight(34)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.show_create_dialog)
        toolbar_layout.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setIcon(icons.refresh_icon())
        self.refresh_btn.setMinimumHeight(34)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_workflows)
        toolbar_layout.addWidget(self.refresh_btn)

        toolbar_layout.addStretch()
        layout.addWidget(toolbar_frame)

        self.tabs = QTabWidget()

        self.workflow_list_tab = QWidget()
        list_layout = QVBoxLayout(self.workflow_list_tab)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "ID", "名称", "描述", "创建时间", "操作"
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

        self.table.doubleClicked.connect(self.show_edit_dialog)

        list_layout.addWidget(self.table)
        self.tabs.addTab(self.workflow_list_tab, "工作流列表")

        self.execution_tab = QWidget()
        exec_layout = QVBoxLayout(self.execution_tab)

        exec_toolbar = QHBoxLayout()
        exec_toolbar.addWidget(QLabel("执行历史"))

        self.exec_refresh_btn = QPushButton("刷新")
        self.exec_refresh_btn.clicked.connect(self.load_executions)
        exec_toolbar.addWidget(self.exec_refresh_btn)
        exec_toolbar.addStretch()
        exec_layout.addLayout(exec_toolbar)

        self.exec_table = QTableWidget()
        self.exec_table.setColumnCount(5)
        self.exec_table.setHorizontalHeaderLabels([
            "ID", "工作流", "状态", "开始时间", "结束时间"
        ])
        self.exec_table.setAlternatingRowColors(True)
        self.exec_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.exec_table.verticalHeader().setVisible(False)
        self.exec_table.setShowGrid(False)
        self.exec_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        exec_header = self.exec_table.horizontalHeader()
        exec_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        exec_layout.addWidget(self.exec_table)
        self.tabs.addTab(self.execution_tab, "执行历史")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def load_workflows(self):
        if self.loading_worker and self.loading_worker.isRunning():
            return

        self.loading_worker = WorkflowLoadWorker(self.workflow_service)
        self.loading_worker.finished.connect(self._on_workflows_loaded)
        self.loading_worker.error.connect(self._on_load_error)
        self.loading_worker.start()

    def _on_workflows_loaded(self, workflows):
        self.workflows_data = workflows
        self.table.setRowCount(len(workflows))

        for row, workflow in enumerate(workflows):
            self.table.setItem(row, 0, QTableWidgetItem(str(workflow.id)))
            self.table.setItem(row, 1, QTableWidgetItem(workflow.name))
            self.table.setItem(row, 2, QTableWidgetItem(workflow.description or ""))

            created_at = workflow.created_at.strftime("%Y-%m-%d %H:%M") if workflow.created_at else ""
            self.table.setItem(row, 3, QTableWidgetItem(created_at))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            edit_btn = QPushButton("编辑")
            edit_btn.setProperty("class", "table-edit")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda checked, w=workflow: self.show_edit_dialog(w))
            btn_layout.addWidget(edit_btn)

            run_btn = QPushButton("执行")
            run_btn.setProperty("class", "table-run")
            run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            run_btn.clicked.connect(lambda checked, w=workflow: self.execute_workflow(w))
            btn_layout.addWidget(run_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setProperty("class", "table-delete")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.clicked.connect(lambda checked, w=workflow: self.delete_workflow(w))
            btn_layout.addWidget(delete_btn)

            self.table.setCellWidget(row, 4, btn_widget)

    def _on_load_error(self, error_msg):
        logger.error(f"加载工作流失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"加载工作流失败: {error_msg}")

    def show_create_dialog(self):
        dialog = WorkflowEditDialog(self.workflow_service, current_user_id=self.current_user_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_workflows()

    def show_edit_dialog(self, workflow=None):
        if isinstance(workflow, int):
            row = self.table.currentRow()
            if row >= 0 and row < len(self.workflows_data):
                workflow = self.workflows_data[row]
            else:
                return

        dialog = WorkflowEditDialog(self.workflow_service, workflow, current_user_id=self.current_user_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_workflows()

    def execute_workflow(self, workflow):
        if not workflow.graph_data or not workflow.graph_data.get("nodes"):
            QMessageBox.warning(self, "警告", "工作流没有节点，请先编辑添加节点")
            return

        if self.execution_worker and self.execution_worker.isRunning():
            QMessageBox.warning(self, "警告", "已有工作流正在执行中")
            return

        dialog = WorkflowEditDialog(
            self.workflow_service, workflow,
            mode=WorkflowEditDialog.MODE_EXECUTE,
            current_user_id=self.current_user_id,
            parent=self
        )

        re_exec_btn = QPushButton("重新执行")
        re_exec_btn.setProperty("class", "success")
        re_exec_btn.clicked.connect(lambda: self._start_execution(dialog, workflow.id))
        dialog.findChild(QHBoxLayout).insertWidget(0, re_exec_btn)

        dialog.show()
        self._start_execution(dialog, workflow.id)

    def _start_execution(self, dialog: WorkflowEditDialog, workflow_id: int):
        if self.execution_worker and self.execution_worker.isRunning():
            return

        dialog.canvas.reset_all_status()

        self.execution_worker = WorkflowExecutionWorker(
            self.workflow_service,
            workflow_id,
            user_id=self.current_user_id,
            max_workers=4
        )
        self.execution_worker.progress.connect(
            lambda update: self._on_execution_progress(dialog, update)
        )
        self.execution_worker.log.connect(
            lambda log: self._on_execution_log(dialog, log)
        )
        self.execution_worker.finished.connect(
            lambda result: self._on_execution_finished(dialog, result)
        )
        self.execution_worker.start()

    def _on_execution_progress(self, dialog: WorkflowEditDialog, update: dict):
        node_id = update.get("node_id")
        status = update.get("status")
        if node_id is not None:
            dialog.canvas.set_node_status(node_id, status)

    def _on_execution_log(self, dialog: WorkflowEditDialog, log: dict):
        level = log.get("level", "INFO")
        message = log.get("message", "")
        dialog._append_log(level, message)

    def _on_execution_finished(self, dialog: WorkflowEditDialog, result: dict):
        status = result.get("status")
        if status == "success":
            dialog._append_log("SUCCESS", "工作流执行完成")
        else:
            dialog._append_log("ERROR", f"工作流执行失败: {result.get('error', '未知错误')}")

        self.load_executions()

    def delete_workflow(self, workflow):
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除工作流 '{workflow.name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.workflow_service.delete(workflow.id, user_id=self.current_user_id)
            self.load_workflows()

    def load_executions(self):
        executions = self.workflow_service.get_executions(limit=100)

        self.exec_table.setRowCount(len(executions))

        status_colors = {
            "pending": "#FFC107",
            "running": "#2196F3",
            "success": "#4CAF50",
            "failed": "#F44336"
        }

        for row, execution in enumerate(executions):
            self.exec_table.setItem(row, 0, QTableWidgetItem(str(execution.id)))

            workflow_name = execution.workflow.name if execution.workflow else f"#{execution.workflow_id}"
            self.exec_table.setItem(row, 1, QTableWidgetItem(workflow_name))

            status_item = QTableWidgetItem(execution.status)
            status_item.setBackground(QColor(status_colors.get(execution.status, "#9E9E9E")))
            self.exec_table.setItem(row, 2, status_item)

            started_at = execution.started_at.strftime("%Y-%m-%d %H:%M:%S") if execution.started_at else ""
            self.exec_table.setItem(row, 3, QTableWidgetItem(started_at))

            finished_at = execution.finished_at.strftime("%Y-%m-%d %H:%M:%S") if execution.finished_at else ""
            self.exec_table.setItem(row, 4, QTableWidgetItem(finished_at))

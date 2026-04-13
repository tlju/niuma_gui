from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QMessageBox, QHeaderView, QFrame, QApplication,
    QTabWidget, QTextEdit, QSplitter
)
from PyQt6.QtCore import Qt
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet
from services.workflow_service import WorkflowService
from models.workflow_run import RunStatus, TriggerType
from typing import Optional

logger = get_logger(__name__)


class RunDetailDialog(QDialog):
    def __init__(self, workflow_service: WorkflowService, run_id: int, parent=None):
        super().__init__(parent)
        self.workflow_service = workflow_service
        self.run_id = run_id
        self.setWindowTitle(f"执行记录详情 - ID: {run_id}")
        self.setMinimumSize(800, 600)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.Shape.StyledPanel)
        info_layout = QHBoxLayout(info_frame)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        info_layout.addWidget(QLabel("状态:"))
        info_layout.addWidget(self.status_label)
        info_layout.addStretch()

        self.time_label = QLabel()
        info_layout.addWidget(self.time_label)

        layout.addWidget(info_frame)

        tabs = QTabWidget()

        nodes_tab = QWidget()
        nodes_layout = QVBoxLayout(nodes_tab)
        self.nodes_table = QTableWidget()
        self.nodes_table.setColumnCount(5)
        self.nodes_table.setHorizontalHeaderLabels([
            "节点Key", "状态", "开始时间", "结束时间", "错误信息"
        ])
        self.nodes_table.setAlternatingRowColors(True)
        self.nodes_table.verticalHeader().setVisible(False)
        self.nodes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.nodes_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        nodes_layout.addWidget(self.nodes_table)
        tabs.addTab(nodes_tab, "节点执行记录")

        output_tab = QWidget()
        output_layout = QVBoxLayout(output_tab)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        tabs.addTab(output_tab, "执行输出")

        layout.addWidget(tabs)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def load_data(self):
        run = self.workflow_service.get_run_by_id(self.run_id)
        if not run:
            return

        status_map = {
            RunStatus.PENDING: ("待执行", "gray"),
            RunStatus.RUNNING: ("执行中", "blue"),
            RunStatus.SUCCESS: ("成功", "green"),
            RunStatus.FAILED: ("失败", "red"),
            RunStatus.CANCELLED: ("已取消", "orange"),
        }
        status_text, color = status_map.get(run.status, ("未知", "gray"))
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {color};")

        time_text = ""
        if run.start_time:
            time_text += f"开始: {run.start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        if run.end_time:
            time_text += f"  |  结束: {run.end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        self.time_label.setText(time_text)

        node_runs = self.workflow_service.get_run_nodes(self.run_id)
        self.nodes_table.setRowCount(len(node_runs))

        outputs = []
        for row, node_run in enumerate(node_runs):
            self.nodes_table.setItem(row, 0, QTableWidgetItem(node_run.node_key[:8] + "..."))

            node_status_text, node_color = status_map.get(node_run.status, ("未知", "gray"))
            status_item = QTableWidgetItem(node_status_text)
            status_item.setForeground(Qt.GlobalColor.darkGreen if node_run.status == RunStatus.SUCCESS else Qt.GlobalColor.red)
            self.nodes_table.setItem(row, 1, status_item)

            self.nodes_table.setItem(row, 2, QTableWidgetItem(
                node_run.start_time.strftime('%H:%M:%S') if node_run.start_time else ""
            ))
            self.nodes_table.setItem(row, 3, QTableWidgetItem(
                node_run.end_time.strftime('%H:%M:%S') if node_run.end_time else ""
            ))
            self.nodes_table.setItem(row, 4, QTableWidgetItem(node_run.error or ""))

            if node_run.output:
                outputs.append(f"[{node_run.node_key[:8]}] {node_run.output}")

        self.output_text.setPlainText("\n".join(outputs))


class WorkflowRunsPage(QWidget):
    def __init__(self, workflow_service: WorkflowService, parent=None):
        super().__init__(parent)
        self.workflow_service = workflow_service
        self.runs_data = []
        self.init_ui()
        self.load_runs()

    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "workflow_runs_page"])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        toolbar_frame = QFrame()
        toolbar_frame.setProperty("class", "toolbar")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)

        self.refresh_btn = QPushButton("  刷新")
        self.refresh_btn.setIcon(icons.refresh_icon())
        self.refresh_btn.setMinimumHeight(34)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_runs)
        toolbar_layout.addWidget(self.refresh_btn)

        toolbar_layout.addStretch()
        layout.addWidget(toolbar_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "工作流ID", "状态", "触发方式", "开始时间", "结束时间", "操作"
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
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        self.table.doubleClicked.connect(self.show_detail)
        layout.addWidget(self.table)

    def load_runs(self):
        try:
            workflows = self.workflow_service.get_all_workflows()
            all_runs = []
            for workflow in workflows:
                runs = self.workflow_service.get_runs_by_workflow(workflow.id)
                all_runs.extend(runs)

            all_runs.sort(key=lambda r: r.created_at or r.id, reverse=True)
            self.runs_data = all_runs
            self._populate_table(all_runs)
            logger.info(f"加载了 {len(all_runs)} 条执行记录")
        except Exception as e:
            logger.error(f"加载执行记录失败: {e}")
            QMessageBox.critical(self, "错误", f"加载执行记录失败:\n{str(e)}")

    def _populate_table(self, runs):
        self.table.setRowCount(len(runs))

        status_map = {
            RunStatus.PENDING: "待执行",
            RunStatus.RUNNING: "执行中",
            RunStatus.SUCCESS: "成功",
            RunStatus.FAILED: "失败",
            RunStatus.CANCELLED: "已取消",
        }

        trigger_map = {
            TriggerType.MANUAL: "手动",
            TriggerType.SCHEDULED: "定时",
        }

        for row, run in enumerate(runs):
            self.table.setItem(row, 0, QTableWidgetItem(str(run.id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(run.workflow_id)))

            status_item = QTableWidgetItem(status_map.get(run.status, "未知"))
            if run.status == RunStatus.SUCCESS:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            elif run.status == RunStatus.FAILED:
                status_item.setForeground(Qt.GlobalColor.red)
            elif run.status == RunStatus.RUNNING:
                status_item.setForeground(Qt.GlobalColor.blue)
            self.table.setItem(row, 2, status_item)

            self.table.setItem(row, 3, QTableWidgetItem(trigger_map.get(run.trigger_type, "未知")))
            self.table.setItem(row, 4, QTableWidgetItem(
                run.start_time.strftime('%Y-%m-%d %H:%M:%S') if run.start_time else ""
            ))
            self.table.setItem(row, 5, QTableWidgetItem(
                run.end_time.strftime('%Y-%m-%d %H:%M:%S') if run.end_time else ""
            ))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            detail_btn = QPushButton("详情")
            detail_btn.setProperty("class", "table-run")
            detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            detail_btn.clicked.connect(
                lambda checked, r=run.id: self.show_detail_by_id(r)
            )
            btn_layout.addWidget(detail_btn)

            self.table.setCellWidget(row, 6, btn_widget)

    def show_detail(self):
        indexes = self.table.selectedIndexes()
        if not indexes:
            return
        row = indexes[0].row()
        run = self.runs_data[row]
        self.show_detail_by_id(run.id)

    def show_detail_by_id(self, run_id: int):
        dialog = RunDetailDialog(self.workflow_service, run_id, self)
        dialog.exec()

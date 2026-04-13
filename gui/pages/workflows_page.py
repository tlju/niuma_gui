from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QMessageBox, QHeaderView, QFrame,
    QApplication, QTextEdit, QComboBox, QStackedWidget
)
from PyQt6.QtCore import Qt
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet
from services.workflow_service import WorkflowService
from models.workflow import WorkflowStatus
from typing import Optional

logger = get_logger(__name__)


class WorkflowDialog(QDialog):
    def __init__(self, parent=None, workflow=None):
        super().__init__(parent)
        self.workflow = workflow
        self.setWindowTitle("编辑工作流" if workflow else "新建工作流")
        self.setMinimumWidth(450)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)

        name_label = QLabel("工作流名称:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入工作流名称")
        if self.workflow:
            self.name_edit.setText(self.workflow.name)
        form_layout.addWidget(name_label)
        form_layout.addWidget(self.name_edit)

        desc_label = QLabel("描述:")
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("请输入工作流描述（可选）")
        self.desc_edit.setMaximumHeight(80)
        if self.workflow and self.workflow.description:
            self.desc_edit.setPlainText(self.workflow.description)
        form_layout.addWidget(desc_label)
        form_layout.addWidget(self.desc_edit)

        status_label = QLabel("状态:")
        self.status_combo = QComboBox()
        self.status_combo.addItem("草稿", WorkflowStatus.DRAFT)
        self.status_combo.addItem("已发布", WorkflowStatus.PUBLISHED)
        if self.workflow:
            index = self.status_combo.findData(self.workflow.status)
            if index >= 0:
                self.status_combo.setCurrentIndex(index)
        form_layout.addWidget(status_label)
        form_layout.addWidget(self.status_combo)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setProperty("class", "success")
        save_btn.setMinimumWidth(80)
        save_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "description": self.desc_edit.toPlainText().strip(),
            "status": self.status_combo.currentData()
        }


class WorkflowsPage(QWidget):
    def __init__(self, workflow_service: WorkflowService, current_user_id: int, parent=None):
        super().__init__(parent)
        self.workflow_service = workflow_service
        self.current_user_id = current_user_id
        self.workflows_data = []
        self.init_ui()
        self.load_workflows()

    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "workflows_page"])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        toolbar_frame = QFrame()
        toolbar_frame.setProperty("class", "toolbar")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)

        self.add_btn = QPushButton("  新建工作流")
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
        self.refresh_btn.clicked.connect(self.load_workflows)
        toolbar_layout.addWidget(self.refresh_btn)

        toolbar_layout.addStretch()
        layout.addWidget(toolbar_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "名称", "描述", "状态", "版本", "操作"
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
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.table.doubleClicked.connect(self.open_editor)
        layout.addWidget(self.table)

    def load_workflows(self):
        try:
            workflows = self.workflow_service.get_all_workflows()
            self.workflows_data = workflows
            self._populate_table(workflows)
            logger.info(f"加载了 {len(workflows)} 个工作流")
        except Exception as e:
            logger.error(f"加载工作流失败: {e}")
            QMessageBox.critical(self, "错误", f"加载工作流失败:\n{str(e)}")

    def _populate_table(self, workflows):
        self.table.setRowCount(len(workflows))

        for row, workflow in enumerate(workflows):
            self.table.setItem(row, 0, QTableWidgetItem(str(workflow.id)))
            self.table.setItem(row, 1, QTableWidgetItem(workflow.name))
            self.table.setItem(row, 2, QTableWidgetItem(workflow.description or ""))

            status_text = "草稿" if workflow.status == WorkflowStatus.DRAFT else "已发布"
            status_item = QTableWidgetItem(status_text)
            if workflow.status == WorkflowStatus.PUBLISHED:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            self.table.setItem(row, 3, status_item)

            self.table.setItem(row, 4, QTableWidgetItem(str(workflow.version or 1)))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            edit_btn = QPushButton("编辑")
            edit_btn.setProperty("class", "table-run")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(
                lambda checked, w=workflow: self.open_editor(w)
            )
            btn_layout.addWidget(edit_btn)

            run_btn = QPushButton("执行")
            run_btn.setProperty("class", "success")
            run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            run_btn.clicked.connect(
                lambda checked, w=workflow: self.execute_workflow(w)
            )
            btn_layout.addWidget(run_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setProperty("class", "table-delete")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.clicked.connect(
                lambda checked, w=workflow.id: self.delete_workflow(w)
            )
            btn_layout.addWidget(delete_btn)

            self.table.setCellWidget(row, 5, btn_widget)

    def show_add_dialog(self):
        dialog = WorkflowDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "提示", "请输入工作流名称")
                return

            workflow_id = self.workflow_service.create_workflow(
                name=data["name"],
                description=data["description"],
                user_id=self.current_user_id
            )

            if workflow_id:
                if data["status"] == WorkflowStatus.PUBLISHED:
                    self.workflow_service.update_workflow(
                        workflow_id,
                        status=WorkflowStatus.PUBLISHED,
                        user_id=self.current_user_id
                    )

                QMessageBox.information(self, "成功", "工作流创建成功")
                self.load_workflows()
                self._open_editor_with_id(workflow_id)
            else:
                QMessageBox.critical(self, "错误", "创建工作流失败")

    def open_editor(self, workflow=None):
        if workflow is None:
            indexes = self.table.selectedIndexes()
            if not indexes:
                QMessageBox.warning(self, "提示", "请选择要编辑的工作流")
                return
            row = indexes[0].row()
            workflow = self.workflows_data[row]

        self._open_editor_with_id(workflow.id)

    def _open_editor_with_id(self, workflow_id: int):
        from gui.pages.workflow_editor_page import WorkflowEditorPage

        main_window = self.window()
        if hasattr(main_window, 'open_workflow_editor'):
            main_window.open_workflow_editor(workflow_id)
        else:
            editor = WorkflowEditorPage(
                self.workflow_service,
                workflow_id,
                self
            )
            dialog = QDialog(self)
            dialog.setWindowTitle("工作流编辑器")
            dialog.setMinimumSize(1000, 700)
            layout = QVBoxLayout(dialog)
            layout.addWidget(editor)
            dialog.exec()

    def execute_workflow(self, workflow):
        from services.workflow_engine import WorkflowEngine
        from models.workflow_run import TriggerType

        reply = QMessageBox.question(
            self, "确认",
            f"确定要执行工作流 '{workflow.name}' 吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        engine = WorkflowEngine(self.workflow_service)
        run_id = engine.execute_workflow(workflow.id, TriggerType.MANUAL)

        QMessageBox.information(
            self, "成功",
            f"工作流已开始执行\n执行记录ID: {run_id}"
        )

    def delete_workflow(self, workflow_id: int):
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除此工作流吗？\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self.workflow_service.delete_workflow(
                workflow_id,
                user_id=self.current_user_id
            )
            if success:
                QMessageBox.information(self, "成功", "工作流已删除")
                self.load_workflows()
            else:
                QMessageBox.critical(self, "错误", "删除工作流失败")

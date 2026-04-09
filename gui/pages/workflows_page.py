from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QComboBox, QMessageBox, QHeaderView,
    QFrame, QFormLayout, QTextEdit, QTabWidget, QApplication
)
from PyQt6.QtCore import Qt
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet

logger = get_logger(__name__)


class WorkflowsPage(QWidget):
    def __init__(self, workflow_service, current_user_id, parent=None):
        super().__init__(parent)
        self.workflow_service = workflow_service
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_templates()

    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "workflows_page"])
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        toolbar_frame = QFrame()
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)

        self.add_btn = QPushButton("  添加模板")
        self.add_btn.setIcon(icons.add_icon())
        self.add_btn.setMinimumHeight(36)
        self.add_btn.clicked.connect(self.show_add_template_dialog)
        toolbar_layout.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("  刷新")
        self.refresh_btn.setIcon(icons.refresh_icon())
        self.refresh_btn.setMinimumHeight(36)
        self.refresh_btn.clicked.connect(self.load_templates)
        toolbar_layout.addWidget(self.refresh_btn)

        toolbar_layout.addStretch()

        self.count_label = QLabel("共 0 条记录")
        toolbar_layout.addWidget(self.count_label)

        layout.addWidget(toolbar_frame)

        self.tabs = QTabWidget()

        self.template_table = QTableWidget()
        self.template_table.setColumnCount(5)
        self.template_table.setHorizontalHeaderLabels(["ID", "名称", "描述", "状态", "操作"])
        self.template_table.setAlternatingRowColors(True)
        self.template_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.template_table.verticalHeader().setVisible(False)
        self.template_table.setShowGrid(False)
        self.template_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.instance_table = QTableWidget()
        self.instance_table.setColumnCount(6)
        self.instance_table.setHorizontalHeaderLabels(["ID", "名称", "模板", "状态", "开始时间", "操作"])
        self.instance_table.setAlternatingRowColors(True)
        self.instance_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.instance_table.verticalHeader().setVisible(False)
        self.instance_table.setShowGrid(False)
        self.instance_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.tabs.addTab(self.template_table, "工作流模板")
        self.tabs.addTab(self.instance_table, "工作流实例")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.all_templates = []
        self.all_instances = []

    def load_templates(self):
        try:
            self.all_templates = self.workflow_service.get_templates(limit=1000)
            self._populate_templates(self.all_templates)
            self.count_label.setText(f"共 {len(self.all_templates)} 个模板")
            self.load_instances()
            logger.info(f"加载了 {len(self.all_templates)} 个工作流模板")
        except Exception as e:
            logger.error(f"加载工作流模板失败: {e}")
            QMessageBox.critical(self, "错误", f"加载工作流模板失败:\n{e}")

    def load_instances(self):
        try:
            self.all_instances = self.workflow_service.get_instances(limit=1000)
            self._populate_instances(self.all_instances)
        except Exception as e:
            logger.error(f"加载工作流实例失败: {e}")

    def _populate_templates(self, templates):
        self.template_table.setRowCount(len(templates))
        for row, t in enumerate(templates):
            self.template_table.setItem(row, 0, QTableWidgetItem(str(t.id)))
            self.template_table.setItem(row, 1, QTableWidgetItem(t.name or ""))
            self.template_table.setItem(row, 2, QTableWidgetItem(t.description or ""))
            self.template_table.setItem(row, 3, QTableWidgetItem(t.is_active or "Y"))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 4, 4, 4)

            run_btn = QPushButton("运行")
            run_btn.clicked.connect(lambda checked, tid=t.id: self.run_template(tid))
            edit_btn = QPushButton("编辑")
            edit_btn.clicked.connect(lambda checked, tmpl=t: self.show_edit_template_dialog(tmpl))
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda checked, tid=t.id: self.delete_template(tid))

            btn_layout.addWidget(run_btn)
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            self.template_table.setCellWidget(row, 4, btn_widget)

    def _populate_instances(self, instances):
        self.instance_table.setRowCount(len(instances))
        for row, inst in enumerate(instances):
            self.instance_table.setItem(row, 0, QTableWidgetItem(str(inst.id)))
            self.instance_table.setItem(row, 1, QTableWidgetItem(inst.name or ""))
            template_name = ""
            template = self.workflow_service.get_template(inst.template_id)
            if template:
                template_name = template.name
            self.instance_table.setItem(row, 2, QTableWidgetItem(template_name))
            self.instance_table.setItem(row, 3, QTableWidgetItem(inst.status or ""))
            started_at = inst.started_at.strftime("%Y-%m-%d %H:%M") if inst.started_at else ""
            self.instance_table.setItem(row, 4, QTableWidgetItem(started_at))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 4, 4, 4)

            view_btn = QPushButton("查看")
            view_btn.clicked.connect(lambda checked, i=inst: self.show_instance_detail(i))

            btn_layout.addWidget(view_btn)
            self.instance_table.setCellWidget(row, 5, btn_widget)

    def show_add_template_dialog(self):
        dialog = WorkflowTemplateDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.workflow_service.create_template(**data, created_by=self.current_user_id)
                self.load_templates()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def show_edit_template_dialog(self, template):
        dialog = WorkflowTemplateDialog(self, template)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.workflow_service.update_template(template.id, **data)
                self.load_templates()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def delete_template(self, template_id):
        reply = QMessageBox.question(self, "确认删除", "确定要删除此模板吗？\n关联的实例也会被删除。",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.workflow_service.delete_template(template_id)
                self.load_templates()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def run_template(self, template_id):
        try:
            instance = self.workflow_service.create_instance(template_id)
            self.workflow_service.start_instance(instance.id)
            QMessageBox.information(self, "成功", f"工作流实例 {instance.name} 已启动")
            self.load_instances()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def show_instance_detail(self, instance):
        executions = self.workflow_service.get_executions(instance.id)
        dialog = WorkflowInstanceDialog(self, instance, executions)
        dialog.exec()


class WorkflowTemplateDialog(QDialog):
    def __init__(self, parent=None, template=None):
        super().__init__(parent)
        self.template = template
        self.setWindowTitle("编辑模板" if template else "添加模板")
        self.setFixedSize(500, 400)
        self.init_ui()
        if template:
            self._populate_data()

    def init_ui(self):
        layout = QFormLayout()

        self.name_input = QLineEdit()
        layout.addRow("名称:", self.name_input)

        self.desc_input = QLineEdit()
        layout.addRow("描述:", self.desc_input)

        self.definition_input = QTextEdit()
        self.definition_input.setPlaceholderText('{"nodes": [], "edges": []}')
        self.definition_input.setMaximumHeight(150)
        layout.addRow("定义(JSON):", self.definition_input)

        self.active_combo = QComboBox()
        self.active_combo.addItems(["Y", "N"])
        layout.addRow("状态:", self.active_combo)

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
        self.name_input.setText(self.template.name or "")
        self.desc_input.setText(self.template.description or "")
        self.definition_input.setPlainText(self.template.definition or "{}")
        self.active_combo.setCurrentText(self.template.is_active or "Y")

    def get_data(self):
        import json
        definition = {}
        try:
            definition = json.loads(self.definition_input.toPlainText())
        except:
            pass
        return {
            "name": self.name_input.text(),
            "description": self.desc_input.text(),
            "definition": definition,
            "is_active": self.active_combo.currentText()
        }


class WorkflowInstanceDialog(QDialog):
    def __init__(self, parent=None, instance=None, executions=None):
        super().__init__(parent)
        self.instance = instance
        self.executions = executions or []
        self.setWindowTitle(f"工作流实例: {instance.name if instance else ''}")
        self.setFixedSize(600, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"状态: {self.instance.status if self.instance else ''}"))
        if self.instance and self.instance.started_at:
            info_layout.addWidget(QLabel(f"开始时间: {self.instance.started_at.strftime('%Y-%m-%d %H:%M')}"))
        info_layout.addStretch()
        layout.addLayout(info_layout)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["步骤名称", "状态", "输出", "错误", "执行时间"])
        table.setRowCount(len(self.executions))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for row, exec in enumerate(self.executions):
            table.setItem(row, 0, QTableWidgetItem(exec.step_name or ""))
            table.setItem(row, 1, QTableWidgetItem(exec.status or ""))
            table.setItem(row, 2, QTableWidgetItem((exec.output or "")[:50]))
            table.setItem(row, 3, QTableWidgetItem((exec.error or "")[:50]))
            executed_at = exec.executed_at.strftime("%Y-%m-%d %H:%M") if exec.executed_at else ""
            table.setItem(row, 4, QTableWidgetItem(executed_at))

        layout.addWidget(table)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)

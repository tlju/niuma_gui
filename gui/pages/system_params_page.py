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


class SystemParamsPage(QWidget):
    def __init__(self, param_service, parent=None):
        super().__init__(parent)
        self.param_service = param_service
        self.init_ui()
        self.load_params()

    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "system_params_page"])
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        toolbar_frame = QFrame()
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)

        self.add_btn = QPushButton("  添加参数")
        self.add_btn.setIcon(icons.add_icon())
        self.add_btn.setMinimumHeight(36)
        self.add_btn.clicked.connect(self.show_add_dialog)
        toolbar_layout.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("  刷新")
        self.refresh_btn.setIcon(icons.refresh_icon())
        self.refresh_btn.setMinimumHeight(36)
        self.refresh_btn.clicked.connect(self.load_params)
        toolbar_layout.addWidget(self.refresh_btn)

        toolbar_layout.addSpacing(20)

        search_label = QLabel("搜索:")
        toolbar_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入参数名称、代码或描述搜索...")
        self.search_input.setMinimumWidth(250)
        self.search_input.setMinimumHeight(36)
        self.search_input.textChanged.connect(self._filter_params)
        toolbar_layout.addWidget(self.search_input)

        toolbar_layout.addStretch()

        self.count_label = QLabel("共 0 条记录")
        toolbar_layout.addWidget(self.count_label)

        layout.addWidget(toolbar_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "参数名称", "参数代码", "参数值", "状态", "描述", "操作"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.all_params = []

    def load_params(self):
        try:
            self.all_params = self.param_service.get_params(limit=1000)
            self._populate_table(self.all_params)
            self.count_label.setText(f"共 {len(self.all_params)} 条记录")
            logger.info(f"加载了 {len(self.all_params)} 个系统参数")
        except Exception as e:
            logger.error(f"加载系统参数失败: {e}")
            QMessageBox.critical(self, "错误", f"加载系统参数失败:\n{e}")

    def _populate_table(self, params):
        self.table.setRowCount(len(params))
        for row, param in enumerate(params):
            self.table.setItem(row, 0, QTableWidgetItem(str(param.id)))
            self.table.setItem(row, 1, QTableWidgetItem(param.param_name or ""))
            self.table.setItem(row, 2, QTableWidgetItem(param.param_code or ""))
            self.table.setItem(row, 3, QTableWidgetItem(param.param_value or ""))
            status_text = "启用" if param.status == 1 else "禁用"
            self.table.setItem(row, 4, QTableWidgetItem(status_text))
            self.table.setItem(row, 5, QTableWidgetItem(param.description or ""))

            edit_btn = QPushButton("编辑")
            edit_btn.setIcon(icons.edit_icon())
            edit_btn.clicked.connect(lambda checked, p=param: self.show_edit_dialog(p))
            delete_btn = QPushButton("删除")
            delete_btn.setIcon(icons.delete_icon())
            delete_btn.clicked.connect(lambda checked, pid=param.id: self.delete_param(pid))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 4, 4, 4)
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            btn_layout.addStretch()
            self.table.setCellWidget(row, 6, btn_widget)

    def _filter_params(self, text):
        if not text:
            self._populate_table(self.all_params)
            return
        filtered = [p for p in self.all_params if
                    text.lower() in (p.param_name or "").lower() or
                    text.lower() in (p.param_code or "").lower() or
                    text.lower() in (p.description or "").lower()]
        self._populate_table(filtered)

    def show_add_dialog(self):
        dialog = ParamDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.param_service.create_param(**data)
                self.load_params()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def show_edit_dialog(self, param):
        dialog = ParamDialog(self, param)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.param_service.update_param(param.id, **data)
                self.load_params()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def delete_param(self, param_id):
        reply = QMessageBox.question(self, "确认删除", "确定要删除此参数吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.param_service.delete_param(param_id)
                self.load_params()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))


class ParamDialog(QDialog):
    def __init__(self, parent=None, param=None):
        super().__init__(parent)
        self.param = param
        self.setWindowTitle("编辑参数" if param else "添加参数")
        self.setFixedSize(450, 300)
        self.init_ui()
        if param:
            self._populate_data()

    def init_ui(self):
        layout = QFormLayout()

        self.name_input = QLineEdit()
        layout.addRow("参数名称:", self.name_input)

        self.code_input = QLineEdit()
        layout.addRow("参数代码:", self.code_input)

        self.value_input = QTextEdit()
        self.value_input.setMaximumHeight(80)
        layout.addRow("参数值:", self.value_input)

        self.status_combo = QComboBox()
        self.status_combo.addItem("启用", 1)
        self.status_combo.addItem("禁用", 0)
        layout.addRow("状态:", self.status_combo)

        self.desc_input = QLineEdit()
        layout.addRow("描述:", self.desc_input)

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
        self.name_input.setText(self.param.param_name or "")
        self.code_input.setText(self.param.param_code or "")
        self.value_input.setPlainText(self.param.param_value or "")
        status = self.param.status or "active"
        index = self.status_combo.findData(status)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)
        self.desc_input.setText(self.param.description or "")

    def get_data(self):
        return {
            "param_name": self.name_input.text(),
            "param_code": self.code_input.text(),
            "param_value": self.value_input.toPlainText(),
            "status": self.status_combo.currentData(),
            "description": self.desc_input.text()
        }

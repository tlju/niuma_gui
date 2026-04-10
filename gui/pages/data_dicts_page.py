from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QComboBox, QMessageBox, QHeaderView,
    QFrame, QFormLayout, QTabWidget, QSpinBox, QApplication
)
from PyQt6.QtCore import Qt
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet

logger = get_logger(__name__)


class DataDictsPage(QWidget):
    def __init__(self, dict_service, parent=None):
        super().__init__(parent)
        self.dict_service = dict_service
        self.init_ui()
        self.load_dicts()

    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "data_dicts_page"])

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        toolbar_frame = QFrame()
        toolbar_frame.setProperty("class", "toolbar")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)

        self.add_btn = QPushButton("  添加字典")
        self.add_btn.setIcon(icons.add_icon())
        self.add_btn.setProperty("class", "success")
        self.add_btn.setMinimumHeight(34)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.show_add_dict_dialog)
        toolbar_layout.addWidget(self.add_btn)

        self.add_item_btn = QPushButton("  添加字典项")
        self.add_item_btn.setIcon(icons.add_icon())
        self.add_item_btn.setProperty("class", "success")
        self.add_item_btn.setMinimumHeight(34)
        self.add_item_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_item_btn.clicked.connect(self.show_add_item_dialog)
        self.add_item_btn.setEnabled(False)
        toolbar_layout.addWidget(self.add_item_btn)

        self.refresh_btn = QPushButton("  刷新")
        self.refresh_btn.setIcon(icons.refresh_icon())
        self.refresh_btn.setMinimumHeight(34)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_dicts)
        toolbar_layout.addWidget(self.refresh_btn)

        toolbar_layout.addStretch()

        self.count_label = QLabel("共 0 条记录")
        toolbar_layout.addWidget(self.count_label)

        layout.addWidget(toolbar_frame)

        self.tabs = QTabWidget()
        self.dict_table = QTableWidget()
        self.dict_table.setColumnCount(4)
        self.dict_table.setHorizontalHeaderLabels(["代码", "名称", "描述", "操作"])
        self.dict_table.setAlternatingRowColors(True)
        self.dict_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.dict_table.verticalHeader().setVisible(False)
        self.dict_table.setShowGrid(False)
        self.dict_table.verticalHeader().setDefaultSectionSize(42)
        self.dict_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.dict_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.dict_table.setColumnWidth(3, 180)

        self.item_table = QTableWidget()
        self.item_table.setColumnCount(4)
        self.item_table.setHorizontalHeaderLabels(["排序", "项代码", "项名称", "操作"])
        self.item_table.setAlternatingRowColors(True)
        self.item_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.item_table.verticalHeader().setVisible(False)
        self.item_table.setShowGrid(False)
        self.item_table.verticalHeader().setDefaultSectionSize(42)
        self.item_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.item_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.item_table.setColumnWidth(3, 120)

        self.tabs.addTab(self.dict_table, "字典列表")
        self.tabs.addTab(self.item_table, "字典项列表")
        self.tabs.currentChanged.connect(self.on_tab_changed)

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.all_dicts = []
        self.current_dict = None

    def load_dicts(self):
        try:
            self.all_dicts = self.dict_service.get_dicts(limit=1000)
            self._populate_dicts(self.all_dicts)
            self.count_label.setText(f"共 {len(self.all_dicts)} 条记录")
            logger.info(f"加载了 {len(self.all_dicts)} 个数据字典")
        except Exception as e:
            logger.error(f"加载数据字典失败: {e}")
            QMessageBox.critical(self, "错误", f"加载数据字典失败:\n{e}")

    def _populate_dicts(self, dicts):
        self.dict_table.setRowCount(len(dicts))
        for row, d in enumerate(dicts):
            self.dict_table.setItem(row, 0, QTableWidgetItem(d.code or ""))
            self.dict_table.setItem(row, 1, QTableWidgetItem(d.name or ""))
            self.dict_table.setItem(row, 2, QTableWidgetItem(d.description or ""))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            edit_btn = QPushButton("编辑")
            edit_btn.setProperty("class", "table-edit")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda checked, dict_obj=d: self.show_edit_dict_dialog(dict_obj))
            btn_layout.addWidget(edit_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setProperty("class", "table-delete")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.clicked.connect(lambda checked, did=d.id: self.delete_dict(did))
            btn_layout.addWidget(delete_btn)

            items_btn = QPushButton("项")
            items_btn.setProperty("class", "table-view")
            items_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            items_btn.clicked.connect(lambda checked, dict_obj=d: self.show_dict_items(dict_obj))
            btn_layout.addWidget(items_btn)

            self.dict_table.setCellWidget(row, 3, btn_widget)

    def on_dict_selected(self, item):
        row = item.row()
        if row < len(self.all_dicts):
            self.show_dict_items(self.all_dicts[row])

    def on_tab_changed(self, index):
        if index == 0:
            self.add_item_btn.setEnabled(False)

    def show_dict_items(self, dict_obj):
        self.current_dict = dict_obj
        self.tabs.setCurrentIndex(1)
        self.add_item_btn.setEnabled(True)
        self.load_dict_items(dict_obj.code)

    def load_dict_items(self, dict_code):
        try:
            items = self.dict_service.get_dict_items(dict_code)
            self._populate_items(items)
        except Exception as e:
            logger.error(f"加载字典项失败: {e}")

    def _populate_items(self, items):
        self.item_table.setRowCount(len(items))
        for row, item in enumerate(items):
            self.item_table.setItem(row, 0, QTableWidgetItem(str(item.sort_order or 0)))
            self.item_table.setItem(row, 1, QTableWidgetItem(item.item_code or ""))
            self.item_table.setItem(row, 2, QTableWidgetItem(item.item_name or ""))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            edit_btn = QPushButton("编辑")
            edit_btn.setProperty("class", "table-edit")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda checked, i=item: self.show_edit_item_dialog(i))
            btn_layout.addWidget(edit_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setProperty("class", "table-delete")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.clicked.connect(lambda checked, iid=item.id: self.delete_item(iid))
            btn_layout.addWidget(delete_btn)

            self.item_table.setCellWidget(row, 3, btn_widget)

    def show_add_dict_dialog(self):
        dialog = DictDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.dict_service.create_dict(**data)
                self.load_dicts()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def show_edit_dict_dialog(self, dict_obj):
        dialog = DictDialog(self, dict_obj)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.dict_service.update_dict(dict_obj.id, **data)
                self.load_dicts()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def delete_dict(self, dict_id):
        reply = QMessageBox.question(self, "确认删除", "确定要删除此字典吗？\n关联的字典项也会被删除。",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.dict_service.delete_dict(dict_id)
                self.load_dicts()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def show_add_item_dialog(self):
        if not self.current_dict:
            QMessageBox.warning(self, "提示", "请先选择一个字典")
            return
        dialog = DictItemDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.dict_service.create_dict_item(self.current_dict.code, **data)
                self.load_dict_items(self.current_dict.code)
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def show_edit_item_dialog(self, item):
        dialog = DictItemDialog(self, item)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.dict_service.update_dict_item(item.id, **data)
                self.load_dict_items(self.current_dict.code)
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def delete_item(self, item_id):
        reply = QMessageBox.question(self, "确认删除", "确定要删除此字典项吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.dict_service.delete_dict_item(item_id)
                self.load_dict_items(self.current_dict.code)
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))


class DictDialog(QDialog):
    def __init__(self, parent=None, dict_obj=None):
        super().__init__(parent)
        self.dict_obj = dict_obj
        self.setWindowTitle("编辑字典" if dict_obj else "添加字典")
        self.setMinimumSize(400, 220)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()
        if dict_obj:
            self._populate_data()

    def init_ui(self):
        layout = QFormLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        self.code_input = QLineEdit()
        self.code_input.setMinimumHeight(34)
        layout.addRow("代码:", self.code_input)

        self.name_input = QLineEdit()
        self.name_input.setMinimumHeight(34)
        layout.addRow("名称:", self.name_input)

        self.desc_input = QLineEdit()
        self.desc_input.setMinimumHeight(34)
        layout.addRow("描述:", self.desc_input)

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
        self.code_input.setText(self.dict_obj.code or "")
        self.name_input.setText(self.dict_obj.name or "")
        self.desc_input.setText(self.dict_obj.description or "")

    def get_data(self):
        return {
            "code": self.code_input.text(),
            "name": self.name_input.text(),
            "description": self.desc_input.text()
        }


class DictItemDialog(QDialog):
    def __init__(self, parent=None, item=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("编辑字典项" if item else "添加字典项")
        self.setMinimumSize(400, 220)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()
        if item:
            self._populate_data()

    def init_ui(self):
        layout = QFormLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        self.code_input = QLineEdit()
        self.code_input.setMinimumHeight(34)
        layout.addRow("项代码:", self.code_input)

        self.name_input = QLineEdit()
        self.name_input.setMinimumHeight(34)
        layout.addRow("项名称:", self.name_input)

        self.sort_input = QSpinBox()
        self.sort_input.setMaximum(9999)
        self.sort_input.setMinimumHeight(34)
        layout.addRow("排序:", self.sort_input)

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
        self.code_input.setText(self.item.item_code or "")
        self.name_input.setText(self.item.item_name or "")
        self.sort_input.setValue(self.item.sort_order or 0)

    def get_data(self):
        return {
            "item_code": self.code_input.text(),
            "item_name": self.name_input.text(),
            "sort_order": self.sort_input.value()
        }

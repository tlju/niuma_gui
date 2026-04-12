from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QMessageBox, QHeaderView,
    QFrame, QApplication, QComboBox
)
from PyQt6.QtCore import Qt
from core.workers import ScriptLoadWorker
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet
from gui.code_editor import CodeEditor

logger = get_logger(__name__)

class ScriptsPage(QWidget):
    def __init__(self, script_service, current_user_id, dict_service=None, param_service=None, parent=None):
        super().__init__(parent)
        self.script_service = script_service
        self.current_user_id = current_user_id
        self.dict_service = dict_service
        self.param_service = param_service
        self.loading_worker = None
        self.scripts_data = []
        self.dict_cache = {}
        self._load_dict_cache()
        self.init_ui()
        self.load_scripts()

    def _load_dict_cache(self):
        if self.dict_service:
            items = self.dict_service.get_dict_items("script_language")
            self.dict_cache["script_language"] = {item.item_code: item.item_name for item in items}

    def _get_language_name(self, language_code):
        if not language_code:
            return ""
        if "script_language" in self.dict_cache and language_code in self.dict_cache["script_language"]:
            return self.dict_cache["script_language"][language_code]
        return language_code

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

        self.table.doubleClicked.connect(self.show_detail_dialog)

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
        self.scripts_data = scripts
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
            language_name = self._get_language_name(script.language)
            self.table.setItem(row, 3, QTableWidgetItem(language_name))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            edit_btn = QPushButton("编辑")
            edit_btn.setProperty("class", "table-run")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(
                lambda checked, s=script: self.show_edit_dialog(s)
            )
            btn_layout.addWidget(edit_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setProperty("class", "table-delete")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.clicked.connect(
                lambda checked, s=script.id: self.delete_script(s)
            )
            btn_layout.addWidget(delete_btn)

            self.table.setCellWidget(row, 4, btn_widget)

    def show_add_dialog(self):
        dialog = ScriptDialog(self, dict_service=self.dict_service, param_service=self.param_service)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, content, description, language = dialog.get_data()
            self.script_service.create(
                name=name,
                content=content,
                description=description,
                language=language,
                created_by=self.current_user_id
            )
            self.load_scripts()

    def show_edit_dialog(self, script):
        dialog = ScriptDialog(self, script=script, dict_service=self.dict_service, param_service=self.param_service)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, content, description, language = dialog.get_data()
            self.script_service.update(
                script_id=script.id,
                name=name,
                content=content,
                description=description,
                language=language,
                updated_by=self.current_user_id
            )
            self.load_scripts()

    def show_detail_dialog(self, index):
        row = index.row()
        if row < len(self.scripts_data):
            script = self.scripts_data[row]
            dialog = ScriptDetailDialog(script, self, dict_service=self.dict_service)
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
    def __init__(self, parent=None, script=None, dict_service=None, param_service=None):
        super().__init__(parent)
        self.script = script
        self.dict_service = dict_service
        self.param_service = param_service
        self.setWindowTitle("编辑脚本" if script else "添加脚本")
        self.setMinimumSize(700, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()
        self._load_dict_data()

        if script:
            self.name_input.setText(script.name)
            self.desc_input.setText(script.description or "")
            self.content_input.set_text(script.content or "")
            self._set_language(script.language)

    def _load_dict_data(self):
        if self.dict_service:
            items = self.dict_service.get_dict_items("script_language")
            for item in items:
                self.language_combo.addItem(item.item_name, item.item_code)

    def _set_language(self, language_code):
        if not language_code:
            return
        index = self.language_combo.findData(language_code)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
            self._on_language_changed(index)

    def _on_language_changed(self, index):
        language_code = self.language_combo.currentData()
        if language_code:
            self.content_input.set_language(language_code)

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

        layout.addWidget(QLabel("语言: *"))
        self.language_combo = QComboBox()
        self.language_combo.setMinimumHeight(34)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        layout.addWidget(self.language_combo)

        layout.addWidget(QLabel("脚本内容:"))
        self.content_input = CodeEditor(param_service=self.param_service, dict_service=self.dict_service)
        self.content_input.setMinimumHeight(300)
        layout.addWidget(self.content_input)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        ok_btn = QPushButton("确定")
        ok_btn.setProperty("class", "success")
        ok_btn.setMinimumHeight(38)
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _on_accept(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入脚本名称")
            return
        if not self.language_combo.currentData():
            QMessageBox.warning(self, "提示", "请选择脚本语言")
            return
        if not self.content_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入脚本内容")
            return
        self.accept()

    def get_data(self):
        return (
            self.name_input.text().strip(),
            self.content_input.text(),
            self.desc_input.text().strip(),
            self.language_combo.currentData()
        )


class ScriptDetailDialog(QDialog):
    def __init__(self, script, parent=None, dict_service=None):
        super().__init__(parent)
        self.script = script
        self.dict_service = dict_service
        self.setWindowTitle(f"脚本详情: {script.name}")
        self.setMinimumSize(700, 550)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()

    def _get_language_name(self, language_code):
        if not language_code:
            return "无"
        if self.dict_service:
            items = self.dict_service.get_dict_items("script_language")
            for item in items:
                if item.item_code == language_code:
                    return item.item_name
        return language_code

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        name_label = QLabel(f"<b>名称:</b> {self.script.name}")
        name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info_layout.addWidget(name_label)

        desc_text = self.script.description or "无"
        desc_label = QLabel(f"<b>描述:</b> {desc_text}")
        desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label)

        lang_text = self._get_language_name(self.script.language)
        lang_label = QLabel(f"<b>语言:</b> {lang_text}")
        lang_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info_layout.addWidget(lang_label)

        layout.addLayout(info_layout)

        layout.addWidget(QLabel("脚本内容:"))
        self.content_display = CodeEditor()
        self.content_display.set_text(self.script.content or "")
        self.content_display.set_read_only(True)
        self.content_display.setMinimumHeight(300)
        if self.script.language:
            self.content_display.set_language(self.script.language)
        layout.addWidget(self.content_display)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        close_btn = QPushButton("关闭")
        close_btn.setProperty("class", "secondary")
        close_btn.setMinimumHeight(38)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        self.setLayout(layout)

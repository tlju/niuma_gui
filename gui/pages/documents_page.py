from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QComboBox, QMessageBox, QHeaderView,
    QFrame, QFormLayout, QApplication
)
from PyQt6.QtCore import Qt
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet
from gui.rich_text_editor import RichTextEditor

logger = get_logger(__name__)


class DocumentsPage(QWidget):
    def __init__(self, document_service, current_user_id, parent=None):
        super().__init__(parent)
        self.document_service = document_service
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_documents()

    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "documents_page"])

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        toolbar_frame = QFrame()
        toolbar_frame.setProperty("class", "toolbar")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)

        self.add_btn = QPushButton("  添加文档")
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
        self.refresh_btn.clicked.connect(self.load_documents)
        toolbar_layout.addWidget(self.refresh_btn)

        toolbar_layout.addSpacing(20)

        category_label = QLabel("分类:")
        toolbar_layout.addWidget(category_label)

        self.category_combo = QComboBox()
        self.category_combo.setMinimumHeight(34)
        self.category_combo.addItem("全部", "")
        self.category_combo.currentIndexChanged.connect(self.load_documents)
        toolbar_layout.addWidget(self.category_combo)

        toolbar_layout.addSpacing(20)

        search_label = QLabel("搜索:")
        toolbar_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索标题或内容...")
        self.search_input.setMinimumWidth(200)
        self.search_input.setMinimumHeight(34)
        self.search_input.textChanged.connect(self._filter_documents)
        toolbar_layout.addWidget(self.search_input)

        toolbar_layout.addStretch()

        self.count_label = QLabel("共 0 条记录")
        toolbar_layout.addWidget(self.count_label)

        layout.addWidget(toolbar_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "标题", "分类", "标签", "创建时间", "操作"])
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

        self.all_documents = []

    def load_documents(self, reload_categories=True):
        try:
            category = self.category_combo.currentData()
            if category:
                self.all_documents = self.document_service.get_documents(category=category, limit=1000)
            else:
                self.all_documents = self.document_service.get_documents(limit=1000)
            self._populate_table(self.all_documents)
            self.count_label.setText(f"共 {len(self.all_documents)} 条记录")
            if reload_categories:
                self._load_categories()
            logger.info(f"加载了 {len(self.all_documents)} 个文档")
        except Exception as e:
            logger.error(f"加载文档失败: {e}")
            QMessageBox.critical(self, "错误", f"加载文档失败:\n{e}")

    def _load_categories(self):
        try:
            categories = self.document_service.get_categories()
            current_category = self.category_combo.currentData()
            self.category_combo.blockSignals(True)
            self.category_combo.clear()
            self.category_combo.addItem("全部", "")
            for cat in categories:
                self.category_combo.addItem(cat, cat)
            if current_category:
                index = self.category_combo.findData(current_category)
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)
            self.category_combo.blockSignals(False)
        except Exception as e:
            logger.error(f"加载分类失败: {e}")
            self.category_combo.blockSignals(False)

    def _populate_table(self, documents):
        self.table.setRowCount(len(documents))
        for row, doc in enumerate(documents):
            self.table.setItem(row, 0, QTableWidgetItem(str(doc.id)))
            self.table.setItem(row, 1, QTableWidgetItem(doc.title or ""))
            self.table.setItem(row, 2, QTableWidgetItem(doc.category or ""))
            self.table.setItem(row, 3, QTableWidgetItem(doc.tags or ""))
            created_at = doc.created_at.strftime("%Y-%m-%d %H:%M") if doc.created_at else ""
            self.table.setItem(row, 4, QTableWidgetItem(created_at))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            view_btn = QPushButton("查看")
            view_btn.setProperty("class", "table-view")
            view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            view_btn.clicked.connect(lambda checked, d=doc: self.show_view_dialog(d))
            btn_layout.addWidget(view_btn)

            edit_btn = QPushButton("编辑")
            edit_btn.setProperty("class", "table-edit")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda checked, d=doc: self.show_edit_dialog(d))
            btn_layout.addWidget(edit_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setProperty("class", "table-delete")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.clicked.connect(lambda checked, did=doc.id: self.delete_document(did))
            btn_layout.addWidget(delete_btn)

            self.table.setCellWidget(row, 5, btn_widget)

    def _filter_documents(self, text):
        if not text:
            self._populate_table(self.all_documents)
            return
        filtered = [d for d in self.all_documents if
                    text.lower() in (d.title or "").lower() or
                    text.lower() in (d.content or "").lower()]
        self._populate_table(filtered)

    def show_add_dialog(self):
        dialog = DocumentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.document_service.create_document(**data, created_by=self.current_user_id)
                self.load_documents()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def show_view_dialog(self, doc):
        dialog = DocumentDialog(self, doc, readonly=True)
        dialog.exec()

    def show_edit_dialog(self, doc):
        dialog = DocumentDialog(self, doc)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.document_service.update_document(doc.id, **data)
                self.load_documents()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def delete_document(self, doc_id):
        reply = QMessageBox.question(self, "确认删除", "确定要删除此文档吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.document_service.delete_document(doc_id)
                self.load_documents()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))


class DocumentDialog(QDialog):
    def __init__(self, parent=None, document=None, readonly=False):
        super().__init__(parent)
        self.document = document
        self.readonly = readonly
        self.setWindowTitle("查看文档" if readonly else ("编辑文档" if document else "添加文档"))
        self.resize(800, 600)
        self.setMinimumSize(600, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()
        if document:
            self._populate_data()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 16, 20, 16)

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(10)

        self.title_input = QLineEdit()
        self.title_input.setMinimumHeight(34)
        if self.readonly:
            self.title_input.setReadOnly(True)
        form_layout.addRow("标题:", self.title_input)

        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("如: 技术文档、操作手册等")
        self.category_input.setMinimumHeight(34)
        if self.readonly:
            self.category_input.setReadOnly(True)
        form_layout.addRow("分类:", self.category_input)

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("多个标签用逗号分隔")
        self.tags_input.setMinimumHeight(34)
        if self.readonly:
            self.tags_input.setReadOnly(True)
        form_layout.addRow("标签:", self.tags_input)

        main_layout.addWidget(form_widget)

        content_label = QLabel("内容:")
        main_layout.addWidget(content_label)

        self.content_input = RichTextEditor()
        self.content_input.setMinimumHeight(300)
        if self.readonly:
            self.content_input.set_read_only(True)

        main_layout.addWidget(self.content_input)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        if not self.readonly:
            ok_btn = QPushButton("确定")
            ok_btn.setProperty("class", "success")
            ok_btn.setMinimumHeight(38)
            ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            ok_btn.clicked.connect(self.accept)
            btn_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("关闭" if self.readonly else "取消")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def _populate_data(self):
        self.title_input.setText(self.document.title or "")
        self.category_input.setText(self.document.category or "")
        self.tags_input.setText(self.document.tags or "")
        self.content_input.set_text(self.document.content or "")

    def get_data(self):
        return {
            "title": self.title_input.text(),
            "category": self.category_input.text(),
            "tags": self.tags_input.text(),
            "content": self.content_input.get_text()
        }

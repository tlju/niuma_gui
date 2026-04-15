import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QFontComboBox, QComboBox, QToolButton, QColorDialog,
    QFileDialog, QSpinBox, QLabel, QFrame, QMenu, QGridLayout
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import (
    QTextCharFormat, QTextCursor, QFont, QColor, QIcon,
    QAction, QTextBlockFormat, QTextListFormat, QPixmap
)
from core.logger import get_logger

logger = get_logger(__name__)


class RichTextEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    @staticmethod
    def _get_default_font() -> QFont:
        if sys.platform == "win32":
            return QFont("Microsoft YaHei", 12)
        else:
            font = QFont("DejaVu Sans", 12)
            if not font.exactMatch():
                font = QFont("Liberation Sans", 12)
            if not font.exactMatch():
                font = QFont("Ubuntu", 12)
            if not font.exactMatch():
                font = QFont("SansSerif", 12)
            return font

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._toolbar = self._create_toolbar()
        layout.addWidget(self._toolbar)

        self._editor = QTextEdit()
        self._editor.setAcceptRichText(True)
        self._editor.setPlaceholderText("在此输入内容...")
        self._editor.setMinimumHeight(200)
        self._editor.setFont(self._get_default_font())
        self._editor.currentCharFormatChanged.connect(self._update_toolbar_state)
        self._editor.cursorPositionChanged.connect(self._update_toolbar_state)
        layout.addWidget(self._editor)

        self._update_toolbar_state()

    def _create_toolbar(self):
        toolbar = QFrame()
        toolbar.setProperty("class", "rich-text-toolbar")
        main_layout = QVBoxLayout(toolbar)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(4)

        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(4)

        btn_style = """
            QToolButton {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 4px;
                min-width: 28px;
                min-height: 24px;
            }
            QToolButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QToolButton:pressed {
                background-color: #dee2e6;
            }
            QToolButton:checked {
                background-color: #d0ebff;
                border-color: #339af0;
            }
        """

        font_label = QLabel("字体:")
        font_label.setStyleSheet("color: #495057; font-size: 12px;")
        row1_layout.addWidget(font_label)

        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(self._get_default_font())
        self._font_combo.setMinimumWidth(120)
        self._font_combo.setMaximumWidth(150)
        self._font_combo.currentFontChanged.connect(self._on_font_changed)
        row1_layout.addWidget(self._font_combo)

        size_label = QLabel("字号:")
        size_label.setStyleSheet("color: #495057; font-size: 12px; margin-left: 8px;")
        row1_layout.addWidget(size_label)

        self._font_size = QSpinBox()
        self._font_size.setRange(6, 72)
        self._font_size.setValue(15)
        self._font_size.setMinimumWidth(50)
        self._font_size.valueChanged.connect(self._on_font_size_changed)
        row1_layout.addWidget(self._font_size)

        row1_layout.addSpacing(8)

        self._bold_btn = QToolButton()
        self._bold_btn.setText("B")
        self._bold_btn.setToolTip("粗体 (Ctrl+B)")
        self._bold_btn.setStyleSheet(btn_style + "QToolButton { font-weight: bold; }")
        self._bold_btn.setCheckable(True)
        self._bold_btn.clicked.connect(self._toggle_bold)
        row1_layout.addWidget(self._bold_btn)

        self._italic_btn = QToolButton()
        self._italic_btn.setText("I")
        self._italic_btn.setToolTip("斜体 (Ctrl+I)")
        self._italic_btn.setStyleSheet(btn_style + "QToolButton { font-style: italic; }")
        self._italic_btn.setCheckable(True)
        self._italic_btn.clicked.connect(self._toggle_italic)
        row1_layout.addWidget(self._italic_btn)

        self._underline_btn = QToolButton()
        self._underline_btn.setText("U")
        self._underline_btn.setToolTip("下划线 (Ctrl+U)")
        self._underline_btn.setStyleSheet(btn_style + "QToolButton { text-decoration: underline; }")
        self._underline_btn.setCheckable(True)
        self._underline_btn.clicked.connect(self._toggle_underline)
        row1_layout.addWidget(self._underline_btn)

        self._strike_btn = QToolButton()
        self._strike_btn.setText("S")
        self._strike_btn.setToolTip("删除线")
        self._strike_btn.setStyleSheet(btn_style + "QToolButton { text-decoration: line-through; }")
        self._strike_btn.setCheckable(True)
        self._strike_btn.clicked.connect(self._toggle_strikethrough)
        row1_layout.addWidget(self._strike_btn)

        row1_layout.addSpacing(8)

        self._color_btn = QToolButton()
        self._color_btn.setText("A")
        self._color_btn.setToolTip("文字颜色")
        self._color_btn.setStyleSheet(btn_style)
        self._color_btn.clicked.connect(self._choose_color)
        row1_layout.addWidget(self._color_btn)

        self._highlight_btn = QToolButton()
        self._highlight_btn.setToolTip("背景高亮")
        self._highlight_btn.setStyleSheet(btn_style)
        self._highlight_btn.clicked.connect(self._choose_highlight)
        highlight_icon = self._create_highlight_icon()
        self._highlight_btn.setIcon(highlight_icon)
        self._highlight_btn.setIconSize(QSize(16, 16))
        row1_layout.addWidget(self._highlight_btn)

        row1_layout.addStretch()

        align_left_btn = QToolButton()
        align_left_btn.setToolTip("左对齐")
        align_left_btn.setStyleSheet(btn_style)
        align_left_btn.clicked.connect(lambda: self._set_alignment(Qt.AlignmentFlag.AlignLeft))
        align_left_btn.setText("≡")
        row2_layout.addWidget(align_left_btn)

        align_center_btn = QToolButton()
        align_center_btn.setToolTip("居中对齐")
        align_center_btn.setStyleSheet(btn_style)
        align_center_btn.clicked.connect(lambda: self._set_alignment(Qt.AlignmentFlag.AlignHCenter))
        align_center_btn.setText("☰")
        row2_layout.addWidget(align_center_btn)

        align_right_btn = QToolButton()
        align_right_btn.setToolTip("右对齐")
        align_right_btn.setStyleSheet(btn_style)
        align_right_btn.clicked.connect(lambda: self._set_alignment(Qt.AlignmentFlag.AlignRight))
        align_right_btn.setText("≡")
        row2_layout.addWidget(align_right_btn)

        row2_layout.addSpacing(8)

        self._list_menu = QMenu(self)
        bullet_action = QAction("无序列表", self)
        bullet_action.triggered.connect(lambda: self._insert_list(QTextListFormat.Style.ListDisc))
        self._list_menu.addAction(bullet_action)
        decimal_action = QAction("有序列表", self)
        decimal_action.triggered.connect(lambda: self._insert_list(QTextListFormat.Style.ListDecimal))
        self._list_menu.addAction(decimal_action)

        list_btn = QToolButton()
        list_btn.setToolTip("列表")
        list_btn.setStyleSheet(btn_style)
        list_btn.setText("≡≡")
        list_btn.setMenu(self._list_menu)
        list_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        row2_layout.addWidget(list_btn)

        indent_btn = QToolButton()
        indent_btn.setToolTip("增加缩进")
        indent_btn.setStyleSheet(btn_style)
        indent_btn.clicked.connect(self._indent)
        indent_btn.setText("→")
        row2_layout.addWidget(indent_btn)

        unindent_btn = QToolButton()
        unindent_btn.setToolTip("减少缩进")
        unindent_btn.setStyleSheet(btn_style)
        unindent_btn.clicked.connect(self._unindent)
        unindent_btn.setText("←")
        row2_layout.addWidget(unindent_btn)

        row2_layout.addSpacing(8)

        link_btn = QToolButton()
        link_btn.setToolTip("插入链接")
        link_btn.setStyleSheet(btn_style)
        link_btn.clicked.connect(self._insert_link)
        link_btn.setText("🔗")
        row2_layout.addWidget(link_btn)

        image_btn = QToolButton()
        image_btn.setToolTip("插入图片")
        image_btn.setStyleSheet(btn_style)
        image_btn.clicked.connect(self._insert_image)
        image_btn.setText("🖼")
        row2_layout.addWidget(image_btn)

        table_btn = QToolButton()
        table_btn.setToolTip("插入表格")
        table_btn.setStyleSheet(btn_style)
        table_btn.clicked.connect(self._insert_table)
        table_btn.setText("⊞")
        row2_layout.addWidget(table_btn)

        row2_layout.addSpacing(8)

        hr_btn = QToolButton()
        hr_btn.setToolTip("插入分割线")
        hr_btn.setStyleSheet(btn_style)
        hr_btn.clicked.connect(self._insert_horizontal_rule)
        hr_btn.setText("—")
        row2_layout.addWidget(hr_btn)

        clear_btn = QToolButton()
        clear_btn.setToolTip("清除格式")
        clear_btn.setStyleSheet(btn_style)
        clear_btn.clicked.connect(self._clear_format)
        clear_btn.setText("✕")
        row2_layout.addWidget(clear_btn)

        row2_layout.addStretch()

        main_layout.addLayout(row1_layout)
        main_layout.addLayout(row2_layout)

        return toolbar

    def _create_highlight_icon(self):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        from PyQt6.QtGui import QPainter, QBrush
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(QColor("#ffeb3b")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 8, 16, 8)
        painter.end()
        return QIcon(pixmap)

    def _update_toolbar_state(self):
        cursor = self._editor.textCursor()
        char_format = cursor.charFormat()

        self._font_combo.blockSignals(True)
        self._font_combo.setCurrentFont(char_format.font())
        self._font_combo.blockSignals(False)

        self._font_size.blockSignals(True)
        font_size = char_format.fontPointSize()
        if font_size == 0:
            font_size = 11
        self._font_size.setValue(int(font_size))
        self._font_size.blockSignals(False)

        self._bold_btn.blockSignals(True)
        self._bold_btn.setChecked(char_format.fontWeight() == QFont.Weight.Bold)
        self._bold_btn.blockSignals(False)

        self._italic_btn.blockSignals(True)
        self._italic_btn.setChecked(char_format.fontItalic())
        self._italic_btn.blockSignals(False)

        self._underline_btn.blockSignals(True)
        self._underline_btn.setChecked(char_format.fontUnderline())
        self._underline_btn.blockSignals(False)

        self._strike_btn.blockSignals(True)
        self._strike_btn.setChecked(char_format.fontStrikeOut())
        self._strike_btn.blockSignals(False)

    def _on_font_changed(self, font):
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            char_format = QTextCharFormat()
            char_format.setFontFamily(font.family())
            cursor.mergeCharFormat(char_format)
        else:
            char_format = self._editor.currentCharFormat()
            char_format.setFontFamily(font.family())
            self._editor.setCurrentCharFormat(char_format)

    def _on_font_size_changed(self, size):
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            char_format = QTextCharFormat()
            char_format.setFontPointSize(size)
            cursor.mergeCharFormat(char_format)
        else:
            char_format = self._editor.currentCharFormat()
            char_format.setFontPointSize(size)
            self._editor.setCurrentCharFormat(char_format)

    def _toggle_bold(self):
        cursor = self._editor.textCursor()
        char_format = QTextCharFormat()
        if self._bold_btn.isChecked():
            char_format.setFontWeight(QFont.Weight.Bold)
        else:
            char_format.setFontWeight(QFont.Weight.Normal)
        cursor.mergeCharFormat(char_format)

    def _toggle_italic(self):
        cursor = self._editor.textCursor()
        char_format = QTextCharFormat()
        char_format.setFontItalic(self._italic_btn.isChecked())
        cursor.mergeCharFormat(char_format)

    def _toggle_underline(self):
        cursor = self._editor.textCursor()
        char_format = QTextCharFormat()
        char_format.setFontUnderline(self._underline_btn.isChecked())
        cursor.mergeCharFormat(char_format)

    def _toggle_strikethrough(self):
        cursor = self._editor.textCursor()
        char_format = QTextCharFormat()
        char_format.setFontStrikeOut(self._strike_btn.isChecked())
        cursor.mergeCharFormat(char_format)

    def _choose_color(self):
        color = QColorDialog.getColor(Qt.GlobalColor.black, self, "选择文字颜色")
        if color.isValid():
            cursor = self._editor.textCursor()
            char_format = QTextCharFormat()
            char_format.setForeground(color)
            cursor.mergeCharFormat(char_format)

    def _choose_highlight(self):
        color = QColorDialog.getColor(QColor("#ffeb3b"), self, "选择背景颜色")
        if color.isValid():
            cursor = self._editor.textCursor()
            char_format = QTextCharFormat()
            char_format.setBackground(color)
            cursor.mergeCharFormat(char_format)

    def _set_alignment(self, alignment):
        self._editor.setAlignment(alignment)

    def _insert_list(self, style):
        cursor = self._editor.textCursor()
        cursor.insertList(style)

    def _indent(self):
        cursor = self._editor.textCursor()
        cursor.insertText("\t")

    def _unindent(self):
        cursor = self._editor.textCursor()
        cursor.deletePreviousChar()

    def _insert_link(self):
        cursor = self._editor.textCursor()
        selected_text = cursor.selectedText()
        if selected_text:
            cursor.insertText(f'<a href="url">{selected_text}</a>')
        else:
            cursor.insertText('<a href="url">链接文字</a>')

    def _insert_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if file_path:
            cursor = self._editor.textCursor()
            image = QPixmap(file_path)
            if not image.isNull():
                max_width = self._editor.width() - 40
                if image.width() > max_width:
                    image = image.scaledToWidth(max_width, Qt.TransformationMode.SmoothTransformation)
                cursor.insertImage(image)

    def _insert_table(self):
        cursor = self._editor.textCursor()
        table_html = """<table border="1" cellpadding="4" cellspacing="0" style="border-collapse: collapse;">
<tr><th>列1</th><th>列2</th><th>列3</th></tr>
<tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
<tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
</table><br>"""
        cursor.insertHtml(table_html)

    def _insert_horizontal_rule(self):
        cursor = self._editor.textCursor()
        cursor.insertHtml("<hr><br>")

    def _clear_format(self):
        cursor = self._editor.textCursor()
        cursor.setCharFormat(QTextCharFormat())

    def set_read_only(self, read_only: bool):
        self._editor.setReadOnly(read_only)
        self._toolbar.setVisible(not read_only)

    def set_text(self, text: str):
        if text:
            self._editor.setHtml(text)
        else:
            self._editor.clear()

    def get_text(self) -> str:
        return self._editor.toHtml()

    def set_plain_text(self, text: str):
        self._editor.setPlainText(text)

    def get_plain_text(self) -> str:
        return self._editor.toPlainText()

    def insert_text(self, text: str):
        cursor = self._editor.textCursor()
        cursor.insertText(text)

    def clear(self):
        self._editor.clear()

    def set_placeholder(self, text: str):
        self._editor.setPlaceholderText(text)

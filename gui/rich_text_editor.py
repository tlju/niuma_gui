import sys
import base64
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QFontComboBox, QComboBox, QToolButton, QColorDialog,
    QFileDialog, QSpinBox, QLabel, QFrame, QMenu, QGridLayout,
    QApplication, QAction
)
from PyQt5.QtCore import Qt, QSize, QBuffer
from PyQt5.QtGui import (
    QTextCharFormat, QTextCursor, QFont, QColor, QIcon,
    QTextBlockFormat, QTextListFormat, QPixmap, QPainter, QBrush, QImage
)
from core.logger import get_logger
from gui.style_manager import load_combined_stylesheet

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
        load_combined_stylesheet(QApplication.instance(), ["common", "rich_text_editor"])
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
        toolbar.setObjectName("richTextToolbar")
        main_layout = QHBoxLayout(toolbar)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        font_label = QLabel("字体:")
        font_label.setObjectName("toolbarLabel")
        main_layout.addWidget(font_label)

        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(self._get_default_font())
        self._font_combo.setMinimumWidth(120)
        self._font_combo.setMaximumWidth(150)
        self._font_combo.currentFontChanged.connect(self._on_font_changed)
        main_layout.addWidget(self._font_combo)

        size_label = QLabel("字号:")
        size_label.setObjectName("toolbarLabelSize")
        main_layout.addWidget(size_label)

        self._font_size = QSpinBox()
        self._font_size.setRange(6, 72)
        self._font_size.setValue(15)
        self._font_size.setMinimumWidth(50)
        self._font_size.valueChanged.connect(self._on_font_size_changed)
        main_layout.addWidget(self._font_size)

        main_layout.addSpacing(8)

        self._bold_btn = QToolButton()
        self._bold_btn.setText("B")
        self._bold_btn.setToolTip("粗体 (Ctrl+B)")
        self._bold_btn.setObjectName("toolbarBtnBold")
        self._bold_btn.setCheckable(True)
        self._bold_btn.clicked.connect(self._toggle_bold)
        main_layout.addWidget(self._bold_btn)

        self._italic_btn = QToolButton()
        self._italic_btn.setText("I")
        self._italic_btn.setToolTip("斜体 (Ctrl+I)")
        self._italic_btn.setObjectName("toolbarBtnItalic")
        self._italic_btn.setCheckable(True)
        self._italic_btn.clicked.connect(self._toggle_italic)
        main_layout.addWidget(self._italic_btn)

        self._underline_btn = QToolButton()
        self._underline_btn.setText("U")
        self._underline_btn.setToolTip("下划线 (Ctrl+U)")
        self._underline_btn.setObjectName("toolbarBtnUnderline")
        self._underline_btn.setCheckable(True)
        self._underline_btn.clicked.connect(self._toggle_underline)
        main_layout.addWidget(self._underline_btn)

        self._strike_btn = QToolButton()
        self._strike_btn.setText("S")
        self._strike_btn.setToolTip("删除线")
        self._strike_btn.setObjectName("toolbarBtnStrike")
        self._strike_btn.setCheckable(True)
        self._strike_btn.clicked.connect(self._toggle_strikethrough)
        main_layout.addWidget(self._strike_btn)

        main_layout.addSpacing(8)

        self._color_btn = QToolButton()
        self._color_btn.setText("A")
        self._color_btn.setToolTip("文字颜色")
        self._color_btn.setObjectName("toolbarBtn")
        self._color_btn.clicked.connect(self._choose_color)
        main_layout.addWidget(self._color_btn)

        self._highlight_btn = QToolButton()
        self._highlight_btn.setToolTip("背景高亮")
        self._highlight_btn.setObjectName("toolbarBtn")
        self._highlight_btn.clicked.connect(self._choose_highlight)
        highlight_icon = self._create_highlight_icon()
        self._highlight_btn.setIcon(highlight_icon)
        self._highlight_btn.setIconSize(QSize(16, 16))
        main_layout.addWidget(self._highlight_btn)

        main_layout.addSpacing(8)

        align_left_btn = QToolButton()
        align_left_btn.setToolTip("左对齐")
        align_left_btn.setObjectName("toolbarBtn")
        align_left_btn.clicked.connect(lambda: self._set_alignment(Qt.AlignLeft))
        align_left_btn.setText("≡")
        main_layout.addWidget(align_left_btn)

        align_center_btn = QToolButton()
        align_center_btn.setToolTip("居中对齐")
        align_center_btn.setObjectName("toolbarBtn")
        align_center_btn.clicked.connect(lambda: self._set_alignment(Qt.AlignHCenter))
        align_center_btn.setText("☰")
        main_layout.addWidget(align_center_btn)

        align_right_btn = QToolButton()
        align_right_btn.setToolTip("右对齐")
        align_right_btn.setObjectName("toolbarBtn")
        align_right_btn.clicked.connect(lambda: self._set_alignment(Qt.AlignRight))
        align_right_btn.setText("≡")
        main_layout.addWidget(align_right_btn)

        main_layout.addSpacing(8)

        self._list_menu = QMenu(self)
        bullet_action = QAction("无序列表", self)
        bullet_action.triggered.connect(lambda: self._insert_list(QTextListFormat.ListDisc))
        self._list_menu.addAction(bullet_action)
        decimal_action = QAction("有序列表", self)
        decimal_action.triggered.connect(lambda: self._insert_list(QTextListFormat.ListDecimal))
        self._list_menu.addAction(decimal_action)

        list_btn = QToolButton()
        list_btn.setToolTip("列表")
        list_btn.setObjectName("toolbarBtn")
        list_btn.setText("≡≡")
        list_btn.setMenu(self._list_menu)
        list_btn.setPopupMode(QToolButton.InstantPopup)
        main_layout.addWidget(list_btn)

        indent_btn = QToolButton()
        indent_btn.setToolTip("增加缩进")
        indent_btn.setObjectName("toolbarBtn")
        indent_btn.clicked.connect(self._indent)
        indent_btn.setText("→")
        main_layout.addWidget(indent_btn)

        unindent_btn = QToolButton()
        unindent_btn.setToolTip("减少缩进")
        unindent_btn.setObjectName("toolbarBtn")
        unindent_btn.clicked.connect(self._unindent)
        unindent_btn.setText("←")
        main_layout.addWidget(unindent_btn)

        main_layout.addSpacing(8)

        link_btn = QToolButton()
        link_btn.setToolTip("插入链接")
        link_btn.setObjectName("toolbarBtn")
        link_btn.clicked.connect(self._insert_link)
        link_btn.setText("🔗")
        main_layout.addWidget(link_btn)

        image_btn = QToolButton()
        image_btn.setToolTip("插入图片")
        image_btn.setObjectName("toolbarBtn")
        image_btn.clicked.connect(self._insert_image)
        image_btn.setText("🖼")
        main_layout.addWidget(image_btn)

        table_btn = QToolButton()
        table_btn.setToolTip("插入表格")
        table_btn.setObjectName("toolbarBtn")
        table_btn.clicked.connect(self._insert_table)
        table_btn.setText("⊞")
        main_layout.addWidget(table_btn)

        main_layout.addSpacing(8)

        hr_btn = QToolButton()
        hr_btn.setToolTip("插入分割线")
        hr_btn.setObjectName("toolbarBtn")
        hr_btn.clicked.connect(self._insert_horizontal_rule)
        hr_btn.setText("—")
        main_layout.addWidget(hr_btn)

        clear_btn = QToolButton()
        clear_btn.setToolTip("清除格式")
        clear_btn.setObjectName("toolbarBtn")
        clear_btn.clicked.connect(self._clear_format)
        clear_btn.setText("✕")
        main_layout.addWidget(clear_btn)

        main_layout.addStretch()

        return toolbar

    def _create_highlight_icon(self):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(QColor("#ffeb3b")))
        painter.setPen(Qt.NoPen)
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
            font_size = 15
        self._font_size.setValue(int(font_size))
        self._font_size.blockSignals(False)

        self._bold_btn.blockSignals(True)
        self._bold_btn.setChecked(char_format.fontWeight() == QFont.Bold)
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
            char_format.setFontWeight(QFont.Bold)
        else:
            char_format.setFontWeight(QFont.Normal)
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
        color = QColorDialog.getColor(Qt.black, self, "选择文字颜色")
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
                    image = image.scaledToWidth(max_width, Qt.SmoothTransformation)
                
                qimage = image.toImage()
                buffer = QBuffer()
                buffer.open(QBuffer.ReadWrite)
                qimage.save(buffer, "PNG")
                img_base64 = base64.b64encode(buffer.data()).decode('utf-8')
                
                img_html = f'<img src="data:image/png;base64,{img_base64}" style="max-width: {max_width}px;">'
                cursor.insertHtml(img_html)

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

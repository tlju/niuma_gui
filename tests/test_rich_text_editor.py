import pytest


class TestRichTextEditor:
    def test_editor_creation(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        assert editor is not None

    def test_set_text(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        test_text = "<p>Hello World</p>"
        editor.set_text(test_text)
        assert "Hello World" in editor.get_text()

    def test_get_text(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        test_text = "<p>Test Heading</p>"
        editor.set_text(test_text)
        result = editor.get_text()
        assert "Test Heading" in result

    def test_set_read_only_true(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        editor.set_read_only(True)
        assert editor._editor.isReadOnly() is True

    def test_set_read_only_false(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        editor.set_read_only(True)
        editor.set_read_only(False)
        assert editor._editor.isReadOnly() is False

    def test_empty_text(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        editor.set_text("")
        assert editor.get_plain_text() == ""

    def test_set_plain_text(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        editor.set_plain_text("Plain text content")
        assert editor.get_plain_text() == "Plain text content"

    def test_get_plain_text(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        editor.set_text("<p><b>Bold</b> text</p>")
        plain = editor.get_plain_text()
        assert "Bold" in plain
        assert "text" in plain

    def test_clear(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        editor.set_text("Some content")
        editor.clear()
        assert editor.get_plain_text() == ""

    def test_insert_text(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        editor.set_text("Hello World")
        cursor = editor._editor.textCursor()
        cursor.setPosition(5)
        editor._editor.setTextCursor(cursor)
        editor.insert_text(" Beautiful")
        assert "Beautiful" in editor.get_plain_text()

    def test_set_placeholder(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        editor.set_placeholder("Enter text here...")
        assert editor._editor.placeholderText() == "Enter text here..."


class TestRichTextEditorFormatting:
    def test_html_output_contains_formatting(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        editor.set_text("<p><b>Bold</b> and <i>italic</i></p>")
        html = editor.get_text()
        assert "Bold" in html
        assert "italic" in html

    def test_text_with_links(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        editor.set_text('<a href="https://example.com">Link</a>')
        html = editor.get_text()
        assert "Link" in html

    def test_text_with_color(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        editor.set_text('<span style="color: red;">Red text</span>')
        html = editor.get_text()
        assert "Red text" in html


class TestRichTextEditorToolbar:
    def test_toolbar_exists(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        assert editor._toolbar is not None

    def test_font_combo_exists(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        assert editor._font_combo is not None

    def test_font_size_exists(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        assert editor._font_size is not None

    def test_bold_button_exists(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        assert editor._bold_btn is not None

    def test_italic_button_exists(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        assert editor._italic_btn is not None

    def test_underline_button_exists(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        assert editor._underline_btn is not None

    def test_strike_button_exists(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        assert editor._strike_btn is not None


class TestRichTextEditorReadOnly:
    def test_toolbar_hidden_when_readonly(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        editor.show()
        editor.set_read_only(True)
        assert editor._toolbar.isHidden() is True

    def test_toolbar_visible_when_not_readonly(self, qapp):
        from gui.rich_text_editor import RichTextEditor
        editor = RichTextEditor()
        editor.show()
        editor.set_read_only(True)
        editor.set_read_only(False)
        assert editor._toolbar.isHidden() is False

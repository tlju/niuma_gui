import pytest


class TestHelpPage:
    def test_help_page_creation(self, qapp):
        from gui.pages.help_page import HelpPage
        dialog = HelpPage()
        assert dialog is not None
        assert dialog.windowTitle() == "帮助 - 运维辅助工具"

    def test_help_data_not_empty(self):
        from gui.pages.help_page import HELP_DATA
        assert len(HELP_DATA) > 0

    def test_help_data_structure(self):
        from gui.pages.help_page import HELP_DATA
        required_keys = {"id", "title", "icon_func", "content"}
        for section in HELP_DATA:
            assert required_keys.issubset(set(section.keys())), f"缺少键: {required_keys - set(section.keys())}"

    def test_help_data_unique_ids(self):
        from gui.pages.help_page import HELP_DATA
        ids = [s["id"] for s in HELP_DATA]
        assert len(ids) == len(set(ids)), "存在重复的id"

    def test_help_data_has_faq(self):
        from gui.pages.help_page import HELP_DATA
        faq_sections = [s for s in HELP_DATA if s["id"] == "faq"]
        assert len(faq_sections) == 1

    def test_sidebar_populated(self, qapp):
        from gui.pages.help_page import HelpPage
        dialog = HelpPage()
        assert dialog.sidebar_list.count() > 0

    def test_sidebar_count_matches_data(self, qapp):
        from gui.pages.help_page import HelpPage, HELP_DATA
        dialog = HelpPage()
        assert dialog.sidebar_list.count() == len(HELP_DATA)

    def test_sidebar_icons_set(self, qapp):
        from gui.pages.help_page import HelpPage
        dialog = HelpPage()
        for i in range(dialog.sidebar_list.count()):
            item = dialog.sidebar_list.item(i)
            assert item.icon() is not None

    def test_default_selection(self, qapp):
        from gui.pages.help_page import HelpPage
        dialog = HelpPage()
        assert dialog.sidebar_list.currentRow() == 0

    def test_content_displayed_on_select(self, qapp):
        from gui.pages.help_page import HelpPage
        dialog = HelpPage()
        dialog.sidebar_list.setCurrentRow(0)
        html = dialog.content_browser.toHtml()
        assert len(html) > 0

    def test_search_filter(self, qapp):
        from gui.pages.help_page import HelpPage
        dialog = HelpPage()
        initial_count = dialog.sidebar_list.count()
        dialog.search_input.setText("FAQ")
        filtered_count = dialog.sidebar_list.count()
        assert filtered_count <= initial_count
        assert filtered_count >= 1

    def test_search_clear_restores(self, qapp):
        from gui.pages.help_page import HelpPage, HELP_DATA
        dialog = HelpPage()
        initial_count = dialog.sidebar_list.count()
        dialog.search_input.setText("FAQ")
        dialog.search_input.setText("")
        restored_count = dialog.sidebar_list.count()
        assert restored_count == initial_count
        assert restored_count == len(HELP_DATA)

    def test_search_no_results(self, qapp):
        from gui.pages.help_page import HelpPage
        dialog = HelpPage()
        dialog.search_input.setText("zzzzz_not_exist_12345")
        assert dialog.sidebar_list.count() == 0
        html = dialog.content_browser.toHtml()
        assert "未找到" in html

    def test_sidebar_click_changes_content(self, qapp):
        from gui.pages.help_page import HelpPage
        dialog = HelpPage()
        dialog.sidebar_list.setCurrentRow(0)
        first_html = dialog.content_browser.toHtml()
        if dialog.sidebar_list.count() > 1:
            dialog.sidebar_list.setCurrentRow(1)
            second_html = dialog.content_browser.toHtml()
            assert first_html != second_html

    def test_content_has_html_structure(self, qapp):
        from gui.pages.help_page import HelpPage
        dialog = HelpPage()
        dialog.sidebar_list.setCurrentRow(0)
        html = dialog.content_browser.toHtml()
        assert "登录系统" in html or "<h2" in html

    def test_all_help_data_content_not_empty(self):
        from gui.pages.help_page import HELP_DATA
        for section in HELP_DATA:
            assert len(section["content"].strip()) > 0, f"内容为空: {section['id']}"

    def test_help_data_icon_funcs_exist(self):
        from gui.pages.help_page import HELP_DATA
        from gui.icons import icons
        for section in HELP_DATA:
            icon_func = getattr(icons, section["icon_func"], None)
            assert icon_func is not None, f"图标函数不存在: {section['icon_func']}"

    def test_back_button_exists(self, qapp):
        from gui.pages.help_page import HelpPage
        dialog = HelpPage()
        back_btn = dialog.findChild(object, "helpBackBtn")
        assert back_btn is not None

    def test_minimum_size(self, qapp):
        from gui.pages.help_page import HelpPage
        dialog = HelpPage()
        assert dialog.minimumWidth() == 900
        assert dialog.minimumHeight() == 600

    def test_each_section_renders(self, qapp):
        from gui.pages.help_page import HelpPage, HELP_DATA
        dialog = HelpPage()
        for i in range(len(HELP_DATA)):
            dialog.sidebar_list.setCurrentRow(i)
            html = dialog.content_browser.toHtml()
            assert len(html) > 100, f"第{i}节内容渲染异常"

    def test_help_data_covers_all_modules(self):
        from gui.pages.help_page import HELP_DATA
        expected_ids = {"login", "assets", "scripts", "todos", "documents",
                        "workflow", "audit", "params", "dicts", "bastion", "faq"}
        actual_ids = {s["id"] for s in HELP_DATA}
        missing = expected_ids - actual_ids
        assert not missing, f"缺少模块帮助: {missing}"

import pytest
from unittest.mock import MagicMock
from models.data_dict import DataDict
from models.data_dict_item import DataDictItem


@pytest.fixture
def mock_dict_service():
    service = MagicMock()
    service.get_dicts.return_value = []
    service.get_dict_items.return_value = []
    return service


@pytest.fixture
def dict_objects():
    d1 = DataDict(id=1, code="unit", name="单位", description="计量单位")
    d2 = DataDict(id=2, code="status", name="状态", description="状态字典")
    return [d1, d2]


@pytest.fixture
def dict_item_objects():
    i1 = DataDictItem(id=1, dict_code="unit", item_code="kg", item_name="千克", sort_order=1)
    i2 = DataDictItem(id=2, dict_code="unit", item_code="m", item_name="米", sort_order=2)
    return [i1, i2]


class TestDataDictsPageClick:
    def test_item_clicked_signal_connected(self, qapp, mock_dict_service):
        from gui.pages.data_dicts_page import DataDictsPage
        page = DataDictsPage(mock_dict_service)

        receivers_count = page.dict_table.receivers(page.dict_table.itemClicked)
        assert receivers_count > 0, "dict_table的itemClicked信号未连接到任何槽函数"

    def test_on_dict_selected_calls_show_dict_items(self, qapp, mock_dict_service, dict_objects):
        from gui.pages.data_dicts_page import DataDictsPage
        mock_dict_service.get_dicts.return_value = dict_objects
        page = DataDictsPage(mock_dict_service)
        page.load_dicts()

        page.show_dict_items = MagicMock()
        mock_item = MagicMock()
        mock_item.row.return_value = 0

        page.on_dict_selected(mock_item)

        page.show_dict_items.assert_called_once_with(dict_objects[0])

    def test_on_dict_selected_with_invalid_row(self, qapp, mock_dict_service, dict_objects):
        from gui.pages.data_dicts_page import DataDictsPage
        mock_dict_service.get_dicts.return_value = dict_objects
        page = DataDictsPage(mock_dict_service)
        page.load_dicts()

        page.show_dict_items = MagicMock()
        mock_item = MagicMock()
        mock_item.row.return_value = 999

        page.on_dict_selected(mock_item)

        page.show_dict_items.assert_not_called()

    def test_show_dict_items_switches_tab(self, qapp, mock_dict_service, dict_objects, dict_item_objects):
        from gui.pages.data_dicts_page import DataDictsPage
        mock_dict_service.get_dicts.return_value = dict_objects
        mock_dict_service.get_dict_items.return_value = dict_item_objects
        page = DataDictsPage(mock_dict_service)
        page.load_dicts()

        assert page.tabs.currentIndex() == 0

        page.show_dict_items(dict_objects[0])

        assert page.tabs.currentIndex() == 1
        assert page.current_dict == dict_objects[0]
        assert page.add_item_btn.isEnabled()

    def test_show_dict_items_loads_items(self, qapp, mock_dict_service, dict_objects, dict_item_objects):
        from gui.pages.data_dicts_page import DataDictsPage
        mock_dict_service.get_dicts.return_value = dict_objects
        mock_dict_service.get_dict_items.return_value = dict_item_objects
        page = DataDictsPage(mock_dict_service)
        page.load_dicts()

        page.show_dict_items(dict_objects[0])

        mock_dict_service.get_dict_items.assert_called_with("unit")
        assert page.item_table.rowCount() == 2

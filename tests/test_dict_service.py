import pytest
from services.dict_service import DictService

@pytest.fixture
def dict_service(db_session):
    return DictService()

def test_create_dict(dict_service):
    dict_obj = dict_service.create_dict(
        code="test_dict",
        name="Test Dictionary",
        description="Test dictionary description"
    )
    assert dict_obj is not None
    assert dict_obj.code == "test_dict"
    assert dict_obj.name == "Test Dictionary"
    assert dict_obj.description == "Test dictionary description"

def test_create_dict_duplicate_code(dict_service):
    dict_service.create_dict("test_dict", "Test Dictionary")

    with pytest.raises(ValueError) as exc_info:
        dict_service.create_dict("test_dict", "Another Dictionary")
    assert "字典代码 test_dict 已存在" in str(exc_info.value)

def test_get_dicts(dict_service):
    dict_service.create_dict("dict1", "Dictionary 1")
    dict_service.create_dict("dict2", "Dictionary 2")
    dict_service.create_dict("dict3", "Dictionary 3")

    dicts = dict_service.get_dicts()
    assert len(dicts) == 3

def test_get_dict(dict_service):
    created = dict_service.create_dict("test_dict", "Test Dictionary")

    dict_obj = dict_service.get_dict(created.id)
    assert dict_obj is not None
    assert dict_obj.code == "test_dict"

    non_existent = dict_service.get_dict(999)
    assert non_existent is None

def test_get_dict_by_code(dict_service):
    dict_service.create_dict("test_dict", "Test Dictionary")

    dict_obj = dict_service.get_dict_by_code("test_dict")
    assert dict_obj is not None
    assert dict_obj.code == "test_dict"

    non_existent = dict_service.get_dict_by_code("non_existent")
    assert non_existent is None

def test_update_dict(dict_service):
    dict_obj = dict_service.create_dict("test_dict", "Original Name")

    updated = dict_service.update_dict(
        dict_obj.id,
        name="Updated Name",
        description="Updated description"
    )
    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.description == "Updated description"

def test_update_dict_code(dict_service):
    dict_obj = dict_service.create_dict("test_dict", "Test Dictionary")

    updated = dict_service.update_dict(dict_obj.id, code="new_code")
    assert updated is not None
    assert updated.code == "new_code"

def test_update_dict_duplicate_code(dict_service):
    dict1 = dict_service.create_dict("dict1", "Dictionary 1")
    dict2 = dict_service.create_dict("dict2", "Dictionary 2")

    with pytest.raises(ValueError) as exc_info:
        dict_service.update_dict(dict2.id, code="dict1")
    assert "字典代码 dict1 已存在" in str(exc_info.value)

def test_update_non_existent_dict(dict_service):
    result = dict_service.update_dict(999, name="New Name")
    assert result is None

def test_delete_dict(dict_service):
    dict_obj = dict_service.create_dict("test_dict", "Test Dictionary")

    deleted = dict_service.delete_dict(dict_obj.id)
    assert deleted is True

    dict_after_delete = dict_service.get_dict(dict_obj.id)
    assert dict_after_delete is None

def test_delete_non_existent_dict(dict_service):
    deleted = dict_service.delete_dict(999)
    assert deleted is False

def test_create_dict_item(dict_service):
    dict_service.create_dict("test_dict", "Test Dictionary")

    item = dict_service.create_dict_item(
        dict_code="test_dict",
        item_code="item1",
        item_name="Item 1",
        sort_order=1
    )
    assert item is not None
    assert item.dict_code == "test_dict"
    assert item.item_code == "item1"
    assert item.item_name == "Item 1"
    assert item.sort_order == 1

def test_create_dict_item_non_existent_dict(dict_service):
    with pytest.raises(ValueError) as exc_info:
        dict_service.create_dict_item("non_existent", "item1", "Item 1")
    assert "字典 non_existent 不存在" in str(exc_info.value)

def test_create_dict_item_duplicate_code(dict_service):
    dict_service.create_dict("test_dict", "Test Dictionary")
    dict_service.create_dict_item("test_dict", "item1", "Item 1")

    with pytest.raises(ValueError) as exc_info:
        dict_service.create_dict_item("test_dict", "item1", "Another Item")
    assert "字典项代码 item1 已存在" in str(exc_info.value)

def test_get_dict_items(dict_service):
    dict_service.create_dict("test_dict", "Test Dictionary")
    dict_service.create_dict_item("test_dict", "item1", "Item 1", sort_order=2)
    dict_service.create_dict_item("test_dict", "item2", "Item 2", sort_order=1)
    dict_service.create_dict_item("test_dict", "item3", "Item 3", sort_order=3)

    items = dict_service.get_dict_items("test_dict")
    assert len(items) == 3
    assert items[0].item_code == "item2"
    assert items[1].item_code == "item1"
    assert items[2].item_code == "item3"

def test_get_dict_item(dict_service):
    dict_service.create_dict("test_dict", "Test Dictionary")
    created = dict_service.create_dict_item("test_dict", "item1", "Item 1")

    item = dict_service.get_dict_item(created.id)
    assert item is not None
    assert item.item_code == "item1"

    non_existent = dict_service.get_dict_item(999)
    assert non_existent is None

def test_update_dict_item(dict_service):
    dict_service.create_dict("test_dict", "Test Dictionary")
    item = dict_service.create_dict_item("test_dict", "item1", "Original Name")

    updated = dict_service.update_dict_item(
        item.id,
        item_name="Updated Name"
    )
    assert updated is not None
    assert updated.item_name == "Updated Name"

def test_update_non_existent_dict_item(dict_service):
    result = dict_service.update_dict_item(999, item_name="New Name")
    assert result is None

def test_delete_dict_item(dict_service):
    dict_service.create_dict("test_dict", "Test Dictionary")
    item = dict_service.create_dict_item("test_dict", "item1", "Item 1")

    deleted = dict_service.delete_dict_item(item.id)
    assert deleted is True

    item_after_delete = dict_service.get_dict_item(item.id)
    assert item_after_delete is None

def test_delete_non_existent_dict_item(dict_service):
    deleted = dict_service.delete_dict_item(999)
    assert deleted is False

def test_search_dicts(dict_service):
    dict_service.create_dict("server_config", "Server Configuration")
    dict_service.create_dict("database_config", "Database Configuration")
    dict_service.create_dict("user_settings", "User Settings")

    results = dict_service.search_dicts("config")
    assert len(results) == 2

    results = dict_service.search_dicts("server")
    assert len(results) == 1
    assert results[0].code == "server_config"

def test_get_item_name_by_code(dict_service):
    dict_service.create_dict("unit", "单位")
    dict_service.create_dict_item("unit", "unit1", "单位1")
    dict_service.create_dict_item("unit", "unit2", "单位2")

    name = dict_service.get_item_name_by_code("unit", "unit1")
    assert name == "单位1"

    name = dict_service.get_item_name_by_code("unit", "unit2")
    assert name == "单位2"

    name = dict_service.get_item_name_by_code("unit", "non_existent")
    assert name is None

    name = dict_service.get_item_name_by_code("non_existent_dict", "unit1")
    assert name is None

def test_get_item_code_by_name(dict_service):
    dict_service.create_dict("system", "系统")
    dict_service.create_dict_item("system", "sys1", "系统1")
    dict_service.create_dict_item("system", "sys2", "系统2")

    code = dict_service.get_item_code_by_name("system", "系统1")
    assert code == "sys1"

    code = dict_service.get_item_code_by_name("system", "系统2")
    assert code == "sys2"

    code = dict_service.get_item_code_by_name("system", "non_existent")
    assert code is None

    code = dict_service.get_item_code_by_name("non_existent_dict", "系统1")
    assert code is None

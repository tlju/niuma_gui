import pytest
from services.asset_service import AssetService

@pytest.fixture
def asset_service(db_session):
    return AssetService(db_session)

def test_create_asset(asset_service):
    asset_id = asset_service.create(
        unit_name="Test Unit",
        system_name="Test System",
        username="admin",
        password="secret123",
        ip="192.168.1.100",
        port=22
    )
    assert asset_id is not None

    asset = asset_service.get_by_id(asset_id)
    assert asset.unit_name == "Test Unit"
    assert asset.system_name == "Test System"
    assert asset.ip == "192.168.1.100"

def test_list_assets(asset_service):
    asset_service.create("Unit1", "System1", "admin", "pass", ip="192.168.1.1", port=22)
    asset_service.create("Unit2", "System2", "admin", "pass", ip="192.168.1.2", port=22)

    assets = asset_service.get_all()
    assert len(assets) >= 2

import pytest
from services.asset_service import AssetService

@pytest.fixture
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.base import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def asset_service(db_session):
    return AssetService(db_session)

def test_create_asset(asset_service):
    asset_id = asset_service.create(
        name="Test Server",
        ip="192.168.1.100",
        port=22,
        username="admin",
        password="secret123"
    )
    assert asset_id is not None

    asset = asset_service.get_by_id(asset_id)
    assert asset.name == "Test Server"
    assert asset.ip == "192.168.1.100"

def test_list_assets(asset_service):
    asset_service.create("Server1", "192.168.1.1", 22, "admin", "pass")
    asset_service.create("Server2", "192.168.1.2", 22, "admin", "pass")

    assets = asset_service.get_all()
    assert len(assets) >= 2

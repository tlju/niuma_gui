import pytest
from models.user import User, UserStatus
from models.server_asset import ServerAsset

def test_create_user(db_session):
    user = User(
        username="testuser",
        hashed_password="$2b$12$hashed_password",
        full_name="Test User",
        email="test@example.com"
    )
    db_session.add(user)
    db_session.commit()

    retrieved = db_session.query(User).filter(User.username == "testuser").first()
    assert retrieved is not None
    assert retrieved.username == "testuser"
    assert retrieved.status == UserStatus.ACTIVE

def test_create_server_asset(db_session):
    asset = ServerAsset(
        unit_name="Test Unit",
        system_name="Test System",
        ip="192.168.1.100",
        port=22,
        host_name="test.example.com",
        username="admin",
        password_cipher="encrypted_password"
    )
    db_session.add(asset)
    db_session.commit()

    retrieved = db_session.query(ServerAsset).filter(
        ServerAsset.unit_name == "Test Unit"
    ).first()
    assert retrieved is not None
    assert retrieved.ip == "192.168.1.100"

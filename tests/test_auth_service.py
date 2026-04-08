import pytest
from services.auth_service import AuthService
from services.crypto import hash_password, verify_password

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
def auth_service(db_session):
    return AuthService(db_session)

def test_hash_verify_password():
    password = "test_password_123"
    hashed = hash_password(password)
    assert verify_password(password, hashed) == True
    assert verify_password("wrong_password", hashed) == False

def test_register_user(auth_service):
    user_id = auth_service.register("testuser", "password123", "Test User")
    assert user_id is not None

    user = auth_service.get_user_by_username("testuser")
    assert user.username == "testuser"
    assert user.full_name == "Test User"

def test_authenticate_user(auth_service):
    auth_service.register("testuser", "password123", "Test User")

    user = auth_service.authenticate("testuser", "password123")
    assert user is not None
    assert user.username == "testuser"

    # 错误密码
    invalid = auth_service.authenticate("testuser", "wrongpassword")
    assert invalid is None

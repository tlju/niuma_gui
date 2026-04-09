import pytest
from services.auth_service import AuthService
from services.crypto import hash_password, verify_password
from models.user import User, UserStatus

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

def test_create_user_directly(auth_service):
    user = User(
        username="testuser",
        hashed_password=hash_password("password123"),
        full_name="Test User",
        status=UserStatus.ACTIVE
    )
    auth_service.db.add(user)
    auth_service.db.commit()

    retrieved_user = auth_service.get_user_by_username("testuser")
    assert retrieved_user.username == "testuser"
    assert retrieved_user.full_name == "Test User"

def test_authenticate_user(auth_service):
    user = User(
        username="testuser",
        hashed_password=hash_password("password123"),
        full_name="Test User",
        status=UserStatus.ACTIVE
    )
    auth_service.db.add(user)
    auth_service.db.commit()

    authenticated_user = auth_service.authenticate("testuser", "password123")
    assert authenticated_user is not None
    assert authenticated_user.username == "testuser"

    invalid = auth_service.authenticate("testuser", "wrongpassword")
    assert invalid is None

def test_authenticate_non_existent_user(auth_service):
    user = auth_service.authenticate("nonexistent", "password")
    assert user is None

def test_authenticate_inactive_user(auth_service):
    user = User(
        username="testuser",
        hashed_password=hash_password("password123"),
        full_name="Test User",
        status=UserStatus.INACTIVE
    )
    auth_service.db.add(user)
    auth_service.db.commit()

    authenticated_user = auth_service.authenticate("testuser", "password123")
    assert authenticated_user is None

def test_get_user_by_id(auth_service):
    user = User(
        username="testuser",
        hashed_password=hash_password("password123"),
        full_name="Test User",
        status=UserStatus.ACTIVE
    )
    auth_service.db.add(user)
    auth_service.db.commit()

    retrieved_user = auth_service.get_user_by_id(user.id)
    assert retrieved_user is not None
    assert retrieved_user.username == "testuser"

    non_existent = auth_service.get_user_by_id(999)
    assert non_existent is None

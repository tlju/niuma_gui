import pytest
from services.auth_service import AuthService
from services.crypto import hash_password, verify_password
from models.user import User, UserStatus

@pytest.fixture
def auth_service(db_session):
    return AuthService()

def test_hash_verify_password():
    password = "test_password_123"
    hashed = hash_password(password)
    assert verify_password(password, hashed) == True
    assert verify_password("wrong_password", hashed) == False

def test_create_user_directly(auth_service, db_session):
    user = User(
        username="testuser",
        hashed_password=hash_password("password123"),
        full_name="Test User",
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    db_session.commit()

    retrieved_user = auth_service.get_user_by_username("testuser")
    assert retrieved_user.username == "testuser"
    assert retrieved_user.full_name == "Test User"

def test_authenticate_user(auth_service, db_session):
    user = User(
        username="testuser",
        hashed_password=hash_password("password123"),
        full_name="Test User",
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    db_session.commit()

    authenticated_user = auth_service.authenticate("testuser", "password123")
    assert authenticated_user is not None
    assert authenticated_user.username == "testuser"

    invalid = auth_service.authenticate("testuser", "wrongpassword")
    assert invalid is None

def test_authenticate_non_existent_user(auth_service):
    user = auth_service.authenticate("nonexistent", "password")
    assert user is None

def test_authenticate_inactive_user(auth_service, db_session):
    user = User(
        username="testuser",
        hashed_password=hash_password("password123"),
        full_name="Test User",
        status=UserStatus.INACTIVE
    )
    db_session.add(user)
    db_session.commit()

    authenticated_user = auth_service.authenticate("testuser", "password123")
    assert authenticated_user is None

def test_get_user_by_id(auth_service, db_session):
    user = User(
        username="testuser",
        hashed_password=hash_password("password123"),
        full_name="Test User",
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    db_session.commit()

    retrieved_user = auth_service.get_user_by_id(user.id)
    assert retrieved_user is not None
    assert retrieved_user.username == "testuser"

    non_existent = auth_service.get_user_by_id(999)
    assert non_existent is None

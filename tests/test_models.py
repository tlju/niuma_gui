import pytest
from models.user import User, UserStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

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

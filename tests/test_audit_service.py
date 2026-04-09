import pytest
from services.audit_service import AuditService
from datetime import datetime, timedelta

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
def audit_service(db_session):
    return AuditService(db_session)

def test_log_action(audit_service):
    audit_service.log_action(
        user_id=1,
        action_type="create",
        resource_type="document",
        resource_id=100,
        details="Created a new document",
        ip_address="192.168.1.1"
    )

    logs = audit_service.get_logs()
    assert len(logs) == 1
    assert logs[0].user_id == 1
    assert logs[0].action_type == "create"
    assert logs[0].resource_type == "document"
    assert logs[0].resource_id == 100
    assert logs[0].details == "Created a new document"
    assert logs[0].ip_address == "192.168.1.1"

def test_get_logs_all(audit_service):
    audit_service.log_action(1, "create", "document", 1)
    audit_service.log_action(2, "update", "document", 2)
    audit_service.log_action(1, "delete", "document", 3)

    logs = audit_service.get_logs()
    assert len(logs) == 3

def test_get_logs_by_user_id(audit_service):
    audit_service.log_action(1, "create", "document", 1)
    audit_service.log_action(2, "update", "document", 2)
    audit_service.log_action(1, "delete", "document", 3)

    logs = audit_service.get_logs(user_id=1)
    assert len(logs) == 2
    assert all(log.user_id == 1 for log in logs)

def test_get_logs_by_action_type(audit_service):
    audit_service.log_action(1, "create", "document", 1)
    audit_service.log_action(2, "update", "document", 2)
    audit_service.log_action(1, "create", "document", 3)

    logs = audit_service.get_logs(action_type="create")
    assert len(logs) == 2
    assert all(log.action_type == "create" for log in logs)

def test_get_logs_by_resource_type(audit_service):
    audit_service.log_action(1, "create", "document", 1)
    audit_service.log_action(2, "update", "user", 2)
    audit_service.log_action(1, "delete", "document", 3)

    logs = audit_service.get_logs(resource_type="document")
    assert len(logs) == 2
    assert all(log.resource_type == "document" for log in logs)

def test_get_logs_by_date_range(audit_service):
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)

    audit_service.log_action(1, "create", "document", 1)

    logs = audit_service.get_logs(start_date=yesterday, end_date=tomorrow)
    assert len(logs) == 1

def test_get_logs_with_limit(audit_service):
    for i in range(10):
        audit_service.log_action(1, "create", "document", i)

    logs = audit_service.get_logs(limit=5)
    assert len(logs) == 5

def test_get_logs_with_multiple_filters(audit_service):
    audit_service.log_action(1, "create", "document", 1)
    audit_service.log_action(1, "update", "document", 2)
    audit_service.log_action(2, "create", "document", 3)
    audit_service.log_action(1, "create", "user", 4)

    logs = audit_service.get_logs(user_id=1, action_type="create", resource_type="document")
    assert len(logs) == 1
    assert logs[0].user_id == 1
    assert logs[0].action_type == "create"
    assert logs[0].resource_type == "document"

def test_get_logs_empty_result(audit_service):
    logs = audit_service.get_logs(user_id=999)
    assert len(logs) == 0

def test_log_action_with_optional_fields(audit_service):
    audit_service.log_action(
        user_id=1,
        action_type="login",
        resource_type="system"
    )

    logs = audit_service.get_logs()
    assert len(logs) == 1
    assert logs[0].resource_id is None
    assert logs[0].details is None
    assert logs[0].ip_address is None

import pytest
from services.script_service import ScriptService
from unittest.mock import Mock, patch

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
def script_service(db_session):
    return ScriptService(db_session)

def test_create_script(script_service):
    script_id = script_service.create(
        name="test_script",
        content="echo 'Hello World'",
        description="Test script",
        server_id=None,
        created_by=1
    )
    assert script_id is not None

    script = script_service.get_by_id(script_id)
    assert script.name == "test_script"
    assert script.content == "echo 'Hello World'"
    assert script.description == "Test script"

def test_create_script_with_server(script_service):
    from services.asset_service import AssetService
    asset_service = AssetService(script_service.db)
    server_id = asset_service.create("Test Server", "192.168.1.1", 22, "admin", "password")

    script_id = script_service.create(
        name="test_script",
        content="echo 'Hello'",
        server_id=server_id,
        created_by=1
    )
    assert script_id is not None

    script = script_service.get_by_id(script_id)
    assert script.server_id == server_id

def test_get_all_scripts(script_service):
    script_service.create("script1", "echo '1'", created_by=1)
    script_service.create("script2", "echo '2'", created_by=1)
    script_service.create("script3", "echo '3'", created_by=1)

    scripts = script_service.get_all()
    assert len(scripts) == 3

def test_get_script_by_id(script_service):
    created_id = script_service.create("test_script", "echo 'test'", created_by=1)

    script = script_service.get_by_id(created_id)
    assert script is not None
    assert script.name == "test_script"

    non_existent = script_service.get_by_id(999)
    assert non_existent is None

def test_execute_script_mock(script_service):
    from services.asset_service import AssetService
    asset_service = AssetService(script_service.db)
    server_id = asset_service.create("Test Server", "192.168.1.1", 22, "admin", "password")

    script_id = script_service.create("test_script", "echo 'Hello'", created_by=1)
    script = script_service.get_by_id(script_id)

    with patch('paramiko.SSHClient') as mock_ssh_class:
        mock_ssh = Mock()
        mock_ssh_class.return_value = mock_ssh
        mock_stdout = Mock()
        mock_stdout.read.return_value = b"Hello\n"
        mock_stderr = Mock()
        mock_stderr.read.return_value = b""
        mock_ssh.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)

        exec_log_id = script_service.execute(script, server_id, executed_by=1)
        assert exec_log_id is not None

def test_execute_script_non_existent_server(script_service):
    script_id = script_service.create("test_script", "echo 'Hello'", created_by=1)
    script = script_service.get_by_id(script_id)

    exec_log_id = script_service.execute(script, 999, executed_by=1)
    assert exec_log_id is None

def test_delete_script(script_service):
    script_id = script_service.create("test_script", "echo 'Hello'", created_by=1)

    deleted = script_service.delete(script_id, user_id=1)
    assert deleted is True

    script_after_delete = script_service.get_by_id(script_id)
    assert script_after_delete is None

def test_delete_non_existent_script(script_service):
    deleted = script_service.delete(999, user_id=1)
    assert deleted is False

def test_create_script_creates_audit_log(script_service):
    script_id = script_service.create("test_script", "echo 'Hello'", created_by=1)

    from models.audit_log import AuditLog
    audit_logs = script_service.db.query(AuditLog).filter(
        AuditLog.resource_type == "script",
        AuditLog.resource_id == script_id
    ).all()
    assert len(audit_logs) == 1
    assert audit_logs[0].action_type == "create"
    assert audit_logs[0].user_id == 1

def test_delete_script_creates_audit_log(script_service):
    script_id = script_service.create("test_script", "echo 'Hello'", created_by=1)
    script_service.delete(script_id, user_id=1)

    from models.audit_log import AuditLog
    audit_logs = script_service.db.query(AuditLog).filter(
        AuditLog.resource_type == "script",
        AuditLog.action_type == "delete"
    ).all()
    assert len(audit_logs) == 1
    assert audit_logs[0].user_id == 1

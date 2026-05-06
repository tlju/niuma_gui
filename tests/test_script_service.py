from __future__ import annotations

import pytest
from services.script_service import ScriptService
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager


@pytest.fixture
def script_service(db_session):
    return ScriptService()


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
    asset_service = AssetService()
    server_id = asset_service.create(
        unit_name="TestUnit",
        system_name="TestSystem",
        username="admin",
        password="password",
        ip="192.168.1.1",
        port=22
    )

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


def test_delete_script(script_service):
    script_id = script_service.create("test_script", "echo 'Hello'", created_by=1)

    deleted = script_service.delete(script_id, user_id=1)
    assert deleted is True

    script_after_delete = script_service.get_by_id(script_id)
    assert script_after_delete is None


def test_delete_non_existent_script(script_service):
    deleted = script_service.delete(999, user_id=1)
    assert deleted is False


def test_create_script_creates_audit_log(script_service, db_session):
    @contextmanager
    def mock_get_db():
        yield db_session

    with patch('services.audit_mixin.get_db', side_effect=mock_get_db):
        script_id = script_service.create("test_script", "echo 'Hello'", created_by=1)

        from models.audit_log import AuditLog
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.resource_type == "script",
            AuditLog.resource_id == script_id
        ).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].action_type == "create"
        assert audit_logs[0].user_id == 1


def test_delete_script_creates_audit_log(script_service, db_session):
    @contextmanager
    def mock_get_db():
        yield db_session

    with patch('services.audit_mixin.get_db', side_effect=mock_get_db):
        script_id = script_service.create("test_script", "echo 'Hello'", created_by=1)
        script_service.delete(script_id, user_id=1)

        from models.audit_log import AuditLog
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.resource_type == "script",
            AuditLog.action_type == "delete"
        ).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].user_id == 1

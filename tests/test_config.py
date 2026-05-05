from __future__ import annotations

import pytest
from core.config import settings


class TestConfig:
    def test_default_admin_username(self):
        assert settings.DEFAULT_ADMIN_USERNAME == "admin"

    def test_default_admin_password(self):
        assert settings.DEFAULT_ADMIN_PASSWORD == "admin123"

    def test_default_admin_full_name(self):
        assert settings.DEFAULT_ADMIN_FULL_NAME == "系统管理员"

    def test_bastion_max_retries(self):
        assert settings.BASTION_MAX_RETRIES == 3

    def test_bastion_retry_interval(self):
        assert settings.BASTION_RETRY_INTERVAL == 5

    def test_bastion_connection_timeout(self):
        assert settings.BASTION_CONNECTION_TIMEOUT == 30

    def test_workflow_max_workers(self):
        assert settings.WORKFLOW_MAX_WORKERS == 4

    def test_ssh_default_port(self):
        assert settings.SSH_DEFAULT_PORT == 22

    def test_log_level(self):
        assert settings.LOG_LEVEL in ("WARNING", "INFO", "DEBUG", "ERROR")

    def test_log_max_bytes(self):
        assert settings.LOG_MAX_BYTES == 10 * 1024 * 1024

    def test_log_backup_count(self):
        assert settings.LOG_BACKUP_COUNT == 5

    def test_session_timeout(self):
        assert settings.SESSION_TIMEOUT == 1800

    def test_max_sessions_per_user(self):
        assert settings.MAX_SESSIONS_PER_USER == 5

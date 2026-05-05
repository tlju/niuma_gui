from __future__ import annotations

import pytest
from schemas.schemas import (
    LoginRequest, UserCreateRequest, AssetCreateRequest,
    TodoCreateRequest, DictCreateRequest, ParamCreateRequest
)


class TestLoginRequest:
    def test_valid(self):
        req = LoginRequest(username="admin", password="123456")
        assert req.username == "admin"

    def test_empty_username(self):
        with pytest.raises(Exception):
            LoginRequest(username="", password="123456")

    def test_empty_password(self):
        with pytest.raises(Exception):
            LoginRequest(username="admin", password="")

    def test_invalid_username_chars(self):
        with pytest.raises(Exception):
            LoginRequest(username="admin@#$", password="123456")

    def test_username_strip(self):
        req = LoginRequest(username="  admin  ", password="123456")
        assert req.username == "admin"


class TestUserCreateRequest:
    def test_valid(self):
        req = UserCreateRequest(username="testuser", password="123456")
        assert req.username == "testuser"

    def test_short_password(self):
        with pytest.raises(Exception):
            UserCreateRequest(username="testuser", password="12345")

    def test_invalid_email(self):
        with pytest.raises(Exception):
            UserCreateRequest(username="testuser", password="123456", email="invalid")

    def test_valid_email(self):
        req = UserCreateRequest(username="testuser", password="123456", email="test@example.com")
        assert req.email == "test@example.com"


class TestAssetCreateRequest:
    def test_valid(self):
        req = AssetCreateRequest(
            unit_name="测试单位", system_name="测试系统",
            username="root", password="secret"
        )
        assert req.unit_name == "测试单位"

    def test_empty_unit_name(self):
        with pytest.raises(Exception):
            AssetCreateRequest(
                unit_name="", system_name="测试系统",
                username="root", password="secret"
            )

    def test_invalid_ip(self):
        with pytest.raises(Exception):
            AssetCreateRequest(
                unit_name="单位", system_name="系统",
                username="root", password="secret",
                ip="999.999.999.999"
            )

    def test_valid_ip(self):
        req = AssetCreateRequest(
            unit_name="单位", system_name="系统",
            username="root", password="secret",
            ip="192.168.1.1"
        )
        assert req.ip == "192.168.1.1"

    def test_port_range(self):
        with pytest.raises(Exception):
            AssetCreateRequest(
                unit_name="单位", system_name="系统",
                username="root", password="secret",
                port=99999
            )

    def test_valid_port(self):
        req = AssetCreateRequest(
            unit_name="单位", system_name="系统",
            username="root", password="secret",
            port=22
        )
        assert req.port == 22


class TestTodoCreateRequest:
    def test_valid(self):
        req = TodoCreateRequest(title="测试任务")
        assert req.title == "测试任务"

    def test_invalid_priority(self):
        with pytest.raises(Exception):
            TodoCreateRequest(title="测试", priority="urgent")

    def test_valid_priority(self):
        req = TodoCreateRequest(title="测试", priority="high")
        assert req.priority == "high"

    def test_invalid_recurrence(self):
        with pytest.raises(Exception):
            TodoCreateRequest(title="测试", recurrence="yearly")

    def test_valid_recurrence(self):
        req = TodoCreateRequest(title="测试", recurrence="daily")
        assert req.recurrence == "daily"


class TestDictCreateRequest:
    def test_valid(self):
        req = DictCreateRequest(name="测试字典", code="test_dict")
        assert req.code == "test_dict"

    def test_invalid_code(self):
        with pytest.raises(Exception):
            DictCreateRequest(name="测试", code="invalid code!")

    def test_code_strip(self):
        req = DictCreateRequest(name="测试", code="  test_code  ")
        assert req.code == "test_code"


class TestParamCreateRequest:
    def test_valid(self):
        req = ParamCreateRequest(
            param_name="测试参数", param_code="test_param",
            param_value="value"
        )
        assert req.param_code == "test_param"

    def test_invalid_code(self):
        with pytest.raises(Exception):
            ParamCreateRequest(
                param_name="测试", param_code="invalid code!",
                param_value="value"
            )

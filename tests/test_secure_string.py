from __future__ import annotations

import pytest
from core.secure_string import SecureString


class TestSecureString:
    def test_value(self):
        s = SecureString("mypassword")
        assert s.value == "mypassword"

    def test_consume(self):
        s = SecureString("mypassword")
        result = s.consume()
        assert result == "mypassword"
        assert s.is_consumed()
        assert s.value == ""
        assert s.consume() == ""

    def test_is_consumed(self):
        s = SecureString("test")
        assert not s.is_consumed()
        s.consume()
        assert s.is_consumed()

    def test_empty_string(self):
        s = SecureString("")
        assert s.value == ""
        assert not s.is_consumed()

    def test_str_redacted(self):
        s = SecureString("secret")
        assert str(s) == "***REDACTED***"

    def test_repr(self):
        s = SecureString("secret")
        assert "consumed=False" in repr(s)
        s.consume()
        assert "consumed=True" in repr(s)

    def test_bool(self):
        s = SecureString("secret")
        assert bool(s) is True
        s.consume()
        assert bool(s) is False

    def test_bool_empty(self):
        s = SecureString("")
        assert bool(s) is False

    def test_unicode(self):
        s = SecureString("密码123")
        assert s.value == "密码123"
        assert s.consume() == "密码123"

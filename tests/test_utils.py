from __future__ import annotations

import pytest
from core.utils import escape_like_wildcards, get_local_now, format_datetime
from datetime import datetime, timezone


class TestEscapeLikeWildcards:
    def test_empty_string(self):
        assert escape_like_wildcards("") == ""

    def test_none(self):
        assert escape_like_wildcards(None) is None

    def test_no_wildcards(self):
        assert escape_like_wildcards("hello") == "hello"

    def test_percent(self):
        assert escape_like_wildcards("100%") == "100\\%"

    def test_underscore(self):
        assert escape_like_wildcards("a_b") == "a\\_b"

    def test_backslash(self):
        assert escape_like_wildcards("a\\b") == "a\\\\b"

    def test_combined(self):
        assert escape_like_wildcards("100%_test\\data") == "100\\%\\_test\\\\data"

    def test_multiple_percent(self):
        assert escape_like_wildcards("%test%") == "\\%test\\%"


class TestGetLocalNow:
    def test_returns_datetime(self):
        result = get_local_now()
        assert isinstance(result, datetime)

    def test_has_timezone(self):
        result = get_local_now()
        assert result.tzinfo is not None


class TestFormatDatetime:
    def test_none(self):
        assert format_datetime(None) == ""

    def test_valid_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = format_datetime(dt)
        assert "2024-01-15" in result
        assert "10:30:00" in result

    def test_custom_format(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = format_datetime(dt, fmt="%Y/%m/%d")
        assert result == "2024/01/15"

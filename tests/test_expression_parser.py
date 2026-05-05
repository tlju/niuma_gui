from __future__ import annotations

import pytest
from core.expression_parser import safe_eval, ExpressionParseError


class TestSafeEval:
    def test_simple_true(self):
        assert safe_eval("True") is True

    def test_simple_false(self):
        assert safe_eval("False") is False

    def test_comparison_eq(self):
        assert safe_eval("1 == 1") is True
        assert safe_eval("1 == 2") is False

    def test_comparison_ne(self):
        assert safe_eval("1 != 2") is True
        assert safe_eval("1 != 1") is False

    def test_comparison_gt(self):
        assert safe_eval("2 > 1") is True
        assert safe_eval("1 > 2") is False

    def test_comparison_ge(self):
        assert safe_eval("2 >= 2") is True
        assert safe_eval("2 >= 1") is True
        assert safe_eval("1 >= 2") is False

    def test_comparison_lt(self):
        assert safe_eval("1 < 2") is True
        assert safe_eval("2 < 1") is False

    def test_comparison_le(self):
        assert safe_eval("1 <= 1") is True
        assert safe_eval("1 <= 2") is True
        assert safe_eval("2 <= 1") is False

    def test_logical_and(self):
        assert safe_eval("True and True") is True
        assert safe_eval("True and False") is False
        assert safe_eval("False and True") is False

    def test_logical_or(self):
        assert safe_eval("True or False") is True
        assert safe_eval("False or True") is True
        assert safe_eval("False or False") is False

    def test_logical_not(self):
        assert safe_eval("not True") is False
        assert safe_eval("not False") is True

    def test_parentheses(self):
        assert safe_eval("(True or False) and True") is True
        assert safe_eval("True or (False and True)") is True

    def test_string_comparison(self):
        assert safe_eval('"hello" == "hello"') is True
        assert safe_eval('"hello" != "world"') is True

    def test_context_variable(self):
        context = {"data": {"status": "active"}}
        assert safe_eval('data.status == "active"', context) is True

    def test_context_input(self):
        context = {"input": "hello"}
        assert safe_eval('input == "hello"', context) is True

    def test_context_nested_data(self):
        context = {"data": {"count": 5}}
        assert safe_eval("data.count > 3", context) is True

    def test_empty_expression(self):
        assert safe_eval("") is True
        assert safe_eval("  ") is True

    def test_invalid_expression(self):
        with pytest.raises(ExpressionParseError):
            safe_eval("import os")

    def test_invalid_function_call(self):
        with pytest.raises(ExpressionParseError):
            safe_eval("print('hello')")

    def test_invalid_attribute_access(self):
        with pytest.raises(ExpressionParseError):
            safe_eval("__import__('os')")

    def test_numeric_comparison_with_context(self):
        context = {"data": {"value": 10}}
        assert safe_eval("data.value >= 10", context) is True
        assert safe_eval("data.value < 5", context) is False

    def test_complex_logical(self):
        assert safe_eval("(1 == 1) and (2 > 1)") is True
        assert safe_eval("(1 == 2) or (3 > 2)") is True

    def test_in_operator_string(self):
        assert safe_eval('"hello" in "hello world"') is True

    def test_not_in_operator_string(self):
        assert safe_eval('"xyz" not in "hello world"') is True

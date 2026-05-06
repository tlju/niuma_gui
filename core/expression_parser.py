from __future__ import annotations

import re
from typing import Any


class ExpressionParseError(Exception):
    pass


_TOKEN_PATTERNS = [
    ('STRING', r"'[^']*'|\"[^\"]*\""),
    ('NUMBER', r'\d+\.?\d*'),
    ('BOOL', r'\bTrue\b|\bFalse\b'),
    ('AND', r'\band\b'),
    ('OR', r'\bor\b'),
    ('NOT', r'\bnot\b'),
    ('CMP', r'==|!=|>=|<=|>|<'),
    ('IN', r'\bin\b'),
    ('IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_\.]*'),
    ('LPAREN', r'\('),
    ('RPAREN', r'\)'),
    ('WS', r'\s+'),
]

_TOKEN_RE = re.compile(
    '|'.join(f'(?P<{name}>{pattern})' for name, pattern in _TOKEN_PATTERNS)
)


def _tokenize(expression: str) -> list[tuple[str, str]]:
    tokens = []
    for match in _TOKEN_RE.finditer(expression):
        kind = match.lastgroup
        value = match.group()
        if kind == 'WS':
            continue
        tokens.append((kind, value))
    return tokens


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]], context: dict[str, Any]):
        self.tokens = tokens
        self.pos = 0
        self.context = context

    def _current(self) -> tuple[str, str] | None:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _consume(self, expected_kind: str | None = None) -> tuple[str, str]:
        token = self._current()
        if token is None:
            raise ExpressionParseError(f"意外的表达式结尾，期望 {expected_kind}")
        if expected_kind and token[0] != expected_kind:
            raise ExpressionParseError(f"意外的标记 {token[1]}，期望 {expected_kind}")
        self.pos += 1
        return token

    def parse(self) -> Any:
        result = self._parse_or()
        if self.pos < len(self.tokens):
            remaining = self.tokens[self.pos][1]
            raise ExpressionParseError(f"意外的标记: {remaining}")
        return result

    def _parse_or(self) -> Any:
        left = self._parse_and()
        while self._current() and self._current()[0] == 'OR':
            self._consume('OR')
            right = self._parse_and()
            left = bool(left) or bool(right)
        return left

    def _parse_and(self) -> Any:
        left = self._parse_not()
        while self._current() and self._current()[0] == 'AND':
            self._consume('AND')
            right = self._parse_not()
            left = bool(left) and bool(right)
        return left

    def _parse_not(self) -> Any:
        if self._current() and self._current()[0] == 'NOT':
            self._consume('NOT')
            operand = self._parse_not()
            return not bool(operand)
        return self._parse_comparison()

    def _parse_comparison(self) -> Any:
        left = self._parse_primary()

        token = self._current()
        if token and token[0] == 'CMP':
            op = self._consume('CMP')[1]
            right = self._parse_primary()
            return self._compare(left, op, right)
        elif token and token[0] == 'IN':
            self._consume('IN')
            right = self._parse_primary()
            if isinstance(right, str):
                return str(left) in right
            elif isinstance(right, (list, tuple, set)):
                return left in right
            raise ExpressionParseError("'in' 运算符右侧必须是字符串或列表")
        elif token and token[0] == 'NOT':
            saved_pos = self.pos
            self._consume('NOT')
            next_token = self._current()
            if next_token and next_token[0] == 'IN':
                self._consume('IN')
                right = self._parse_primary()
                if isinstance(right, str):
                    return str(left) not in right
                elif isinstance(right, (list, tuple, set)):
                    return left not in right
                raise ExpressionParseError("'not in' 运算符右侧必须是字符串或列表")
            else:
                self.pos = saved_pos

        return left

    def _compare(self, left: Any, op: str, right: Any) -> bool:
        try:
            if op == '==':
                return left == right
            elif op == '!=':
                return left != right
            elif op == '>':
                return left > right
            elif op == '<':
                return left < right
            elif op == '>=':
                return left >= right
            elif op == '<=':
                return left <= right
        except TypeError:
            return False
        raise ExpressionParseError(f"不支持的比较运算符: {op}")

    def _parse_primary(self) -> Any:
        token = self._current()
        if token is None:
            raise ExpressionParseError("意外的表达式结尾")

        if token[0] == 'LPAREN':
            self._consume('LPAREN')
            result = self._parse_or()
            self._consume('RPAREN')
            return result
        elif token[0] == 'BOOL':
            value = self._consume('BOOL')[1]
            return value == 'True'
        elif token[0] == 'NUMBER':
            value = self._consume('NUMBER')[1]
            if '.' in value:
                return float(value)
            return int(value)
        elif token[0] == 'STRING':
            value = self._consume('STRING')[1]
            return value[1:-1]
        elif token[0] == 'IDENTIFIER':
            value = self._consume('IDENTIFIER')[1]
            return self._resolve_identifier(value)
        elif token[0] == 'NOT':
            return self._parse_not()
        else:
            raise ExpressionParseError(f"意外的标记: {token[1]}")

    def _resolve_identifier(self, name: str) -> Any:
        """解析标识符，仅支持字典访问，禁止通过属性访问对象内部属性以防止沙箱逃逸"""
        parts = name.split('.')
        obj = self.context
        for part in parts:
            # 禁止访问以下划线开头的属性，防止访问 Python 内省属性
            if part.startswith('_'):
                return ""
            if isinstance(obj, dict):
                obj = obj.get(part, "")
            else:
                # 不再支持通过 hasattr/getattr 访问对象属性，仅允许字典上下文
                return ""
        return obj


def safe_eval(expression: str, context: dict[str, Any] | None = None) -> Any:
    if context is None:
        context = {}

    expression = expression.strip()
    if not expression:
        return True

    try:
        tokens = _tokenize(expression)
        if not tokens:
            return True
        parser = _Parser(tokens, context)
        return bool(parser.parse())
    except ExpressionParseError:
        raise
    except Exception as e:
        raise ExpressionParseError(f"表达式解析错误: {e}")

# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.parsing.lexer
==================

Shared lexer for ucon's recursive-descent parsers.

Both the unit-expression grammar (:mod:`ucon.parsing.units`) and the
dimension-expression grammar (:mod:`ucon.parsing.dimensions`) tokenise
their inputs through :class:`_Tokenizer`. The lexer is target-type
agnostic — it understands operators (``*``, ``·``, ``⋅``, ``×``, ``/``,
``^``), parentheses, ASCII numbers, Unicode superscripts (``⁰¹²³…``),
and identifiers — but knows nothing about :class:`Unit` or
:class:`Dimension`. Each grammar layer maps identifiers to its own
target type.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class _TokenType(Enum):
    """Token types for unit/dimension expression lexers."""
    IDENT = auto()      # Unit/dimension name or scale+unit
    NUMBER = auto()     # Numeric exponent
    MUL = auto()        # *, ·, ⋅, ×
    DIV = auto()        # /
    POW = auto()        # ^
    LPAREN = auto()     # (
    RPAREN = auto()     # )
    EOF = auto()        # End of input


@dataclass
class _Token:
    """A lexical token from an expression."""
    type: _TokenType
    value: str
    position: int


# Unicode superscript to ASCII digit mapping
_SUPERSCRIPT_MAP = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻', '0123456789-')

# Regex for Unicode superscript sequences (including negative)
_SUPERSCRIPT_PATTERN = re.compile(r'^[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+')


class ParseError(ValueError):
    """Raised when expression parsing fails."""

    def __init__(self, message: str, position: int, expression: str):
        self.position = position
        self.expression = expression
        # Create a pointer to the error position
        pointer = ' ' * position + '^'
        super().__init__(f"{message} at position {position}:\n  {expression}\n  {pointer}")


class _Tokenizer:
    """
    Lexer for unit and dimension expressions.

    Produces a stream of tokens from an expression string. Operators,
    parentheses, numbers, Unicode superscripts, and identifiers are
    tokenised; mapping identifiers to a target type is the caller's
    responsibility.
    """

    # Multiplication operators (all normalize to MUL)
    _MUL_CHARS = {'*', '·', '⋅', '×'}

    # Unicode superscript characters (should NOT be part of identifiers)
    _SUPERSCRIPT_CHARS = set('⁰¹²³⁴⁵⁶⁷⁸⁹⁻')

    def __init__(self, expression: str):
        self.expression = expression
        self.pos = 0
        self.length = len(expression)

    def _skip_whitespace(self) -> None:
        """Skip any whitespace characters."""
        while self.pos < self.length and self.expression[self.pos].isspace():
            self.pos += 1

    def _read_identifier(self) -> str:
        """
        Read an identifier (unit or dimension name).

        Identifiers can contain:
        - Letters (including µ, °)
        - ASCII digits (but not starting with digit)
        - Underscores

        Stops at Unicode superscripts (they are separate exponent tokens).
        """
        start = self.pos
        while self.pos < self.length:
            ch = self.expression[self.pos]
            # Stop at superscript characters - they are exponents, not part of an identifier
            if ch in self._SUPERSCRIPT_CHARS:
                break
            # Allow letters, ASCII digits, underscores, and special chars like µ, °
            if ch.isalnum() or ch in '_µ°':
                self.pos += 1
            else:
                break
        return self.expression[start:self.pos]

    def _read_number(self) -> str:
        """Read a numeric value (integer or float, possibly negative)."""
        start = self.pos
        if self.pos < self.length and self.expression[self.pos] == '-':
            self.pos += 1
        while self.pos < self.length and self.expression[self.pos].isdigit():
            self.pos += 1
        # Handle decimal point for float exponents (e.g., ^2.0)
        if (self.pos < self.length and self.expression[self.pos] == '.'
                and self.pos + 1 < self.length
                and self.expression[self.pos + 1].isdigit()):
            self.pos += 1  # consume '.'
            while self.pos < self.length and self.expression[self.pos].isdigit():
                self.pos += 1
        return self.expression[start:self.pos]

    def _read_superscript(self) -> str:
        """Read a Unicode superscript sequence and convert to ASCII."""
        match = _SUPERSCRIPT_PATTERN.match(self.expression[self.pos:])
        if match:
            superscript = match.group()
            self.pos += len(superscript)
            return superscript.translate(_SUPERSCRIPT_MAP)
        return ''

    def peek(self) -> _Token:
        """Look at the next token without consuming it."""
        saved_pos = self.pos
        token = self.next_token()
        self.pos = saved_pos
        return token

    def next_token(self) -> _Token:
        """Return the next token from the input."""
        self._skip_whitespace()

        if self.pos >= self.length:
            return _Token(_TokenType.EOF, '', self.pos)

        start_pos = self.pos
        ch = self.expression[self.pos]

        # Single-character tokens
        if ch == '(':
            self.pos += 1
            return _Token(_TokenType.LPAREN, '(', start_pos)
        if ch == ')':
            self.pos += 1
            return _Token(_TokenType.RPAREN, ')', start_pos)
        if ch == '/':
            self.pos += 1
            return _Token(_TokenType.DIV, '/', start_pos)
        if ch == '^':
            self.pos += 1
            return _Token(_TokenType.POW, '^', start_pos)
        if ch in self._MUL_CHARS:
            self.pos += 1
            return _Token(_TokenType.MUL, ch, start_pos)

        # Unicode superscripts (treated as implicit POW + NUMBER)
        if ch in '⁰¹²³⁴⁵⁶⁷⁸⁹⁻':
            num = self._read_superscript()
            return _Token(_TokenType.NUMBER, num, start_pos)

        # Numbers (for exponents after ^)
        if ch.isdigit() or (ch == '-' and self.pos + 1 < self.length
                           and self.expression[self.pos + 1].isdigit()):
            num = self._read_number()
            return _Token(_TokenType.NUMBER, num, start_pos)

        # Identifiers (unit/dimension names)
        if ch.isalpha() or ch in '_µ°':
            ident = self._read_identifier()
            return _Token(_TokenType.IDENT, ident, start_pos)

        # Unknown character
        raise ParseError(f"Unexpected character '{ch}'", self.pos, self.expression)


__all__ = [
    "ParseError",
    "_Token",
    "_TokenType",
    "_Tokenizer",
]

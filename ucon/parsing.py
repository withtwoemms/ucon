# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.parsing
============

Recursive descent parser for complex unit expressions.

Supports:
- Parentheses: `W/(m²*K)`
- Chained division: `mg/kg/d`
- Unicode operators: `·`, `⋅`, `×`
- Unicode superscripts: `⁰¹²³⁴⁵⁶⁷⁸⁹⁻`
- ASCII equivalents: `*`, `^`, `-`

Grammar
-------
::

    unit_expr  := term (('*' | '·' | '/' | '⋅') term)*
    term       := factor ('^' exponent)?
    factor     := '(' unit_expr ')' | scale_unit
    scale_unit := SCALE? UNIT
    exponent   := INTEGER | '-' INTEGER | '⁻'? SUPERSCRIPT+

"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ucon.core import Scale, Unit, UnitFactor, UnitProduct


class TokenType(Enum):
    """Token types for the unit expression lexer."""
    IDENT = auto()      # Unit name or scale+unit
    NUMBER = auto()     # Numeric exponent
    MUL = auto()        # *, ·, ⋅, ×
    DIV = auto()        # /
    POW = auto()        # ^
    LPAREN = auto()     # (
    RPAREN = auto()     # )
    EOF = auto()        # End of input


@dataclass
class Token:
    """A lexical token from the unit expression."""
    type: TokenType
    value: str
    position: int


# Unicode superscript to ASCII digit mapping
_SUPERSCRIPT_MAP = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻', '0123456789-')

# Regex for Unicode superscript sequences (including negative)
_SUPERSCRIPT_PATTERN = re.compile(r'^[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+')


class ParseError(ValueError):
    """Raised when unit expression parsing fails."""

    def __init__(self, message: str, position: int, expression: str):
        self.position = position
        self.expression = expression
        # Create a pointer to the error position
        pointer = ' ' * position + '^'
        super().__init__(f"{message} at position {position}:\n  {expression}\n  {pointer}")


class Tokenizer:
    """
    Lexer for unit expressions.

    Produces a stream of tokens from a unit string.
    """

    # Multiplication operators (all normalize to MUL)
    _MUL_CHARS = {'*', '·', '⋅', '×'}

    def __init__(self, expression: str):
        self.expression = expression
        self.pos = 0
        self.length = len(expression)

    def _skip_whitespace(self) -> None:
        """Skip any whitespace characters."""
        while self.pos < self.length and self.expression[self.pos].isspace():
            self.pos += 1

    # Unicode superscript characters (should NOT be part of identifiers)
    _SUPERSCRIPT_CHARS = set('⁰¹²³⁴⁵⁶⁷⁸⁹⁻')

    def _read_identifier(self) -> str:
        """
        Read an identifier (unit name).

        Identifiers can contain:
        - Letters (including µ, °)
        - ASCII digits (but not starting with digit)
        - Underscores

        Stops at Unicode superscripts (they are separate exponent tokens).
        """
        start = self.pos
        while self.pos < self.length:
            ch = self.expression[self.pos]
            # Stop at superscript characters - they are exponents, not part of unit name
            if ch in self._SUPERSCRIPT_CHARS:
                break
            # Allow letters, ASCII digits, underscores, and special chars like µ, °
            if ch.isalnum() or ch in '_µ°':
                self.pos += 1
            else:
                break
        return self.expression[start:self.pos]

    def _read_number(self) -> str:
        """Read a numeric value (integer, possibly negative)."""
        start = self.pos
        if self.pos < self.length and self.expression[self.pos] == '-':
            self.pos += 1
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

    def peek(self) -> Token:
        """Look at the next token without consuming it."""
        saved_pos = self.pos
        token = self.next_token()
        self.pos = saved_pos
        return token

    def next_token(self) -> Token:
        """Return the next token from the input."""
        self._skip_whitespace()

        if self.pos >= self.length:
            return Token(TokenType.EOF, '', self.pos)

        start_pos = self.pos
        ch = self.expression[self.pos]

        # Single-character tokens
        if ch == '(':
            self.pos += 1
            return Token(TokenType.LPAREN, '(', start_pos)
        if ch == ')':
            self.pos += 1
            return Token(TokenType.RPAREN, ')', start_pos)
        if ch == '/':
            self.pos += 1
            return Token(TokenType.DIV, '/', start_pos)
        if ch == '^':
            self.pos += 1
            return Token(TokenType.POW, '^', start_pos)
        if ch in self._MUL_CHARS:
            self.pos += 1
            return Token(TokenType.MUL, ch, start_pos)

        # Unicode superscripts (treated as implicit POW + NUMBER)
        if ch in '⁰¹²³⁴⁵⁶⁷⁸⁹⁻':
            num = self._read_superscript()
            return Token(TokenType.NUMBER, num, start_pos)

        # Numbers (for exponents after ^)
        if ch.isdigit() or (ch == '-' and self.pos + 1 < self.length
                           and self.expression[self.pos + 1].isdigit()):
            num = self._read_number()
            return Token(TokenType.NUMBER, num, start_pos)

        # Identifiers (unit names)
        if ch.isalpha() or ch in '_µ°':
            ident = self._read_identifier()
            return Token(TokenType.IDENT, ident, start_pos)

        # Unknown character
        raise ParseError(f"Unexpected character '{ch}'", self.pos, self.expression)


class UnitParser:
    """
    Recursive descent parser for unit expressions.

    Builds a UnitProduct from a string like `W/(m²*K)` or `mg/kg/d`.
    """

    def __init__(
        self,
        expression: str,
        lookup_fn: Callable[[str], Tuple['Unit', 'Scale']],
        unit_factor_cls: type,
        unit_product_cls: type,
    ):
        """
        Initialize the parser.

        Args:
            expression: The unit expression to parse.
            lookup_fn: Function to resolve unit names to (Unit, Scale) tuples.
            unit_factor_cls: The UnitFactor class.
            unit_product_cls: The UnitProduct class.
        """
        self.expression = expression
        self.lookup_fn = lookup_fn
        self.unit_factor_cls = unit_factor_cls
        self.unit_product_cls = unit_product_cls
        self.tokenizer = Tokenizer(expression)
        self.current_token = self.tokenizer.next_token()

    def _advance(self) -> Token:
        """Consume current token and advance to next."""
        token = self.current_token
        self.current_token = self.tokenizer.next_token()
        return token

    def _expect(self, token_type: TokenType) -> Token:
        """Consume a token of the expected type, or raise an error."""
        if self.current_token.type != token_type:
            raise ParseError(
                f"Expected {token_type.name}, got {self.current_token.type.name}",
                self.current_token.position,
                self.expression,
            )
        return self._advance()

    def parse(self) -> 'UnitProduct':
        """
        Parse the expression and return a UnitProduct.

        Raises:
            ParseError: If the expression is malformed.
        """
        result = self._parse_expr()
        if self.current_token.type != TokenType.EOF:
            raise ParseError(
                f"Unexpected token '{self.current_token.value}'",
                self.current_token.position,
                self.expression,
            )
        return result

    def _parse_expr(self) -> 'UnitProduct':
        """
        Parse: unit_expr := term (('*' | '·' | '/' | '⋅') term)*

        Handles multiplication and division at the same precedence level,
        left-to-right associativity.
        """
        left = self._parse_term()

        while self.current_token.type in (TokenType.MUL, TokenType.DIV):
            op = self._advance()
            right = self._parse_term()

            if op.type == TokenType.MUL:
                left = self._multiply(left, right)
            else:  # DIV
                left = self._divide(left, right)

        return left

    def _parse_term(self) -> 'UnitProduct':
        """
        Parse: term := factor ('^' exponent)?

        Also handles implicit exponent from Unicode superscripts.
        """
        base = self._parse_factor()

        # Explicit ^ exponent
        if self.current_token.type == TokenType.POW:
            self._advance()
            exp_token = self._expect(TokenType.NUMBER)
            exp = float(exp_token.value)
            return self._power(base, exp)

        # Implicit exponent from Unicode superscript (NUMBER token follows IDENT)
        if self.current_token.type == TokenType.NUMBER:
            # Only consume if it looks like a superscript-derived number
            # (i.e., the previous factor was a unit, not inside parens)
            exp_token = self._advance()
            exp = float(exp_token.value)
            return self._power(base, exp)

        return base

    def _parse_factor(self) -> 'UnitProduct':
        """
        Parse: factor := '(' unit_expr ')' | scale_unit
        """
        if self.current_token.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expr()
            self._expect(TokenType.RPAREN)
            return expr

        if self.current_token.type == TokenType.IDENT:
            return self._parse_unit_atom()

        raise ParseError(
            f"Expected unit or '(', got {self.current_token.type.name}",
            self.current_token.position,
            self.expression,
        )

    def _parse_unit_atom(self) -> 'UnitProduct':
        """
        Parse a unit identifier and resolve it to a UnitProduct.

        Handles scale prefixes via the lookup function.
        """
        token = self._expect(TokenType.IDENT)
        unit, scale = self.lookup_fn(token.value)
        uf = self.unit_factor_cls(unit, scale)
        return self.unit_product_cls({uf: 1})

    def _multiply(self, left: 'UnitProduct', right: 'UnitProduct') -> 'UnitProduct':
        """Multiply two UnitProducts."""
        factors: Dict['UnitFactor', float] = dict(left.factors)
        for uf, exp in right.factors.items():
            factors[uf] = factors.get(uf, 0) + exp
        return self.unit_product_cls(factors)

    def _divide(self, left: 'UnitProduct', right: 'UnitProduct') -> 'UnitProduct':
        """Divide left by right (negate right's exponents)."""
        factors: Dict['UnitFactor', float] = dict(left.factors)
        for uf, exp in right.factors.items():
            factors[uf] = factors.get(uf, 0) - exp
        return self.unit_product_cls(factors)

    def _power(self, base: 'UnitProduct', exp: float) -> 'UnitProduct':
        """Raise a UnitProduct to a power."""
        factors = {uf: e * exp for uf, e in base.factors.items()}
        return self.unit_product_cls(factors)


def parse_unit_expression(
    expression: str,
    lookup_fn: Callable[[str], Tuple['Unit', 'Scale']],
    unit_factor_cls: type,
    unit_product_cls: type,
) -> 'UnitProduct':
    """
    Parse a unit expression string into a UnitProduct.

    This is the main entry point for parsing complex unit expressions.

    Args:
        expression: The unit expression (e.g., "W/(m²*K)", "mg/kg/d").
        lookup_fn: Function to resolve unit names to (Unit, Scale) tuples.
        unit_factor_cls: The UnitFactor class.
        unit_product_cls: The UnitProduct class.

    Returns:
        A UnitProduct representing the parsed expression.

    Raises:
        ParseError: If the expression is malformed.

    Examples:
        >>> parse_unit_expression("m/s²", lookup_fn, UnitFactor, UnitProduct)
        <UnitProduct m/s²>
    """
    parser = UnitParser(expression, lookup_fn, unit_factor_cls, unit_product_cls)
    return parser.parse()

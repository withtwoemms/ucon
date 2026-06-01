# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.parsing.units
==================

Recursive descent parser for unit expressions and quantity strings.

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
from typing import Callable, Tuple, TYPE_CHECKING

from ucon.core import Number, UnknownUnitError
from ucon.parsing.lexer import (
    ParseError,
    _Token,
    _TokenType,
    _Tokenizer,
)

if TYPE_CHECKING:
    from ucon.system import UnitSystem

if TYPE_CHECKING:
    from ucon.core import Scale, Unit, UnitProduct


class _UnitParser:
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
        self.tokenizer = _Tokenizer(expression)
        self.current_token = self.tokenizer.next_token()

    def _advance(self) -> _Token:
        """Consume current token and advance to next."""
        token = self.current_token
        self.current_token = self.tokenizer.next_token()
        return token

    def _expect(self, token_type: _TokenType) -> _Token:
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
        if self.current_token.type != _TokenType.EOF:
            raise ParseError(
                f"Unexpected token '{self.current_token.value}'",
                self.current_token.position,
                self.expression,
            )
        return result

    def _parse_expr(self) -> 'UnitProduct':
        """
        Parse: unit_expr := term (('*' | '·' | '/' | '⋅') term)*

        Multiplication and division have equal precedence and associate
        left-to-right (standard order of operations).  Use parentheses
        for multi-term denominators: ``m³/(kg·s²)``.
        """
        left = self._parse_term()

        while self.current_token.type in (_TokenType.MUL, _TokenType.DIV):
            op = self._advance()
            right = self._parse_term()

            if op.type == _TokenType.MUL:
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
        if self.current_token.type == _TokenType.POW:
            self._advance()
            exp_token = self._expect(_TokenType.NUMBER)
            exp = float(exp_token.value)
            return self._power(base, exp)

        # Implicit exponent from Unicode superscript (NUMBER token follows IDENT)
        if self.current_token.type == _TokenType.NUMBER:
            # Only consume if it looks like a superscript-derived number
            # (i.e., the previous factor was a unit, not inside parens)
            exp_token = self._advance()
            exp = float(exp_token.value)
            return self._power(base, exp)

        return base

    def _parse_factor(self) -> 'UnitProduct':
        """
        Parse: factor := '(' unit_expr ')' | '1' | scale_unit

        A bare ``1`` is accepted as the dimensionless identity so that
        expressions like ``1/mol`` parse as ``mol⁻¹``.
        """
        if self.current_token.type == _TokenType.LPAREN:
            self._advance()
            expr = self._parse_expr()
            self._expect(_TokenType.RPAREN)
            return expr

        if self.current_token.type == _TokenType.IDENT:
            return self._parse_unit_atom()

        # Bare '1' as dimensionless identity (e.g., "1/mol")
        if (self.current_token.type == _TokenType.NUMBER
                and self.current_token.value == '1'):
            self._advance()
            return self.unit_product_cls({})

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
        token = self._expect(_TokenType.IDENT)
        unit, scale = self.lookup_fn(token.value)
        uf = self.unit_factor_cls(unit, scale)
        return self.unit_product_cls({uf: 1})

    def _multiply(self, left: 'UnitProduct', right: 'UnitProduct') -> 'UnitProduct':
        """Multiply two UnitProducts.

        Accumulates factors and composes canonical_scale from both operands.
        """
        # Accumulate factors from both operands
        combined = {}
        for uf, exp in left.factors.items():
            combined[uf] = combined.get(uf, 0.0) + exp
        for uf, exp in right.factors.items():
            combined[uf] = combined.get(uf, 0.0) + exp

        result = self.unit_product_cls(combined)

        # Compose canonical_scale from both operands
        result.canonical_scale *= left.canonical_scale * right.canonical_scale

        return result

    def _divide(self, left: 'UnitProduct', right: 'UnitProduct') -> 'UnitProduct':
        """Divide left by right (negate right's exponents).

        Accumulates factors and composes canonical_scale from both operands.
        """
        # Accumulate factors: left at +exp, right at -exp
        combined = {}
        for uf, exp in left.factors.items():
            combined[uf] = combined.get(uf, 0.0) + exp
        for uf, exp in right.factors.items():
            combined[uf] = combined.get(uf, 0.0) - exp

        result = self.unit_product_cls(combined)

        # Compose canonical_scale from both operands (right inverted)
        result.canonical_scale *= left.canonical_scale / right.canonical_scale

        return result

    def _power(self, base: 'UnitProduct', exp: float) -> 'UnitProduct':
        """Raise a UnitProduct to a power.

        Uses UnitProduct as a key to leverage its built-in merge logic.
        """
        return self.unit_product_cls({base: exp})


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
    parser = _UnitParser(expression, lookup_fn, unit_factor_cls, unit_product_cls)
    return parser.parse()


# -----------------------------------------------------------------------------
# Quantity parsing moved to ucon.parsing.quantity (Phase 2f).


__all__ = [
    "parse",
    "parse_unit_expression",
]

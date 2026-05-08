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

        Explicitly accumulates factors to:
        1. Handle equal operands correctly (second*second → s²)
        2. Propagate _residual_scale_factor from both operands
        """
        # Accumulate factors from both operands
        combined = {}
        for uf, exp in left.factors.items():
            combined[uf] = combined.get(uf, 0.0) + exp
        for uf, exp in right.factors.items():
            combined[uf] = combined.get(uf, 0.0) + exp

        result = self.unit_product_cls(combined)

        # Propagate residual scale factors from both operands
        left_residual = getattr(left, '_residual_scale_factor', 1.0)
        right_residual = getattr(right, '_residual_scale_factor', 1.0)
        if left_residual != 1.0 or right_residual != 1.0:
            result._residual_scale_factor = result._residual_scale_factor * left_residual * right_residual

        return result

    def _divide(self, left: 'UnitProduct', right: 'UnitProduct') -> 'UnitProduct':
        """Divide left by right (negate right's exponents).

        Explicitly accumulates factors to:
        1. Handle equal operands correctly
        2. Propagate _residual_scale_factor from both operands
        """
        # Accumulate factors: left at +exp, right at -exp
        combined = {}
        for uf, exp in left.factors.items():
            combined[uf] = combined.get(uf, 0.0) + exp
        for uf, exp in right.factors.items():
            combined[uf] = combined.get(uf, 0.0) - exp

        result = self.unit_product_cls(combined)

        # Propagate residual scale factors (right is inverted, so its residual is raised to -1)
        left_residual = getattr(left, '_residual_scale_factor', 1.0)
        right_residual = getattr(right, '_residual_scale_factor', 1.0)
        if left_residual != 1.0 or right_residual != 1.0:
            # right's residual is inverted since we're dividing
            result._residual_scale_factor = result._residual_scale_factor * left_residual / right_residual

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
# Quantity Parsing (v0.8.5)
# -----------------------------------------------------------------------------

# Regex for quantity parsing
# Matches: optional sign, number (int/float/scientific), optional uncertainty, unit
_QUANTITY_PATTERN = re.compile(
    r"""
    ^\s*
    (?P<value>[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)  # numeric value
    \s*
    (?:
        (?:±|\+/-)\s*(?P<uncertainty>\d+\.?\d*(?:[eE][+-]?\d+)?)  # ± uncertainty
        |
        \((?P<paren_unc>\d+)\)  # parenthetical uncertainty
    )?
    \s*
    (?P<unit>.*)  # unit string (may be empty)
    $
    """,
    re.VERBOSE
)

# Pattern for uncertainty with unit: "1.234 m ± 0.005 m"
_UNCERTAINTY_WITH_UNIT_PATTERN = re.compile(
    r"""
    ^\s*
    (?P<value>[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)  # numeric value
    \s+
    (?P<unit1>[^\s±]+(?:\s*/\s*[^\s±]+)*)  # unit (with possible division)
    \s*
    (?:±|\+/-)\s*
    (?P<uncertainty>\d+\.?\d*(?:[eE][+-]?\d+)?)  # uncertainty value
    \s+
    (?P<unit2>.+)  # second unit (should match first)
    $
    """,
    re.VERBOSE
)


def parse(s: str) -> 'Number':
    """Parse a quantity string into a Number.

    Supports various formats:
    - Basic quantities: "60 mph", "9.81 m/s^2", "1.5 kg"
    - Pure numbers: "100", "3.14159" (returns dimensionless Number)
    - Scientific notation: "1.5e3 m", "6.022e23"
    - Negative values: "-273.15 °C"
    - Uncertainty with ±: "1.234 ± 0.005 m"
    - Uncertainty with +/-: "1.234 +/- 0.005 m"
    - Parenthetical uncertainty: "1.234(5) m" (means 1.234 ± 0.005)
    - Uncertainty with unit: "1.234 m ± 0.005 m"

    The function respects context from using_graph() for unit resolution.

    Args:
        s: The quantity string to parse.

    Returns:
        A Number representing the parsed quantity.

    Raises:
        ValueError: If the string cannot be parsed.
        UnknownUnitError: If the unit cannot be resolved.

    Examples:
        >>> parse("60 mph")
        <60 mph>
        >>> parse("1.234 ± 0.005 m")
        <1.234 ± 0.005 m>
        >>> parse("9.81 m/s^2")
        <9.81 m/s²>
        >>> parse("100")
        <100>
    """
    if not s or not s.strip():
        raise ValueError("Cannot parse empty string")

    from ucon.resolver import parse_unit

    s = s.strip()

    # Try "value unit ± uncertainty unit" format first
    unc_with_unit = _UNCERTAINTY_WITH_UNIT_PATTERN.match(s)
    if unc_with_unit:
        value = float(unc_with_unit.group("value"))
        unit_str = unc_with_unit.group("unit1").strip()
        uncertainty = float(unc_with_unit.group("uncertainty"))

        unit = parse_unit(unit_str)
        return Number(quantity=value, unit=unit, uncertainty=uncertainty)

    # Standard quantity pattern
    match = _QUANTITY_PATTERN.match(s)
    if not match:
        raise ValueError(f"Cannot parse quantity: {s!r}")

    value_str = match.group("value")
    unit_str = match.group("unit").strip() if match.group("unit") else ""

    # Validate numeric value
    try:
        value = float(value_str)
    except ValueError:
        raise ValueError(f"Invalid numeric value: {value_str!r}")

    # Handle uncertainty
    uncertainty = None
    if match.group("uncertainty"):
        uncertainty = float(match.group("uncertainty"))
    elif match.group("paren_unc"):
        # Parenthetical: "1.234(5)" means 1.234 ± 0.005
        paren = match.group("paren_unc")
        # Determine scale from decimal places in value
        if "." in value_str:
            # Count decimal places (excluding trailing exponent)
            base_value = value_str.split('e')[0].split('E')[0]
            decimal_part = base_value.split(".")[1] if "." in base_value else ""
            decimal_places = len(decimal_part)
            uncertainty = int(paren) * (10 ** -decimal_places)
        else:
            uncertainty = float(paren)

    # Parse unit (or return dimensionless)
    if unit_str:
        unit = parse_unit(unit_str)
    else:
        unit = None  # Number will use dimensionless default

    return Number(quantity=value, unit=unit, uncertainty=uncertainty)


__all__ = [
    "parse",
    "parse_unit_expression",
]

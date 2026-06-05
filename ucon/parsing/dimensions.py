# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.parsing.dimensions
=======================

Recursive descent parser for dimension expressions.

Accepts three input forms in one parser:

1. **Component symbols** of the active basis (``"M"``, ``"L"``, ``"T"``,
   ``"I"``, ``"Θ"``, ``"J"``, ``"N"``, ``"B"``).
2. **Component / dimension names** (``"mass"``, ``"length"``,
   ``"velocity"``, ``"force"``, ``"energy"``, …).
3. **Algebraic expressions** combining the above with ``*`` / ``·`` /
   ``⋅`` / ``/`` and exponents (``^N`` or Unicode superscripts):
   ``"M·L/T^2"``, ``"L/T"``, ``"L^2"``, ``"M*L/T²"``, ``"1/T"``.

Grammar
-------
::

    dim_expr := term (('*' | '·' | '⋅' | '/') term)*
    term     := factor ('^' NUMBER | NUMBER_superscript)?
    factor   := '(' dim_expr ')' | '1' | IDENT

This module is loaded lazily by :mod:`ucon.parsing` (via PEP 562
``__getattr__``) to avoid a load-time cycle through the
``ucon.units`` → ``ucon.resolver`` → ``ucon.parsing`` chain — by the
time anyone *calls* :func:`parse_dimension`, :mod:`ucon.dimension` is
fully loaded.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ucon.basis import Basis
from ucon.basis.builtin import SI
from ucon._active import _active as _sys_active_var
from ucon.dimension import (
    NONE,
    Dimension,
    _DIMENSION_ATTRS,
)
from ucon.parsing.lexer import _Tokenizer, _TokenType

if TYPE_CHECKING:
    from ucon.system import UnitSystem


def parse_dimension(
    spec: str,
    basis: Basis | None = None,
    *,
    system: "UnitSystem | None" = None,
) -> "Dimension":
    """Parse a dimension string into a :class:`~ucon.dimension.Dimension`.

    Accepts three input forms (all in one parser):

    1. **Component symbols** of the active basis:
       ``"M"``, ``"L"``, ``"T"``, ``"I"``, ``"Θ"``, ``"J"``, ``"N"``, ``"B"``.
    2. **Component / dimension names**: ``"mass"``, ``"length"``,
       ``"velocity"``, ``"force"``, ``"energy"``, etc. (any name registered
       via :func:`Dimension.from_components` or as a module-level constant).
    3. **Algebraic expressions** combining the above with ``*`` / ``·`` /
       ``⋅`` / ``/`` and exponents (``^2`` or Unicode superscripts):
       ``"M·L/T^2"``, ``"L/T"``, ``"L^2"``, ``"M*L/T²"``, ``"1/T"``.

    Parameters
    ----------
    spec : str
        The dimension string to parse.
    basis : Basis, optional
        The basis to interpret component symbols against. Defaults to the
        active :class:`UnitSystem`'s ``basis`` (typically SI), or
        ``system.basis`` when ``system`` is provided.
    system : UnitSystem, optional
        When provided, ``system.basis`` supplies the default basis (unless
        ``basis=`` is given explicitly) and ``system.dimensions`` is
        consulted before the module-level ``_DIMENSION_ATTRS`` registry.

    Returns
    -------
    Dimension
        The resolved dimension.

    Raises
    ------
    ValueError
        If the string is empty, malformed, or references an unknown
        identifier.

    Examples
    --------
    >>> parse_dimension("M")
    Dimension(mass)
    >>> parse_dimension("mass")
    Dimension(mass)
    >>> parse_dimension("M·T⁻¹")
    Dimension(...)
    >>> parse_dimension("velocity")
    Dimension(velocity)

    See Also
    --------
    :func:`~ucon.resolver.parse_unit` — sibling for unit strings.
    """
    if not spec or not spec.strip():
        raise ValueError("Cannot parse empty dimension string")

    spec = spec.strip()
    if basis is None:
        if system is not None:
            basis = system.basis
        else:
            ctx = _sys_active_var.get()
            basis = ctx.system.basis if ctx is not None else SI

    # System override: a direct hit in ``system.dimensions`` short-circuits.
    if system is not None:
        sys_dim = system.dimensions.get(spec)
        if sys_dim is not None:
            return sys_dim

    # Fast path: bare known dimension name (e.g., "length", "velocity").
    if spec in _DIMENSION_ATTRS:
        return _DIMENSION_ATTRS[spec]

    # Fast path: bare component symbol of the active basis (e.g., "M", "Θ").
    for comp in basis:
        if spec == comp.symbol or spec == comp.name:
            return Dimension.from_components(basis, **{comp.name: 1})

    # General path: tokenise and parse as an algebraic expression.
    return _DimensionParser(spec, basis).parse()


class _DimensionParser:
    """Recursive-descent parser for dimension expressions.

    Reuses :class:`ucon.parsing.lexer._Tokenizer` to share lexer behaviour
    with the unit parser (operators, parentheses, ASCII ``^N`` exponents,
    Unicode superscripts). Builds :class:`Dimension` values directly via
    Dimension algebra rather than going through ``UnitProduct``.
    """

    def __init__(self, spec: str, basis: Basis) -> None:
        self._spec = spec
        self._basis = basis
        self._tokenizer = _Tokenizer(spec)
        self._current = self._tokenizer.next_token()

    def _advance(self):
        tok = self._current
        self._current = self._tokenizer.next_token()
        return tok

    def parse(self) -> "Dimension":
        result = self._parse_expr()
        if self._current.type != _TokenType.EOF:
            raise ValueError(
                f"Unexpected token {self._current.value!r} at position "
                f"{self._current.position} in dimension {self._spec!r}"
            )
        return result

    def _parse_expr(self) -> "Dimension":
        left = self._parse_term()
        while self._current.type in (_TokenType.MUL, _TokenType.DIV):
            op = self._advance()
            right = self._parse_term()
            if op.type == _TokenType.MUL:
                left = left * right
            else:
                left = left / right
        return left

    def _parse_term(self) -> "Dimension":
        base = self._parse_factor()
        # Explicit ASCII ^ exponent.
        if self._current.type == _TokenType.POW:
            self._advance()
            exp_tok = self._advance()
            if exp_tok.type != _TokenType.NUMBER:
                raise ValueError(
                    f"Expected exponent at position {exp_tok.position} "
                    f"in dimension {self._spec!r}"
                )
            return base ** _to_exponent(exp_tok.value)
        # Implicit Unicode-superscript exponent.
        if self._current.type == _TokenType.NUMBER:
            exp_tok = self._advance()
            return base ** _to_exponent(exp_tok.value)
        return base

    def _parse_factor(self) -> "Dimension":
        if self._current.type == _TokenType.LPAREN:
            self._advance()
            expr = self._parse_expr()
            if self._current.type != _TokenType.RPAREN:
                raise ValueError(
                    f"Expected ')' at position {self._current.position} "
                    f"in dimension {self._spec!r}"
                )
            self._advance()
            return expr
        # Bare ``1`` as the dimensionless identity (so ``"1/T"`` parses).
        if self._current.type == _TokenType.NUMBER and self._current.value == "1":
            self._advance()
            return NONE
        if self._current.type == _TokenType.IDENT:
            tok = self._advance()
            return self._resolve_atom(tok.value)
        raise ValueError(
            f"Expected dimension or '(' at position {self._current.position} "
            f"in dimension {self._spec!r}"
        )

    def _resolve_atom(self, ident: str) -> "Dimension":
        # Named dimensions (component or derived) take priority. This means
        # "mass" → MASS regardless of basis, and "velocity" → VELOCITY.
        if ident in _DIMENSION_ATTRS:
            return _DIMENSION_ATTRS[ident]
        # Component symbol or name in the active basis.
        for comp in self._basis:
            if ident == comp.symbol or ident == comp.name:
                return Dimension.from_components(self._basis, **{comp.name: 1})
        raise ValueError(
            f"Unknown dimension identifier {ident!r} in dimension {self._spec!r}"
        )


def _to_exponent(s: str) -> int | float:
    """Convert an exponent token to int when integral, else float."""
    if "." in s:
        return float(s)
    return int(s)


__all__ = [
    "parse_dimension",
]

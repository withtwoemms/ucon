# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
ucon.expressions
================

AST-based safe expression evaluator for TOML factor fields.

Evaluates symbolic expressions like ``"1 / Eh"`` or ``"h * c"`` where
symbols resolve to physical constants.  Propagates relative uncertainty
via GUM (Guide to the Expression of Uncertainty in Measurement) rules.

Only ``ast.Constant``, ``ast.Name``, ``ast.BinOp``, and ``ast.UnaryOp``
nodes are accepted — no function calls, attribute access, or other
constructs.
"""
from __future__ import annotations

import ast
import math
from dataclasses import dataclass

__all__ = ['ExprResult', 'evaluate']


@dataclass(frozen=True)
class ExprResult:
    """Result of evaluating an expression with uncertainty.

    Attributes
    ----------
    value : float
        The numeric result.
    rel_uncertainty : float
        Relative standard uncertainty (0.0 for exact values).
    """
    value: float
    rel_uncertainty: float = 0.0


def evaluate(expr: str, constants: dict[str, ExprResult]) -> ExprResult:
    """Evaluate a safe arithmetic expression with constant references.

    Parameters
    ----------
    expr : str
        Expression string, e.g. ``"42"``, ``"1 / Eh"``, ``"h * c"``,
        ``"mP * c**2"``.
    constants : dict[str, ExprResult]
        Mapping of constant symbols to their values and uncertainties.

    Returns
    -------
    ExprResult
        Evaluated value with propagated relative uncertainty.

    Raises
    ------
    ValueError
        On unknown symbols, unsupported syntax, or parse errors.
    """
    try:
        tree = ast.parse(expr, mode='eval')
    except SyntaxError as e:
        raise ValueError(f"Invalid expression: {expr!r}") from e
    return _eval_node(tree.body, constants)


def _eval_node(node: ast.AST, constants: dict[str, ExprResult]) -> ExprResult:
    """Recursively evaluate an AST node."""

    # Numeric literal
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return ExprResult(float(node.value))

    # Constant symbol reference
    if isinstance(node, ast.Name):
        if node.id not in constants:
            raise ValueError(f"Unknown symbol: {node.id!r}")
        return constants[node.id]

    # Unary operators: +x, -x
    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, constants)
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.USub):
            return ExprResult(-operand.value, operand.rel_uncertainty)
        raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")

    # Binary operators: +, -, *, /, **
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, constants)
        right = _eval_node(node.right, constants)
        return _eval_binop(node.op, left, right)

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def _eval_binop(op: ast.operator, left: ExprResult, right: ExprResult) -> ExprResult:
    """Evaluate a binary operation with GUM uncertainty propagation."""

    # Multiplication: rel = sqrt(r_left² + r_right²)
    if isinstance(op, ast.Mult):
        value = left.value * right.value
        rel = math.hypot(left.rel_uncertainty, right.rel_uncertainty)
        return ExprResult(value, rel)

    # Division: rel = sqrt(r_left² + r_right²)
    if isinstance(op, ast.Div):
        if right.value == 0:
            raise ValueError("Division by zero in expression")
        value = left.value / right.value
        rel = math.hypot(left.rel_uncertainty, right.rel_uncertainty)
        return ExprResult(value, rel)

    # Power: rel = |n| * rel(base), exponent must be exact
    if isinstance(op, ast.Pow):
        if right.rel_uncertainty != 0:
            raise ValueError(
                "Exponent must be an exact value (no uncertainty)"
            )
        value = left.value ** right.value
        rel = abs(right.value) * left.rel_uncertainty
        return ExprResult(value, rel)

    # Addition: propagate absolute uncertainties, convert back to relative
    if isinstance(op, ast.Add):
        value = left.value + right.value
        abs_left = abs(left.value) * left.rel_uncertainty
        abs_right = abs(right.value) * right.rel_uncertainty
        abs_unc = math.hypot(abs_left, abs_right)
        rel = abs_unc / abs(value) if value != 0 else 0.0
        return ExprResult(value, rel)

    # Subtraction: propagate absolute uncertainties, convert back to relative
    if isinstance(op, ast.Sub):
        value = left.value - right.value
        abs_left = abs(left.value) * left.rel_uncertainty
        abs_right = abs(right.value) * right.rel_uncertainty
        abs_unc = math.hypot(abs_left, abs_right)
        rel = abs_unc / abs(value) if value != 0 else 0.0
        return ExprResult(value, rel)

    raise ValueError(f"Unsupported binary operator: {type(op).__name__}")

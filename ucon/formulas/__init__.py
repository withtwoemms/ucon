# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Kind formulas: declared relationships between :class:`~ucon.kinds.types.Kind` nodes.

A formula is the **edge** of the kind graph: it documents the
relationship between operand kinds and a result kind, and (in later
versions) drives kind assignment for multiplication and named
computation. Addition dispatch is governed by the kind lattice, not
by formulas.

This subpackage is not wired into :class:`~ucon.quantity.Number` in
v1.9.x. ``aspect_rules`` gained operational semantics in v1.9.1 via
:meth:`~ucon.formulas.types.KindFormula.project_aspects` and
:meth:`~ucon.formulas.registry.FormulaRegistry.apply`.
``generalizes`` and ``commutative`` (higher-arity) are inert until
v1.9.2.
"""

from ucon.formulas.exceptions import (
    DuplicateFormula,
    FormulaError,
    FormulaNotFound,
)
from ucon.formulas.registry import FormulaRegistry
from ucon.formulas.types import AspectRule, KindFormula


__all__ = [
    # Types
    "KindFormula",
    "AspectRule",
    # Registry
    "FormulaRegistry",
    # Exceptions
    "FormulaError",
    "FormulaNotFound",
    "DuplicateFormula",
]

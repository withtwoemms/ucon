# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Kind formulas: declared relationships between :class:`~ucon.kinds.types.Kind` nodes.

A formula is the **edge** of the kind graph: it documents the
relationship between operand kinds and a result kind, and (in later
versions) drives kind assignment for multiplication and named
computation. Addition dispatch is governed by the kind lattice, not
by formulas.

Formulas do kind work only: aspect propagation is the aspect
stratum's carry rule (``ucon.aspects``), not a formula concern —
formulas do not produce aspects. ``generalizes`` and ``commutative``
gained semantics in v1.9.2.
"""

from ucon.formulas.exceptions import (
    AmbiguousFormula,
    DuplicateFormula,
    FormulaError,
    FormulaNotFound,
)
from ucon.formulas.registry import FormulaRegistry
from ucon.formulas.types import KindFormula, LookupResult, MatchKind


__all__ = [
    # Types
    "KindFormula",
    "LookupResult",
    "MatchKind",
    # Registry
    "FormulaRegistry",
    # Exceptions
    "FormulaError",
    "FormulaNotFound",
    "DuplicateFormula",
    "AmbiguousFormula",
]

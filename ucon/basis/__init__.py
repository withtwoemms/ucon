# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Basis abstraction for user-definable dimensional coordinate systems.

This package provides the foundation for representing dimensions in arbitrary
bases (SI, CGS, CGS-ESU, natural units, custom domains) without hardcoding
to a specific set of components.

Submodules
----------
- ``types``: Core types (``Basis``, ``BasisComponent``, exceptions including
  ``BasisMismatch``, ``LossyProjection``, ``NoTransformPath``).
- ``vector``: ``Vector`` dimensional exponent vectors. Arithmetic is strict
  same-basis; cross-basis arithmetic lives in ``ops``.
- ``transforms``: Transform types and standard transform instances.
- ``graph``: ``BasisGraph`` registry and standard-graph factory.
- ``ops``: Explicit cross-basis arithmetic (``multiply_via``, ``divide_via``,
  ``unify``).
- ``builtin``: Standard bases (SI, CGS, CGS-ESU, CGS-EMU, NATURAL, PLANCK, ATOMIC).
"""

from ucon.basis import ops
from ucon.basis.graph import BasisGraph
from ucon.basis.transforms import (
    BasisTransform,
    ConstantBinding,
    ConstantBoundBasisTransform,
)
from ucon.basis.types import (
    Basis,
    BasisComponent,
    BasisMismatch,
    LossyProjection,
    NoTransformPath,
)
from ucon.basis.vector import Vector

__all__ = [
    "Basis",
    "BasisComponent",
    "BasisGraph",
    "BasisMismatch",
    "BasisTransform",
    "ConstantBinding",
    "ConstantBoundBasisTransform",
    "LossyProjection",
    "NoTransformPath",
    "Vector",
    "ops",
]

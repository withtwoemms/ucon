# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Basis abstraction for user-definable dimensional coordinate systems.

This package provides the foundation for representing dimensions in arbitrary
bases (SI, CGS, CGS-ESU, natural units, custom domains) without hardcoding
to a specific set of components.

Submodules
----------
- ``types``: Core types (``Basis``, ``BasisComponent``, exceptions)
- ``vector``: ``Vector`` dimensional exponent vectors
- ``transforms``: Transform types and standard transform instances
- ``graph``: ``BasisGraph`` registry, standard-graph factory, and
  ContextVar-scoped active state (``get_basis_graph``, ``using_basis``, etc.)
- ``builtin``: Standard bases (SI, CGS, CGS-ESU, CGS-EMU, NATURAL, PLANCK, ATOMIC)
"""

from ucon.basis.graph import (
    BasisGraph,
    get_basis_graph,
    get_default_basis,
    reset_default_basis_graph,
    set_default_basis_graph,
    using_basis,
    using_basis_graph,
)
from ucon.basis.transforms import (
    BasisTransform,
    ConstantBinding,
    ConstantBoundBasisTransform,
)
from ucon.basis.types import (
    Basis,
    BasisComponent,
    LossyProjection,
    NoTransformPath,
)
from ucon.basis.vector import Vector

__all__ = [
    "Basis",
    "BasisComponent",
    "BasisGraph",
    "BasisTransform",
    "ConstantBinding",
    "ConstantBoundBasisTransform",
    "LossyProjection",
    "NoTransformPath",
    "Vector",
    "get_basis_graph",
    "get_default_basis",
    "reset_default_basis_graph",
    "set_default_basis_graph",
    "using_basis",
    "using_basis_graph",
]

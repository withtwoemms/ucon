# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Kind lattice: dimensional refinements for :class:`~ucon.quantity.Number`.

A *kind* refines a dimension. Energy is a dimension; kinetic energy,
potential energy, and enthalpy are kinds within that dimension. Kinds
form rooted trees, partitioned by dimensional equivalence class, and
arithmetic that crosses the partition is governed by the kind's
``join_policy``.

This subpackage provides storage and structural reasoning only. It is
not wired into :class:`~ucon.quantity.Number` in v1.9.x; users build
lattices, query LCAs, and test load-time validation in isolation. In
v2.0.0 the lattice becomes a member of ``UnitSystem``.
"""

from ucon.kinds.exceptions import (
    AliasCollision,
    CrossDimensionParent,
    JoinRefused,
    KindCycle,
    KindError,
    KindNotFound,
    NameCollision,
    OrphanParent,
)
from ucon.kinds.lattice import KindLattice, lca
from ucon.kinds.types import JoinPolicy, Kind


__all__ = [
    # Types
    "Kind",
    "JoinPolicy",
    # Lattice
    "KindLattice",
    "lca",
    # Exceptions
    "KindError",
    "KindCycle",
    "OrphanParent",
    "CrossDimensionParent",
    "NameCollision",
    "AliasCollision",
    "KindNotFound",
    "JoinRefused",
]

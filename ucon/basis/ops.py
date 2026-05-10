# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Explicit cross-basis arithmetic for :class:`ucon.basis.vector.Vector`.

``Vector`` arithmetic is strict same-basis (raises
:class:`ucon.basis.types.BasisMismatch`). When two vectors live in
different bases, the active :class:`ucon.basis.graph.BasisGraph` is consulted
for a clean (non-lossy) projection between them. Both directions are tried;
the first clean projection wins. A "clean" projection is one that does not
raise :class:`ucon.basis.types.LossyProjection` — i.e., no non-zero
component of the source vector would be discarded.

Public surface
--------------
- :func:`unify` — re-express two vectors in a common basis.
- :func:`multiply_via` — multiply two vectors, unifying bases as needed.
- :func:`divide_via` — divide two vectors, unifying bases as needed.

All three accept an optional ``graph=`` kwarg or an optional ``system=``
kwarg (which contributes its ``basis_graph``). When neither is given, the
ContextVar-scoped active graph from
:func:`ucon.basis.graph.get_basis_graph` is used.

This module sits at the top of the basis subpackage's import DAG: it
imports ``types``, ``vector``, and ``graph``, but nothing imports it from
within ``ucon.basis``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ucon.basis.graph import BasisGraph, get_basis_graph
from ucon.basis.types import BasisMismatch, LossyProjection, NoTransformPath
from ucon.basis.vector import Vector

if TYPE_CHECKING:
    from ucon.system import UnitSystem


def _resolve_graph(
    *, system: "UnitSystem | None", graph: BasisGraph | None
) -> BasisGraph:
    """Pick the BasisGraph to consult.

    Preference order: explicit ``graph`` > ``system.basis_graph`` >
    ContextVar-scoped active graph.
    """
    if graph is not None:
        return graph
    if system is not None:
        return system.basis_graph
    return get_basis_graph()


def unify(
    a: Vector,
    b: Vector,
    *,
    system: "UnitSystem | None" = None,
    graph: BasisGraph | None = None,
) -> tuple[Vector, Vector]:
    """Bring two vectors into a common basis.

    If ``a`` and ``b`` already share a basis, they are returned unchanged.
    Otherwise a clean (non-lossy) projection is sought in both directions
    via the resolved :class:`BasisGraph`.

    Parameters
    ----------
    a, b : Vector
        Vectors to unify.
    system : UnitSystem, optional
        If provided (and ``graph`` is not), the system's ``basis_graph`` is
        consulted.
    graph : BasisGraph, optional
        Explicit graph override. Wins over ``system``.

    Returns
    -------
    tuple[Vector, Vector]
        ``(a', b')`` re-expressed in a single common basis.

    Raises
    ------
    BasisMismatch
        If no clean projection connects the two bases in either direction.
    """
    if a.basis == b.basis:
        return a, b

    g = _resolve_graph(system=system, graph=graph)

    # Try projecting a into b's basis.
    try:
        transform = g.get_transform(a.basis, b.basis)
        return transform(a), b
    except (NoTransformPath, LossyProjection):
        pass

    # Try projecting b into a's basis.
    try:
        transform = g.get_transform(b.basis, a.basis)
        return a, transform(b)
    except (NoTransformPath, LossyProjection):
        pass

    raise BasisMismatch(
        f"Cannot unify vectors from different bases: "
        f"'{a.basis.name}' and '{b.basis.name}'",
        left=a.basis,
        right=b.basis,
        op="unify",
    )


def multiply_via(
    a: Vector,
    b: Vector,
    *,
    system: "UnitSystem | None" = None,
    graph: BasisGraph | None = None,
) -> Vector:
    """Multiply two vectors, unifying bases via a :class:`BasisGraph`.

    Same-basis multiplication is identical to ``a * b``. Cross-basis
    multiplication consults the resolved graph for a clean projection.

    Parameters
    ----------
    a, b : Vector
        Vectors to multiply.
    system : UnitSystem, optional
        If provided (and ``graph`` is not), the system's ``basis_graph`` is
        consulted for cross-basis projection.
    graph : BasisGraph, optional
        Explicit graph override. Wins over ``system``.

    Returns
    -------
    Vector
        The component-wise sum of the two vectors after unification, in
        the common basis.

    Raises
    ------
    BasisMismatch
        If no clean projection connects the two bases.
    """
    if a.basis == b.basis:
        return a * b
    a_, b_ = unify(a, b, system=system, graph=graph)
    return Vector(
        a_.basis,
        tuple(x + y for x, y in zip(a_.components, b_.components)),
    )


def divide_via(
    a: Vector,
    b: Vector,
    *,
    system: "UnitSystem | None" = None,
    graph: BasisGraph | None = None,
) -> Vector:
    """Divide two vectors, unifying bases via a :class:`BasisGraph`.

    Same-basis division is identical to ``a / b``. Cross-basis division
    consults the resolved graph for a clean projection.

    Parameters
    ----------
    a, b : Vector
        Vectors to divide.
    system : UnitSystem, optional
        If provided (and ``graph`` is not), the system's ``basis_graph`` is
        consulted for cross-basis projection.
    graph : BasisGraph, optional
        Explicit graph override. Wins over ``system``.

    Returns
    -------
    Vector
        The component-wise difference of the two vectors after unification.

    Raises
    ------
    BasisMismatch
        If no clean projection connects the two bases.
    """
    if a.basis == b.basis:
        return a / b
    a_, b_ = unify(a, b, system=system, graph=graph)
    return Vector(
        a_.basis,
        tuple(x - y for x, y in zip(a_.components, b_.components)),
    )


__all__ = [
    "divide_via",
    "multiply_via",
    "unify",
]

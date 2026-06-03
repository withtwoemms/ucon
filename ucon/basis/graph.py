# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
BasisGraph registry, standard-graph factory, and active-state accessors.

This module owns three cohesive concerns:

1. :class:`BasisGraph` — the graph type and path-finding/composition logic.
2. :func:`_build_standard_basis_graph` — factory that constructs the default
   graph populated with the standard SI/CGS/CGS-ESU/CGS-EMU/natural/planck/atomic
   transforms.
3. ContextVar-scoped active state and accessors (:func:`get_basis_graph`,
   :func:`using_basis`, :func:`using_basis_graph`, :func:`get_default_basis`).

The accessors live alongside the graph type because they exist to serve it.
The basis subpackage is a clean DAG (``types ← vector ← transforms ← graph
← ops``); ``transforms`` does not depend on ``graph``, so all imports here
sit at module top.
"""

from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Union

from ucon.basis.builtin import SI
from ucon.basis.transforms import (
    ATOMIC_TO_NATURAL,
    ATOMIC_TO_PLANCK,
    CGS_EMU_TO_CGS_ESU,
    CGS_ESU_TO_CGS_EMU,
    CGS_TO_SI,
    NATURAL_TO_ATOMIC,
    NATURAL_TO_PLANCK,
    PLANCK_TO_ATOMIC,
    PLANCK_TO_NATURAL,
    SI_TO_ATOMIC,
    SI_TO_CGS,
    SI_TO_CGS_EMU,
    SI_TO_CGS_ESU,
    SI_TO_NATURAL,
    SI_TO_PLANCK,
    BasisTransform,
    ConstantBoundBasisTransform,
)
from ucon.basis.types import Basis, NoTransformPath
from ucon._active import _active as _active_system

_Transform = Union[BasisTransform, ConstantBoundBasisTransform]


class BasisGraph:
    """Graph of basis transforms with path-finding and composition.

    Nodes are Basis objects (dimensional coordinate systems).
    Edges are BasisTransform objects.
    Path-finding composes transforms transitively.

    Examples:
        >>> graph = BasisGraph()
        >>> graph.add_transform(SI_TO_CGS)
        >>> graph.add_transform(CGS_TO_CGS_ESU)
        >>> # Transitive composition: SI -> CGS -> CGS-ESU
        >>> transform = graph.get_transform(SI, CGS_ESU)
    """

    def __init__(self) -> None:
        self._edges: dict[Basis, dict[Basis, "_Transform"]] = {}
        self._cache: dict[tuple[Basis, Basis], "_Transform"] = {}

    def add_transform(self, transform: "_Transform") -> None:
        """Register a transform. Does NOT auto-register inverse.

        Args:
            transform: The transform to register.
        """
        if transform.source not in self._edges:
            self._edges[transform.source] = {}
        self._edges[transform.source][transform.target] = transform
        self._cache.clear()  # Invalidate composed transforms

    def add_transform_pair(
        self,
        forward: "BasisTransform",
        reverse: "BasisTransform",
    ) -> None:
        """Register bidirectional transforms (e.g., projection + embedding).

        Args:
            forward: Transform A -> B.
            reverse: Transform B -> A.
        """
        self.add_transform(forward)
        self.add_transform(reverse)

    def get_transform(self, source: Basis, target: Basis) -> "BasisTransform":
        """Find or compose a transform between bases.

        Args:
            source: The source basis.
            target: The target basis.

        Returns:
            A BasisTransform from source to target.

        Raises:
            NoTransformPath: If no path exists between the bases.
        """
        if source == target:
            return BasisTransform.identity(source)

        cache_key = (source, target)
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self._find_path(source, target)
        if path is None:
            raise NoTransformPath(source, target)

        composed = self._compose_path(path)
        self._cache[cache_key] = composed
        return composed

    def _find_path(
        self,
        source: Basis,
        target: Basis,
    ) -> "list[BasisTransform] | None":
        """BFS to find shortest transform path."""
        if source not in self._edges:
            return None

        queue: deque = deque([(source, [])])
        visited: set[Basis] = {source}

        while queue:
            current, path = queue.popleft()
            if current not in self._edges:
                continue

            for next_basis, transform in self._edges[current].items():
                if next_basis == target:
                    return path + [transform]
                if next_basis not in visited:
                    visited.add(next_basis)
                    queue.append((next_basis, path + [transform]))

        return None

    def _compose_path(self, path: "list[BasisTransform]") -> "BasisTransform":
        """Compose transforms along path via matrix multiplication."""
        result = path[0]
        for transform in path[1:]:
            result = transform @ result
        return result

    def are_connected(self, a: Basis, b: Basis) -> bool:
        """Check if two bases can interoperate.

        Args:
            a: First basis.
            b: Second basis.

        Returns:
            True if a path exists between the bases.
        """
        if a == b:
            return True
        return self._find_path(a, b) is not None

    def reachable_from(self, basis: Basis) -> set[Basis]:
        """Return all bases reachable from the given basis.

        Args:
            basis: The starting basis.

        Returns:
            Set of all bases reachable via transforms.
        """
        reachable: set[Basis] = {basis}
        frontier: list[Basis] = [basis]

        while frontier:
            current = frontier.pop()
            if current not in self._edges:
                continue
            for next_basis in self._edges[current]:
                if next_basis not in reachable:
                    reachable.add(next_basis)
                    frontier.append(next_basis)

        return reachable

    def with_transform(self, transform: "BasisTransform") -> "BasisGraph":
        """Return a new graph with an additional transform (copy-on-extend).

        Args:
            transform: The transform to add.

        Returns:
            A new BasisGraph with the additional transform.
        """
        new_graph = BasisGraph()
        # Deep copy edges
        for src, targets in self._edges.items():
            new_graph._edges[src] = dict(targets)
        new_graph.add_transform(transform)
        return new_graph

    def __repr__(self) -> str:
        edge_count = sum(len(targets) for targets in self._edges.values())
        basis_count = len(self._edges)
        return f"BasisGraph({basis_count} bases, {edge_count} transforms)"


def _build_standard_basis_graph() -> BasisGraph:
    """Build standard basis graph with SI/CGS/CGS-ESU/CGS-EMU/natural/planck/atomic transforms."""
    graph = BasisGraph()
    graph.add_transform(SI_TO_CGS)
    graph.add_transform(SI_TO_CGS_ESU)
    graph.add_transform(SI_TO_CGS_EMU)
    graph.add_transform(CGS_TO_SI)
    graph.add_transform(CGS_ESU_TO_CGS_EMU)
    graph.add_transform(CGS_EMU_TO_CGS_ESU)
    graph.add_transform(SI_TO_NATURAL)
    graph.add_transform(SI_TO_PLANCK)
    graph.add_transform(SI_TO_ATOMIC)
    graph.add_transform(NATURAL_TO_PLANCK)
    graph.add_transform(PLANCK_TO_NATURAL)
    graph.add_transform(NATURAL_TO_ATOMIC)
    graph.add_transform(ATOMIC_TO_NATURAL)
    graph.add_transform(PLANCK_TO_ATOMIC)
    graph.add_transform(ATOMIC_TO_PLANCK)
    return graph


# -----------------------------------------------------------------------------
# Active state: ContextVar-scoped basis and basis-graph
# -----------------------------------------------------------------------------

_default_basis: ContextVar[Basis | None] = ContextVar("basis", default=None)
_basis_graph_context: ContextVar[BasisGraph | None] = ContextVar(
    "basis_graph", default=None
)
def get_default_basis() -> Basis:
    """Get the current default basis.

    Returns the context-local basis if one has been set via
    :func:`using_basis`, otherwise returns SI.

    Returns
    -------
    Basis
        The active basis for the current context.
    """
    return _default_basis.get() or SI


def get_basis_graph() -> BasisGraph:
    """Get the current basis graph.

    Priority:

    1. Context-local graph (from :func:`using_basis_graph`).
    2. The active :class:`~ucon.system.UnitSystem`'s ``basis_graph``
       (from :func:`ucon.system.use`).
    3. Standard basis graph (bootstrap fallback, used only during
       ``import ucon`` before the active system is set).

    Returns
    -------
    BasisGraph
        The active basis graph for the current context.
    """
    ctx_graph = _basis_graph_context.get()
    if ctx_graph is not None:
        return ctx_graph

    # Active UnitSystem: _active is imported at top level from the
    # low-level ucon._active module (Layer 0), which has zero
    # intra-ucon imports. Payload is an ucon.system.ActiveContext
    # bundling system + formulas + kinds + strict.
    ctx = _active_system.get()
    if ctx is not None:
        return ctx.system.basis_graph

    # Bootstrap fallback: during `import ucon` the active system is not
    # yet set, but get_basis_graph() is called to construct the initial
    # UnitSystem. Build the standard graph on the fly.
    return _build_standard_basis_graph()


@contextmanager
def using_basis(basis: Basis):
    """Context manager for scoped basis override.

    Within the ``with`` block, :func:`get_default_basis` returns the
    provided basis instead of SI. Thread-safe via ContextVar.

    Parameters
    ----------
    basis : Basis
        The basis to use within this context.

    Yields
    ------
    Basis
        The provided basis.
    """
    token = _default_basis.set(basis)
    try:
        yield basis
    finally:
        _default_basis.reset(token)


@contextmanager
def using_basis_graph(graph: BasisGraph | None):
    """Context manager for scoped basis graph override.

    Within the ``with`` block, :func:`get_basis_graph` returns the
    provided graph. Thread-safe via ContextVar.

    Parameters
    ----------
    graph : BasisGraph or None
        The basis graph to use, or None to fall back to the module default.

    Yields
    ------
    BasisGraph or None
        The provided graph.
    """
    token = _basis_graph_context.set(graph)
    try:
        yield graph
    finally:
        _basis_graph_context.reset(token)


__all__ = [
    "BasisGraph",
    "get_basis_graph",
    "get_default_basis",
    "using_basis",
    "using_basis_graph",
]

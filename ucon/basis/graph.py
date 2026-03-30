# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
BasisGraph registry and context scoping for basis transforms.

Provides path-finding and transitive composition of basis transforms,
plus ContextVar-based scoping for default basis and basis graph overrides.
"""

from __future__ import annotations

from contextvars import ContextVar
from contextlib import contextmanager

from ucon.basis import Basis, Vector, NoTransformPath
from typing import Union
from ucon.basis.transforms import BasisTransform, ConstantBoundBasisTransform

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
        self._edges: dict[Basis, dict[Basis, _Transform]] = {}
        self._cache: dict[tuple[Basis, Basis], _Transform] = {}

    def add_transform(self, transform: _Transform) -> None:
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
        forward: BasisTransform,
        reverse: BasisTransform,
    ) -> None:
        """Register bidirectional transforms (e.g., projection + embedding).

        Args:
            forward: Transform A -> B.
            reverse: Transform B -> A.
        """
        self.add_transform(forward)
        self.add_transform(reverse)

    def get_transform(self, source: Basis, target: Basis) -> BasisTransform:
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
    ) -> list[BasisTransform] | None:
        """BFS to find shortest transform path."""
        from collections import deque

        if source not in self._edges:
            return None

        queue: deque[tuple[Basis, list[BasisTransform]]] = deque([(source, [])])
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

    def _compose_path(self, path: list[BasisTransform]) -> BasisTransform:
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

    def with_transform(self, transform: BasisTransform) -> "BasisGraph":
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


# -----------------------------------------------------------------------------
# Basis Context Scoping (v0.8.4)
# -----------------------------------------------------------------------------

_default_basis: ContextVar[Basis | None] = ContextVar("basis", default=None)
_basis_graph_context: ContextVar[BasisGraph | None] = ContextVar("basis_graph", default=None)
_default_basis_graph: BasisGraph | None = None


def _build_standard_basis_graph() -> BasisGraph:
    """Build standard basis graph with SI/CGS/CGS-ESU/natural transforms."""
    from ucon.basis.transforms import SI_TO_CGS, SI_TO_CGS_ESU, CGS_TO_SI, SI_TO_NATURAL
    graph = BasisGraph()
    graph.add_transform(SI_TO_CGS)
    graph.add_transform(SI_TO_CGS_ESU)
    graph.add_transform(CGS_TO_SI)
    graph.add_transform(SI_TO_NATURAL)
    return graph


def get_default_basis() -> Basis:
    """Get the current default basis.

    Returns the context-local basis if one has been set via
    :func:`using_basis`, otherwise returns SI.

    Returns
    -------
    Basis
        The active basis for the current context.
    """
    from ucon.basis.builtin import SI
    return _default_basis.get() or SI


def get_basis_graph() -> BasisGraph:
    """Get the current basis graph.

    Priority:

    1. Context-local graph (from :func:`using_basis_graph`)
    2. Module-level default graph (lazily built with standard transforms)

    Returns
    -------
    BasisGraph
        The active basis graph for the current context.
    """
    global _default_basis_graph
    ctx_graph = _basis_graph_context.get()
    if ctx_graph is not None:
        return ctx_graph
    if _default_basis_graph is None:
        _default_basis_graph = _build_standard_basis_graph()
    return _default_basis_graph


def set_default_basis_graph(graph: BasisGraph) -> None:
    """Replace the module-level default basis graph.

    Parameters
    ----------
    graph : BasisGraph
        The new default basis graph.
    """
    global _default_basis_graph
    _default_basis_graph = graph


def reset_default_basis_graph() -> None:
    """Reset to the standard basis graph on next access.

    The standard graph (with SI, CGS, CGS-ESU, and NATURAL transforms)
    is lazily rebuilt when :func:`get_basis_graph` is next called.
    """
    global _default_basis_graph
    _default_basis_graph = None


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

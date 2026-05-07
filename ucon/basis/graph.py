# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
BasisGraph registry for basis transforms.

Provides path-finding and transitive composition of basis transforms.
ContextVar-based scoping for default basis and basis graph overrides
lives in :mod:`ucon.basis._active`; the relevant accessors are
re-exported from this module for back-compat.
"""

from __future__ import annotations

from collections import deque
from typing import Union

from ucon.basis import Basis, NoTransformPath
from ucon.basis.transforms import (
    BasisTransform,
    ConstantBoundBasisTransform,
    SI_TO_CGS,
    SI_TO_CGS_ESU,
    SI_TO_CGS_EMU,
    CGS_TO_SI,
    CGS_ESU_TO_CGS_EMU,
    CGS_EMU_TO_CGS_ESU,
    SI_TO_NATURAL,
    SI_TO_PLANCK,
    SI_TO_ATOMIC,
    NATURAL_TO_PLANCK,
    PLANCK_TO_NATURAL,
    NATURAL_TO_ATOMIC,
    ATOMIC_TO_NATURAL,
    PLANCK_TO_ATOMIC,
    ATOMIC_TO_PLANCK,
)

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
# Standard Graph Builder
# -----------------------------------------------------------------------------


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
# Active-context accessors (canonical home: ucon.basis._active)
# -----------------------------------------------------------------------------
# Re-exported here for backward compatibility with callers that import these
# names directly from ``ucon.basis.graph`` (e.g., ucon.checking, ucon.graph,
# and the test suite). The canonical definitions live in
# :mod:`ucon.basis._active` so that ``ucon.basis.__init__`` (where ``Vector``
# is defined) can resolve :func:`get_basis_graph` at module load without
# importing :mod:`ucon.basis.graph` (which would create a cycle through
# ``Vector``).

from ucon.basis._active import (  # noqa: E402
    get_default_basis,
    get_basis_graph,
    set_default_basis_graph,
    reset_default_basis_graph,
    using_basis,
    using_basis_graph,
)

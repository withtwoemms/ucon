# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Kind lattice: storage, validation, and LCA computation.

A :class:`KindLattice` owns a set of :class:`~ucon.kinds.types.Kind`
nodes and the parent edges that connect them. Construction performs
load-time validation in a fixed order:

1. Name and alias collisions across the flat namespace.
2. Orphan parent references.
3. Cross-dimension parent edges.
4. Cycles in the parent chain.

Once constructed, the lattice exposes:

* :meth:`KindLattice.get` — resolve a name or alias to a :class:`Kind`.
* :meth:`KindLattice.lca` — lowest common ancestor with join policy.
* :meth:`KindLattice.is_descendant` — ancestry test.
* :meth:`KindLattice.register` — additive extension, revalidates.

There is no module-level default lattice in v1.9.x. In v2.0.0 the
lattice becomes a member of ``UnitSystem``; this module's API does not
change.
"""

from __future__ import annotations

from typing import Iterable, Iterator

from ucon.kinds.exceptions import (
    AliasCollision,
    CrossDimensionParent,
    JoinRefused,
    KindCycle,
    KindNotFound,
    NameCollision,
    OrphanParent,
)
from ucon.kinds.types import JoinPolicy, Kind


__all__ = ["KindLattice", "lca"]


class KindLattice:
    """A collection of :class:`Kind` nodes with parent edges.

    Parameters
    ----------
    kinds
        Initial kinds to load. Validated on construction.

    Notes
    -----
    The lattice owns canonical ``Kind`` instances and a flat name/alias
    index. Lookups by alias return the kind those aliases resolve to.
    """

    def __init__(self, kinds: Iterable[Kind] = ()) -> None:
        self._by_name: dict[str, Kind] = {}
        self._index: dict[str, Kind] = {}  # name OR alias -> Kind
        for kind in kinds:
            self._add(kind)
        self._validate_structure()

    # ---------- ingestion / indexing ----------

    def _add(self, kind: Kind) -> None:
        """Register a kind in the flat namespace. Raises on collision."""
        if kind.name in self._index:
            existing = self._index[kind.name]
            if existing.name == kind.name and existing is not kind:
                raise NameCollision(kind.name)
            raise AliasCollision(kind.name, existing.name)
        self._by_name[kind.name] = kind
        self._index[kind.name] = kind
        for alias in kind.aliases:
            if alias in self._index:
                raise AliasCollision(alias, self._index[alias].name)
            self._index[alias] = kind

    # ---------- validation ----------

    def _validate_structure(self) -> None:
        """Run orphan, cross-dimension, and cycle checks across all kinds."""
        # Orphan parents are detected when the parent reference does not
        # resolve to a registered kind. We compare parent identity by name
        # because callers may pass freshly-constructed Kind placeholders.
        for kind in self._by_name.values():
            if kind.parent is None:
                continue
            registered = self._by_name.get(kind.parent.name)
            if registered is None:
                raise OrphanParent(kind.name, kind.parent.name)
            if registered.dimension != kind.dimension:
                raise CrossDimensionParent(
                    kind_name=kind.name,
                    parent_name=registered.name,
                    kind_dimension=kind.dimension,
                    parent_dimension=registered.dimension,
                )

        # Cycle detection via DFS, using parent-by-name to tolerate
        # placeholder parents.
        visiting: set[str] = set()
        visited: set[str] = set()

        def walk(name: str, path: list[str]) -> None:
            if name in visited:
                return
            if name in visiting:
                raise KindCycle(path + [name])
            visiting.add(name)
            kind = self._by_name[name]
            if kind.parent is not None:
                walk(kind.parent.name, path + [name])
            visiting.discard(name)
            visited.add(name)

        for name in self._by_name:
            walk(name, [])

    # ---------- public lookups ----------

    def __contains__(self, name: str) -> bool:
        return name in self._index

    def __len__(self) -> int:
        return len(self._by_name)

    def __iter__(self) -> Iterator[Kind]:
        return iter(self._by_name.values())

    def get(self, name: str) -> Kind:
        """Resolve a primary name or alias to its canonical :class:`Kind`.

        Raises
        ------
        KindNotFound
            If no kind or alias matches ``name``.
        """
        kind = self._index.get(name)
        if kind is None:
            raise KindNotFound(name)
        return kind

    def names(self) -> tuple[str, ...]:
        """All registered primary names."""
        return tuple(self._by_name.keys())

    # ---------- structural queries ----------

    def ancestors(self, kind: Kind) -> list[Kind]:
        """Return the chain ``[kind, parent, grandparent, ..., root]``."""
        chain: list[Kind] = []
        current: Kind | None = self.get(kind.name)
        while current is not None:
            chain.append(current)
            current = (
                self._by_name[current.parent.name]
                if current.parent is not None
                else None
            )
        return chain

    def is_descendant(self, child: Kind, ancestor: Kind) -> bool:
        """True if ``child`` is ``ancestor`` or any descendant of it."""
        target = self.get(ancestor.name)
        for node in self.ancestors(child):
            if node == target:
                return True
        return False

    def lca(self, a: Kind, b: Kind) -> tuple[Kind, JoinPolicy]:
        """Lowest common ancestor of ``a`` and ``b``.

        Returns the ancestor kind and the ``join_policy`` declared at
        that ancestor. The caller decides whether to honor the policy;
        a convenience :meth:`join` consults it directly and raises
        :class:`JoinRefused` when blocked.

        Raises
        ------
        KindNotFound
            If ``a`` or ``b`` refer to unregistered kinds.
        ValueError
            If ``a`` and ``b`` belong to disjoint trees (no common
            ancestor). Distinct roots cannot be joined.
        """
        chain_a = self.ancestors(a)
        chain_b_set = {k.name for k in self.ancestors(b)}
        for node in chain_a:
            if node.name in chain_b_set:
                return node, node.join_policy
        raise ValueError(
            f"Kinds {a.name!r} and {b.name!r} have no common ancestor"
        )

    def join(self, a: Kind, b: Kind) -> Kind:
        """LCA-based join that honors ``join_policy``.

        Equivalent kinds short-circuit to ``a``. Otherwise consults
        :meth:`lca`; raises :class:`JoinRefused` when the ancestor's
        policy blocks the join.
        """
        if a == b:
            return self.get(a.name)
        ancestor, policy = self.lca(a, b)
        if policy is JoinPolicy.REFUSE:
            raise JoinRefused(left=a, right=b, parent=ancestor)
        return ancestor

    # ---------- additive extension ----------

    def register(self, kind: Kind) -> None:
        """Add a kind to an existing lattice.

        Re-runs the same load-time validation. Provided primarily as a
        building block for parsers; users typically construct a lattice
        in one shot.
        """
        self._add(kind)
        self._validate_structure()


def lca(a: Kind, b: Kind, *, lattice: KindLattice) -> tuple[Kind, JoinPolicy]:
    """Module-level convenience for :meth:`KindLattice.lca`.

    Takes an explicit lattice; there is no implicit global. In v2.0.0
    this is the same shape as the bound method on ``UnitSystem``.
    """
    return lattice.lca(a, b)

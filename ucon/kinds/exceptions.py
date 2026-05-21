# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Exceptions raised by the kind lattice.

All construction-time exceptions surface from
:class:`~ucon.kinds.lattice.KindLattice`. Operational refusals
(``JoinRefused``) surface from :meth:`KindLattice.lca` when two
distinct kinds share a parent with ``join_policy = REFUSE``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ucon.kinds.types import Kind


__all__ = [
    "KindError",
    "KindCycle",
    "OrphanParent",
    "CrossDimensionParent",
    "NameCollision",
    "AliasCollision",
    "JoinRefused",
    "KindNotFound",
]


class KindError(Exception):
    """Base class for kind lattice errors."""


class KindCycle(KindError):
    """A parent chain forms a cycle.

    The ``cycle`` attribute lists the kind names that participate in
    the cycle, in walk order.
    """

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = list(cycle)
        chain = " -> ".join(self.cycle)
        super().__init__(f"Cycle in kind parent chain: {chain}")


class OrphanParent(KindError):
    """A kind references a parent name that is not declared."""

    def __init__(self, kind_name: str, missing_parent: str) -> None:
        self.kind_name = kind_name
        self.missing_parent = missing_parent
        super().__init__(
            f"Kind {kind_name!r} references undeclared parent {missing_parent!r}"
        )


class CrossDimensionParent(KindError):
    """A kind's declared parent has a different dimension.

    The kind tree partitions by dimensional equivalence class. A
    parent edge across dimensions is structurally invalid.
    """

    def __init__(
        self,
        kind_name: str,
        parent_name: str,
        kind_dimension: "object",
        parent_dimension: "object",
    ) -> None:
        self.kind_name = kind_name
        self.parent_name = parent_name
        self.kind_dimension = kind_dimension
        self.parent_dimension = parent_dimension
        super().__init__(
            f"Kind {kind_name!r} (dimension={kind_dimension}) declares parent "
            f"{parent_name!r} with different dimension ({parent_dimension})"
        )


class NameCollision(KindError):
    """Two kinds share the same primary name."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Duplicate kind name: {name!r}")


class AliasCollision(KindError):
    """An alias collides with another name or alias.

    Aliases share the flat name/alias namespace with primary names.
    The ``conflict_with`` attribute names the existing entry.
    """

    def __init__(self, alias: str, conflict_with: str) -> None:
        self.alias = alias
        self.conflict_with = conflict_with
        super().__init__(
            f"Alias {alias!r} collides with existing entry {conflict_with!r}"
        )


class KindNotFound(KindError):
    """A kind lookup by name or alias failed."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Unknown kind: {name!r}")


class JoinRefused(KindError):
    """Two sibling kinds share a parent with join_policy = REFUSE.

    Raised by :meth:`KindLattice.lca` when the lowest common ancestor's
    ``join_policy`` forbids the join. The ``left``, ``right``, and
    ``parent`` attributes carry the involved kinds; the caller can use
    them to produce a domain-appropriate diagnostic.
    """

    def __init__(self, left: "Kind", right: "Kind", parent: "Kind") -> None:
        self.left = left
        self.right = right
        self.parent = parent
        super().__init__(
            f"Cannot join kinds {left.name!r} and {right.name!r}: parent "
            f"{parent.name!r} has join_policy=refuse"
        )

# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Kind data types.

A :class:`Kind` is a refinement within a dimensional equivalence class.
Two quantities sharing a dimension but carrying different kinds are not
interchangeable without an explicit formula. Kinds form rooted trees
(one tree per dimensional partition), interrogated via
:class:`~ucon.kinds.lattice.KindLattice`.

This module defines storage and tagging only. Algorithms (LCA,
validation, join policy enforcement) live in
:mod:`ucon.kinds.lattice`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ucon.dimension import Dimension


__all__ = ["JoinPolicy", "Kind"]


class JoinPolicy(Enum):
    """Policy applied when joining sibling kinds at a parent node.

    ``LCA`` lifts the result to the lowest common ancestor.
    ``REFUSE`` blocks the join; the operation must be expressed via a
    named formula instead.
    """

    LCA = "lca"
    REFUSE = "refuse"


@dataclass(frozen=True)
class Kind:
    """A refinement within a dimensional equivalence class.

    Parameters
    ----------
    name
        Primary identifier. Must be unique across the lattice's flat
        name/alias namespace.
    dimension
        The dimension this kind refines. All ancestors in the kind tree
        must share this dimension.
    parent
        The parent kind, or ``None`` for a root.
    join_policy
        Policy applied to additions of distinct descendants of this
        kind. Defaults to :attr:`JoinPolicy.LCA`.
    aliases
        Legacy or alternate names that resolve to this kind. Share the
        flat name/alias namespace with primary names; collisions refuse
        at load time.

    Notes
    -----
    ``Kind`` is intentionally storage-only. All structural reasoning
    (parent walks, LCA, validation) lives on
    :class:`~ucon.kinds.lattice.KindLattice`.

    Equality and hashing key off ``name`` only. Two ``Kind`` instances
    with the same name are treated as the same kind, regardless of
    parent or join policy. This permits constructing a kind reference
    by name during parse before the parent is resolvable.
    """

    name: str
    dimension: Dimension
    parent: Optional["Kind"] = None
    join_policy: JoinPolicy = JoinPolicy.LCA
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Kind):
            return NotImplemented
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(("Kind", self.name))

    def __repr__(self) -> str:
        parent_part = f", parent={self.parent.name!r}" if self.parent else ""
        return f"Kind({self.name!r}{parent_part})"

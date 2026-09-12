# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
The aspect data model: one node type, trees keyed by their roots.

An :class:`Aspect` is the peer of :class:`~ucon.kinds.types.Kind` —
same fields, same engine, same kind of tree. A quantity's aspects are
adjectives: they say something further about it that matters for
combination (which weighting standard, which sample basis, which
coverage factor) without changing what the quantity *is*.

The **root of a tree is the family** and its ⊤: a `Number` carrying a
root aspect is *some member of this family, unspecified*, distinct from
carrying nothing. There is no synthetic top and no separate "facet"
type — the root plays both parts by construction.

Roots carry the family's rules; declaring :attr:`Aspect.applies_to` or
:attr:`Aspect.multiplication_policy` on a non-root is a load-time
error (enforced where trees are assembled, not here — this module is a
Layer-0-style leaf holding data types only).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Optional

from ucon.kinds.types import JoinPolicy


__all__ = [
    "Aspect",
    "MultPolicy",
]


class MultPolicy(Enum):
    """How a family's aspects behave under multiplicative operations.

    CARRY
        Aspects propagate onto the product/quotient whenever either
        operand carries them — provenance survives multiplication, so
        refusals outlive kind degradation. The default, and the reason
        the stratum is load-bearing.
    """

    CARRY = "carry"


@dataclass(frozen=True)
class Aspect:
    """One node in an aspect tree.

    Attributes
    ----------
    name : str
        Node name. Package-declared aspects are fully qualified
        (``"radsafe:icrp103"``); root builtins are unprefixed.
    parent : Aspect | None
        Parent node; ``None`` marks a family root.
    join_policy : JoinPolicy
        Policy consulted when two positions in this family meet at this
        node as their lowest common ancestor. Defaults to ``REFUSE`` —
        strict matching is the zero-configuration behavior; LCA
        degradation is opt-in per node.
    applies_to : frozenset[str]
        Root-only. Kind names this family may attach to, or ``{"*"}``
        for kind-independent families (coverage factor, calibration
        status). Checked at attachment, never during resolution.
    multiplication_policy : MultPolicy
        Root-only. Behavior under ``×``/``÷``; see :class:`MultPolicy`.
    """

    name: str
    parent: Optional["Aspect"] = None
    join_policy: JoinPolicy = JoinPolicy.REFUSE
    applies_to: FrozenSet[str] = field(default_factory=frozenset)
    multiplication_policy: MultPolicy = MultPolicy.CARRY

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Aspect name must be non-empty")
        if not isinstance(self.applies_to, frozenset):
            object.__setattr__(self, "applies_to", frozenset(self.applies_to))

    @property
    def is_root(self) -> bool:
        """True when this node is a family root (and family ⊤)."""
        return self.parent is None

    @property
    def root(self) -> "Aspect":
        """The family root this node belongs to."""
        node: Aspect = self
        while node.parent is not None:
            node = node.parent
        return node

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        role = "root" if self.is_root else f"under {self.parent.name!r}"
        return f"<Aspect {self.name!r} ({role})>"

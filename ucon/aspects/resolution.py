# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Family-wise aspect resolution for Number arithmetic.

Resolution never compares across families. Both operands' aspects are
grouped by family root, and each family resolves independently:

- **Equal** positions carry through unchanged.
- **Differing** positions join at their LCA, honoring the ancestor's
  ``join_policy`` (``refuse`` raises :class:`AspectRefused`; ``lca``
  carries the ancestor). The join runs on the vetted forest engine —
  the same code paths exercised by :class:`AspectForest` directly.
- **Partial** presence (one operand carries the family, the other is
  silent) is where addition and multiplication diverge. Addition
  consults the ambient strict bit: strict refuses (silence is not
  agreement), permissive inherits with a warning. Multiplication
  consults the family root's ``multiplication_policy``: ``carry``
  threads the present positions onto the product — a factor's
  provenance survives being multiplied by something unqualified
  (ADR 008: the carry rule).

There is no ``drop``: no resolution path silently discards a position.
These functions read nothing but their operands and the strict bit the
caller passes — resolution is context-free beyond that one ambient
flag, mirroring the kind stratum.
"""

from __future__ import annotations

import warnings
from typing import AbstractSet, Dict, FrozenSet, Set

from ucon.aspects.exceptions import AspectRefused
from ucon.aspects.forest import AspectForest
from ucon.aspects.types import Aspect, MultPolicy


__all__ = ["resolve_add_aspects", "resolve_mul_aspects"]


def _by_family(aspects: AbstractSet[Aspect]) -> Dict[str, Set[Aspect]]:
    grouped: Dict[str, Set[Aspect]] = {}
    for aspect in aspects:
        grouped.setdefault(aspect.root.name, set()).add(aspect)
    return grouped


def _join_family(members: Set[Aspect]) -> Aspect:
    """Fold all positions within one family down to a single node.

    Runs on the forest engine so LCA/policy semantics are the vetted
    ones. Within-family joins are associative (upward closure), so a
    name-sorted fold is deterministic without being order-privileged.
    """
    forest = AspectForest(members)
    ordered = sorted(members, key=lambda a: a.name)
    acc = ordered[0]
    for nxt in ordered[1:]:
        acc = forest.join(acc, nxt)
    return acc


def resolve_add_aspects(
    left: AbstractSet[Aspect],
    right: AbstractSet[Aspect],
    *,
    strict: bool,
    warn: bool = True,
    op: str = "Adding",
) -> FrozenSet[Aspect]:
    """Resolve result aspects for addition or subtraction.

    Family-wise: equal carries, differing joins at LCA under the
    ancestor's policy, partial refuses under ``strict`` and inherits
    (with a warning, unless ``warn`` is false) otherwise.
    """
    left_families = _by_family(left)
    right_families = _by_family(right)
    resolved: Set[Aspect] = set()
    for family_name in sorted(set(left_families) | set(right_families)):
        l_members = left_families.get(family_name)
        r_members = right_families.get(family_name)
        if l_members and r_members:
            if l_members == r_members:
                resolved |= l_members
            else:
                resolved.add(_join_family(l_members | r_members))
            continue
        # partial: one operand carries the family, the other is silent
        present = l_members or r_members
        position = (_join_family(present) if len(present) > 1
                    else next(iter(present)))
        family = position.root
        if strict:
            raise AspectRefused(
                family=family,
                left=position if l_members else None,
                right=position if r_members else None,
                policy=family.join_policy,
            )
        if warn:
            warnings.warn(
                f"{op} aspected (#{position.name}) and aspect-silent "
                f"Numbers; #{position.name} inherited",
                stacklevel=4,
            )
        resolved |= present
    return frozenset(resolved)


def resolve_mul_aspects(
    left: AbstractSet[Aspect],
    right: AbstractSet[Aspect],
    *,
    op: str = "Multiplying",
) -> FrozenSet[Aspect]:
    """Resolve result aspects for multiplication or division.

    Family-wise: equal carries, differing joins at LCA under the
    ancestor's policy, partial follows the family root's
    ``multiplication_policy`` (``carry`` threads the present positions
    onto the product). ``op`` names the operation in any refusal
    message; the rules themselves are symmetric.
    """
    del op  # symmetric rules; parameter reserved for future messaging
    left_families = _by_family(left)
    right_families = _by_family(right)
    resolved: Set[Aspect] = set()
    for family_name in sorted(set(left_families) | set(right_families)):
        l_members = left_families.get(family_name)
        r_members = right_families.get(family_name)
        if l_members and r_members:
            if l_members == r_members:
                resolved |= l_members
            else:
                resolved.add(_join_family(l_members | r_members))
            continue
        present = l_members or r_members
        family = next(iter(present)).root
        if family.multiplication_policy is MultPolicy.CARRY:
            resolved |= present
    return frozenset(resolved)

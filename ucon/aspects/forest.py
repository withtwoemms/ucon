# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
The aspect forest: family-grouped trees over the shared lattice engine.

Aspect trees run on the *kind-lattice engine* — each family's nodes are
mirrored into :class:`~ucon.kinds.types.Kind` objects (over the ``none``
dimension) and loaded into a private per-family
:class:`~ucon.kinds.lattice.KindLattice`. The engine is untouched
byte-for-byte, which is what preserves the vetted isomorphism: every
join/LCA behavior demonstrated for kinds transfers to aspects because it
*is* the same code.

Two boundary rules keep the layers legible:

- **Rewrap:** engine errors are ``KindError`` flavors; no Kind-named
  exception may leak from an aspect declaration. Everything structural
  is caught here and re-raised as :class:`AspectError` (with the engine
  error chained as ``__cause__``); operational refusals become
  :class:`AspectRefused`.
- **Root = family = ⊤:** the family is its tree's root by construction
  — no synthetic top. Two disjoint subtrees within one family meet at
  the root, whose default policy is ``refuse``.
"""

from __future__ import annotations

from typing import Dict, Iterable, Iterator, List, Tuple

from ucon.aspects.exceptions import AspectError, AspectRefused
from ucon.aspects.types import Aspect
from ucon.dimension import Dimension
from ucon.kinds.exceptions import KindError
from ucon.kinds.lattice import KindLattice
from ucon.kinds.types import JoinPolicy, Kind


__all__ = ["AspectForest"]


# The engine requires a dimension; aspects have none. Every mirrored
# node shares this, so the engine's cross-dimension guard is inert.
_MIRROR_DIMENSION = Dimension.none


class AspectForest:
    """A collection of aspect trees, one lattice engine per family.

    Construction closes over parents (passing leaves is enough),
    validates root-only fields, and loads each family into its own
    mirrored :class:`KindLattice`. All structural failures surface as
    :class:`AspectError`.
    """

    def __init__(self, aspects: Iterable[Aspect] = ()) -> None:
        self._by_name: Dict[str, Aspect] = {}
        # collect the parent-closure, dedup by name with identity check
        for aspect in aspects:
            node: Aspect | None = aspect
            while node is not None:
                existing = self._by_name.get(node.name)
                if existing is None:
                    self._by_name[node.name] = node
                elif existing is not node:
                    raise AspectError(
                        f"Duplicate aspect name {node.name!r}: two distinct "
                        f"nodes share it"
                    )
                node = node.parent

        # root-only field validation
        for node in self._by_name.values():
            if not node.is_root and node.applies_to:
                raise AspectError(
                    f"Aspect {node.name!r} declares applies_to but is not a "
                    f"family root; the root ({node.root.name!r}) carries the "
                    f"family's rules"
                )

        # group by family and mirror each family into its own engine
        self._families: Dict[str, List[Aspect]] = {}
        for node in self._by_name.values():
            self._families.setdefault(node.root.name, []).append(node)

        self._engines: Dict[str, KindLattice] = {}
        for root_name, members in self._families.items():
            mirrored: Dict[str, Kind] = {}

            def mirror(a: Aspect) -> Kind:
                if a.name not in mirrored:
                    mirrored[a.name] = Kind(
                        a.name,
                        dimension=_MIRROR_DIMENSION,
                        parent=mirror(a.parent) if a.parent is not None else None,
                        join_policy=a.join_policy,
                    )
                return mirrored[a.name]

            try:
                for member in members:
                    mirror(member)
                self._engines[root_name] = KindLattice(mirrored.values())
            except KindError as exc:
                raise AspectError(
                    f"Invalid aspect family {root_name!r}: {exc}"
                ) from exc

    # ---------- lookups ----------

    def __contains__(self, name: str) -> bool:
        return name in self._by_name

    def __len__(self) -> int:
        return len(self._by_name)

    def __iter__(self) -> Iterator[Aspect]:
        return iter(self._by_name.values())

    def get(self, name: str) -> Aspect:
        """Resolve a name to its aspect; :class:`AspectError` if absent."""
        aspect = self._by_name.get(name)
        if aspect is None:
            raise AspectError(f"Unknown aspect: {name!r}")
        return aspect

    def families(self) -> Tuple[Aspect, ...]:
        """The family roots, one per tree."""
        return tuple(self.get(name) for name in self._families)

    def family_of(self, aspect: Aspect) -> Aspect:
        """The family root governing *aspect* (registered instance)."""
        return self.get(aspect.root.name)

    # ---------- family-wise operations ----------

    def lca(self, a: Aspect, b: Aspect) -> Tuple[Aspect, JoinPolicy]:
        """Lowest common ancestor within one family, with its policy.

        Operands from different families are a caller error — resolution
        groups by family before consulting the engine — and raise
        :class:`AspectError`.
        """
        family_a, family_b = a.root.name, b.root.name
        if family_a != family_b:
            raise AspectError(
                f"Aspects {a.name!r} and {b.name!r} belong to different "
                f"families ({family_a!r} vs {family_b!r}); family-wise "
                f"resolution never compares across families"
            )
        engine = self._engines.get(family_a)
        if engine is None:
            raise AspectError(f"Unknown aspect family: {family_a!r}")
        try:
            node, policy = engine.lca(engine.get(a.name), engine.get(b.name))
        except KindError as exc:
            raise AspectError(
                f"Aspect resolution failed in family {family_a!r}: {exc}"
            ) from exc
        return self.get(node.name), policy

    def join(self, a: Aspect, b: Aspect) -> Aspect:
        """LCA-based join honoring the ancestor's policy.

        Equal aspects short-circuit. A ``refuse`` ancestor raises
        :class:`AspectRefused` carrying the family, both operands, and
        the policy consulted.
        """
        if a.name == b.name:
            return self.get(a.name)
        ancestor, policy = self.lca(a, b)
        if policy is JoinPolicy.REFUSE:
            raise AspectRefused(
                family=self.family_of(a),
                left=self.get(a.name),
                right=self.get(b.name),
                policy=policy,
            )
        return ancestor

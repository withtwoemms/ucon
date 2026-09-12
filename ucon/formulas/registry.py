# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Formula registry.

The :class:`FormulaRegistry` indexes :class:`~ucon.formulas.types.KindFormula`
instances by name and by input-kind tuple, with tiered resolution via
:meth:`~FormulaRegistry.resolve`:

1. **EXACT** — direct input-kind tuple match.
2. **COMMUTATIVE** — canonical sorted-key match (any arity).
3. **GENERALIZED** — ancestor-walk via a ``KindLattice`` at increasing
   L1 distance (formulas with ``generalizes=True`` only).
4. **DIMENSIONAL** — dimension-tuple match ignoring kind identity
   (opt-in via ``dimension_fallback=True``).

There is no module-level default registry in v1.9.x. In v2.0.0 the
registry becomes a member of ``UnitSystem``; this module's API does
not change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Iterator, Mapping, Tuple

if TYPE_CHECKING:
    from ucon.kinds import KindLattice

from ucon.formulas.exceptions import AmbiguousFormula, DuplicateFormula, FormulaNotFound
from ucon.formulas.types import KindFormula, LookupResult, MatchKind
from ucon.kinds import Kind, KindNotFound


__all__ = ["FormulaRegistry"]


def _partitions(
    total: int,
    n: int,
    caps: list[int],
) -> Iterator[tuple[int, ...]]:
    """Yield all tuples of length *n* that sum to *total*.

    Each position ``i`` is bounded by ``0 <= t[i] <= caps[i]``.
    This is a bounded integer-composition problem; the search space is
    small for realistic lattices (depth <= 4, arity <= 5).
    """
    if n == 1:
        if 0 <= total <= caps[0]:
            yield (total,)
        return
    for value in range(min(total, caps[0]), -1, -1):
        for rest in _partitions(total - value, n - 1, caps[1:]):
            yield (value,) + rest


class FormulaRegistry:
    """Indexes formulas by name and by input-kind tuple.

    Parameters
    ----------
    formulas
        Initial formulas to register.

    Notes
    -----
    Equality semantics on :class:`~ucon.formulas.types.KindFormula`
    key off name. Registering two formulas with the same name raises
    :class:`~ucon.formulas.exceptions.DuplicateFormula`.

    Input-kind indexing keys by ordered tuple of input kinds. When a
    formula declares ``commutative=True``, the registry indexes both
    the original ordering and a canonical sorted key — so
    ``voltage × current`` and ``current × voltage`` both resolve to
    the same formula at any arity via :meth:`resolve`.
    """

    def __init__(self, formulas: Iterable[KindFormula] = ()) -> None:
        self._by_name: dict[str, KindFormula] = {}
        self._by_inputs: dict[tuple[Kind, ...], KindFormula] = {}
        self._by_inputs_canonical: dict[tuple[Kind, ...], KindFormula] = {}
        self._by_dimensions: dict[tuple[object, ...], KindFormula] = {}
        self._by_dimensions_canonical: dict[tuple[object, ...], KindFormula] = {}
        for f in formulas:
            self.register(f)

    # ---------- ingestion ----------

    def register(self, formula: KindFormula) -> None:
        """Add a formula to the registry. Refuses duplicate names."""
        if formula.name in self._by_name:
            raise DuplicateFormula(formula.name)
        self._by_name[formula.name] = formula

        key = formula.input_kind_tuple()
        # First-writer wins on input-tuple collisions; the name index
        # is the primary key.
        self._by_inputs.setdefault(key, formula)
        if formula.commutative and len(key) == 2 and key[0] != key[1]:
            self._by_inputs.setdefault((key[1], key[0]), formula)

        # Canonical sorted key for commutative n-ary lookup.
        if formula.commutative:
            canonical = tuple(sorted(key, key=lambda k: k.name))
            self._by_inputs_canonical.setdefault(canonical, formula)

        # Dimension-tuple indexes for dimensional fallback.
        dim_key = tuple(k.dimension for k in key)
        self._by_dimensions.setdefault(dim_key, formula)
        if formula.commutative:
            dim_canonical = tuple(sorted(dim_key, key=str))
            self._by_dimensions_canonical.setdefault(dim_canonical, formula)

    # ---------- public lookups ----------

    def __contains__(self, name: str) -> bool:
        return name in self._by_name

    def __len__(self) -> int:
        return len(self._by_name)

    def __iter__(self) -> Iterator[KindFormula]:
        return iter(self._by_name.values())

    def names(self) -> tuple[str, ...]:
        """All registered formula names."""
        return tuple(self._by_name.keys())

    def get(self, name: str) -> KindFormula:
        """Resolve a formula by name.

        Raises
        ------
        FormulaNotFound
            If no formula matches.
        """
        formula = self._by_name.get(name)
        if formula is None:
            raise FormulaNotFound(name)
        return formula

    def lookup(self, *input_kinds: Kind) -> KindFormula:
        """Resolve a formula by exact input-kind tuple.

        Performs EXACT tier lookup only (including the arity-2
        commutative mirror in ``_by_inputs``). Callers wanting the
        richer tiered resolution should use :meth:`resolve`.

        Raises
        ------
        FormulaNotFound
            If no formula matches the supplied input kinds.
        """
        key = tuple(input_kinds)
        formula = self._by_inputs.get(key)
        if formula is None:
            raise FormulaNotFound(key)
        return formula

    def resolve(
        self,
        *input_kinds: Kind,
        lattice: "KindLattice | None" = None,
        dimension_fallback: bool = False,
    ) -> LookupResult:
        """Resolve a formula through successive match tiers.

        Tiers are checked in strict priority order; the first to
        produce a match wins:

        1. **EXACT** — exact input-kind tuple match.
        2. **COMMUTATIVE** — canonical sorted-key match (any arity).
        3. **GENERALIZED** — ancestor-walk via ``lattice`` at
           increasing L1 distance (requires ``lattice``; only formulas
           with ``generalizes=True``).
        4. **DIMENSIONAL** — dimension-tuple match ignoring kind
           identity (requires ``dimension_fallback=True``).

        Parameters
        ----------
        *input_kinds
            Kinds to match, in caller-supplied order.
        lattice
            When provided, enables GENERALIZED matching via ancestor
            walk.
        dimension_fallback
            When True, enables DIMENSIONAL matching as a last resort.

        Returns
        -------
        LookupResult
            The matched formula and the tier that resolved it.

        Raises
        ------
        FormulaNotFound
            No formula matched at any enabled tier.
        AmbiguousFormula
            Multiple formulas matched at the same GENERALIZED distance.
        """
        key = tuple(input_kinds)

        # --- Tier 1: EXACT ---
        formula = self._by_inputs.get(key)
        if formula is not None:
            return LookupResult(formula, MatchKind.EXACT)

        # --- Tier 2: COMMUTATIVE ---
        canonical = tuple(sorted(key, key=lambda k: k.name))
        formula = self._by_inputs_canonical.get(canonical)
        if formula is not None:
            return LookupResult(formula, MatchKind.COMMUTATIVE)

        # --- Tier 3: GENERALIZED ---
        if lattice is not None:
            result = self._generalized_search(key, lattice)
            if result is not None:
                return result

        # --- Tier 4: DIMENSIONAL ---
        if dimension_fallback:
            dim_key = tuple(k.dimension for k in key)
            formula = self._by_dimensions.get(dim_key)
            if formula is not None:
                return LookupResult(formula, MatchKind.DIMENSIONAL)
            dim_canonical = tuple(sorted(dim_key, key=str))
            formula = self._by_dimensions_canonical.get(dim_canonical)
            if formula is not None:
                return LookupResult(formula, MatchKind.DIMENSIONAL)

        raise FormulaNotFound(key)

    # ---------- private helpers ----------

    def _try_match(self, candidate: tuple[Kind, ...]) -> KindFormula | None:
        """Check a candidate tuple against exact and canonical indexes."""
        formula = self._by_inputs.get(candidate)
        if formula is not None:
            return formula
        canonical = tuple(sorted(candidate, key=lambda k: k.name))
        return self._by_inputs_canonical.get(canonical)

    def _generalized_search(
        self,
        input_kinds: tuple[Kind, ...],
        lattice: KindLattice,
        max_distance: int = 10,
    ) -> LookupResult | None:
        """Ancestor-walk at increasing L1 distance.

        At each distance d, enumerate all ways to distribute d
        parent-climbs across n input positions. For each candidate
        tuple, check indexes. Only accept formulas with
        ``generalizes=True``. Exactly one → return. More than one at
        the same distance → :class:`AmbiguousFormula`.
        """
        n = len(input_kinds)
        # Pre-compute ancestor chains (excluding position 0 = the kind itself).
        # Kinds not registered in the lattice have no ancestors to climb.
        chains: list[list[Kind]] = []
        for k in input_kinds:
            try:
                chains.append(lattice.ancestors(k)[1:])
            except KindNotFound:
                chains.append([])
        depth_cap = min(sum(len(c) for c in chains), max_distance)

        for distance in range(1, depth_cap + 1):
            hits: dict[str, KindFormula] = {}
            for dist in _partitions(distance, n, [len(c) for c in chains]):
                candidate = tuple(
                    chains[i][d - 1] if d > 0 else input_kinds[i]
                    for i, d in enumerate(dist)
                )
                formula = self._try_match(candidate)
                if formula is not None and formula.generalizes:
                    hits[formula.name] = formula
            if len(hits) == 1:
                return LookupResult(
                    next(iter(hits.values())),
                    MatchKind.GENERALIZED,
                    distance=distance,
                )
            if len(hits) > 1:
                raise AmbiguousFormula(tuple(hits.values()), distance)
        return None

    def apply(
        self,
        inputs: Mapping[str, Kind],
        *,
        lattice: KindLattice | None = None,
        dimension_fallback: bool = False,
    ) -> Tuple[KindFormula, Kind, MatchKind]:
        """Resolve a formula for the supplied input kinds.

        The caller supplies one kind per binding; resolution consults
        the declared input kinds (in the order of ``inputs``) and
        returns the formula, its output kind, and the match tier.

        Parameters
        ----------
        inputs
            Mapping from binding name to the operand's kind.
        lattice
            Passed through to :meth:`resolve` for generalized matching.
        dimension_fallback
            Passed through to :meth:`resolve`.

        Returns
        -------
        tuple
            ``(formula, output_kind, match_kind)``.

        Raises
        ------
        FormulaNotFound
            Propagated from :meth:`resolve` when no formula matches the
            supplied input kinds at any enabled tier.
        AmbiguousFormula
            Propagated from :meth:`resolve`.
        """
        kinds = tuple(inputs.values())
        result = self.resolve(
            *kinds, lattice=lattice, dimension_fallback=dimension_fallback
        )
        return result.formula, result.formula.output_kind, result.match_kind

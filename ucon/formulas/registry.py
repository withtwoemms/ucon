# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Formula registry.

The :class:`FormulaRegistry` indexes :class:`~ucon.formulas.types.KindFormula`
instances by name and by input-kind tuple. v1.9.0 supports exact-match
lookup only; subkind-climb lookup (``generalizes``) and same-level
ambiguity handling land in v1.9.2.

There is no module-level default registry in v1.9.x. In v2.0.0 the
registry becomes a member of ``UnitSystem``; this module's API does
not change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, FrozenSet, Iterable, Iterator, Mapping, Tuple

if TYPE_CHECKING:
    from ucon.kinds import KindLattice

from ucon.aspects.types import AspectSet
from ucon.formulas.exceptions import DuplicateFormula, FormulaNotFound
from ucon.formulas.types import KindFormula, LookupResult, MatchKind
from ucon.kinds import Kind


__all__ = ["FormulaRegistry"]


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
    formula declares ``commutative=True`` and has exactly two inputs,
    the registry also indexes the reversed ordering — so
    ``voltage × current`` and ``current × voltage`` both resolve to
    the same formula. Higher-arity commutativity (full input
    permutations) lands with v1.9.2's lookup work.
    """

    def __init__(self, formulas: Iterable[KindFormula] = ()) -> None:
        self._by_name: dict[str, KindFormula] = {}
        self._by_inputs: dict[tuple[Kind, ...], KindFormula] = {}
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
        # is the primary key and disambiguation policy across formulas
        # sharing an input tuple lands with v1.9.2 lookup semantics.
        self._by_inputs.setdefault(key, formula)
        if formula.commutative and len(key) == 2 and key[0] != key[1]:
            self._by_inputs.setdefault((key[1], key[0]), formula)

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

        raise FormulaNotFound(key)

    def apply(
        self,
        inputs: Mapping[str, Tuple[Kind, FrozenSet[str]]],
    ) -> Tuple[KindFormula, Kind, FrozenSet[str]]:
        """Resolve a formula and project operand aspects in one step.

        Combines :meth:`lookup` with
        :meth:`~ucon.formulas.types.KindFormula.project_aspects`. The
        caller supplies one ``(kind, aspect_set)`` pair per binding;
        the registry resolves the formula by the kinds (in iteration
        order of ``inputs``) and returns the formula together with the
        output kind and the projected output aspect set.

        Parameters
        ----------
        inputs
            Mapping from binding name to a ``(kind, aspect_set)`` pair.
            Iteration order determines the positional order passed to
            :meth:`lookup`.

        Returns
        -------
        tuple
            ``(formula, output_kind, output_aspects)`` where
            ``output_kind`` is :attr:`KindFormula.output_kind` and
            ``output_aspects`` is the projection of the input aspect
            sets through :attr:`KindFormula.aspect_rules`.

        Raises
        ------
        FormulaNotFound
            Propagated from :meth:`lookup` when no formula matches the
            supplied input kinds (in iteration order).

        Notes
        -----
        ``apply`` is additive. :meth:`lookup` remains the lower-level
        surface; callers that do not carry aspects continue to use it.

        Binding names in ``inputs`` are not validated against the
        resolved formula's :attr:`~KindFormula.input_kinds`. Mismatches
        manifest in the projection step: rules keyed on the formula's
        bindings consult ``inputs`` by the same names; aspects supplied
        under unrelated names contribute nothing to the projection.
        """
        kinds: Tuple[Kind, ...] = tuple(kind for kind, _ in inputs.values())
        formula = self.lookup(*kinds)
        aspects: dict[str, FrozenSet[str]] = {
            name: aspect_set for name, (_, aspect_set) in inputs.items()
        }
        out_aspects = formula.project_aspects(aspects)
        return formula, formula.output_kind, out_aspects

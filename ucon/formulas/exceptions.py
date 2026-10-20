# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Exceptions raised by the formula registry.
"""

from __future__ import annotations


__all__ = [
    "AmbiguousFormula",
    "CollidingFormula",
    "DuplicateFormula",
    "FormulaError",
    "FormulaNotFound",
]


class FormulaError(Exception):
    """Base class for formula registry errors."""


class FormulaNotFound(FormulaError):
    """No formula matches the supplied lookup key.

    ``name_or_kinds`` carries the lookup argument for the diagnostic.
    """

    def __init__(self, name_or_kinds: object) -> None:
        self.name_or_kinds = name_or_kinds
        super().__init__(f"No formula found for {name_or_kinds!r}")


class DuplicateFormula(FormulaError):
    """A formula with the given name is already registered.

    The registry's primary key is the formula name. Re-registering a
    formula with the same name is refused.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Duplicate formula: {name!r}")


class AmbiguousFormula(FormulaError):
    """Two or more formulas match at the same specificity level.

    Raised during ancestor-walk when multiple formulas match at the
    same L1 distance. Callers must disambiguate by using more specific
    kinds or by naming the formula explicitly.
    """

    def __init__(
        self,
        candidates: tuple["KindFormula", ...],
        distance: int,
    ) -> None:
        self.candidates = candidates
        self.distance = distance
        names = ", ".join(f.name for f in candidates)
        super().__init__(
            f"Ambiguous: {len(candidates)} formulas match at distance "
            f"{distance}: {names}"
        )


class CollidingFormula(FormulaError):
    """Two formulas claim one input signature with differing output kinds.

    Every kind-identity resolution tier reads indexes keyed by input
    signature and returns at most one formula, so a second claim on an
    already-claimed signature would make the resolved output kind a
    function of registration order.
    :meth:`~ucon.formulas.registry.FormulaRegistry.register` refuses it
    instead.

    Formulas that claim one signature but *agree* on ``output_kind`` are
    not a collision: the kind the stratum reads is the same whichever
    one resolves, so the first registered wins and registration
    succeeds.

    ``signature`` carries the contested input-kind tuple; ``existing``
    and ``incoming`` carry the two formulas.
    """

    def __init__(
        self,
        existing: "KindFormula",
        incoming: "KindFormula",
        signature: tuple["Kind", ...],
    ) -> None:
        self.existing = existing
        self.incoming = incoming
        self.signature = signature
        rendered = " × ".join(kind.name for kind in signature)
        super().__init__(
            f"Formula {incoming.name!r} claims input signature "
            f"({rendered}), already claimed by {existing.name!r}, with a "
            f"different output kind ({incoming.output_kind.name!r} vs "
            f"{existing.output_kind.name!r})"
        )

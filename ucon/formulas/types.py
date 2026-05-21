# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Formula data types.

A :class:`KindFormula` declares a relationship between kinds. It is
the **edge** in the kind graph. Formulas serve three roles:

1. Documentation of the physical relationship.
2. Kind assignment for multiplication / division (the lattice handles
   addition).
3. Named computation surface, invoked outside operator overloads.

:class:`AspectRule` shipped from this module in v1.9.0. It now lives
in :mod:`ucon.aspects.types` (aspects are orthogonal to kinds and
deserve their own subpackage); the symbol is re-exported here so that
existing import paths — ``from ucon.formulas import AspectRule`` and
``from ucon.formulas.types import AspectRule`` — keep working.

``generalizes`` and ``commutative`` are stored but inert until v1.9.2
wires them into formula lookup.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ucon.aspects.types import AspectRule
from ucon.kinds import Kind


__all__ = ["AspectRule", "KindFormula"]


@dataclass(frozen=True)
class KindFormula:
    """A declared relationship between kinds.

    Parameters
    ----------
    name
        Unique formula identifier. Used as the lookup key for named
        computation.
    expression
        Free-text expression for documentation and rendering, e.g.
        ``"D * w_R"``. ucon does not evaluate expressions.
    input_kinds
        Operands of the formula keyed by binding name. The binding
        names appear in ``expression``.
    output_kind
        The kind of the result.
    aspect_rules
        Per-facet behavior under multiplication. Opaque in v1.9.0;
        semantics activate in v1.9.1.
    generalizes
        Opt-in: when ``True``, formula lookup may match this formula
        against subkinds of the declared inputs. Default ``False``.
        Inert in v1.9.0; lookup semantics activate in v1.9.2.
    commutative
        Operand order policy under multiplication lookup. Default
        ``True`` (matching ``×``). Set to ``False`` for division and
        other order-sensitive formulas. Inert in v1.9.0.
    notes
        Free-text documentation. Useful for capturing context that the
        formula declaration alone does not convey (e.g., "w_R depends
        on radiation type per ICRP 103; caller selects appropriate
        value").

    Notes
    -----
    Equality and hashing key off ``name`` only, matching :class:`Kind`.
    """

    name: str
    expression: str
    input_kinds: dict[str, Kind]
    output_kind: Kind
    aspect_rules: dict[str, AspectRule] = field(default_factory=dict)
    generalizes: bool = False
    commutative: bool = True
    notes: str = ""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, KindFormula):
            return NotImplemented
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(("KindFormula", self.name))

    def __repr__(self) -> str:
        return f"KindFormula({self.name!r})"

    def input_kind_tuple(self) -> tuple[Kind, ...]:
        """Input kinds in the binding order declared on the formula.

        The order is the iteration order of :attr:`input_kinds`
        (insertion order, per dict semantics). Used by
        :class:`~ucon.formulas.registry.FormulaRegistry` to key
        positional lookups.
        """
        return tuple(self.input_kinds.values())

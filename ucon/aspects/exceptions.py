# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Exceptions raised by the aspect stratum.

Mirrors the kind layer's discipline (:mod:`ucon.kinds.exceptions`):
a common base, structured payloads, and messages that name what was
caught. ``AspectRefused`` covers both runtime refusal categories —
family conflict, and partial-under-strict — distinguished by whether
one side of the payload is ``None``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ucon.aspects.types import Aspect
    from ucon.kinds.types import JoinPolicy, Kind


__all__ = [
    "AspectClaimRefused",
    "AspectError",
    "AspectRefused",
    "AspectNotApplicable",
]


class AspectError(Exception):
    """Base class for aspect stratum errors."""


class AspectRefused(AspectError):
    """An operation's operands cannot be reconciled within one family.

    Two categories share this type:

    - **Family conflict** — both operands carry positions in the family
      and the lowest common ancestor's policy refuses the join
      (``left`` and ``right`` are both :class:`Aspect`\\ s).
    - **Partial under strict** — one operand carries the family and the
      other is silent (the silent side is ``None``).

    The ``family`` attribute is the family's root aspect; ``policy`` is
    the join policy consulted. The payload is deliberately
    warrant-shaped so a future unified refusal can wrap it losslessly.
    """

    def __init__(
        self,
        *,
        family: "Aspect",
        left: "Aspect | None",
        right: "Aspect | None",
        policy: "JoinPolicy | None" = None,
    ) -> None:
        self.family = family
        self.left = left
        self.right = right
        self.policy = policy
        if left is not None and right is not None:
            detail = (
                f"'{left.name}' and '{right.name}' cannot be reconciled "
                f"under family '{family.name}'"
            )
        else:
            present = left if left is not None else right
            detail = (
                f"one operand carries '{present.name}' "
                f"(family '{family.name}') and the other is silent"
            )
        super().__init__(f"Aspect refusal: {detail}")


class AspectClaimRefused(AspectError):
    """A conversion's claimed aspect is not supported by the value.

    The aspect peer of
    :class:`~ucon.core.exceptions.KindClaimRefused`, and admitted by the same
    rule: a claim may restate the aspect already carried in that family, or
    weaken it to an ancestor whose ``join_policy`` permits generalizing across
    that ancestor's children. It may not strengthen, nor exchange one sibling
    for another.

    This is the stratum where the distinction between combining and asserting
    bites hardest. ``pressure_role`` carries ``JoinPolicy.LCA`` precisely so
    that ``static + dynamic`` resolves to the family root — a total pressure,
    role unspecified, which is what Bernoulli's ``P0 = P + ½ρV²`` produces.
    Reporting a dynamic pressure *as* a static pressure is a different act, and
    refusing it is not in tension with summing them: one asks what two
    quantities make together, the other whether a value supports an assertion.

    Attributes
    ----------
    current : Aspect
        The aspect carried in the claimed aspect's family.
    claimed : Aspect
        The aspect the caller claimed.
    unit : Unit | UnitProduct
        The target unit.
    """

    def __init__(self, *, current, claimed, unit) -> None:
        self.current = current
        self.claimed = claimed
        self.unit = unit
        unit_name = getattr(unit, "name", None) or repr(unit)
        super().__init__(
            f"Cannot claim aspect {claimed.name!r} for a value carrying "
            f"{current.name!r} on conversion to {unit_name!r}: the claim is not "
            f"implied by the aspect already carried. A claim may restate it, or "
            f"weaken it to an ancestor that permits generalizing; it may not "
            f"strengthen it or exchange it for a sibling."
        )


class AspectNotApplicable(AspectError):
    """An aspect family does not apply to the quantity's kind.

    Raised at attachment time — ``Number(...)`` construction or formula
    load — never during resolution. The ``family`` attribute is the
    family root; ``kind`` is the offending kind (or ``None`` when the
    family requires a kind and none was given).
    """

    def __init__(self, *, family: "Aspect", kind: "Kind | None") -> None:
        self.family = family
        self.kind = kind
        kind_name = kind.name if kind is not None else "<unkinded>"
        super().__init__(
            f"Aspect family '{family.name}' does not apply to kind "
            f"'{kind_name}' (applies_to = {sorted(family.applies_to)!r})"
        )

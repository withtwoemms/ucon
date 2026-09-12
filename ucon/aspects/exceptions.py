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

# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.core.exceptions
====================

Exception classes for the ucon core layer.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ucon.conversion import Graph as ConversionGraph
    from ucon.core._types import Unit, UnitProduct
    from ucon.kinds.types import Kind


class DimensionNotCovered(Exception):
    """Raised when a BaseUnits mapping doesn't cover a requested dimension."""
    pass


class UnknownUnitError(Exception):
    """Raised when a unit string cannot be resolved to a known unit."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Unknown unit: {name!r}")


class NonScalableError(UnknownUnitError):
    """Raised when a scale prefix is applied to a unit marked non-scalable.

    Subclass of :class:`UnknownUnitError` so that callers that catch the
    parent class continue to work. Callers that want the richer diagnostic
    can catch :class:`NonScalableError` directly and inspect :attr:`base`
    and :attr:`prefix`.

    Attributes
    ----------
    attempted : str
        The full unit string that failed to parse (e.g. ``"Pflop"``).
    base : Unit
        The base unit that was found but is marked non-scalable.
    prefix : str
        The prefix shorthand that was attempted (e.g. ``"P"`` for peta).
    """

    def __init__(self, attempted: str, base: 'Unit', prefix: str):
        self.attempted = attempted
        self.base = base
        self.prefix = prefix
        # Bypass UnknownUnitError.__init__ to install a precise message.
        Exception.__init__(
            self,
            f"Unit {attempted!r} not found: base unit {base.name!r} is "
            f"registered but marked non-scalable, so prefix {prefix!r} "
            f"cannot be applied.",
        )
        self.name = attempted


class UnitDefinitionMismatch(Exception):
    """Source unit not in the active conversion graph by identity.

    Raised by :meth:`ucon.Number.to` (and :meth:`ucon.NumberArray.to`)
    under ``strict=True`` (the v2.0 default) when ``self.unit`` is not
    registered in the resolution graph by object identity. The most common
    cause is using a :class:`Number` constructed under one
    :class:`UnitSystem` against another. Re-bind via ``system.adopt(n)`` if
    the unit names match across systems, or
    ``Bridge(src, dst, ...).apply(n)`` when names or bases diverge.

    Attributes
    ----------
    unit : Unit | UnitProduct
        The source unit that failed identity-based resolution.
    graph : ConversionGraph
        The active conversion graph that did not contain ``unit`` by
        identity.
    """

    def __init__(
        self,
        unit: 'Unit | UnitProduct',
        *,
        graph: 'ConversionGraph',
    ) -> None:
        self.unit = unit
        self.graph = graph
        name = getattr(unit, "name", None) or repr(unit)
        super().__init__(
            f"Unit {name!r} is not in the active conversion graph by "
            f"identity. Use system.adopt(n) or "
            f"Bridge(src, dst, ...).apply(n) to rebind."
        )


class KindMismatch(Exception):
    """Kinded and unkinded Numbers combined under strict mode.

    Raised by ``Number.__add__`` / ``Number.__sub__`` /
    ``Number.__mul__`` / ``Number.__truediv__`` when one operand
    has ``kind`` set and the other does not, and the active context has
    ``strict=True``.

    Attributes
    ----------
    kinded : Kind
        The kind present on the annotated operand.
    unkinded_side : str
        Which operand was unkinded (``"left"`` or ``"right"``).
    """

    def __init__(self, *, kinded: 'Kind', unkinded_side: str) -> None:
        self.kinded = kinded
        self.unkinded_side = unkinded_side
        super().__init__(
            f"Cannot combine kinded ({kinded.name!r}) and unkinded "
            f"Numbers in strict mode ({unkinded_side} operand is unkinded)"
        )


class KindDimensionMismatch(Exception):
    """Kind's dimension does not match the Number's unit dimension.

    Raised at :meth:`ucon.Number.__post_init__` when ``kind`` is supplied
    and ``kind.dimension != unit.dimension``. A Number's kind must refine
    the same dimensional equivalence class its unit lives in.

    Attributes
    ----------
    kind : Kind
        The kind whose dimension did not match.
    unit : Unit | UnitProduct
        The unit the Number was constructed with.
    """

    def __init__(self, *, kind: 'Kind', unit: 'Unit | UnitProduct') -> None:
        self.kind = kind
        self.unit = unit
        unit_name = getattr(unit, "name", None) or repr(unit)
        super().__init__(
            f"Kind {kind.name!r} has dimension {kind.dimension!r}, "
            f"but unit {unit_name!r} has dimension {unit.dimension!r}. "
            f"A Number's kind must refine the dimension of its unit."
        )


class UnitsNotNormalizable(Exception):
    """Two same-dimension units cannot be reconciled without a graph.

    Raised by :meth:`ucon.Number.__eq__`, :meth:`ucon.Number.__add__`
    and :meth:`ucon.Number.__sub__` when the operands carry different
    units of the same dimension and at least one of them has no
    ``base_form``, so no purely algebraic factor relates them.

    Comparison and additive arithmetic are pure functions of
    ``(quantity, unit)`` — they never consult a
    :class:`~ucon.conversion.Graph` — which means they cannot express an
    affine offset (celsius, fahrenheit), a logarithmic level (decibel,
    neper, bel), or a pseudo-dimensional ratio whose canonical unit is
    outside the SI basis (degree against radian). Before v2.2.2 these
    combined unconverted, so ``Number(1, kelvin) == Number(1, celsius)``
    reported ``True`` and ``Number(180, degree) - Number(pi, radian)``
    returned ``176.86 deg``.

    The conversion graph *does* know these relationships. Convert first
    and the operation succeeds::

        a - b.to(a.unit)
        a == b.to(a.unit)

    Attributes
    ----------
    left : Unit | UnitProduct
        The left operand's unit.
    right : Unit | UnitProduct
        The right operand's unit.
    operation : str
        The operation that refused (``"compare"``, ``"add"`` or
        ``"subtract"``).
    """

    def __init__(
        self,
        *,
        left: 'Unit | UnitProduct',
        right: 'Unit | UnitProduct',
        operation: str,
    ) -> None:
        self.left = left
        self.right = right
        self.operation = operation
        left_name = getattr(left, "name", None) or repr(left)
        right_name = getattr(right, "name", None) or repr(right)
        missing = [
            getattr(u, "name", None) or repr(u)
            for u in (left, right)
            if getattr(u, "base_form", None) is None
        ]
        super().__init__(
            f"Cannot {operation} {left_name!r} and {right_name!r} without "
            f"converting first: {' and '.join(repr(m) for m in missing)} "
            f"{'have' if len(missing) > 1 else 'has'} no base_form, so no "
            f"algebraic factor relates the two units. Use "
            f".to({left_name!r}) on the right operand first."
        )


class ContingentCompositionRefused(Exception):
    """A conversion path would chain two different contingent contexts.

    Raised when pathfinding can reach the target only by composing edges
    from more than one dated table — an exchange rate with a tariff, two
    rate tables from different days.

    The refusal is not about reachability. A path exists; it is declined,
    because the figure it would produce was published by neither table:
    it cannot be cited, it will not match a directly quoted rate (the gap
    has a name — arbitrage), and it carries no well-defined date. Only a
    dated table has a truth value, so a value derived across two of them
    has none.

    Composition *within* one contingent context is permitted — that is
    what lets a rate package quote every currency against one base and
    have cross-rates derived. Definitional contexts (``spectroscopy``,
    ``boltzmann``) chain without limit, since c, h, and k_B are exact.

    Attributes
    ----------
    src, dst : Unit | UnitProduct
        The endpoints of the requested conversion.
    contexts : tuple[str, ...]
        Names of the contingent contexts the path would have had to mix.
    """

    def __init__(self, *, src, dst, contexts: tuple) -> None:
        self.src = src
        self.dst = dst
        self.contexts = contexts
        src_name = getattr(src, "name", None) or repr(src)
        dst_name = getattr(dst, "name", None) or repr(dst)
        named = " and ".join(repr(c) for c in contexts)
        super().__init__(
            f"Cannot convert {src_name!r} to {dst_name!r}: the only path "
            f"chains {named}, which are separate dated tables. The result "
            f"would be a figure neither table published, with no date of "
            f"its own. Convert through one table at a time."
        )

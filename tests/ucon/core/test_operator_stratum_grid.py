# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""The operator x stratum grid (#352).

Every cell is one operator applied to a pair of operands that differ in
*exactly one* stratum — dimension (ψ), chart, kind, or aspect. The grid
exists because the strata were wired operator by operator: ``+``, ``*``
and ``.to()`` consulted the kind lattice while ``/`` cancelled disjoint
kinds to an anonymous ``1.0`` and ``==`` answered ``True`` for the very
pairs ``.to()`` refuses. Asserting the whole cross-product cell by cell
is what makes the next ungated operator fail CI instead of shipping.

Expectations are classifications, not messages: a refusal names the
exception type, an admission says only that the operator answered
(``==``/``!=`` additionally pin the boolean). ``NO_OP`` marks an
operator Python does not dispatch at all — ordering, reflected scalar
multiplication, floor division, negation — which is missing capability
(#353 and the ROADMAP's unsequenced ergonomics row), not a stratum hole.
"""

from __future__ import annotations

from typing import Callable, Dict, Tuple

import pytest

from ucon import (
    Aspect,
    AspectRefused,
    DimensionMismatch,
    KindArrivalRefused,
    Number,
    UnitsNotNormalizable,
    units,
)
from ucon.formulas import FormulaNotFound
from ucon.kinds import JoinRefused


ADMITS = "admits"
"""The operator answered; the value is not pinned by this grid."""

NO_OP = "no-op"
"""Python does not dispatch the operator on ``Number`` at all."""


# --- fixtures: one stratum apart, everything else held equal ---------------

def _dimension_pair() -> Tuple[Number, Number]:
    """ψ apart: length against time."""
    return Number(1, units.meter), Number(1, units.second)


def _chart_pair() -> Tuple[Number, Number]:
    """Chart apart: an interval scale against its ratio scale."""
    return Number(1, units.celsius), Number(1, units.kelvin)


def _kind_pair() -> Tuple[Number, Number]:
    """Kind apart: the J/kg degeneracy cluster, same dimension and
    base form, two kinds whose shared parent refuses the join."""
    return Number(1, units.gray), Number(1, units.sievert)


def _aspect_pair() -> Tuple[Number, Number]:
    """Aspect apart: two sibling positions in one family."""
    family = Aspect("sample_basis", applies_to=frozenset({"*"}))
    dry = Aspect("dry_basis", parent=family)
    wet = Aspect("wet_basis", parent=family)
    return (Number(1, units.gray, aspects=[dry]),
            Number(1, units.gray, aspects=[wet]))


PAIRS: Dict[str, Callable[[], Tuple[Number, Number]]] = {
    "dimension": _dimension_pair,
    "chart": _chart_pair,
    "kind": _kind_pair,
    "aspect": _aspect_pair,
}

OPERATORS: Dict[str, Callable[[Number, Number], object]] = {
    "a + b": lambda a, b: a + b,
    "a - b": lambda a, b: a - b,
    "a * b": lambda a, b: a * b,
    "a / b": lambda a, b: a / b,
    "a ** 2": lambda a, b: a ** 2,
    "a == b": lambda a, b: a == b,
    "a != b": lambda a, b: a != b,
    "a < b": lambda a, b: a < b,
    "a // b": lambda a, b: a // b,
    "a.to(b.unit)": lambda a, b: a.to(b.unit),
    "hash(a)": lambda a, b: hash(a),
    "a * 2": lambda a, b: a * 2,
    "a / 2": lambda a, b: a / 2,
    "2 * a": lambda a, b: 2 * a,
    "-a": lambda a, b: -a,
    "abs(a)": lambda a, b: abs(a),
    "a.to_base()": lambda a, b: a.to_base(),
    "a.simplify()": lambda a, b: a.simplify(),
}


# --- the grid --------------------------------------------------------------
#
# Chart-column admissions (`a * b`, `a / b`, `a ** 2`, the scalar rows and
# the representation changes) are expected-for-now: chart dispatch is not
# implemented. It lands with four-stratum arithmetic dispatch in v3.2.0 —
# see ROADMAP "Where the chart defects land" ("Chart-crossing arithmetic
# returns a value | 3.2.0"). Until then the chart stratum is enforced only
# where `base_form` happens to proxy for it (the additive rows, and `==`).
#
# The aspect column's `==`/`!=` admissions are likewise current behaviour
# rather than endorsed behaviour: `__eq__` consults dimension and kind, not
# aspect. #352 is scoped to the kind stratum; recorded here so the gap is
# visible rather than discovered.

GRID: Dict[Tuple[str, str], object] = {
    # --- additive: every stratum refuses -----------------------------------
    ("a + b", "dimension"): TypeError,
    ("a + b", "chart"): UnitsNotNormalizable,
    ("a + b", "kind"): JoinRefused,
    ("a + b", "aspect"): AspectRefused,
    ("a - b", "dimension"): TypeError,
    ("a - b", "chart"): UnitsNotNormalizable,
    ("a - b", "kind"): JoinRefused,
    ("a - b", "aspect"): AspectRefused,
    # --- multiplicative ----------------------------------------------------
    # A product of differing dimensions is meaningful (m·s); a product of
    # kinds without a formula is not.
    ("a * b", "dimension"): ADMITS,
    ("a * b", "chart"): ADMITS,
    ("a * b", "kind"): FormulaNotFound,
    ("a * b", "aspect"): AspectRefused,
    # `/` closed in #352: the dimensionless quotient used to discard both
    # kinds and answer a bare 1.0.
    ("a / b", "dimension"): ADMITS,
    ("a / b", "chart"): ADMITS,
    ("a / b", "kind"): FormulaNotFound,
    ("a / b", "aspect"): AspectRefused,
    # `**` is single-operand, so no stratum pair meets; a dispatch row for
    # it arrives with the kind algebra (v3.2.0).
    ("a ** 2", "dimension"): ADMITS,
    ("a ** 2", "chart"): ADMITS,
    ("a ** 2", "kind"): ADMITS,
    ("a ** 2", "aspect"): ADMITS,
    # --- comparison --------------------------------------------------------
    # `==` stays total: a refusal is reported as "unequal", never raised.
    # The kind cells closed in #352 (they answered True/False).
    ("a == b", "dimension"): False,
    ("a == b", "chart"): UnitsNotNormalizable,
    ("a == b", "kind"): False,
    ("a == b", "aspect"): True,
    # `__ne__` is undefined and inherits from `__eq__`.
    ("a != b", "dimension"): True,
    ("a != b", "chart"): UnitsNotNormalizable,
    ("a != b", "kind"): True,
    ("a != b", "aspect"): False,
    ("a < b", "dimension"): NO_OP,
    ("a < b", "chart"): NO_OP,
    ("a < b", "kind"): NO_OP,
    ("a < b", "aspect"): NO_OP,
    ("a // b", "dimension"): NO_OP,
    ("a // b", "chart"): NO_OP,
    ("a // b", "kind"): NO_OP,
    ("a // b", "aspect"): NO_OP,
    ("hash(a)", "dimension"): TypeError,
    ("hash(a)", "chart"): TypeError,
    ("hash(a)", "kind"): TypeError,
    ("hash(a)", "aspect"): TypeError,
    # --- arrival -----------------------------------------------------------
    ("a.to(b.unit)", "dimension"): DimensionMismatch,
    ("a.to(b.unit)", "chart"): ADMITS,  # °C → K is the chart's own job
    ("a.to(b.unit)", "kind"): KindArrivalRefused,
    ("a.to(b.unit)", "aspect"): ADMITS,  # same unit; aspects thread through
    # --- single-operand rows: nothing to refuse ----------------------------
    # Scalar `*`/`/` are gated on level-vs-gain in #340, not here.
    ("a * 2", "dimension"): ADMITS,
    ("a * 2", "chart"): ADMITS,
    ("a * 2", "kind"): ADMITS,
    ("a * 2", "aspect"): ADMITS,
    ("a / 2", "dimension"): ADMITS,
    ("a / 2", "chart"): ADMITS,
    ("a / 2", "kind"): ADMITS,
    ("a / 2", "aspect"): ADMITS,
    ("2 * a", "dimension"): NO_OP,
    ("2 * a", "chart"): NO_OP,
    ("2 * a", "kind"): NO_OP,
    ("2 * a", "aspect"): NO_OP,
    ("-a", "dimension"): TypeError,
    ("-a", "chart"): TypeError,
    ("-a", "kind"): TypeError,
    ("-a", "aspect"): TypeError,
    ("abs(a)", "dimension"): TypeError,
    ("abs(a)", "chart"): TypeError,
    ("abs(a)", "kind"): TypeError,
    ("abs(a)", "aspect"): TypeError,
    ("a.to_base()", "dimension"): ADMITS,
    ("a.to_base()", "chart"): ADMITS,
    ("a.to_base()", "kind"): ADMITS,
    ("a.to_base()", "aspect"): ADMITS,
    ("a.simplify()", "dimension"): ADMITS,
    ("a.simplify()", "chart"): ADMITS,
    ("a.simplify()", "kind"): ADMITS,
    ("a.simplify()", "aspect"): ADMITS,
}


def _classify(operator: Callable[[Number, Number], object],
              a: Number, b: Number) -> object:
    """Run one cell and report what happened.

    Returns the exception *type* for a refusal, :data:`NO_OP` for the
    ``TypeError`` Python raises when an operator is not dispatched at
    all, a bool for a boolean answer, and :data:`ADMITS` otherwise.
    """
    try:
        result = operator(a, b)
    except TypeError as exc:
        message = str(exc)
        if "not supported" in message or "unsupported operand" in message:
            return NO_OP
        return TypeError
    except Exception as exc:  # noqa: BLE001 — the grid records the type
        return type(exc)
    if isinstance(result, bool):
        return result
    return ADMITS


def test_grid_covers_the_cross_product() -> None:
    """Every operator x stratum cell has a recorded expectation."""
    assert set(GRID) == {
        (operator, stratum)
        for operator in OPERATORS
        for stratum in PAIRS
    }


@pytest.mark.parametrize(("operator", "stratum"), sorted(GRID))
def test_operator_stratum_cell(operator: str, stratum: str) -> None:
    a, b = PAIRS[stratum]()
    assert _classify(OPERATORS[operator], a, b) == GRID[(operator, stratum)]


# --- the two cells #352 closed, spelled out --------------------------------

def test_disjoint_kinds_do_not_cancel_to_one() -> None:
    """`Gy / Sv` refuses where it used to answer a bare `1.0`."""
    with pytest.raises(FormulaNotFound):
        Number(2, units.gray) / Number(2, units.sievert)


def test_disjoint_kinds_are_unequal() -> None:
    """`Gy == Sv` is False, the treatment the cross-dimension case gets."""
    assert (Number(2, units.gray) == Number(2, units.sievert)) is False
    assert (Number(2, units.gray) != Number(2, units.sievert)) is True
    # The other shipped degeneracy clusters, same hole, same fix.
    assert (Number(1, units.watt) == Number(1, units.volt_ampere)) is False
    assert (Number(1, units.hertz) == Number(1, units.becquerel)) is False


def test_same_kind_division_still_cancels() -> None:
    """The anonymous ratio survives: same kind, no kind on the quotient."""
    quotient = Number(100, units.gray) / Number(50, units.gray)
    assert quotient.quantity == 2.0
    assert quotient.kind is None


def test_kinded_over_unkinded_division_still_cancels() -> None:
    """One side unkinded is not a stratum conflict.

    `gray` declares a `default_kind`, so the unkinded operand is spelled
    as the bare base form the cluster shares.
    """
    unkinded = Number(50, units.meter ** 2 / units.second ** 2)
    assert unkinded.kind is None
    quotient = Number(100, units.gray) / unkinded
    assert quotient.quantity == 2.0
    assert quotient.kind is None

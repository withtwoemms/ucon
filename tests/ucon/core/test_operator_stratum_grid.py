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
operator Python does not dispatch at all — floor division, negation —
which is missing capability (#353 and the ROADMAP's unsequenced
ergonomics row), not a stratum hole.

The ordering rows, the reflected scalar rows and the aspect column's
``==``/``!=`` cells were ``NO_OP``/admitting when this grid was written
and were closed by #353. The four scalar rows' chart cells admitted until
#340, which derived their refusal from scalar multiplication being
repeated addition rather than from chart dispatch.
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
    Ratio,
    ScalarArithmeticRefused,
    Scale,
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
    "a <= b": lambda a, b: a <= b,
    "a > b": lambda a, b: a > b,
    "a >= b": lambda a, b: a >= b,
    "a // b": lambda a, b: a // b,
    "a.to(b.unit)": lambda a, b: a.to(b.unit),
    "hash(a)": lambda a, b: hash(a),
    "a * 2": lambda a, b: a * 2,
    "a / 2": lambda a, b: a / 2,
    "2 * a": lambda a, b: 2 * a,
    "2 / a": lambda a, b: 2 / a,
    "-a": lambda a, b: -a,
    "abs(a)": lambda a, b: abs(a),
    "a.to_base()": lambda a, b: a.to_base(),
    "a.simplify()": lambda a, b: a.simplify(),
}


# --- the grid --------------------------------------------------------------
#
# The remaining chart-column admissions (`a * b`, `a / b`, `a ** 2` and the
# representation changes) are expected-for-now: chart dispatch is not
# implemented. It lands with four-stratum arithmetic dispatch in v3.2.0 —
# see ROADMAP "Where the chart defects land" ("Chart-crossing arithmetic
# returns a value | 3.2.0"). Until then the chart stratum is enforced where
# `base_form` happens to proxy for it (the additive rows, and `==`) and on
# the four scalar rows, which #340 closed without chart dispatch — see the
# note on those rows below.
#
# The ordering rows admit on the chart column where the additive rows
# refuse. That is derived, not conceded: ordering survives any monotone
# change of coordinate, and the identity, affine and log coordinates are
# all monotone, so `3 dB < 10 dB` and `20 °C < 25 °C` are well posed
# where `3 dB + 10 dB` is not. What the chart cell records is narrower —
# `celsius` and `kelvin` have no algebraic factor relating them, so the
# comparison needs `.to()` first, exactly as `==` does.

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
    # The kind cells closed in #352; the aspect cells in #353.
    ("a == b", "dimension"): False,
    ("a == b", "chart"): UnitsNotNormalizable,
    ("a == b", "kind"): False,
    ("a == b", "aspect"): False,
    # `__ne__` is defined in #353 rather than inherited, and negates
    # `__eq__` cell for cell — refusals included.
    ("a != b", "dimension"): True,
    ("a != b", "chart"): UnitsNotNormalizable,
    ("a != b", "kind"): True,
    ("a != b", "aspect"): True,
    # Ordering refuses on dimension, kind and aspect, as `+` does, and
    # admits across charts — see the note above. All four operators route
    # through one three-way comparison, so the rows are identical.
    ("a < b", "dimension"): TypeError,
    ("a < b", "chart"): UnitsNotNormalizable,
    ("a < b", "kind"): JoinRefused,
    ("a < b", "aspect"): AspectRefused,
    ("a <= b", "dimension"): TypeError,
    ("a <= b", "chart"): UnitsNotNormalizable,
    ("a <= b", "kind"): JoinRefused,
    ("a <= b", "aspect"): AspectRefused,
    ("a > b", "dimension"): TypeError,
    ("a > b", "chart"): UnitsNotNormalizable,
    ("a > b", "kind"): JoinRefused,
    ("a > b", "aspect"): AspectRefused,
    ("a >= b", "dimension"): TypeError,
    ("a >= b", "chart"): UnitsNotNormalizable,
    ("a >= b", "kind"): JoinRefused,
    ("a >= b", "aspect"): AspectRefused,
    ("a // b", "dimension"): NO_OP,
    ("a // b", "chart"): NO_OP,
    ("a // b", "kind"): NO_OP,
    ("a // b", "aspect"): NO_OP,
    # `Number` is a mutable dataclass, so defining `__eq__` without
    # `__hash__` is defensible rather than accidental: hashing on mutable
    # fields is the hazard `__hash__ = None` exists to prevent. #353
    # leaves these four cells alone; ADR 009 sequences "`Number` frozen"
    # at 3.0.0, after which the hash can be taken on the canonical
    # magnitude (`1 m == 100 cm`, so `(quantity, unit)` would not do).
    ("hash(a)", "dimension"): TypeError,
    ("hash(a)", "chart"): TypeError,
    ("hash(a)", "kind"): TypeError,
    ("hash(a)", "aspect"): TypeError,
    # --- arrival -----------------------------------------------------------
    ("a.to(b.unit)", "dimension"): DimensionMismatch,
    ("a.to(b.unit)", "chart"): ADMITS,  # °C → K is the chart's own job
    ("a.to(b.unit)", "kind"): KindArrivalRefused,
    ("a.to(b.unit)", "aspect"): ADMITS,  # same unit; aspects thread through
    # --- single-operand rows -----------------------------------------------
    # The scalar rows closed in #340, and the chart column is the only one
    # they close. The rule is derived, not dispatched: scalar
    # multiplication is repeated addition (`a * n == a + a + …`, identical
    # on every unit in the catalog, the broken ones included), so it obeys
    # the *additive* rules. `2 * (1 °C)` expands to `1 °C + 1 °C` — point
    # plus point — and refuses; `2 * (10 dBW)` to level plus level, and
    # refuses; `2 * (3 dB)` to gain plus gain, which is the cascade of two
    # gains (`<6 dB>`, ratio 3.981 = 1.995²) and still admits. The
    # distinction is level-versus-gain, read off the declared edges by
    # `Graph.scale_class`, not a chart class on the unit.
    #
    # The chart fixture is `celsius`, a point, so all four cells refuse.
    # Nothing else moved: the kind and aspect columns are `gray`, a ratio
    # scale, and the dimension column is `meter`.
    ("a * 2", "dimension"): ADMITS,
    ("a * 2", "chart"): ScalarArithmeticRefused,
    ("a * 2", "kind"): ADMITS,
    ("a * 2", "aspect"): ADMITS,
    ("a / 2", "dimension"): ADMITS,
    ("a / 2", "chart"): ScalarArithmeticRefused,
    ("a / 2", "kind"): ADMITS,
    ("a / 2", "aspect"): ADMITS,
    # The reflected forms, added in #353. Each admits exactly what its
    # forward form admits, so these mirror the `a * 2` / `a / 2` rows —
    # including the #340 refusal, which `2 / a` earns on its own account:
    # a reciprocal reads a magnitude, and a point has none.
    ("2 * a", "dimension"): ADMITS,
    ("2 * a", "chart"): ScalarArithmeticRefused,
    ("2 * a", "kind"): ADMITS,
    ("2 * a", "aspect"): ADMITS,
    ("2 / a", "dimension"): ADMITS,
    ("2 / a", "chart"): ScalarArithmeticRefused,
    ("2 / a", "kind"): ADMITS,
    ("2 / a", "aspect"): ADMITS,
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


# --- the cells #353 closed, spelled out ------------------------------------

def test_ordering_crosses_units_within_a_dimension() -> None:
    """`1 ft < 1 m`, the comparison pint, unyt and astropy all answer True."""
    assert (Number(1, units.foot) < Number(1, units.meter)) is True
    assert (Number(1, units.meter) < Number(1, units.foot)) is False
    assert (Number(1, units.meter) > Number(1, units.foot)) is True
    assert (Number(1, units.foot) <= Number(1, units.meter)) is True
    assert (Number(1, units.foot) >= Number(1, units.meter)) is False


def test_ordering_agrees_with_equality_across_scales() -> None:
    """A scale change is not an ordering: `1 m` and `100 cm` tie."""
    centimeter = Scale.centi * units.meter
    meter, hundred_cm = Number(1, units.meter), Number(100, centimeter)
    assert (meter == hundred_cm) is True
    assert (meter < hundred_cm) is False
    assert (meter > hundred_cm) is False
    assert (meter <= hundred_cm) is True
    assert (meter >= hundred_cm) is True


def test_ordering_admits_the_logarithmic_chart() -> None:
    """`3 dB < 10 dB`: a log coordinate is monotone, so ordering survives it."""
    assert (Number(3, units.decibel) < Number(10, units.decibel)) is True
    assert (Number(10, units.decibel) < Number(3, units.decibel)) is False
    assert (Number(10, units.decibel) >= Number(10, units.decibel)) is True


def test_ordering_admits_the_interval_chart() -> None:
    """`20 °C < 25 °C`: an affine coordinate is monotone too."""
    assert (Number(20, units.celsius) < Number(25, units.celsius)) is True
    assert (Number(25, units.celsius) <= Number(20, units.celsius)) is False
    assert (Number(20, units.celsius) >= Number(20, units.celsius)) is True


def test_ordering_across_charts_refuses_like_equality() -> None:
    """`celsius(20) < kelvin(300)` refuses exactly where `==` does.

    Not a chart refusal: no algebraic factor relates the two units, so
    there is no magnitude to compare until `.to()` has been called.
    """
    celsius, kelvin = Number(20, units.celsius), Number(300, units.kelvin)
    with pytest.raises(UnitsNotNormalizable):
        celsius == kelvin
    for comparison in (lambda: celsius < kelvin, lambda: celsius <= kelvin,
                       lambda: celsius > kelvin, lambda: celsius >= kelvin):
        with pytest.raises(UnitsNotNormalizable):
            comparison()


def test_sorted_min_and_max_work() -> None:
    """The point of the exercise: the stdlib protocols come for free."""
    lengths = [Number(3, units.meter), Number(1, units.meter),
               Number(2, units.meter)]
    assert [n.quantity for n in sorted(lengths)] == [1, 2, 3]
    assert max(Number(1, units.meter), Number(2, units.foot)).unit is units.meter
    assert min(Number(1, units.meter), Number(2, units.foot)).unit is units.foot


def test_conflicting_aspects_are_unequal() -> None:
    """Sibling positions in one family compare False, and `!=` True.

    `+`, `*` and `/` all raise `AspectRefused` for this pair while `==`
    answered `True` — the aspect peer of the kind hole #352 closed.
    """
    a, b = _aspect_pair()
    assert (a == b) is False
    assert (a != b) is True


def test_aspect_silence_is_not_an_aspect_conflict() -> None:
    """One operand aspect-silent is partial presence, not conflict.

    Comparison refuses on conflict only, so the carry rule's reading is
    the one `==` takes: an unqualified operand contradicts nothing.
    """
    aspected, _ = _aspect_pair()
    plain = Number(1, units.gray)
    assert (aspected == plain) is True
    assert (aspected != plain) is False
    assert (aspected <= plain) is True


def test_identical_aspects_still_compare() -> None:
    """Equal positions carry through, as they do under every operator."""
    aspected, _ = _aspect_pair()
    twin = Number(1, units.gray, aspects=aspected.aspects)
    assert (aspected == twin) is True
    assert (aspected < twin) is False


def test_reflected_scalar_multiplication_matches_the_forward_form() -> None:
    """`2 * a` answers what `a * 2` answers, for every operand type."""
    length = Number(3, units.meter)
    assert (2 * length).quantity == (length * 2).quantity == 6
    assert (2.5 * length).quantity == (length * 2.5).quantity == 7.5
    assert (2 * length).unit is length.unit


def test_reflected_scalar_multiplication_preserves_the_strata() -> None:
    """Delegation means the kind and aspects ride along unchanged."""
    dose = Number(1, units.gray)
    doubled = 2 * dose
    assert doubled.kind == dose.kind
    aspected, _ = _aspect_pair()
    assert (2 * aspected).aspects == aspected.aspects


def test_reflected_division_restores_the_operand_order() -> None:
    """`2 / a` is a reciprocal, not `a / 2`."""
    reciprocal = 2 / Number(4, units.meter)
    assert reciprocal.quantity == 0.5
    assert reciprocal.unit.dimension == (units.meter ** -1).dimension
    assert (Number(4, units.meter) / 2).quantity == 2.0


def test_reflected_additive_forms_refuse_as_the_forward_forms_do() -> None:
    """A bare scalar has no dimension, so neither direction admits it.

    `__radd__`/`__rsub__` exist to remove the dispatch asymmetry, not to
    widen what `+` and `-` accept: all four spellings are a `TypeError`.
    """
    length = Number(3, units.meter)
    for expression in (lambda: 2 + length, lambda: length + 2,
                       lambda: 2 - length, lambda: length - 2):
        with pytest.raises(TypeError):
            expression()


def test_reflected_subtraction_keeps_the_operand_order() -> None:
    """Where the operands are commensurable, `b - a` is not `a - b`."""
    two, half = Number(2), Number(0.5)
    assert two.__rsub__(half).quantity == -1.5
    assert (half - two).quantity == -1.5
    assert (two - half).quantity == 1.5


def test_number_stays_unhashable() -> None:
    """Deliberate: `Number` is mutable, so #353 leaves `__hash__` alone."""
    with pytest.raises(TypeError):
        hash(Number(1, units.meter))


def test_ordering_accepts_a_ratio_as_equality_does() -> None:
    """A `Ratio` evaluates to a `Number`, so it is orderable too."""
    ratio = Ratio(Number(4, units.meter), Number(2, units.meter))
    assert (Number(1) < ratio) is True
    assert (Number(3) > ratio) is True
    assert (Number(2) <= ratio) is True
    assert (Number(2) >= ratio) is True


def test_ordering_against_a_foreign_type_defers_to_python() -> None:
    """Non-quantities yield `NotImplemented`, so Python reports the pair."""
    length = Number(1, units.meter)
    assert length.__lt__(2) is NotImplemented
    assert length.__le__("x") is NotImplemented
    assert length.__gt__(None) is NotImplemented
    assert length.__ge__(object()) is NotImplemented
    with pytest.raises(TypeError, match="not supported between"):
        length < 2


def test_reflected_forms_against_a_foreign_type_defer_to_python() -> None:
    """Same contract on the reflected side: defer, never raise."""
    length = Number(1, units.meter)
    assert length.__rmul__("x") is NotImplemented
    assert length.__rsub__(2) is NotImplemented
    assert length.__rtruediv__("x") is NotImplemented


def test_reflected_subtraction_takes_a_ratio_left_operand() -> None:
    """`Ratio` defines no `__sub__`, so `__rsub__` is the path it takes."""
    ratio = Ratio(Number(4, units.meter), Number(2, units.meter))
    assert (ratio - Number(1)).quantity == 1.0
    assert Number(1).__rtruediv__(ratio).quantity == 2.0


# --- the cells #340 closed, spelled out ------------------------------------

def test_scaling_a_level_refuses() -> None:
    """`10 dBW * 2` answered `<20 dBW>` — 100 W, where 2 x 10 W is 13.010 dBW."""
    level = Number(10, units.decibel_watt)
    for expression in (lambda: level * 2, lambda: 2 * level,
                       lambda: level / 2, lambda: 2 / level):
        with pytest.raises(ScalarArithmeticRefused):
            expression()


def test_scaling_an_interval_point_refuses() -> None:
    """`10 °C * 2` answered `<20 °C>`, where twice 283.15 K is 293.15 °C."""
    point = Number(10, units.celsius)
    for expression in (lambda: point * 2, lambda: 2 * point,
                       lambda: point / 2, lambda: 2 / point):
        with pytest.raises(ScalarArithmeticRefused):
            expression()


def test_scaling_a_gain_still_admits() -> None:
    """`3 dB + 3 dB = 6 dB` is the cascade of two gains, so `2 * 3 dB` is too.

    Ratio 1.995 twice over is 3.981, which is 6 dB. The admission is the
    derivation's own result, not an exemption carved around `dB`.
    """
    assert (Number(3, units.decibel) * 2).quantity == 6
    assert (2 * Number(3, units.decibel)).quantity == 6
    # The geometric half: `5 dB + 5 dB` is `10 dB`.
    assert (Number(10, units.decibel) / 2).quantity == 5.0
    for gain in (units.bel, units.neper):
        assert (Number(2, gain) * 2).quantity == 4


def test_the_level_gain_split_is_not_the_reference_field() -> None:
    """`decibel_watt`'s log edge carries `reference=1.0`, as a bare `dB` does.

    0 dBW *is* 1 W, so the referent's numeric value is 1 and the field
    cannot tell a level from a gain on its own — `decibel_volt` is the
    same story (0 dBV is 1 V). What separates them is that the referent
    is a watt: the level is dimensionful, the gain is not.
    """
    for level in (units.decibel_watt, units.decibel_volt,
                  units.decibel_milliwatt, units.decibel_spl, units.pH):
        with pytest.raises(ScalarArithmeticRefused):
            Number(1, level) * 2
    for gain in (units.decibel, units.bel, units.neper):
        assert (Number(1, gain) * 2).quantity == 2


def test_rankine_scales_because_it_is_a_ratio_scale() -> None:
    """`°R` is listed with the affine units but has a true zero.

    A pure scaling of kelvin (#339), so it carries a `base_form` and
    `2 x 10 °R` is simply `20 °R`.
    """
    assert units.rankine.base_form is not None
    assert (Number(10, units.rankine) * 2).quantity == 20


def test_reaumur_refuses_though_its_own_edge_carries_no_offset() -> None:
    """Locality is not enough: `°Ré → °C` is a pure scaling.

    Réaumur is an interval scale all the same, because its only path to
    kelvin runs through celsius's offset. The gate walks the whole
    multiplicative neighbourhood for exactly this case.
    """
    with pytest.raises(ScalarArithmeticRefused):
        Number(10, units.reaumur) * 2


def test_pseudo_dimensional_ratio_scales_still_scale() -> None:
    """`radian`, `percent` and friends have no `base_form` and are fine.

    They are unanchored ratio scales, not points or levels, so the gate
    must not read "no base_form" as "no magnitude".
    """
    for unit in (units.radian, units.degree, units.percent, units.fraction,
                 units.permille, units.steradian, units.gauss,
                 units.electron_volt):
        assert (Number(2, unit) * 2).quantity == 4


def test_exponentiation_is_out_of_scope() -> None:
    """`a ** 2` is repeated *multiplication*, a different rule entirely."""
    assert (Number(2, units.celsius) ** 2).quantity == 4

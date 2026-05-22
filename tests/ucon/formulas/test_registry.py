# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for FormulaRegistry: registration, lookup, commutativity, duplicates."""

from __future__ import annotations

import pytest

from ucon.dimension import LENGTH, MASS, TIME
from ucon.formulas import (
    DuplicateFormula,
    FormulaNotFound,
    FormulaRegistry,
    KindFormula,
    MatchKind,
)
from ucon.kinds import Kind


LENGTH_DIM = LENGTH
TIME_DIM = TIME
DIMENSIONLESS = LENGTH / LENGTH
FREQ_DIM = TIME ** -1
VELOCITY_DIM = LENGTH / TIME
MOMENTUM_DIM = MASS * LENGTH / TIME


def _voltage_current_power_formula():
    voltage = Kind("voltage", dimension=LENGTH_DIM)        # stand-in dims
    current = Kind("current", dimension=TIME_DIM)
    power = Kind("power", dimension=LENGTH_DIM * TIME_DIM)
    f = KindFormula(
        name="ohms_power",
        expression="V * I",
        input_kinds={"V": voltage, "I": current},
        output_kind=power,
        commutative=True,
    )
    return f, voltage, current, power


def test_register_and_get_by_name():
    f, *_ = _voltage_current_power_formula()
    reg = FormulaRegistry([f])
    assert reg.get("ohms_power") is f
    assert "ohms_power" in reg


def test_register_duplicates_refused():
    f, *_ = _voltage_current_power_formula()
    reg = FormulaRegistry([f])
    with pytest.raises(DuplicateFormula) as exc:
        reg.register(f)
    assert exc.value.name == "ohms_power"


def test_get_unknown_raises_formula_not_found():
    reg = FormulaRegistry()
    with pytest.raises(FormulaNotFound) as exc:
        reg.get("missing")
    assert exc.value.name_or_kinds == "missing"


def test_lookup_exact_match_forward_order():
    f, v, i, _ = _voltage_current_power_formula()
    reg = FormulaRegistry([f])
    assert reg.lookup(v, i) is f


def test_lookup_commutative_reverse_order_resolves():
    f, v, i, _ = _voltage_current_power_formula()
    reg = FormulaRegistry([f])
    # Commutative: registry indexed reversed key.
    assert reg.lookup(i, v) is f


def test_lookup_non_commutative_only_matches_forward_order():
    N = Kind("cycle_count", dimension=DIMENSIONLESS)
    t = Kind("duration", dimension=TIME_DIM)
    freq = Kind("frequency", dimension=FREQ_DIM)
    f = KindFormula(
        name="cycles_to_frequency",
        expression="N / t",
        input_kinds={"N": N, "t": t},
        output_kind=freq,
        commutative=False,
    )
    reg = FormulaRegistry([f])
    assert reg.lookup(N, t) is f
    with pytest.raises(FormulaNotFound):
        reg.lookup(t, N)


def test_lookup_unmatched_raises_formula_not_found():
    f, v, _, _ = _voltage_current_power_formula()
    reg = FormulaRegistry([f])
    stranger = Kind("stranger", dimension=DIMENSIONLESS)
    with pytest.raises(FormulaNotFound):
        reg.lookup(v, stranger)


def test_commutative_with_two_equal_inputs_does_not_duplicate_index():
    # Sanity: when both inputs are the same kind, reversed key is the
    # same tuple, so commutative registration is a no-op rather than an
    # error.
    mass = Kind("mass", dimension=MASS)
    momentum_sq = Kind("mass_squared", dimension=MASS * MASS)
    f = KindFormula(
        name="square_mass",
        expression="m * m",
        input_kinds={"m1": mass, "m2": mass},
        output_kind=momentum_sq,
        commutative=True,
    )
    reg = FormulaRegistry([f])
    assert reg.lookup(mass, mass) is f


def test_higher_arity_commutative_lookup_only():
    # lookup() is conservative: exact + arity-2 commutative only.
    # Higher-arity permutations require resolve().
    a = Kind("a", dimension=LENGTH_DIM)
    b = Kind("b", dimension=MASS)
    c = Kind("c", dimension=TIME_DIM)
    out = Kind("abc", dimension=LENGTH_DIM * MASS * TIME_DIM)
    f = KindFormula(
        name="triple_product",
        expression="a * b * c",
        input_kinds={"a": a, "b": b, "c": c},
        output_kind=out,
        commutative=True,
    )
    reg = FormulaRegistry([f])
    assert reg.lookup(a, b, c) is f
    with pytest.raises(FormulaNotFound):
        reg.lookup(c, b, a)


def test_higher_arity_commutative_permuted_via_resolve():
    # resolve() uses canonical sorted key for commutative formulas.
    a = Kind("a", dimension=LENGTH_DIM)
    b = Kind("b", dimension=MASS)
    c = Kind("c", dimension=TIME_DIM)
    out = Kind("abc", dimension=LENGTH_DIM * MASS * TIME_DIM)
    f = KindFormula(
        name="triple_product",
        expression="a * b * c",
        input_kinds={"a": a, "b": b, "c": c},
        output_kind=out,
        commutative=True,
    )
    reg = FormulaRegistry([f])
    result = reg.resolve(c, b, a)
    assert result.formula is f
    assert result.match_kind == MatchKind.COMMUTATIVE


def test_registry_contains_len_iter():
    f, *_ = _voltage_current_power_formula()
    g = KindFormula(
        name="other",
        expression="x",
        input_kinds={},
        output_kind=Kind("scalar", dimension=DIMENSIONLESS),
    )
    reg = FormulaRegistry([f, g])
    assert len(reg) == 2
    assert "ohms_power" in reg
    assert "other" in reg
    assert "missing" not in reg
    assert {x.name for x in reg} == {"ohms_power", "other"}


def test_registry_names_returns_primary_only():
    f, *_ = _voltage_current_power_formula()
    reg = FormulaRegistry([f])
    assert reg.names() == ("ohms_power",)


def test_register_via_constructor_iterable():
    f, *_ = _voltage_current_power_formula()
    reg = FormulaRegistry(iter([f]))
    assert "ohms_power" in reg


def test_apply_composes_lookup_and_projection():
    # Co-located with the lookup tests because `apply` composes lookup
    # with aspect projection over the same registry surface. The full
    # behaviour matrix (rules, missing bindings, exception propagation,
    # commutativity) lives in `test_registry_apply.py`.
    f, v, i, p = _voltage_current_power_formula()
    reg = FormulaRegistry([f])
    formula, out_kind, out_aspects, match_kind = reg.apply(
        {
            "V": (v, frozenset({"calibrated"})),
            "I": (i, frozenset()),
        }
    )
    assert formula is f
    assert out_kind is p
    assert out_aspects == frozenset({"calibrated"})
    assert match_kind == MatchKind.EXACT

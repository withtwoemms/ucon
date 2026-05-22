# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""End-to-end tests for FormulaRegistry.apply.

`apply` is the single entry point that composes formula lookup with
aspect projection. The caller supplies `(kind, aspect_set)` per binding;
the registry returns `(formula, output_kind, projected_aspects, match_kind)`.
"""

from __future__ import annotations

import pytest

from ucon.aspects import AspectRule
from ucon.dimension import LENGTH, MASS, TIME
from ucon.formulas import (
    FormulaNotFound,
    FormulaRegistry,
    KindFormula,
    MatchKind,
)
from ucon.kinds import Kind


ABSORBED_DOSE_DIM = (LENGTH ** 2) / (TIME ** 2)
DIMENSIONLESS = LENGTH / LENGTH


def _equivalent_dose_registry(
    aspect_rules: dict | None = None,
    commutative: bool = False,
) -> tuple[FormulaRegistry, KindFormula, Kind, Kind, Kind]:
    D = Kind("absorbed_dose", dimension=ABSORBED_DOSE_DIM)
    wR = Kind("radiation_weighting_factor", dimension=DIMENSIONLESS)
    H = Kind("equivalent_dose", dimension=ABSORBED_DOSE_DIM)
    f = KindFormula(
        name="equivalent_dose",
        expression="D * w_R",
        input_kinds={"D": D, "w_R": wR},
        output_kind=H,
        aspect_rules=aspect_rules or {},
        commutative=commutative,
    )
    return FormulaRegistry([f]), f, D, wR, H


# ---------- End-to-end resolution + projection ----------


def test_apply_returns_formula_output_kind_and_projected_aspects():
    reg, f, D, wR, H = _equivalent_dose_registry(
        aspect_rules={"w_R": AspectRule.CONSUME}
    )
    formula, out_kind, out_aspects, match_kind = reg.apply(
        {
            "D": (D, frozenset({"signal_summary", "calibrated"})),
            "w_R": (wR, frozenset({"ICRP103"})),
        }
    )
    assert formula is f
    assert out_kind is H
    assert out_aspects == frozenset({"signal_summary", "calibrated"})
    assert match_kind == MatchKind.EXACT


def test_apply_with_no_rules_unions_all_aspects():
    reg, f, D, wR, H = _equivalent_dose_registry()
    _, _, out_aspects, _ = reg.apply(
        {
            "D": (D, frozenset({"a"})),
            "w_R": (wR, frozenset({"b"})),
        }
    )
    assert out_aspects == frozenset({"a", "b"})


def test_apply_with_all_consume_yields_empty_aspects():
    reg, _, D, wR, _ = _equivalent_dose_registry(
        aspect_rules={
            "D": AspectRule.CONSUME,
            "w_R": AspectRule.CONSUME,
        }
    )
    _, _, out_aspects, _ = reg.apply(
        {"D": (D, frozenset({"a"})), "w_R": (wR, frozenset({"b"}))}
    )
    assert out_aspects == frozenset()


# ---------- Exception propagation ----------


def test_apply_propagates_formula_not_found():
    reg, _, _, _, _ = _equivalent_dose_registry()
    stranger = Kind("stranger", dimension=DIMENSIONLESS)
    with pytest.raises(FormulaNotFound):
        reg.apply(
            {
                "X": (stranger, frozenset()),
                "Y": (stranger, frozenset()),
            }
        )


def test_apply_empty_inputs_raises_formula_not_found():
    reg, *_ = _equivalent_dose_registry()
    # Empty inputs → lookup(*()) finds nothing.
    with pytest.raises(FormulaNotFound):
        reg.apply({})


# ---------- Argument order ----------


def test_apply_lookup_is_positional_in_iteration_order():
    # Non-commutative: only the declared binding order resolves.
    reg, _, D, wR, _ = _equivalent_dose_registry()  # commutative=False
    with pytest.raises(FormulaNotFound):
        reg.apply(
            {
                "w_R": (wR, frozenset({"b"})),
                "D": (D, frozenset({"a"})),
            }
        )


def test_apply_commutative_two_arg_resolves_in_either_order():
    reg, f, D, wR, H = _equivalent_dose_registry(commutative=True)
    forward = reg.apply(
        {"D": (D, frozenset({"a"})), "w_R": (wR, frozenset({"b"}))}
    )
    reversed_ = reg.apply(
        {"w_R": (wR, frozenset({"b"})), "D": (D, frozenset({"a"}))}
    )
    assert forward[0] is f and reversed_[0] is f
    assert forward[1] is H and reversed_[1] is H
    assert forward[2] == reversed_[2] == frozenset({"a", "b"})


# ---------- Independence from lookup ----------


def test_apply_does_not_disturb_existing_lookup_surface():
    # `lookup` continues to work alongside `apply`.
    reg, f, D, wR, _ = _equivalent_dose_registry()
    assert reg.lookup(D, wR) is f


# ---------- Binding-name independence ----------


def test_apply_uses_supplied_binding_names_for_projection_only():
    # The projection step keys on the formula's binding names; if the
    # caller supplies aspects under a name the formula doesn't declare,
    # those aspects do not propagate.
    reg, _, D, wR, _ = _equivalent_dose_registry(
        aspect_rules={"D": AspectRule.CARRY, "w_R": AspectRule.CONSUME}
    )
    _, _, out_aspects, _ = reg.apply(
        {
            "D": (D, frozenset({"d_aspect"})),
            "w_R": (wR, frozenset({"will_be_consumed"})),
        }
    )
    assert out_aspects == frozenset({"d_aspect"})

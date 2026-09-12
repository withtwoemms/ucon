# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for FormulaRegistry.apply — binding-keyed formula resolution.

``apply`` resolves a formula from named operand kinds and returns
``(formula, output_kind, match_kind)``. Aspect propagation is not a
formula concern (the aspect stratum's carry rule owns it — ADR 008);
formulas do kind work only.
"""

from __future__ import annotations

import pytest

from ucon.dimension import LENGTH, MASS, TIME
from ucon.formulas import FormulaNotFound, FormulaRegistry, KindFormula, MatchKind
from ucon.kinds import Kind

ENERGY_DIM = (LENGTH ** 2) * MASS / (TIME ** 2)
NONE_DIM = ENERGY_DIM / ENERGY_DIM

absorbed = Kind("absorbed_dose", dimension=ENERGY_DIM)
w_r = Kind("radiation_weighting_factor", dimension=NONE_DIM)
equivalent = Kind("dose_equivalent", dimension=ENERGY_DIM)


def _weighting(commutative: bool = True) -> KindFormula:
    return KindFormula(
        name="radiation_weighting",
        expression="H = D * w_R",
        input_kinds={"D": absorbed, "w_R": w_r},
        output_kind=equivalent,
        commutative=commutative,
    )


def test_apply_returns_formula_output_kind_and_match_kind():
    reg = FormulaRegistry([_weighting()])
    formula, out_kind, match = reg.apply({"D": absorbed, "w_R": w_r})
    assert formula.name == "radiation_weighting"
    assert out_kind == equivalent
    assert match is MatchKind.EXACT


def test_apply_propagates_formula_not_found():
    reg = FormulaRegistry([_weighting()])
    stray = Kind("stray", dimension=ENERGY_DIM)
    with pytest.raises(FormulaNotFound):
        reg.apply({"a": stray, "b": stray})


def test_apply_empty_inputs_raises_formula_not_found():
    reg = FormulaRegistry([_weighting()])
    with pytest.raises(FormulaNotFound):
        reg.apply({})


def test_apply_lookup_is_positional_in_iteration_order():
    reg = FormulaRegistry([_weighting(commutative=False)])
    formula, out_kind, _ = reg.apply({"D": absorbed, "w_R": w_r})
    assert out_kind == equivalent
    with pytest.raises(FormulaNotFound):
        reg.apply({"w_R": w_r, "D": absorbed})


def test_apply_commutative_two_arg_resolves_in_either_order():
    reg = FormulaRegistry([_weighting(commutative=True)])
    _, out_a, _ = reg.apply({"D": absorbed, "w_R": w_r})
    _, out_b, _ = reg.apply({"w_R": w_r, "D": absorbed})
    assert out_a == out_b == equivalent


def test_apply_does_not_disturb_existing_lookup_surface():
    reg = FormulaRegistry([_weighting()])
    result = reg.resolve(absorbed, w_r)
    assert result.formula.name == "radiation_weighting"
    formula, _, _ = reg.apply({"D": absorbed, "w_R": w_r})
    assert formula is result.formula

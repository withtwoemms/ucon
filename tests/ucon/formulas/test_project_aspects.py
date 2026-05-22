# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for KindFormula.project_aspects.

`project_aspects` is the multiplication-path aspect projector: for each
binding in `input_kinds`, the formula's `aspect_rules` decides whether
the operand's aspect set is unioned into the output (CARRY) or dropped
(CONSUME). Bindings missing from `aspect_rules` default to CARRY (D1).
"""

from __future__ import annotations

from ucon.aspects import AspectRule
from ucon.dimension import LENGTH, MASS, TIME
from ucon.formulas import KindFormula
from ucon.kinds import Kind


ABSORBED_DOSE_DIM = (LENGTH ** 2) / (TIME ** 2)
DIMENSIONLESS = LENGTH / LENGTH


def _radiation_formula(
    aspect_rules: dict | None = None,
) -> tuple[KindFormula, Kind, Kind]:
    D = Kind("absorbed_dose", dimension=ABSORBED_DOSE_DIM)
    wR = Kind("radiation_weighting_factor", dimension=DIMENSIONLESS)
    out = Kind("equivalent_dose", dimension=ABSORBED_DOSE_DIM)
    f = KindFormula(
        name="equivalent_dose",
        expression="D * w_R",
        input_kinds={"D": D, "w_R": wR},
        output_kind=out,
        aspect_rules=aspect_rules or {},
    )
    return f, D, wR


# ---------- CARRY / default ----------


def test_project_aspects_empty_rules_carries_all_inputs():
    f, *_ = _radiation_formula()
    out = f.project_aspects(
        {"D": frozenset({"a"}), "w_R": frozenset({"b"})}
    )
    assert out == frozenset({"a", "b"})


def test_project_aspects_explicit_carry_carries_input():
    f, *_ = _radiation_formula(
        aspect_rules={
            "D": AspectRule.CARRY,
            "w_R": AspectRule.CARRY,
        }
    )
    out = f.project_aspects(
        {"D": frozenset({"a"}), "w_R": frozenset({"b"})}
    )
    assert out == frozenset({"a", "b"})


def test_project_aspects_missing_rule_defaults_to_carry():
    # Only `w_R` declared; `D` defaults to CARRY (per D1).
    f, *_ = _radiation_formula(aspect_rules={"w_R": AspectRule.CARRY})
    out = f.project_aspects(
        {"D": frozenset({"d_only"}), "w_R": frozenset({"w_only"})}
    )
    assert out == frozenset({"d_only", "w_only"})


# ---------- CONSUME ----------


def test_project_aspects_consume_drops_input():
    f, *_ = _radiation_formula(aspect_rules={"w_R": AspectRule.CONSUME})
    out = f.project_aspects(
        {
            "D": frozenset({"signal_summary", "calibrated"}),
            "w_R": frozenset({"ICRP103"}),
        }
    )
    assert out == frozenset({"signal_summary", "calibrated"})


def test_project_aspects_all_consume_yields_empty():
    f, *_ = _radiation_formula(
        aspect_rules={
            "D": AspectRule.CONSUME,
            "w_R": AspectRule.CONSUME,
        }
    )
    out = f.project_aspects(
        {"D": frozenset({"a"}), "w_R": frozenset({"b"})}
    )
    assert out == frozenset()


# ---------- Missing / extra bindings ----------


def test_project_aspects_missing_input_binding_contributes_empty():
    f, *_ = _radiation_formula()
    out = f.project_aspects({"D": frozenset({"a"})})
    # `w_R` not supplied → contributes empty under default CARRY.
    assert out == frozenset({"a"})


def test_project_aspects_empty_inputs_yields_empty():
    f, *_ = _radiation_formula()
    assert f.project_aspects({}) == frozenset()


def test_project_aspects_ignores_rules_for_undeclared_bindings():
    # An `aspect_rules` entry whose key is not a binding in
    # `input_kinds` is silently ignored.
    f, *_ = _radiation_formula(
        aspect_rules={"phantom": AspectRule.CONSUME}
    )
    out = f.project_aspects(
        {"D": frozenset({"a"}), "w_R": frozenset({"b"})}
    )
    assert out == frozenset({"a", "b"})


def test_project_aspects_ignores_extra_aspects_supplied_by_caller():
    # An `inputs` entry whose key is not declared in `input_kinds` is
    # also ignored — the formula's binding declaration is authoritative.
    f, *_ = _radiation_formula()
    out = f.project_aspects(
        {
            "D": frozenset({"a"}),
            "w_R": frozenset({"b"}),
            "extra_caller_aspect": frozenset({"never_propagates"}),
        }
    )
    assert out == frozenset({"a", "b"})


# ---------- Empty operand aspects ----------


def test_project_aspects_empty_operand_aspects_yields_empty_output():
    f, *_ = _radiation_formula()
    out = f.project_aspects({"D": frozenset(), "w_R": frozenset()})
    assert out == frozenset()


# ---------- Return type ----------


def test_project_aspects_returns_frozenset():
    f, *_ = _radiation_formula(aspect_rules={"w_R": AspectRule.CONSUME})
    out = f.project_aspects(
        {"D": frozenset({"a"}), "w_R": frozenset({"b"})}
    )
    assert isinstance(out, frozenset)


# ---------- Purity ----------


def test_project_aspects_does_not_mutate_inputs():
    f, *_ = _radiation_formula(aspect_rules={"w_R": AspectRule.CONSUME})
    d_aspects = frozenset({"a"})
    w_aspects = frozenset({"b"})
    inputs = {"D": d_aspects, "w_R": w_aspects}
    snapshot = dict(inputs)
    _ = f.project_aspects(inputs)
    assert inputs == snapshot
    assert inputs["D"] is d_aspects
    assert inputs["w_R"] is w_aspects

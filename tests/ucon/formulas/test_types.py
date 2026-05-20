# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for the KindFormula dataclass."""

from __future__ import annotations

import pytest

from ucon.dimension import LENGTH, MASS, TIME
from ucon.formulas import AspectRule, KindFormula
from ucon.kinds import Kind


ENERGY_DIM = (LENGTH ** 2) * MASS / (TIME ** 2)
ABSORBED_DOSE_DIM = (LENGTH ** 2) / (TIME ** 2)
DIMENSIONLESS = LENGTH / LENGTH


def _radiation_inputs():
    D = Kind("absorbed_dose", dimension=ABSORBED_DOSE_DIM)
    wR = Kind("radiation_weighting_factor", dimension=DIMENSIONLESS)
    out = Kind("equivalent_dose", dimension=ABSORBED_DOSE_DIM)
    return D, wR, out


def test_kindformula_minimal_construction():
    D, wR, out = _radiation_inputs()
    f = KindFormula(
        name="radiation_weighting",
        expression="D * w_R",
        input_kinds={"D": D, "w_R": wR},
        output_kind=out,
    )
    assert f.name == "radiation_weighting"
    assert f.expression == "D * w_R"
    assert f.input_kinds == {"D": D, "w_R": wR}
    assert f.output_kind == out
    assert f.aspect_rules == {}
    assert f.generalizes is False
    assert f.commutative is True
    assert f.notes == ""


def test_kindformula_with_aspect_rules():
    D, wR, out = _radiation_inputs()
    f = KindFormula(
        name="radiation_weighting",
        expression="D * w_R",
        input_kinds={"D": D, "w_R": wR},
        output_kind=out,
        aspect_rules={"signal_summary": AspectRule.CONSUME},
    )
    assert f.aspect_rules == {"signal_summary": AspectRule.CONSUME}


def test_kindformula_input_kind_tuple_preserves_insertion_order():
    D, wR, out = _radiation_inputs()
    f = KindFormula(
        name="radiation_weighting",
        expression="D * w_R",
        input_kinds={"D": D, "w_R": wR},
        output_kind=out,
    )
    assert f.input_kind_tuple() == (D, wR)

    g = KindFormula(
        name="reversed",
        expression="w_R * D",
        input_kinds={"w_R": wR, "D": D},
        output_kind=out,
    )
    assert g.input_kind_tuple() == (wR, D)


def test_kindformula_equality_keys_off_name_only():
    D, wR, out = _radiation_inputs()
    a = KindFormula(
        name="f",
        expression="D * w_R",
        input_kinds={"D": D, "w_R": wR},
        output_kind=out,
    )
    b = KindFormula(
        name="f",
        expression="different",
        input_kinds={"w_R": wR, "D": D},
        output_kind=out,
        commutative=False,
        notes="different too",
    )
    c = KindFormula(
        name="g",
        expression="D * w_R",
        input_kinds={"D": D, "w_R": wR},
        output_kind=out,
    )
    assert a == b
    assert hash(a) == hash(b)
    assert a != c


def test_kindformula_is_frozen():
    D, wR, out = _radiation_inputs()
    f = KindFormula(
        name="f",
        expression="D * w_R",
        input_kinds={"D": D, "w_R": wR},
        output_kind=out,
    )
    with pytest.raises(Exception):
        f.name = "tampered"  # type: ignore[misc]


def test_kindformula_repr_renders_name():
    D, wR, out = _radiation_inputs()
    f = KindFormula(
        name="radiation_weighting",
        expression="D * w_R",
        input_kinds={"D": D, "w_R": wR},
        output_kind=out,
    )
    assert repr(f) == "KindFormula('radiation_weighting')"


def test_aspect_rule_enum_string_values():
    assert AspectRule("consume") is AspectRule.CONSUME
    assert AspectRule("carry") is AspectRule.CARRY


def test_kindformula_notes_field_is_freeform():
    D, wR, out = _radiation_inputs()
    f = KindFormula(
        name="radiation_weighting",
        expression="D * w_R",
        input_kinds={"D": D, "w_R": wR},
        output_kind=out,
        notes="w_R per ICRP 103; caller selects.",
    )
    assert "ICRP" in f.notes

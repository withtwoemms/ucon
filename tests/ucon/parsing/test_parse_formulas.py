# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for the [[formulas]] TOML parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from ucon.formulas import AspectRule, FormulaNotFound, FormulaRegistry
from ucon.kinds import KindNotFound
from ucon.parsing import (
    load_formulas_file,
    load_kinds_file,
    parse_formulas_payload,
    parse_kinds_payload,
)


FIXTURES = Path(__file__).parent.parent / "formulas" / "fixtures"


# --------- happy paths ---------

def test_load_radiation_weighting():
    # The fixture contains both [[kinds]] and [[formulas]] in one file;
    # each loader consults its own section.
    lat = load_kinds_file(FIXTURES / "radiation_weighting.ucon.toml")
    reg = load_formulas_file(
        FIXTURES / "radiation_weighting.ucon.toml", lattice=lat
    )
    assert isinstance(reg, FormulaRegistry)
    assert len(reg) == 1
    f = reg.get("radiation_weighting")
    assert f.expression == "D * w_R"
    assert f.output_kind.name == "equivalent_dose"
    assert set(f.input_kinds.keys()) == {"D", "w_R"}
    assert f.commutative is True
    assert "ICRP" in f.notes


def test_load_radiation_weighting_parses_aspect_rules():
    lat = load_kinds_file(FIXTURES / "radiation_weighting.ucon.toml")
    reg = load_formulas_file(
        FIXTURES / "radiation_weighting.ucon.toml", lattice=lat
    )
    f = reg.get("radiation_weighting")
    assert f.aspect_rules == {"w_R": AspectRule.CONSUME}


def test_load_radiation_weighting_commutative_lookup_both_orders():
    lat = load_kinds_file(FIXTURES / "radiation_weighting.ucon.toml")
    reg = load_formulas_file(
        FIXTURES / "radiation_weighting.ucon.toml", lattice=lat
    )
    D = lat.get("absorbed_dose")
    wR = lat.get("radiation_weighting_factor")
    assert reg.lookup(D, wR).name == "radiation_weighting"
    assert reg.lookup(wR, D).name == "radiation_weighting"


def test_load_cycles_to_frequency_non_commutative():
    lat = load_kinds_file(FIXTURES / "cycles_to_frequency.ucon.toml")
    reg = load_formulas_file(
        FIXTURES / "cycles_to_frequency.ucon.toml", lattice=lat
    )
    f = reg.get("cycles_to_frequency")
    assert f.commutative is False
    N = lat.get("cycle_count")
    t = lat.get("duration")
    assert reg.lookup(N, t).name == "cycles_to_frequency"
    with pytest.raises(FormulaNotFound):
        reg.lookup(t, N)


# --------- error paths ---------

def test_missing_name_raises():
    payload = {"formulas": [{"expression": "x", "output_kind": "y"}]}
    lat = parse_kinds_payload({})
    with pytest.raises(ValueError, match="missing 'name'"):
        parse_formulas_payload(payload, lattice=lat)


def test_missing_expression_raises():
    payload = {"formulas": [{"name": "f", "output_kind": "y"}]}
    lat = parse_kinds_payload({})
    with pytest.raises(ValueError, match="missing 'expression'"):
        parse_formulas_payload(payload, lattice=lat)


def test_missing_output_kind_raises():
    payload = {"formulas": [{"name": "f", "expression": "x"}]}
    lat = parse_kinds_payload({})
    with pytest.raises(ValueError, match="missing 'output_kind'"):
        parse_formulas_payload(payload, lattice=lat)


def test_unknown_output_kind_raises_kind_not_found():
    lat = parse_kinds_payload({
        "kinds": [{"name": "a", "dimension": "1"}]
    })
    payload = {
        "formulas": [
            {"name": "f", "expression": "x", "output_kind": "missing",
             "inputs": {"x": {"kind": "a"}}}
        ]
    }
    with pytest.raises(KindNotFound):
        parse_formulas_payload(payload, lattice=lat)


def test_unknown_input_kind_raises_kind_not_found():
    lat = parse_kinds_payload({
        "kinds": [{"name": "a", "dimension": "1"}]
    })
    payload = {
        "formulas": [
            {"name": "f", "expression": "x", "output_kind": "a",
             "inputs": {"x": {"kind": "missing"}}}
        ]
    }
    with pytest.raises(KindNotFound):
        parse_formulas_payload(payload, lattice=lat)


def test_input_without_kind_field_raises():
    lat = parse_kinds_payload({
        "kinds": [{"name": "a", "dimension": "1"}]
    })
    payload = {
        "formulas": [
            {"name": "f", "expression": "x", "output_kind": "a",
             "inputs": {"x": {"not_kind": "a"}}}
        ]
    }
    with pytest.raises(ValueError, match=r"must be \{ kind"):
        parse_formulas_payload(payload, lattice=lat)


def test_unrecognized_aspect_rule_raises():
    lat = parse_kinds_payload({
        "kinds": [{"name": "a", "dimension": "1"}]
    })
    payload = {
        "formulas": [
            {
                "name": "f",
                "expression": "x",
                "output_kind": "a",
                "inputs": {"x": {"kind": "a"}},
                "aspect_rules": {"signal": "bogus"},
            }
        ]
    }
    with pytest.raises(ValueError, match="unrecognized value"):
        parse_formulas_payload(payload, lattice=lat)


def test_formulas_must_be_array_of_tables():
    lat = parse_kinds_payload({})
    with pytest.raises(ValueError, match="array of tables"):
        parse_formulas_payload({"formulas": "not a list"}, lattice=lat)


def test_empty_payload_yields_empty_registry():
    lat = parse_kinds_payload({})
    reg = parse_formulas_payload({}, lattice=lat)
    assert len(reg) == 0


def test_defaults_applied_when_optional_fields_missing():
    lat = parse_kinds_payload({
        "kinds": [{"name": "a", "dimension": "1"}]
    })
    payload = {
        "formulas": [
            {"name": "f", "expression": "x", "output_kind": "a",
             "inputs": {"x": {"kind": "a"}}}
        ]
    }
    reg = parse_formulas_payload(payload, lattice=lat)
    f = reg.get("f")
    assert f.aspect_rules == {}
    assert f.generalizes is False
    assert f.commutative is True
    assert f.notes == ""


# --------- end-to-end: TOML -> apply ---------


def _load_aspect_rules_fixture():
    lat = load_kinds_file(FIXTURES / "aspect_rules.ucon.toml")
    reg = load_formulas_file(
        FIXTURES / "aspect_rules.ucon.toml", lattice=lat
    )
    return lat, reg


def test_e2e_sparse_rules_consume_binding_carry_default():
    """Sparse rules: w_R=CONSUME, D defaults to CARRY."""
    lat, reg = _load_aspect_rules_fixture()
    D = lat.get("absorbed_dose")
    wR = lat.get("radiation_weighting_factor")
    formula, out_kind, out_aspects, _ = reg.apply({
        "D":   (D,  frozenset({"signal_summary"})),
        "w_R": (wR, frozenset({"calibrated"})),
    })
    assert formula.name == "equivalent_dose"
    assert out_kind.name == "equivalent_dose"
    # D carried, w_R consumed
    assert out_aspects == frozenset({"signal_summary"})


def test_e2e_fully_declared_rules_mixed_carry_and_consume():
    """Fully-declared rules: H=CARRY, w_T=CONSUME."""
    lat, reg = _load_aspect_rules_fixture()
    H = lat.get("equivalent_dose")
    wT = lat.get("tissue_weighting_factor")
    formula, out_kind, out_aspects, _ = reg.apply({
        "H":   (H,  frozenset({"signal_summary", "calibrated"})),
        "w_T": (wT, frozenset({"ICRP103"})),
    })
    assert formula.name == "effective_dose"
    assert out_kind.name == "effective_dose"
    # H carried, w_T consumed
    assert out_aspects == frozenset({"signal_summary", "calibrated"})


def test_e2e_absent_rules_carry_all():
    """Absent aspect_rules: every binding defaults to CARRY."""
    lat, reg = _load_aspect_rules_fixture()
    H = lat.get("equivalent_dose")
    formula, out_kind, out_aspects, _ = reg.apply({
        "H_a": (H, frozenset({"a_tag"})),
        "H_b": (H, frozenset({"b_tag"})),
    })
    assert formula.name == "dose_sum"
    assert out_kind.name == "equivalent_dose"
    # Both carried — union
    assert out_aspects == frozenset({"a_tag", "b_tag"})


def test_e2e_empty_aspects_propagate_cleanly():
    """Apply with empty aspect sets returns empty output."""
    lat, reg = _load_aspect_rules_fixture()
    D = lat.get("absorbed_dose")
    wR = lat.get("radiation_weighting_factor")
    _, _, out_aspects, _ = reg.apply({
        "D":   (D,  frozenset()),
        "w_R": (wR, frozenset()),
    })
    assert out_aspects == frozenset()

# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for the namespace rewriter (A6 of the aspect stratum, #285).

Full qualification (``pkg:name`` for every package-declared kind and
aspect, aliases included) is the namespacing rule; the rewriter
recovers the ergonomics. It is a pure ``dict → dict`` transformation
that consults nothing loaded — so it cannot shadow — and it consumes
the ``namespace`` key, which makes it idempotent and its output equal
to the hand-qualified file.
"""

from __future__ import annotations

import copy

import pytest

from ucon.parsing import rewrite_namespace


def _payload() -> dict:
    return {
        "package": {"name": "radsafe", "namespace": "radsafe"},
        "kinds": [
            {"name": "dose_equivalent", "dimension": "L²/T²",
             "aliases": ["H"]},
            {"name": "ambient_dose", "dimension": "L²/T²",
             "parent": "dose_equivalent"},
            {"name": "exotic_energy", "dimension": "L²·M/T²",
             "parent": "@energy"},
        ],
        "aspects": [
            {"name": "weighting_standard",
             "applies_to": ["dose_equivalent", "@energy"]},
            {"name": "icrp103", "parent": "weighting_standard"},
            {"name": "coverage", "applies_to": ["*"]},
        ],
        "formulas": [
            {"name": "weighting", "expression": "D * w",
             "output_kind": "dose_equivalent",
             "inputs": {"D": {"kind": "@absorbed_dose"},
                        "w": {"kind": "weighting_factor"}}},
        ],
        "constants": [
            {"symbol": "H_ref", "name": "reference dose", "value": 1.0,
             "unit": "Sv", "kind": "dose_equivalent"},
        ],
    }


# --------- qualification ---------

def test_kind_names_parents_and_aliases_qualified():
    out = rewrite_namespace(_payload())
    names = [k["name"] for k in out["kinds"]]
    assert names == ["radsafe:dose_equivalent", "radsafe:ambient_dose",
                     "radsafe:exotic_energy"]
    assert out["kinds"][1]["parent"] == "radsafe:dose_equivalent"
    # aliases included — an unqualified alias would collide across
    # packages exactly the way an unqualified name would
    assert out["kinds"][0]["aliases"] == ["radsafe:H"]


def test_aspect_names_parents_and_applies_to_qualified():
    out = rewrite_namespace(_payload())
    assert out["aspects"][0]["name"] == "radsafe:weighting_standard"
    assert out["aspects"][1]["parent"] == "radsafe:weighting_standard"
    assert out["aspects"][0]["applies_to"] == [
        "radsafe:dose_equivalent", "energy"]


def test_wildcard_applies_to_untouched():
    out = rewrite_namespace(_payload())
    assert out["aspects"][2]["applies_to"] == ["*"]


def test_formula_kind_references_qualified_bindings_untouched():
    out = rewrite_namespace(_payload())
    f = out["formulas"][0]
    assert f["output_kind"] == "radsafe:dose_equivalent"
    assert set(f["inputs"]) == {"D", "w"}          # binding names local
    assert f["inputs"]["D"]["kind"] == "absorbed_dose"   # root escape
    assert f["inputs"]["w"]["kind"] == "radsafe:weighting_factor"


def test_constant_kind_reference_qualified():
    out = rewrite_namespace(_payload())
    assert out["constants"][0]["kind"] == "radsafe:dose_equivalent"


def test_root_escape_strips_at_sign():
    out = rewrite_namespace(_payload())
    assert out["kinds"][2]["parent"] == "energy"


def test_already_qualified_names_untouched():
    payload = _payload()
    payload["kinds"][1]["parent"] = "pharma:dose"   # explicit cross-package
    out = rewrite_namespace(payload)
    assert out["kinds"][1]["parent"] == "pharma:dose"


def test_units_and_edges_pass_through():
    payload = _payload()
    payload["units"] = [{"name": "sievert", "dimension": "specific_energy"}]
    payload["edges"] = [{"src": "sievert", "dst": "gray", "factor": 1.0}]
    out = rewrite_namespace(payload)
    assert out["units"] == payload["units"]
    assert out["edges"] == payload["edges"]


# --------- the vetted properties ---------

def test_idempotent():
    """The namespace key is consumed, so a second application is the
    identity."""
    once = rewrite_namespace(_payload())
    assert "namespace" not in once["package"]
    assert rewrite_namespace(once) == once


def test_output_equals_hand_qualified_file():
    """Rewriting the shorthand file yields exactly the dict the
    hand-qualified file parses to."""
    hand = {
        "package": {"name": "radsafe"},
        "kinds": [
            {"name": "radsafe:dose_equivalent", "dimension": "L²/T²",
             "aliases": ["radsafe:H"]},
            {"name": "radsafe:ambient_dose", "dimension": "L²/T²",
             "parent": "radsafe:dose_equivalent"},
            {"name": "radsafe:exotic_energy", "dimension": "L²·M/T²",
             "parent": "energy"},
        ],
        "aspects": [
            {"name": "radsafe:weighting_standard",
             "applies_to": ["radsafe:dose_equivalent", "energy"]},
            {"name": "radsafe:icrp103",
             "parent": "radsafe:weighting_standard"},
            {"name": "radsafe:coverage", "applies_to": ["*"]},
        ],
        "formulas": [
            {"name": "weighting", "expression": "D * w",
             "output_kind": "radsafe:dose_equivalent",
             "inputs": {"D": {"kind": "absorbed_dose"},
                        "w": {"kind": "radsafe:weighting_factor"}}},
        ],
        "constants": [
            {"symbol": "H_ref", "name": "reference dose", "value": 1.0,
             "unit": "Sv", "kind": "radsafe:dose_equivalent"},
        ],
    }
    assert rewrite_namespace(_payload()) == hand


def test_pure_input_not_mutated():
    payload = _payload()
    snapshot = copy.deepcopy(payload)
    rewrite_namespace(payload)
    assert payload == snapshot


def test_no_namespace_is_identity():
    payload = _payload()
    del payload["package"]["namespace"]
    assert rewrite_namespace(payload) is payload


# --------- namespace value validation ---------

@pytest.mark.parametrize("bad", ["", 7, "a:b", "a@b"])
def test_invalid_namespace_values_raise(bad):
    payload = {"package": {"namespace": bad}}
    with pytest.raises(ValueError):
        rewrite_namespace(payload)

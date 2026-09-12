# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for the [[aspects]] TOML parser (A5 of the aspect stratum, #296)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ucon.aspects import Aspect, AspectError, AspectForest, MultPolicy
from ucon.kinds import JoinPolicy, KindError
from ucon.parsing import load_aspects_file, parse_aspects_payload


FIXTURES = Path(__file__).parent.parent / "aspects" / "fixtures"


# --------- happy paths ---------

def test_load_radsafe_forest():
    forest = load_aspects_file(FIXTURES / "radsafe.ucon.toml")
    assert isinstance(forest, AspectForest)
    assert len(forest) == 8
    assert {a.name for a in forest.families()} == {
        "weighting_standard", "procedure", "coverage"}


def test_declaration_order_is_free():
    """The fixture declares icrp103 before its parent; the parser
    builds in dependency order regardless of file order."""
    forest = load_aspects_file(FIXTURES / "radsafe.ucon.toml")
    icrp103 = forest.get("icrp103")
    assert icrp103.parent is forest.get("weighting_standard")


def test_defaults_applied():
    forest = load_aspects_file(FIXTURES / "radsafe.ucon.toml")
    ws = forest.get("weighting_standard")
    assert ws.join_policy is JoinPolicy.REFUSE      # aspect default
    assert ws.multiplication_policy is MultPolicy.CARRY
    assert ws.applies_to == frozenset({"dose_equivalent"})
    proc = forest.get("procedure")
    assert proc.join_policy is JoinPolicy.LCA       # declared override
    assert forest.get("coverage").applies_to == frozenset({"*"})


def test_parsed_forest_joins_like_a_built_one():
    """The vetted semantics hold on parsed nodes."""
    forest = load_aspects_file(FIXTURES / "radsafe.ucon.toml")
    joined = forest.join(forest.get("measured"), forest.get("simulated"))
    assert joined is forest.get("procedure")


def test_empty_payload_yields_empty_forest():
    forest = parse_aspects_payload({})
    assert len(forest) == 0


# --------- schema errors (ValueError) ---------

def test_missing_name_raises():
    with pytest.raises(ValueError, match="missing 'name'"):
        parse_aspects_payload({"aspects": [{"parent": "x"}]})


def test_non_list_section_raises():
    with pytest.raises(ValueError, match="array of tables"):
        parse_aspects_payload({"aspects": {"name": "x"}})


def test_unrecognized_join_policy_raises():
    with pytest.raises(ValueError, match="unrecognized join_policy"):
        parse_aspects_payload(
            {"aspects": [{"name": "x", "join_policy": "maybe"}]})


def test_unrecognized_multiplication_policy_raises():
    with pytest.raises(ValueError, match="unrecognized multiplication_policy"):
        parse_aspects_payload(
            {"aspects": [{"name": "x", "multiplication_policy": "drop"}]})


def test_applies_to_string_raises():
    """A bare string is a likely authoring mistake; require a list."""
    with pytest.raises(ValueError, match="list of strings"):
        parse_aspects_payload(
            {"aspects": [{"name": "x", "applies_to": "dose_equivalent"}]})


# --------- semantic errors (AspectError, never Kind-named) ---------

def test_duplicate_name_raises_aspect_error():
    with pytest.raises(AspectError, match="Duplicate aspect name"):
        parse_aspects_payload(
            {"aspects": [{"name": "x"}, {"name": "x"}]})


def test_orphan_parent_raises_aspect_error():
    with pytest.raises(AspectError, match="not declared"):
        parse_aspects_payload(
            {"aspects": [{"name": "child", "parent": "ghost"}]})


def test_parent_cycle_raises_aspect_error():
    with pytest.raises(AspectError, match="cycle"):
        parse_aspects_payload({"aspects": [
            {"name": "a", "parent": "b"},
            {"name": "b", "parent": "a"},
        ]})


def test_root_only_applies_to_on_child_raises():
    with pytest.raises(AspectError, match="root-only"):
        parse_aspects_payload({"aspects": [
            {"name": "family"},
            {"name": "child", "parent": "family",
             "applies_to": ["dose_equivalent"]},
        ]})


def test_root_only_multiplication_policy_on_child_raises():
    with pytest.raises(AspectError, match="root-only"):
        parse_aspects_payload({"aspects": [
            {"name": "family"},
            {"name": "child", "parent": "family",
             "multiplication_policy": "carry"},
        ]})


def test_no_kind_named_exception_leaks():
    """The rewrap boundary holds through the parser."""
    cases = [
        {"aspects": [{"name": "x"}, {"name": "x"}]},
        {"aspects": [{"name": "child", "parent": "ghost"}]},
    ]
    for payload in cases:
        try:
            parse_aspects_payload(payload)
        except Exception as exc:
            assert isinstance(exc, AspectError)
            assert not isinstance(exc, KindError)

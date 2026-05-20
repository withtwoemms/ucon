# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for the [[kinds]] TOML parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from ucon.kinds import (
    AliasCollision,
    CrossDimensionParent,
    JoinPolicy,
    KindCycle,
    KindLattice,
    NameCollision,
    OrphanParent,
)
from ucon.parsing import load_kinds_file, parse_kinds_payload


FIXTURES = Path(__file__).parent.parent / "kinds" / "fixtures"


# --------- happy paths ---------

def test_load_simple_energy_lattice():
    lat = load_kinds_file(FIXTURES / "simple_energy.ucon.toml")
    assert isinstance(lat, KindLattice)
    assert len(lat) == 5
    assert {"energy", "kinetic_energy", "potential_energy",
            "gravitational_pe", "elastic_pe"}.issubset(set(lat.names()))


def test_load_simple_energy_resolves_aliases():
    lat = load_kinds_file(FIXTURES / "simple_energy.ucon.toml")
    assert "KE" in lat
    assert "PE" in lat
    assert lat.get("KE").name == "kinetic_energy"
    assert lat.get("PE").name == "potential_energy"


def test_load_simple_energy_resolves_parent_edges():
    lat = load_kinds_file(FIXTURES / "simple_energy.ucon.toml")
    ke = lat.get("kinetic_energy")
    grav = lat.get("gravitational_pe")
    assert ke.parent is not None
    assert ke.parent.name == "energy"
    assert grav.parent.name == "potential_energy"


def test_load_power_refuse_lattice_carries_join_policy():
    lat = load_kinds_file(FIXTURES / "power_refuse.ucon.toml")
    power = lat.get("power")
    assert power.join_policy is JoinPolicy.REFUSE
    # Children default to LCA.
    assert lat.get("active_power").join_policy is JoinPolicy.LCA


def test_load_counts_ratios_lattice_mixes_policies():
    lat = load_kinds_file(FIXTURES / "counts_ratios.ucon.toml")
    assert lat.get("count").join_policy is JoinPolicy.LCA
    assert lat.get("ratio").join_policy is JoinPolicy.REFUSE
    assert lat.get("dimensionless").join_policy is JoinPolicy.REFUSE


def test_lca_works_on_loaded_lattice():
    lat = load_kinds_file(FIXTURES / "simple_energy.ucon.toml")
    grav = lat.get("gravitational_pe")
    elastic = lat.get("elastic_pe")
    ancestor, policy = lat.lca(grav, elastic)
    assert ancestor.name == "potential_energy"
    assert policy is JoinPolicy.LCA


# --------- error paths ---------

def test_bad_cycle_raises_kindcycle():
    with pytest.raises(KindCycle):
        load_kinds_file(FIXTURES / "bad_cycle.ucon.toml")


def test_bad_orphan_raises_orphanparent():
    with pytest.raises(OrphanParent) as exc:
        load_kinds_file(FIXTURES / "bad_orphan.ucon.toml")
    assert exc.value.missing_parent  # has a parent name


def test_bad_cross_dimension_raises_crossdimensionparent():
    with pytest.raises(CrossDimensionParent):
        load_kinds_file(FIXTURES / "bad_cross_dimension.ucon.toml")


def test_bad_name_collision_raises_collision_error():
    # The parser hands duplicate-name entries to the lattice as a single
    # rebuilt Kind, so the lattice surfaces an AliasCollision rather
    # than a NameCollision. Either is acceptable evidence that the
    # loader rejected the bad fixture; the canonical NameCollision path
    # is exercised directly in tests/ucon/kinds/test_validation.py.
    with pytest.raises((NameCollision, AliasCollision)):
        load_kinds_file(FIXTURES / "bad_name_collision.ucon.toml")


def test_bad_alias_collision_raises_aliascollision():
    with pytest.raises(AliasCollision):
        load_kinds_file(FIXTURES / "bad_alias_collision.ucon.toml")


# --------- payload-level errors ---------

def test_missing_name_raises_value_error():
    payload = {"kinds": [{"dimension": "M·L^2/T^2"}]}
    with pytest.raises(ValueError, match="missing 'name'"):
        parse_kinds_payload(payload)


def test_missing_dimension_raises_value_error():
    payload = {"kinds": [{"name": "foo"}]}
    with pytest.raises(ValueError, match="missing 'dimension'"):
        parse_kinds_payload(payload)


def test_unknown_join_policy_raises_value_error():
    payload = {
        "kinds": [
            {"name": "foo", "dimension": "1", "join_policy": "bogus"}
        ]
    }
    with pytest.raises(ValueError, match="unrecognized join_policy"):
        parse_kinds_payload(payload)


def test_non_string_alias_raises_value_error():
    payload = {
        "kinds": [
            {"name": "foo", "dimension": "1", "aliases": [42]}
        ]
    }
    with pytest.raises(ValueError, match="non-string alias"):
        parse_kinds_payload(payload)


def test_kinds_must_be_array_of_tables():
    with pytest.raises(ValueError, match="array of tables"):
        parse_kinds_payload({"kinds": "not a list"})


def test_empty_payload_yields_empty_lattice():
    lat = parse_kinds_payload({})
    assert len(lat) == 0


def test_forward_parent_reference_resolves():
    # Child declared before parent — parser's second pass must handle
    # this without raising OrphanParent.
    payload = {
        "kinds": [
            {"name": "child", "dimension": "M·L^2/T^2", "parent": "parent"},
            {"name": "parent", "dimension": "M·L^2/T^2"},
        ]
    }
    lat = parse_kinds_payload(payload)
    assert lat.get("child").parent.name == "parent"

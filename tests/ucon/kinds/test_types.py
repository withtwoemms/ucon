# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for the Kind dataclass."""

from __future__ import annotations

import pytest

from ucon.dimension import LENGTH, MASS, TIME
from ucon.kinds import JoinPolicy, Kind


ENERGY_DIM = (LENGTH ** 2) * MASS / (TIME ** 2)


def test_kind_minimal_construction():
    k = Kind("energy", dimension=ENERGY_DIM)
    assert k.name == "energy"
    assert k.dimension == ENERGY_DIM
    assert k.parent is None
    assert k.join_policy is JoinPolicy.LCA
    assert k.aliases == ()


def test_kind_with_parent_and_aliases():
    parent = Kind("energy", dimension=ENERGY_DIM)
    child = Kind(
        "kinetic_energy",
        dimension=ENERGY_DIM,
        parent=parent,
        aliases=("KE",),
    )
    assert child.parent is parent
    assert child.aliases == ("KE",)


def test_kind_join_policy_refuse():
    k = Kind("power", dimension=ENERGY_DIM, join_policy=JoinPolicy.REFUSE)
    assert k.join_policy is JoinPolicy.REFUSE


def test_kind_equality_keys_off_name_only():
    a = Kind("foo", dimension=ENERGY_DIM)
    b = Kind("foo", dimension=ENERGY_DIM, join_policy=JoinPolicy.REFUSE)
    c = Kind("bar", dimension=ENERGY_DIM)
    assert a == b
    assert a != c
    assert hash(a) == hash(b)


def test_kind_is_frozen():
    k = Kind("energy", dimension=ENERGY_DIM)
    with pytest.raises(Exception):
        k.name = "tampered"  # type: ignore[misc]


def test_kind_repr_includes_parent():
    parent = Kind("energy", dimension=ENERGY_DIM)
    child = Kind("kinetic_energy", dimension=ENERGY_DIM, parent=parent)
    assert "parent='energy'" in repr(child)
    assert "parent" not in repr(parent)


def test_join_policy_string_values():
    assert JoinPolicy("lca") is JoinPolicy.LCA
    assert JoinPolicy("refuse") is JoinPolicy.REFUSE

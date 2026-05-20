# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for LCA computation and join policy enforcement."""

from __future__ import annotations

import pytest

from ucon.dimension import LENGTH, MASS, TIME
from ucon.kinds import (
    JoinPolicy,
    JoinRefused,
    Kind,
    KindLattice,
    lca as module_lca,
)


ENERGY_DIM = (LENGTH ** 2) * MASS / (TIME ** 2)
POWER_DIM = (LENGTH ** 2) * MASS / (TIME ** 3)


def test_lca_siblings_returns_parent():
    energy = Kind("energy", dimension=ENERGY_DIM)
    ke = Kind("kinetic_energy", dimension=ENERGY_DIM, parent=energy)
    pe = Kind("potential_energy", dimension=ENERGY_DIM, parent=energy)
    lat = KindLattice([energy, ke, pe])
    ancestor, policy = lat.lca(ke, pe)
    assert ancestor == energy
    assert policy is JoinPolicy.LCA


def test_lca_child_and_ancestor_returns_ancestor():
    energy = Kind("energy", dimension=ENERGY_DIM)
    ke = Kind("kinetic_energy", dimension=ENERGY_DIM, parent=energy)
    lat = KindLattice([energy, ke])
    ancestor, _ = lat.lca(ke, energy)
    assert ancestor == energy


def test_lca_same_kind_returns_self():
    energy = Kind("energy", dimension=ENERGY_DIM)
    lat = KindLattice([energy])
    ancestor, _ = lat.lca(energy, energy)
    assert ancestor == energy


def test_lca_across_multiple_levels():
    energy = Kind("energy", dimension=ENERGY_DIM)
    pe = Kind("potential_energy", dimension=ENERGY_DIM, parent=energy)
    grav = Kind("gravitational_pe", dimension=ENERGY_DIM, parent=pe)
    elastic = Kind("elastic_pe", dimension=ENERGY_DIM, parent=pe)
    ke = Kind("kinetic_energy", dimension=ENERGY_DIM, parent=energy)
    lat = KindLattice([energy, pe, grav, elastic, ke])

    ancestor, _ = lat.lca(grav, elastic)
    assert ancestor == pe

    ancestor, _ = lat.lca(grav, ke)
    assert ancestor == energy


def test_lca_disjoint_trees_raises_value_error():
    energy = Kind("energy", dimension=ENERGY_DIM)
    power = Kind("power", dimension=POWER_DIM)
    lat = KindLattice([energy, power])
    with pytest.raises(ValueError, match="no common ancestor"):
        lat.lca(energy, power)


def test_lca_surfaces_refuse_policy():
    power = Kind("power", dimension=POWER_DIM, join_policy=JoinPolicy.REFUSE)
    active = Kind("active_power", dimension=POWER_DIM, parent=power)
    reactive = Kind("reactive_power", dimension=POWER_DIM, parent=power)
    lat = KindLattice([power, active, reactive])
    _, policy = lat.lca(active, reactive)
    assert policy is JoinPolicy.REFUSE


def test_join_short_circuits_on_equal_kinds():
    energy = Kind("energy", dimension=ENERGY_DIM)
    lat = KindLattice([energy])
    assert lat.join(energy, energy) == energy


def test_join_lifts_to_lca():
    energy = Kind("energy", dimension=ENERGY_DIM)
    ke = Kind("kinetic_energy", dimension=ENERGY_DIM, parent=energy)
    pe = Kind("potential_energy", dimension=ENERGY_DIM, parent=energy)
    lat = KindLattice([energy, ke, pe])
    assert lat.join(ke, pe) == energy


def test_join_raises_on_refuse_policy():
    power = Kind("power", dimension=POWER_DIM, join_policy=JoinPolicy.REFUSE)
    active = Kind("active_power", dimension=POWER_DIM, parent=power)
    reactive = Kind("reactive_power", dimension=POWER_DIM, parent=power)
    lat = KindLattice([power, active, reactive])
    with pytest.raises(JoinRefused) as exc:
        lat.join(active, reactive)
    assert exc.value.left == active
    assert exc.value.right == reactive
    assert exc.value.parent == power


def test_module_level_lca_delegates_to_lattice():
    energy = Kind("energy", dimension=ENERGY_DIM)
    ke = Kind("kinetic_energy", dimension=ENERGY_DIM, parent=energy)
    pe = Kind("potential_energy", dimension=ENERGY_DIM, parent=energy)
    lat = KindLattice([energy, ke, pe])
    ancestor, policy = module_lca(ke, pe, lattice=lat)
    assert ancestor == energy
    assert policy is JoinPolicy.LCA

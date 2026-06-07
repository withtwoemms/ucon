# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for KindLattice structure: lookup, ancestors, descendant tests."""

from __future__ import annotations

import pytest

from ucon.dimension import LENGTH, MASS, TIME
from ucon.kinds import (
    Kind,
    KindLattice,
    KindNotFound,
)


ENERGY_DIM = (LENGTH ** 2) * MASS / (TIME ** 2)


def _energy_lattice():
    energy = Kind("energy", dimension=ENERGY_DIM)
    ke = Kind("kinetic_energy", dimension=ENERGY_DIM, parent=energy)
    pe = Kind("potential_energy", dimension=ENERGY_DIM, parent=energy, aliases=("PE",))
    grav = Kind("gravitational_pe", dimension=ENERGY_DIM, parent=pe)
    return KindLattice([energy, ke, pe, grav]), energy, ke, pe, grav


def test_lattice_contains():
    lat, energy, *_ = _energy_lattice()
    assert "energy" in lat
    assert "PE" in lat              # alias resolves
    assert "missing" not in lat


def test_lattice_len_and_iter():
    lat, *_ = _energy_lattice()
    assert len(lat) == 4
    names = {k.name for k in lat}
    assert names == {"energy", "kinetic_energy", "potential_energy", "gravitational_pe"}


def test_lattice_get_by_primary_name():
    lat, energy, *_ = _energy_lattice()
    assert lat.get("energy") is energy


def test_lattice_get_by_alias():
    lat, _, _, pe, _ = _energy_lattice()
    assert lat.get("PE") is pe


def test_lattice_get_unknown_raises():
    lat, *_ = _energy_lattice()
    with pytest.raises(KindNotFound) as exc:
        lat.get("entropy")
    assert exc.value.name == "entropy"


def test_lattice_names_returns_primary_only():
    lat, *_ = _energy_lattice()
    names = lat.names()
    assert "PE" not in names
    assert "potential_energy" in names


def test_lattice_ancestors_root_first_walk():
    lat, energy, _, pe, grav = _energy_lattice()
    chain = lat.ancestors(grav)
    assert [k.name for k in chain] == ["gravitational_pe", "potential_energy", "energy"]


def test_lattice_ancestors_for_root_returns_self():
    lat, energy, *_ = _energy_lattice()
    assert lat.ancestors(energy) == [energy]


def test_lattice_is_descendant_direct():
    lat, energy, ke, _, _ = _energy_lattice()
    assert lat.is_descendant(ke, energy) is True


def test_lattice_is_descendant_transitive():
    lat, energy, _, _, grav = _energy_lattice()
    assert lat.is_descendant(grav, energy) is True


def test_lattice_is_descendant_self():
    lat, energy, *_ = _energy_lattice()
    assert lat.is_descendant(energy, energy) is True


def test_lattice_is_descendant_negative():
    lat, _, ke, pe, _ = _energy_lattice()
    assert lat.is_descendant(ke, pe) is False


def test_lattice_copy_is_independent():
    lat, energy, *_ = _energy_lattice()
    copy = lat.copy()

    # Same contents
    assert len(copy) == len(lat)
    assert copy.get("energy") is energy
    assert copy.get("PE") is lat.get("PE")

    # Mutation on copy does not affect original
    work = Kind("work", dimension=ENERGY_DIM, parent=energy)
    copy.register(work)
    assert "work" in copy
    assert "work" not in lat


def test_lattice_copy_preserves_aliases():
    lat, *_ = _energy_lattice()
    copy = lat.copy()
    # "PE" is an alias for potential_energy
    assert copy.get("PE").name == "potential_energy"


def test_lattice_register_adds_kind():
    lat, energy, *_ = _energy_lattice()
    work = Kind("work", dimension=ENERGY_DIM, parent=energy)
    lat.register(work)
    assert lat.get("work") is work
    assert lat.is_descendant(work, energy)

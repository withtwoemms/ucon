# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for load-time validation: cycles, orphans, cross-dimension, collisions."""

from __future__ import annotations

import pytest

from ucon.dimension import LENGTH, MASS, TIME
from ucon.kinds import (
    AliasCollision,
    CrossDimensionParent,
    Kind,
    KindCycle,
    KindLattice,
    NameCollision,
    OrphanParent,
)


ENERGY_DIM = (LENGTH ** 2) * MASS / (TIME ** 2)
POWER_DIM = (LENGTH ** 2) * MASS / (TIME ** 3)


# --------- orphan parent ---------

def test_orphan_parent_raises():
    placeholder = Kind("missing", dimension=ENERGY_DIM)
    child = Kind("child", dimension=ENERGY_DIM, parent=placeholder)
    with pytest.raises(OrphanParent) as exc:
        KindLattice([child])
    assert exc.value.kind_name == "child"
    assert exc.value.missing_parent == "missing"


# --------- cross-dimension parent ---------

def test_cross_dimension_parent_raises():
    power = Kind("power", dimension=POWER_DIM)
    weird = Kind("weird", dimension=ENERGY_DIM, parent=power)
    with pytest.raises(CrossDimensionParent) as exc:
        KindLattice([power, weird])
    assert exc.value.kind_name == "weird"
    assert exc.value.parent_name == "power"


# --------- name collision ---------

def test_duplicate_primary_name_raises():
    a = Kind("foo", dimension=ENERGY_DIM)
    b = Kind("foo", dimension=POWER_DIM)
    with pytest.raises(NameCollision) as exc:
        KindLattice([a, b])
    assert exc.value.name == "foo"


def test_identical_object_readd_is_idempotent():
    """#284: the same Kind object appearing twice is harmless — previously
    this fell through to a self-referential AliasCollision
    ("Alias 'foo' collides with existing entry 'foo'")."""
    k = Kind("foo", dimension=ENERGY_DIM, aliases=("f",))
    lat = KindLattice([k, k])
    assert lat.get("foo") is k
    assert lat.get("f") is k


def test_distinct_same_name_objects_raise_name_collision():
    """#284: a *distinct* object with the same name is a NameCollision —
    never an AliasCollision when no alias is involved."""
    a = Kind("foo", dimension=ENERGY_DIM)
    b = Kind("foo", dimension=ENERGY_DIM)
    with pytest.raises(NameCollision) as exc:
        KindLattice([a, b])
    assert exc.value.name == "foo"


def test_cross_fiber_collision_diagnoses_and_points_at_qualification():
    """#285 — the decision of record: the flat name index stays in 2.x.

    Same-named kinds in different fibers stay refused, because letting
    them coexist under name-only ``Kind.__eq__`` would silently
    conflate them in every lattice walk (``join`` short-circuits on
    ``a == b``; ``lca``/``ancestors`` compare by name) — a wrong-answer
    failure strictly worse than today's loud one. Re-keying the index
    by ``(name, dimension)`` therefore requires extending ``Kind``
    equality, a breaking change reserved for a major release. What 2.2.0
    delivers instead: ``pkg:name`` qualification (which resolves the
    load-bearing cross-package case) and this diagnostic, which names
    both fibers and the fix."""
    a = Kind("dose", dimension=ENERGY_DIM)
    b = Kind("dose", dimension=POWER_DIM)
    with pytest.raises(NameCollision) as exc:
        KindLattice([a, b])
    err = exc.value
    assert err.name == "dose"
    assert err.existing_dimension == ENERGY_DIM
    assert err.new_dimension == POWER_DIM
    assert "different fibers" in str(err)
    assert "pkg:dose" in str(err)


def test_same_fiber_collision_message_carries_no_fiber_hint():
    """Same name, same dimension: a plain duplicate — qualification
    advice would be misleading, so the message stays as it was."""
    a = Kind("foo", dimension=ENERGY_DIM)
    b = Kind("foo", dimension=ENERGY_DIM)
    with pytest.raises(NameCollision) as exc:
        KindLattice([a, b])
    assert "different fibers" not in str(exc.value)


# --------- alias collisions ---------

def test_alias_collides_with_other_alias():
    a = Kind("foo", dimension=ENERGY_DIM, aliases=("shared",))
    b = Kind("bar", dimension=ENERGY_DIM, aliases=("shared",))
    with pytest.raises(AliasCollision) as exc:
        KindLattice([a, b])
    assert exc.value.alias == "shared"


def test_alias_collides_with_primary_name_later():
    # Alias 'shared' registered first; later primary name 'shared' clashes.
    a = Kind("foo", dimension=ENERGY_DIM, aliases=("shared",))
    b = Kind("shared", dimension=ENERGY_DIM)
    with pytest.raises(AliasCollision):
        KindLattice([a, b])


def test_primary_name_collides_with_earlier_alias():
    # Inverse order: primary first, alias matching it second.
    a = Kind("foo", dimension=ENERGY_DIM)
    b = Kind("bar", dimension=ENERGY_DIM, aliases=("foo",))
    with pytest.raises(AliasCollision):
        KindLattice([a, b])


# --------- cycles ---------

def test_simple_cycle_raises():
    # Kind is frozen; construct via placeholders that resolve to each other.
    placeholder_b = Kind("b", dimension=ENERGY_DIM)
    placeholder_c = Kind("c", dimension=ENERGY_DIM)
    a = Kind("a", dimension=ENERGY_DIM, parent=placeholder_c)
    b = Kind("b", dimension=ENERGY_DIM, parent=a)
    c = Kind("c", dimension=ENERGY_DIM, parent=b)
    with pytest.raises(KindCycle) as exc:
        KindLattice([a, b, c])
    assert "a" in exc.value.cycle


def test_self_cycle_raises():
    placeholder = Kind("self_loop", dimension=ENERGY_DIM)
    s = Kind("self_loop", dimension=ENERGY_DIM, parent=placeholder)
    with pytest.raises(KindCycle):
        KindLattice([s])


# --------- well-formed ---------

def test_valid_lattice_constructs_without_error():
    energy = Kind("energy", dimension=ENERGY_DIM)
    ke = Kind("kinetic_energy", dimension=ENERGY_DIM, parent=energy)
    pe = Kind("potential_energy", dimension=ENERGY_DIM, parent=energy)
    lat = KindLattice([energy, ke, pe])
    assert len(lat) == 3


# --------- additive register revalidates ---------

def test_register_revalidates_and_rejects_orphan_addition():
    energy = Kind("energy", dimension=ENERGY_DIM)
    lat = KindLattice([energy])
    placeholder = Kind("missing", dimension=ENERGY_DIM)
    bad = Kind("bad", dimension=ENERGY_DIM, parent=placeholder)
    with pytest.raises(OrphanParent):
        lat.register(bad)

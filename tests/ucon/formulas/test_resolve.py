# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for FormulaRegistry.resolve: tiered formula resolution.

Covers EXACT, COMMUTATIVE, GENERALIZED, and DIMENSIONAL tiers,
tier priority ordering, ambiguity detection, and gating behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ucon.dimension import LENGTH, MASS, TIME
from ucon.formulas import (
    AmbiguousFormula,
    FormulaNotFound,
    FormulaRegistry,
    KindFormula,
    LookupResult,
    MatchKind,
)
from ucon.kinds import Kind, KindLattice
from ucon.parsing import load_formulas_file, load_kinds_file


LENGTH_DIM = LENGTH
TIME_DIM = TIME
MASS_DIM = MASS
ENERGY_DIM = LENGTH ** 2 * MASS / TIME ** 2
DIMENSIONLESS = LENGTH / LENGTH

FIXTURES = Path(__file__).parent / "fixtures"


# ---------- helpers ----------


def _energy_lattice():
    energy = Kind("energy", dimension=ENERGY_DIM)
    ke = Kind("kinetic_energy", dimension=ENERGY_DIM, parent=energy)
    pe = Kind("potential_energy", dimension=ENERGY_DIM, parent=energy)
    grav = Kind("gravitational_pe", dimension=ENERGY_DIM, parent=pe)
    return KindLattice([energy, ke, pe, grav]), energy, ke, pe, grav


def _scale_energy_formula(energy, generalizes=True, commutative=True):
    scale = Kind("scale_factor", dimension=DIMENSIONLESS)
    scaled = Kind("scaled_energy", dimension=ENERGY_DIM)
    f = KindFormula(
        name="scale_energy",
        expression="E * s",
        input_kinds={"E": energy, "s": scale},
        output_kind=scaled,
        generalizes=generalizes,
        commutative=commutative,
    )
    return f, scale, scaled


# ========== Tier 1: EXACT ==========


def test_resolve_exact_match():
    lat, energy, *_ = _energy_lattice()
    f, scale, _ = _scale_energy_formula(energy)
    reg = FormulaRegistry([f])
    result = reg.resolve(energy, scale)
    assert result.formula is f
    assert result.match_kind == MatchKind.EXACT
    assert result.distance == 0


def test_resolve_exact_arity2_commutative():
    """Arity-2 commutative reversed key is in _by_inputs → EXACT tier."""
    lat, energy, *_ = _energy_lattice()
    f, scale, _ = _scale_energy_formula(energy)
    reg = FormulaRegistry([f])
    # Reversed order hits the mirrored key in _by_inputs.
    result = reg.resolve(scale, energy)
    assert result.formula is f
    assert result.match_kind == MatchKind.EXACT


def test_resolve_no_match_raises_formula_not_found():
    reg = FormulaRegistry()
    stranger = Kind("stranger", dimension=DIMENSIONLESS)
    with pytest.raises(FormulaNotFound):
        reg.resolve(stranger)


# ========== Tier 2: COMMUTATIVE ==========


def test_resolve_commutative_arity3():
    a = Kind("a", dimension=LENGTH_DIM)
    b = Kind("b", dimension=MASS_DIM)
    c = Kind("c", dimension=TIME_DIM)
    out = Kind("abc", dimension=LENGTH_DIM * MASS_DIM * TIME_DIM)
    f = KindFormula(
        name="triple",
        expression="a * b * c",
        input_kinds={"a": a, "b": b, "c": c},
        output_kind=out,
        commutative=True,
    )
    reg = FormulaRegistry([f])
    # Forward order → EXACT.
    assert reg.resolve(a, b, c).match_kind == MatchKind.EXACT
    # Permuted → COMMUTATIVE.
    result = reg.resolve(c, a, b)
    assert result.formula is f
    assert result.match_kind == MatchKind.COMMUTATIVE


def test_resolve_commutative_arity4():
    kinds = [Kind(name, dimension=LENGTH_DIM) for name in ("w", "x", "y", "z")]
    out = Kind("wxyz", dimension=LENGTH_DIM ** 4)
    f = KindFormula(
        name="quad",
        expression="w * x * y * z",
        input_kinds={k.name: k for k in kinds},
        output_kind=out,
        commutative=True,
    )
    reg = FormulaRegistry([f])
    result = reg.resolve(kinds[3], kinds[1], kinds[0], kinds[2])
    assert result.formula is f
    assert result.match_kind == MatchKind.COMMUTATIVE


def test_resolve_commutative_duplicate_kinds():
    mass = Kind("mass", dimension=MASS_DIM)
    out = Kind("mass_squared", dimension=MASS_DIM * MASS_DIM)
    f = KindFormula(
        name="sq_mass",
        expression="m * m",
        input_kinds={"m1": mass, "m2": mass},
        output_kind=out,
        commutative=True,
    )
    reg = FormulaRegistry([f])
    # Both orderings are the same tuple → EXACT.
    result = reg.resolve(mass, mass)
    assert result.match_kind == MatchKind.EXACT


def test_resolve_non_commutative_rejects_permutation():
    a = Kind("a", dimension=LENGTH_DIM)
    b = Kind("b", dimension=MASS_DIM)
    out = Kind("ab", dimension=LENGTH_DIM * MASS_DIM)
    f = KindFormula(
        name="div",
        expression="a / b",
        input_kinds={"a": a, "b": b},
        output_kind=out,
        commutative=False,
    )
    reg = FormulaRegistry([f])
    assert reg.resolve(a, b).match_kind == MatchKind.EXACT
    with pytest.raises(FormulaNotFound):
        reg.resolve(b, a)


# ========== Tier 3: GENERALIZED ==========


def test_resolve_generalized_single_step_climb():
    lat, energy, ke, _, _ = _energy_lattice()
    f, scale, _ = _scale_energy_formula(energy, generalizes=True)
    reg = FormulaRegistry([f])
    result = reg.resolve(ke, scale, lattice=lat)
    assert result.formula is f
    assert result.match_kind == MatchKind.GENERALIZED
    assert result.distance == 1


def test_resolve_generalized_multi_step_climb():
    lat, energy, _, _, grav = _energy_lattice()
    f, scale, _ = _scale_energy_formula(energy, generalizes=True)
    reg = FormulaRegistry([f])
    # gravitational_pe → potential_energy → energy = 2 climbs.
    result = reg.resolve(grav, scale, lattice=lat)
    assert result.formula is f
    assert result.match_kind == MatchKind.GENERALIZED
    assert result.distance == 2


def test_resolve_generalized_commutative_interaction():
    """Generalized + commutative: child kind in reversed order."""
    lat, energy, ke, _, _ = _energy_lattice()
    f, scale, _ = _scale_energy_formula(energy, generalizes=True, commutative=True)
    reg = FormulaRegistry([f])
    # scale first, child kind second → requires both commutative + climb.
    result = reg.resolve(scale, ke, lattice=lat)
    assert result.formula is f
    assert result.match_kind == MatchKind.GENERALIZED
    assert result.distance == 1


def test_resolve_generalized_false_not_reached():
    lat, energy, ke, _, _ = _energy_lattice()
    f, scale, _ = _scale_energy_formula(energy, generalizes=False)
    reg = FormulaRegistry([f])
    with pytest.raises(FormulaNotFound):
        reg.resolve(ke, scale, lattice=lat)


def test_resolve_generalized_without_lattice_skips_tier():
    lat, energy, ke, _, _ = _energy_lattice()
    f, scale, _ = _scale_energy_formula(energy, generalizes=True)
    reg = FormulaRegistry([f])
    # No lattice → no climb.
    with pytest.raises(FormulaNotFound):
        reg.resolve(ke, scale)


def test_resolve_generalized_ambiguity_raises():
    # Ambiguity requires two formulas reachable at the same L1 distance
    # through different candidate tuples. With multi-input climbing and
    # different distributions summing to the same distance:
    #
    # Lattice: gp → p → c  (depth 2)
    #          other → other_parent (depth 1, different dimension)
    #
    # Formula A at (p, other) → reachable from (c, other_parent)
    #   via distribution (1,1) at distance 2.
    # Formula B at (gp, other_parent) → reachable from (c, other_parent)
    #   via distribution (2,0) at distance 2.
    scaled = Kind("scaled_energy", dimension=ENERGY_DIM)
    gp = Kind("gp_energy", dimension=ENERGY_DIM)
    p = Kind("p_energy", dimension=ENERGY_DIM, parent=gp)
    c = Kind("c_energy", dimension=ENERGY_DIM, parent=p)
    other_parent = Kind("other_dim_parent", dimension=DIMENSIONLESS)
    other = Kind("other_dim", dimension=DIMENSIONLESS, parent=other_parent)

    lat = KindLattice([gp, p, c, other_parent, other])

    fA = KindFormula(
        name="f_ambig_A",
        expression="x * y",
        input_kinds={"x": p, "y": other_parent},
        output_kind=scaled,
        generalizes=True,
    )
    fB = KindFormula(
        name="f_ambig_B",
        expression="x * y",
        input_kinds={"x": gp, "y": other},
        output_kind=scaled,
        generalizes=True,
    )
    reg = FormulaRegistry([fA, fB])

    with pytest.raises(AmbiguousFormula) as exc:
        reg.resolve(c, other, lattice=lat)
    assert len(exc.value.candidates) == 2
    assert exc.value.distance == 2


# ========== Tier 4: DIMENSIONAL ==========


def test_resolve_dimensional_fires_when_enabled():
    """Dimensional fallback matches on shared dimension, ignoring kind identity."""
    energy = Kind("energy", dimension=ENERGY_DIM)
    scale = Kind("scale_factor", dimension=DIMENSIONLESS)
    scaled = Kind("scaled_energy", dimension=ENERGY_DIM)
    f = KindFormula(
        name="scale_energy",
        expression="E * s",
        input_kinds={"E": energy, "s": scale},
        output_kind=scaled,
    )
    reg = FormulaRegistry([f])

    # A kind that shares dimension with energy but is not in the lattice.
    other_energy = Kind("thermal_energy", dimension=ENERGY_DIM)
    result = reg.resolve(other_energy, scale, dimension_fallback=True)
    assert result.formula is f
    assert result.match_kind == MatchKind.DIMENSIONAL


def test_resolve_dimensional_off_by_default():
    energy = Kind("energy", dimension=ENERGY_DIM)
    scale = Kind("scale_factor", dimension=DIMENSIONLESS)
    scaled = Kind("scaled_energy", dimension=ENERGY_DIM)
    f = KindFormula(
        name="scale_energy",
        expression="E * s",
        input_kinds={"E": energy, "s": scale},
        output_kind=scaled,
    )
    reg = FormulaRegistry([f])

    other_energy = Kind("thermal_energy", dimension=ENERGY_DIM)
    with pytest.raises(FormulaNotFound):
        reg.resolve(other_energy, scale)


def test_resolve_dimensional_commutative():
    """Dimensional tier respects commutative dimension ordering."""
    energy = Kind("energy", dimension=ENERGY_DIM)
    scale = Kind("scale_factor", dimension=DIMENSIONLESS)
    scaled = Kind("scaled_energy", dimension=ENERGY_DIM)
    f = KindFormula(
        name="scale_energy",
        expression="E * s",
        input_kinds={"E": energy, "s": scale},
        output_kind=scaled,
        commutative=True,
    )
    reg = FormulaRegistry([f])

    other_energy = Kind("thermal_energy", dimension=ENERGY_DIM)
    # Reversed order with dimensional fallback.
    result = reg.resolve(scale, other_energy, dimension_fallback=True)
    assert result.match_kind == MatchKind.DIMENSIONAL


# ========== Tier priority ==========


def test_exact_wins_over_commutative():
    a = Kind("a", dimension=LENGTH_DIM)
    b = Kind("b", dimension=MASS_DIM)
    out = Kind("ab", dimension=LENGTH_DIM * MASS_DIM)
    f = KindFormula(
        name="prod",
        expression="a * b",
        input_kinds={"a": a, "b": b},
        output_kind=out,
        commutative=True,
    )
    reg = FormulaRegistry([f])
    # Forward order → EXACT, not COMMUTATIVE.
    assert reg.resolve(a, b).match_kind == MatchKind.EXACT


def test_commutative_wins_over_generalized():
    lat, energy, ke, _, _ = _energy_lattice()
    f, scale, _ = _scale_energy_formula(energy, generalizes=True, commutative=True)
    reg = FormulaRegistry([f])
    # Reversed order with parent kind → COMMUTATIVE (no climbing needed).
    result = reg.resolve(scale, energy, lattice=lat)
    assert result.match_kind == MatchKind.EXACT  # arity-2 mirror in _by_inputs


def test_generalized_wins_over_dimensional():
    lat, energy, ke, _, _ = _energy_lattice()
    f, scale, _ = _scale_energy_formula(energy, generalizes=True)
    reg = FormulaRegistry([f])
    # ke climbs to energy (GENERALIZED distance 1); dimensional would also
    # match but GENERALIZED fires first.
    result = reg.resolve(ke, scale, lattice=lat, dimension_fallback=True)
    assert result.match_kind == MatchKind.GENERALIZED


# ========== LookupResult dataclass ==========


def test_lookup_result_fields():
    f, _, _ = _scale_energy_formula(
        Kind("energy", dimension=ENERGY_DIM)
    )
    r = LookupResult(f, MatchKind.EXACT)
    assert r.formula is f
    assert r.match_kind == MatchKind.EXACT
    assert r.distance == 0


def test_lookup_result_distance_for_generalized():
    f, _, _ = _scale_energy_formula(
        Kind("energy", dimension=ENERGY_DIM)
    )
    r = LookupResult(f, MatchKind.GENERALIZED, distance=3)
    assert r.distance == 3


def test_lookup_result_is_frozen():
    f, _, _ = _scale_energy_formula(
        Kind("energy", dimension=ENERGY_DIM)
    )
    r = LookupResult(f, MatchKind.EXACT)
    with pytest.raises(AttributeError):
        r.distance = 5  # type: ignore[misc]


# ========== MatchKind enum ==========


def test_match_kind_values():
    assert MatchKind("exact") == MatchKind.EXACT
    assert MatchKind("commutative") == MatchKind.COMMUTATIVE
    assert MatchKind("generalized") == MatchKind.GENERALIZED
    assert MatchKind("dimensional") == MatchKind.DIMENSIONAL


# ========== AmbiguousFormula exception ==========


def test_ambiguous_formula_carries_candidates_and_distance():
    f1 = KindFormula(
        name="f1",
        expression="x",
        input_kinds={},
        output_kind=Kind("out", dimension=DIMENSIONLESS),
    )
    f2 = KindFormula(
        name="f2",
        expression="y",
        input_kinds={},
        output_kind=Kind("out", dimension=DIMENSIONLESS),
    )
    exc = AmbiguousFormula((f1, f2), distance=2)
    assert exc.candidates == (f1, f2)
    assert exc.distance == 2
    assert "f1" in str(exc) and "f2" in str(exc)
    assert "distance 2" in str(exc)


# ========== End-to-end TOML → resolve ==========


def test_e2e_toml_generalized_resolve():
    """Load generalized.ucon.toml and exercise resolve through the pipeline."""
    lat = load_kinds_file(FIXTURES / "generalized.ucon.toml")
    reg = load_formulas_file(FIXTURES / "generalized.ucon.toml", lattice=lat)

    energy = lat.get("energy")
    ke = lat.get("kinetic_energy")
    thermal = lat.get("thermal_energy")
    scale = lat.get("scale_factor")

    # Exact match at parent level.
    result = reg.resolve(energy, scale)
    assert result.match_kind == MatchKind.EXACT

    # Child kind → generalized.
    result = reg.resolve(ke, scale, lattice=lat)
    assert result.match_kind == MatchKind.GENERALIZED
    assert result.distance == 1
    assert result.formula.name == "scale_energy"

    # Another child kind.
    result = reg.resolve(thermal, scale, lattice=lat)
    assert result.match_kind == MatchKind.GENERALIZED
    assert result.distance == 1

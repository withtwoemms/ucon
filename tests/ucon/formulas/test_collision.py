# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for formula signature-collision refusal at registration (#347).

Three of the four resolution tiers key off kind identity and return one
formula per signature: EXACT and COMMUTATIVE read the signature indexes
directly, GENERALIZED reads them through its ancestor walk. A second
claim on a claimed signature with a *different* output kind is therefore
refused at ``register``, which is the single site covering all three.
The DIMENSIONAL tier discards kind identity by construction; its overlap
is pinned here as by-design rather than refused.
"""

from __future__ import annotations

import pytest

from ucon.dimension import LENGTH, MASS, TIME
from ucon.formulas import (
    CollidingFormula,
    FormulaRegistry,
    KindFormula,
    MatchKind,
)
from ucon.kinds import Kind, KindLattice
from ucon.system import active_formulas


ALPHA = Kind("alpha", dimension=LENGTH)
BETA = Kind("beta", dimension=TIME)
GAMMA = Kind("gamma", dimension=MASS)
OUT = Kind("out_one", dimension=LENGTH * TIME)
OTHER_OUT = Kind("out_two", dimension=LENGTH * TIME)


def _formula(name, inputs, output, **kwargs):
    return KindFormula(
        name=name,
        expression=" * ".join(inputs),
        input_kinds=inputs,
        output_kind=output,
        **kwargs,
    )


# ========== Tier 1: EXACT ==========


def test_exact_signature_collision_refused():
    """Same declared signature, different output kinds — refused."""
    first = _formula("exact_first", {"x": ALPHA, "y": BETA}, OUT)
    second = _formula("exact_second", {"x": ALPHA, "y": BETA}, OTHER_OUT)
    reg = FormulaRegistry([first])
    with pytest.raises(CollidingFormula) as exc:
        reg.register(second)
    assert exc.value.existing is first
    assert exc.value.incoming is second
    assert exc.value.signature == (ALPHA, BETA)


def test_collision_refused_in_either_registration_order():
    """The refusal is symmetric: neither ordering admits the pair."""
    first = _formula("sym_first", {"x": ALPHA, "y": BETA}, OUT)
    second = _formula("sym_second", {"x": ALPHA, "y": BETA}, OTHER_OUT)
    with pytest.raises(CollidingFormula):
        FormulaRegistry([first, second])
    with pytest.raises(CollidingFormula):
        FormulaRegistry([second, first])


def test_refused_registration_leaves_registry_unmodified():
    """A refused register writes nothing, not even the name index."""
    first = _formula("intact_first", {"x": ALPHA, "y": BETA}, OUT)
    second = _formula("intact_second", {"x": ALPHA, "y": BETA}, OTHER_OUT)
    reg = FormulaRegistry([first])
    with pytest.raises(CollidingFormula):
        reg.register(second)
    assert reg.names() == ("intact_first",)
    assert len(reg) == 1
    assert "intact_second" not in reg
    assert reg.lookup(ALPHA, BETA) is first


def test_collision_message_names_both_formulas_and_kinds():
    first = _formula("msg_first", {"x": ALPHA, "y": BETA}, OUT)
    second = _formula("msg_second", {"x": ALPHA, "y": BETA}, OTHER_OUT)
    reg = FormulaRegistry([first])
    with pytest.raises(CollidingFormula) as exc:
        reg.register(second)
    message = str(exc.value)
    for fragment in ("msg_first", "msg_second", "alpha", "beta", "out_one", "out_two"):
        assert fragment in message


def test_commutative_mirror_collision_refused():
    """The arity-2 mirror is a claim too: (A, B) vs declared (B, A)."""
    first = _formula("mirror_first", {"x": ALPHA, "y": BETA}, OUT, commutative=True)
    second = _formula("mirror_second", {"y": BETA, "x": ALPHA}, OTHER_OUT, commutative=True)
    reg = FormulaRegistry([first])
    with pytest.raises(CollidingFormula):
        reg.register(second)


def test_distinct_ordered_signatures_are_not_a_collision():
    """Non-commutative formulas may claim opposite operand orders."""
    forward = _formula("ord_forward", {"x": ALPHA, "y": BETA}, OUT, commutative=False)
    reverse = _formula("ord_reverse", {"y": BETA, "x": ALPHA}, OTHER_OUT, commutative=False)
    reg = FormulaRegistry([forward, reverse])
    assert reg.lookup(ALPHA, BETA) is forward
    assert reg.lookup(BETA, ALPHA) is reverse


def test_agreeing_output_kinds_are_admitted_first_writer_wins():
    """One relationship declared twice is legitimate overlap, not a collision."""
    first = _formula("agree_first", {"x": ALPHA, "y": BETA}, OUT)
    second = _formula("agree_second", {"x": ALPHA, "y": BETA}, OUT)
    reg = FormulaRegistry([first, second])
    assert reg.names() == ("agree_first", "agree_second")
    assert reg.lookup(ALPHA, BETA) is first
    assert reg.resolve(ALPHA, BETA).formula is first
    assert reg.get("agree_second") is second


# ========== Tier 2: COMMUTATIVE ==========


def test_canonical_signature_collision_refused_at_higher_arity():
    """Two 3-ary commutative formulas permuting one multiset — refused."""
    first = _formula(
        "canon_first", {"x": ALPHA, "y": BETA, "z": GAMMA}, OUT, commutative=True
    )
    second = _formula(
        "canon_second", {"z": GAMMA, "y": BETA, "x": ALPHA}, OTHER_OUT, commutative=True
    )
    reg = FormulaRegistry([first])
    with pytest.raises(CollidingFormula) as exc:
        reg.register(second)
    assert exc.value.signature == (ALPHA, BETA, GAMMA)


def test_commutative_tier_still_resolves_a_permutation():
    """The guard does not disturb ordinary canonical resolution."""
    only = _formula(
        "canon_only", {"x": ALPHA, "y": BETA, "z": GAMMA}, OUT, commutative=True
    )
    reg = FormulaRegistry([only])
    result = reg.resolve(BETA, GAMMA, ALPHA)
    assert result.formula is only
    assert result.match_kind is MatchKind.COMMUTATIVE


# ========== Tier 3: GENERALIZED ==========


def test_generalized_tier_cannot_see_a_same_signature_collision():
    """The register-time guard is what keeps the ancestor walk single-valued.

    Two generalizing formulas on one parent signature would both be
    reachable from the same subkind at one distance. The pair is refused
    at ingestion, so the walk never has to arbitrate it.
    """
    parent = Kind("gen_parent", dimension=LENGTH)
    child = Kind("gen_child", dimension=LENGTH, parent=parent)
    lattice = KindLattice([parent, child, BETA])
    first = _formula("gen_first", {"x": parent, "y": BETA}, OUT, generalizes=True)
    second = _formula("gen_second", {"x": parent, "y": BETA}, OTHER_OUT, generalizes=True)
    with pytest.raises(CollidingFormula):
        FormulaRegistry([first, second])

    reg = FormulaRegistry([first])
    result = reg.resolve(child, BETA, lattice=lattice)
    assert result.formula is first
    assert result.match_kind is MatchKind.GENERALIZED
    assert result.distance == 1


# ========== Tier 4: DIMENSIONAL ==========


def test_dimensional_overlap_is_admitted_by_design():
    """Shared dimensions are not a signature collision.

    The tier discards kind identity by construction and is opt-in per
    call, so two formulas over distinct kinds of the same dimensions
    register without complaint and the first registered answers.
    """
    other_alpha = Kind("alpha_prime", dimension=LENGTH)
    other_beta = Kind("beta_prime", dimension=TIME)
    first = _formula("dim_first", {"x": ALPHA, "y": BETA}, OUT)
    second = _formula("dim_second", {"x": other_alpha, "y": other_beta}, OTHER_OUT)
    reg = FormulaRegistry([first, second])
    assert len(reg) == 2

    unknown_length = Kind("dim_probe_length", dimension=LENGTH)
    unknown_time = Kind("dim_probe_time", dimension=TIME)
    result = reg.resolve(unknown_length, unknown_time, dimension_fallback=True)
    assert result.formula is first
    assert result.match_kind is MatchKind.DIMENSIONAL


# ========== shipped catalog ==========


def test_shipped_catalog_declares_no_colliding_formulas():
    """The package catalog loads cleanly under the guard.

    It declares a single formula, so no collision is reachable without
    user registration; this pins that the guard costs the catalog
    nothing.
    """
    registry = active_formulas()
    assert "radiation_weighting" in registry
    signatures = [formula.input_kind_tuple() for formula in registry]
    assert len(signatures) == len(set(signatures))

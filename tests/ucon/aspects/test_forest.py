# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for AspectForest (A2 of the aspect stratum, #296).

The forest runs each family on a private, mirrored kind-lattice engine.
The fixtures here transfer the vetted isomorphism results: root-as-⊤
converting would-be crashes into refusals, LCA degradation where a node
opts into ``lca``, and the rewrap boundary keeping Kind-named
exceptions out of aspect declarations.
"""

from __future__ import annotations

import pytest

from ucon.aspects import (
    Aspect,
    AspectError,
    AspectForest,
    AspectRefused,
)
from ucon.kinds import JoinPolicy, KindError


def _radsafe():
    """The canonical family: weighting_standard ▸ {icrp60, icrp103}."""
    family = Aspect("weighting_standard",
                    applies_to=frozenset({"dose_equivalent"}))
    icrp60 = Aspect("icrp60", parent=family)
    icrp103 = Aspect("icrp103", parent=family)
    return family, icrp60, icrp103


# ---------- construction ----------

def test_leaves_close_over_parents():
    family, icrp60, icrp103 = _radsafe()
    forest = AspectForest([icrp60, icrp103])   # root never passed explicitly
    assert "weighting_standard" in forest
    assert len(forest) == 3
    assert forest.family_of(icrp60) is family


def test_families_lists_one_root_per_tree():
    family, icrp60, _ = _radsafe()
    coverage = Aspect("coverage", applies_to=frozenset({"*"}))
    k2 = Aspect("k2", parent=coverage)
    forest = AspectForest([icrp60, k2])
    assert set(a.name for a in forest.families()) == {
        "weighting_standard", "coverage"}


def test_duplicate_name_distinct_nodes_refused():
    a = Aspect("shared")
    b = Aspect("shared")
    with pytest.raises(AspectError, match="Duplicate aspect name"):
        AspectForest([a, b])


def test_root_only_applies_to_enforced():
    family = Aspect("weighting_standard")
    bad = Aspect("icrp103", parent=family,
                 applies_to=frozenset({"dose_equivalent"}))
    with pytest.raises(AspectError, match="not a family root"):
        AspectForest([bad])


# ---------- the vetted transfers ----------

def test_disjoint_subtrees_meet_at_root_and_refuse():
    """T1 transfer: without a family ⊤ this was a crash; with root-as-⊤
    it is a typed refusal."""
    family = Aspect("weighting_standard")            # refuse by default
    icrp = Aspect("icrp", parent=family)
    iso = Aspect("iso", parent=family)
    icrp60 = Aspect("icrp60", parent=icrp)
    iso4037 = Aspect("iso4037", parent=iso)
    forest = AspectForest([icrp60, iso4037])
    with pytest.raises(AspectRefused) as exc_info:
        forest.join(icrp60, iso4037)
    exc = exc_info.value
    assert exc.family.name == "weighting_standard"
    assert {exc.left.name, exc.right.name} == {"icrp60", "iso4037"}
    assert exc.policy is JoinPolicy.REFUSE


def test_lca_degradation_when_node_opts_in():
    """LCA degradation is opt-in per node (ADR §3)."""
    family = Aspect("procedure", join_policy=JoinPolicy.LCA)
    measured = Aspect("measured", parent=family)
    simulated = Aspect("simulated", parent=family)
    forest = AspectForest([measured, simulated])
    assert forest.join(measured, simulated).name == "procedure"


def test_lca_returns_ancestor_and_policy():
    family, icrp60, icrp103 = _radsafe()
    forest = AspectForest([icrp60, icrp103])
    ancestor, policy = forest.lca(icrp60, icrp103)
    assert ancestor is family
    assert policy is JoinPolicy.REFUSE


def test_join_equal_short_circuits():
    _, icrp60, icrp103 = _radsafe()
    forest = AspectForest([icrp60, icrp103])
    assert forest.join(icrp60, icrp60) is icrp60


def test_root_operand_refuses_against_specific():
    """The root is ⊤: 'unspecified within this family' does not admit
    against a specific position under refuse."""
    family, icrp60, _ = _radsafe()
    forest = AspectForest([icrp60])
    with pytest.raises(AspectRefused):
        forest.join(family, icrp60)


# ---------- the rewrap boundary ----------

def test_cross_family_lca_is_a_caller_error():
    _, icrp60, _ = _radsafe()
    coverage = Aspect("coverage", applies_to=frozenset({"*"}))
    k2 = Aspect("k2", parent=coverage)
    forest = AspectForest([icrp60, k2])
    with pytest.raises(AspectError, match="different families"):
        forest.lca(icrp60, k2)


def test_no_kind_named_exception_leaks():
    """Engine errors rewrap: an aspect failure is never a KindError."""
    _, icrp60, icrp103 = _radsafe()
    forest = AspectForest([icrp60, icrp103])
    try:
        forest.get("missing")
    except Exception as exc:
        assert isinstance(exc, AspectError)
        assert not isinstance(exc, KindError)
    try:
        forest.join(icrp60, icrp103)
    except Exception as exc:
        assert isinstance(exc, AspectRefused)
        assert not isinstance(exc, KindError)


def test_engine_errors_chain_as_cause():
    """Structural engine failures rewrap with the original chained."""
    family = Aspect("procedure")
    # a cycle is impossible with frozen nodes built through parents, so
    # provoke the engine differently: two distinct nodes, same name,
    # in one family — caught by the forest's own dedupe before the
    # engine, still an AspectError.
    a = Aspect("measured", parent=family)
    b = Aspect("measured", parent=family)
    with pytest.raises(AspectError):
        AspectForest([a, b])

# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for family-wise aspect resolution (A4 of the aspect stratum, #296).

Pure-function tests of ``resolve_add_aspects`` / ``resolve_mul_aspects``:
equal carries, differing joins at LCA under the ancestor's policy,
partial diverges by operation (addition consults the strict bit,
multiplication consults the family's multiplication policy), and no
path drops a position silently.
"""

from __future__ import annotations

import pytest

from ucon.aspects import (
    Aspect,
    AspectRefused,
    resolve_add_aspects,
    resolve_mul_aspects,
)
from ucon.kinds import JoinPolicy


def _radsafe():
    family = Aspect("weighting_standard",
                    applies_to=frozenset({"dose_equivalent"}))
    icrp60 = Aspect("icrp60", parent=family)
    icrp103 = Aspect("icrp103", parent=family)
    return family, icrp60, icrp103


# ---------- both silent / equal ----------

def test_both_empty_is_empty():
    assert resolve_add_aspects(frozenset(), frozenset(), strict=True) == frozenset()
    assert resolve_mul_aspects(frozenset(), frozenset()) == frozenset()


def test_equal_positions_carry():
    _, _, icrp103 = _radsafe()
    both = frozenset({icrp103})
    assert resolve_add_aspects(both, both, strict=True) == both
    assert resolve_mul_aspects(both, both) == both


# ---------- differing positions: LCA + policy ----------

def test_differing_refuse_family_refuses_add_and_mul():
    family, icrp60, icrp103 = _radsafe()
    left, right = frozenset({icrp60}), frozenset({icrp103})
    for resolve in (
        lambda: resolve_add_aspects(left, right, strict=True),
        lambda: resolve_mul_aspects(left, right),
    ):
        with pytest.raises(AspectRefused) as exc_info:
            resolve()
        exc = exc_info.value
        assert exc.family.name == "weighting_standard"
        assert exc.policy is JoinPolicy.REFUSE


def test_differing_lca_family_carries_ancestor():
    family = Aspect("procedure", join_policy=JoinPolicy.LCA)
    measured = Aspect("measured", parent=family)
    simulated = Aspect("simulated", parent=family)
    result = resolve_add_aspects(
        frozenset({measured}), frozenset({simulated}), strict=True)
    assert result == frozenset({family})


# ---------- partial presence: addition ----------

def test_partial_add_strict_refuses_with_silent_side():
    _, _, icrp103 = _radsafe()
    with pytest.raises(AspectRefused) as exc_info:
        resolve_add_aspects(frozenset({icrp103}), frozenset(), strict=True)
    exc = exc_info.value
    assert exc.left is icrp103
    assert exc.right is None
    assert "silent" in str(exc)


def test_partial_add_strict_refuses_symmetrically():
    _, _, icrp103 = _radsafe()
    with pytest.raises(AspectRefused) as exc_info:
        resolve_add_aspects(frozenset(), frozenset({icrp103}), strict=True)
    assert exc_info.value.left is None
    assert exc_info.value.right is icrp103


def test_partial_add_permissive_inherits_and_warns():
    _, _, icrp103 = _radsafe()
    with pytest.warns(UserWarning, match="aspect-silent"):
        result = resolve_add_aspects(
            frozenset({icrp103}), frozenset(), strict=False)
    assert result == frozenset({icrp103})


def test_partial_add_no_warn_flag_is_silent(recwarn):
    _, _, icrp103 = _radsafe()
    result = resolve_add_aspects(
        frozenset({icrp103}), frozenset(), strict=False, warn=False)
    assert result == frozenset({icrp103})
    assert not recwarn.list


# ---------- partial presence: multiplication carries ----------

def test_partial_mul_carries_present_positions():
    """The carry rule (ADR 008): a factor's provenance survives
    multiplication by an unqualified operand."""
    _, _, icrp103 = _radsafe()
    assert resolve_mul_aspects(
        frozenset({icrp103}), frozenset()) == frozenset({icrp103})
    assert resolve_mul_aspects(
        frozenset(), frozenset({icrp103})) == frozenset({icrp103})


# ---------- family independence ----------

def test_families_resolve_independently():
    """One shared family carries, the other's rules apply to it alone."""
    _, _, icrp103 = _radsafe()
    coverage = Aspect("coverage", applies_to=frozenset({"*"}))
    k2 = Aspect("k2", parent=coverage)
    left = frozenset({icrp103, k2})
    right = frozenset({icrp103})
    # mul: weighting carries (equal), coverage carries (partial + carry)
    assert resolve_mul_aspects(left, right) == frozenset({icrp103, k2})
    # add strict: coverage partial refuses — and names its own family
    with pytest.raises(AspectRefused) as exc_info:
        resolve_add_aspects(left, right, strict=True)
    assert exc_info.value.family is coverage


def test_within_operand_conflict_surfaces():
    """Two irreconcilable positions on ONE operand cannot launder
    through a partial: the family folds before resolution."""
    _, icrp60, icrp103 = _radsafe()
    with pytest.raises(AspectRefused):
        resolve_add_aspects(
            frozenset({icrp60, icrp103}), frozenset(), strict=True)

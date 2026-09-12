# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for the aspect data model (A1 of the aspect stratum, #296).

Covers the `Aspect` node type, `MultPolicy`, and the exception surface.
Family resolution, the shared engine, and `Number.aspects` arrive in
later workstreams; this file pins the types they build on.
"""

from __future__ import annotations

import pytest

from ucon import Aspect, AspectError, AspectNotApplicable, AspectRefused
from ucon.aspects import MultPolicy
from ucon.kinds import JoinPolicy


# ---------- Aspect nodes ----------

def test_root_aspect_defaults():
    family = Aspect("weighting_standard")
    assert family.is_root
    assert family.root is family
    assert family.join_policy is JoinPolicy.REFUSE          # strict by default
    assert family.multiplication_policy is MultPolicy.CARRY
    assert family.applies_to == frozenset()


def test_child_walks_to_root():
    family = Aspect("weighting_standard", applies_to=frozenset({"dose_equivalent"}))
    icrp103 = Aspect("icrp103", parent=family)
    assert not icrp103.is_root
    assert icrp103.root is family


def test_deep_chain_root():
    a = Aspect("a")
    b = Aspect("b", parent=a)
    c = Aspect("c", parent=b)
    assert c.root is a


def test_empty_name_rejected():
    with pytest.raises(ValueError):
        Aspect("")


def test_applies_to_coerced_to_frozenset():
    family = Aspect("coverage", applies_to={"*"})
    assert isinstance(family.applies_to, frozenset)
    assert family.applies_to == frozenset({"*"})


def test_aspect_is_frozen():
    a = Aspect("calibrated")
    with pytest.raises(AttributeError):
        a.name = "other"


# ---------- exception surface ----------

def test_refused_conflict_payload_and_message():
    family = Aspect("weighting_standard")
    left = Aspect("icrp60", parent=family)
    right = Aspect("icrp103", parent=family)
    exc = AspectRefused(family=family, left=left, right=right,
                        policy=JoinPolicy.REFUSE)
    assert isinstance(exc, AspectError)
    assert exc.family is family and exc.left is left and exc.right is right
    assert "icrp60" in str(exc) and "icrp103" in str(exc)
    assert "weighting_standard" in str(exc)


def test_refused_partial_marks_silent_side():
    family = Aspect("coverage", applies_to=frozenset({"*"}))
    k2 = Aspect("k2", parent=family)
    exc = AspectRefused(family=family, left=k2, right=None)
    assert exc.right is None
    assert "silent" in str(exc)


def test_not_applicable_names_family_and_kind():
    from ucon.kinds import Kind
    from ucon.dimension import LENGTH, MASS, TIME
    family = Aspect("weighting_standard",
                    applies_to=frozenset({"dose_equivalent"}))
    absorbed = Kind("absorbed_dose",
                    dimension=(LENGTH ** 2) * MASS / (TIME ** 2))
    exc = AspectNotApplicable(family=family, kind=absorbed)
    assert isinstance(exc, AspectError)
    assert "weighting_standard" in str(exc)
    assert "absorbed_dose" in str(exc)


def test_not_applicable_unkinded():
    family = Aspect("weighting_standard",
                    applies_to=frozenset({"dose_equivalent"}))
    exc = AspectNotApplicable(family=family, kind=None)
    assert "<unkinded>" in str(exc)


# ---------- public surface ----------

def test_public_exports():
    import ucon
    for name in ("Aspect", "AspectError", "AspectRefused", "AspectNotApplicable"):
        assert name in ucon.__all__
        assert getattr(ucon, name) is not None


def test_flat_model_is_gone():
    """The never-exported flat model is removed outright (option 4)."""
    import ucon.aspects as pkg
    for gone in ("AspectSet", "AspectJoinPolicy", "join_aspects", "AspectRule"):
        assert not hasattr(pkg, gone)
    import ucon.formulas as formulas
    assert not hasattr(formulas, "AspectRule")

# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for `join_aspects` and `AspectJoinPolicy`.

`join_aspects` is the addition-path (lattice-join) aspect combiner: a
pure function of two aspect sets and a policy. INTERSECT is the default
because LCA join lifts to a less-specific kind; aspects not shared by
both operands cannot be honestly attributed to the result.
"""

from __future__ import annotations

import pytest

from ucon.aspects import AspectJoinPolicy, join_aspects


# ---------- INTERSECT (default) ----------


def test_intersect_default_keeps_only_shared_aspects():
    a = frozenset({"calibrated", "signal_summary"})
    b = frozenset({"signal_summary", "smoothed"})
    assert join_aspects(a, b) == frozenset({"signal_summary"})


def test_intersect_disjoint_inputs_yield_empty():
    assert join_aspects(frozenset({"a"}), frozenset({"b"})) == frozenset()


def test_intersect_identical_inputs_preserve_set():
    a = frozenset({"x", "y"})
    assert join_aspects(a, a) == a


def test_intersect_with_empty_yields_empty():
    a = frozenset({"x"})
    assert join_aspects(a, frozenset()) == frozenset()
    assert join_aspects(frozenset(), a) == frozenset()


def test_intersect_explicit_policy_matches_default():
    a = frozenset({"a", "b"})
    b = frozenset({"b", "c"})
    assert join_aspects(a, b, AspectJoinPolicy.INTERSECT) == join_aspects(a, b)


# ---------- UNION ----------


def test_union_keeps_every_aspect():
    a = frozenset({"a"})
    b = frozenset({"b"})
    assert join_aspects(a, b, AspectJoinPolicy.UNION) == frozenset({"a", "b"})


def test_union_identical_inputs_preserve_set():
    a = frozenset({"x", "y"})
    assert join_aspects(a, a, AspectJoinPolicy.UNION) == a


def test_union_with_empty_yields_other_side():
    a = frozenset({"x", "y"})
    assert join_aspects(a, frozenset(), AspectJoinPolicy.UNION) == a
    assert join_aspects(frozenset(), a, AspectJoinPolicy.UNION) == a


# ---------- General properties ----------


def test_join_aspects_returns_a_frozenset():
    result = join_aspects(frozenset({"a"}), frozenset({"a", "b"}))
    assert isinstance(result, frozenset)


def test_join_aspects_is_commutative_intersect():
    a = frozenset({"a", "b", "c"})
    b = frozenset({"b", "c", "d"})
    assert join_aspects(a, b) == join_aspects(b, a)


def test_join_aspects_is_commutative_union():
    a = frozenset({"a", "b"})
    b = frozenset({"c", "d"})
    assert join_aspects(a, b, AspectJoinPolicy.UNION) == join_aspects(
        b, a, AspectJoinPolicy.UNION
    )


def test_join_aspects_rejects_unknown_policy():
    class FakePolicy:
        pass

    with pytest.raises(ValueError):
        join_aspects(frozenset({"a"}), frozenset({"b"}), FakePolicy())  # type: ignore[arg-type]


# ---------- Policy enum ----------


def test_policy_enum_values():
    assert AspectJoinPolicy("intersect") is AspectJoinPolicy.INTERSECT
    assert AspectJoinPolicy("union") is AspectJoinPolicy.UNION

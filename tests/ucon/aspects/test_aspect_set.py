# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for the AspectSet class.

`AspectSet` is a ``frozenset[str]`` subclass with a variadic-friendly
constructor (``AspectSet("a", "b")``). These tests pin behaviour the
rest of the aspect machinery relies on: hashability, immutability, set
algebra, equality with plain frozensets, and the constructor surface.
"""

from __future__ import annotations

import pytest

from ucon.aspects import AspectSet


def test_aspect_set_literal_is_a_frozenset():
    a: AspectSet = frozenset({"calibrated"})
    assert isinstance(a, frozenset)


def test_aspect_set_is_hashable():
    a: AspectSet = frozenset({"calibrated", "signal_summary"})
    # Hashable: usable as a dict key / set element.
    {a: 1}
    {a}


def test_aspect_set_is_immutable():
    a: AspectSet = frozenset({"calibrated"})
    with pytest.raises(AttributeError):
        a.add("signal_summary")  # type: ignore[attr-defined]


def test_aspect_set_equality_is_value_based():
    a: AspectSet = frozenset({"calibrated", "signal_summary"})
    b: AspectSet = frozenset({"signal_summary", "calibrated"})
    assert a == b
    assert hash(a) == hash(b)


def test_aspect_set_supports_union():
    a: AspectSet = frozenset({"a"})
    b: AspectSet = frozenset({"b"})
    assert a | b == frozenset({"a", "b"})


def test_aspect_set_supports_intersection():
    a: AspectSet = frozenset({"a", "b"})
    b: AspectSet = frozenset({"b", "c"})
    assert a & b == frozenset({"b"})


def test_aspect_set_empty_literal():
    empty: AspectSet = frozenset()
    assert len(empty) == 0
    assert empty | empty == empty
    assert empty & frozenset({"x"}) == empty


# ---------- New constructor surface ----------


def test_aspect_set_variadic_constructor():
    a = AspectSet("calibrated", "ICRP103")
    assert a == frozenset({"calibrated", "ICRP103"})
    assert isinstance(a, AspectSet)
    assert isinstance(a, frozenset)


def test_aspect_set_empty_constructor():
    empty = AspectSet()
    assert len(empty) == 0
    assert empty == frozenset()
    assert isinstance(empty, AspectSet)


def test_aspect_set_single_string_is_one_aspect_not_iterated():
    # Critical: AspectSet("calibrated") must NOT be expanded into
    # individual characters.
    a = AspectSet("calibrated")
    assert a == frozenset({"calibrated"})
    assert len(a) == 1


def test_aspect_set_from_set_literal():
    a = AspectSet({"calibrated", "ICRP103"})
    assert a == frozenset({"calibrated", "ICRP103"})


def test_aspect_set_from_list():
    a = AspectSet(["calibrated", "ICRP103"])
    assert a == frozenset({"calibrated", "ICRP103"})


def test_aspect_set_from_frozenset():
    src = frozenset({"calibrated", "ICRP103"})
    a = AspectSet(src)
    assert a == src
    assert isinstance(a, AspectSet)


def test_aspect_set_deduplicates_variadic_arguments():
    a = AspectSet("calibrated", "calibrated", "ICRP103")
    assert a == frozenset({"calibrated", "ICRP103"})
    assert len(a) == 2


def test_aspect_set_equality_with_plain_frozenset():
    # AspectSet ↔ frozenset interop matters because internal call sites
    # accept either, and join/intersect operations return plain frozensets.
    a = AspectSet("calibrated")
    b = frozenset({"calibrated"})
    assert a == b
    assert b == a
    assert hash(a) == hash(b)


def test_aspect_set_set_algebra_returns_frozenset():
    # Documented limitation: set operations inherit frozenset semantics
    # and return plain frozenset. This is fine because every internal
    # surface accepts frozenset[str].
    a = AspectSet("a", "b")
    b = AspectSet("b", "c")
    union = a | b
    intersection = a & b
    assert union == frozenset({"a", "b", "c"})
    assert intersection == frozenset({"b"})


def test_aspect_set_subclass_compatible_with_internal_signatures():
    # An AspectSet must drop into any place that expects frozenset[str].
    from ucon.aspects import join_aspects

    a = AspectSet("calibrated", "ICRP103")
    b = AspectSet("calibrated", "smoothed")
    assert join_aspects(a, b) == frozenset({"calibrated"})


def test_aspect_set_is_hashable_under_new_class():
    a = AspectSet("calibrated", "ICRP103")
    {a: 1}
    {a}

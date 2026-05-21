# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for the AspectSet type alias.

`AspectSet` is `frozenset[str]` (declared as `typing.FrozenSet[str]` for
3.7 compatibility). These tests pin behaviour the rest of the aspect
machinery relies on: hashability, immutability, set algebra, and the
fact that literals are usable directly without a wrapper class.
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

# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Number-level aspect arithmetic (A4 of the aspect stratum, #296).

The ADR 008 case studies, run through the real operators: equal-carry
addition, same-kind/different-standard refusal, the carry rule on
products (surviving kind degradation), the round trip back, and
single-operand threading through every representation change.
"""

from __future__ import annotations

import warnings

import pytest

import ucon
from ucon import Aspect, AspectRefused, Number, units
from ucon.core import Ratio
from ucon.dimension import LENGTH, TIME
from ucon.kinds import Kind
from ucon.system import Bridge, use


SPECIFIC_ENERGY_DIM = (LENGTH ** 2) / (TIME ** 2)


def _radsafe():
    family = Aspect("weighting_standard",
                    applies_to=frozenset({"dose_equivalent"}))
    icrp60 = Aspect("icrp60", parent=family)
    icrp103 = Aspect("icrp103", parent=family)
    dose_eq = Kind("dose_equivalent", dimension=SPECIFIC_ENERGY_DIM)
    return family, icrp60, icrp103, dose_eq


def _coverage():
    coverage = Aspect("coverage", applies_to=frozenset({"*"}))
    return coverage, Aspect("k2", parent=coverage)


# ---------- addition / subtraction ----------

def test_case_1a_equal_positions_add():
    _, _, icrp103, dose_eq = _radsafe()
    a = Number(2.0, units.gray, kind=dose_eq, aspects=[icrp103])
    b = Number(3.0, units.gray, kind=dose_eq, aspects=[icrp103])
    total = a + b
    assert total.quantity == 5.0
    assert total.aspects == frozenset({icrp103})
    assert total.kind == dose_eq


def test_case_1b_same_kind_different_standard_refuses():
    """The motivating case: same dimension, same unit, same kind — and
    the sum still conforms to neither standard."""
    _, icrp60, icrp103, dose_eq = _radsafe()
    a = Number(2.0, units.gray, kind=dose_eq, aspects=[icrp103])
    c = Number(3.0, units.gray, kind=dose_eq, aspects=[icrp60])
    with pytest.raises(AspectRefused):
        a + c
    with pytest.raises(AspectRefused):
        a - c


def test_partial_add_refuses_under_ambient_strict():
    """The default context is strict: silence is not agreement."""
    _, _, icrp103, dose_eq = _radsafe()
    a = Number(2.0, units.gray, kind=dose_eq, aspects=[icrp103])
    b = Number(1.0, units.gray, kind=dose_eq)
    with pytest.raises(AspectRefused):
        a + b


def test_partial_add_inherits_with_warning_under_permissive():
    _, _, icrp103, dose_eq = _radsafe()
    a = Number(2.0, units.gray, kind=dose_eq, aspects=[icrp103])
    b = Number(1.0, units.gray, kind=dose_eq)
    with use(ucon.active_system(), strict=False):
        with pytest.warns(UserWarning, match="aspect-silent"):
            total = a + b
    assert total.aspects == frozenset({icrp103})


# ---------- multiplication / division: the carry rule ----------

def test_case_1c_carry_survives_kind_degradation():
    """Multiplying by an unqualified factor: the kind may degrade, but
    the weighting standard rides the product."""
    _, _, icrp103, dose_eq = _radsafe()
    a = Number(2.0, units.gray, kind=dose_eq, aspects=[icrp103])
    t = units.second(2)
    with use(ucon.active_system(), strict=False):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            prod = a * t
    assert prod.kind is None                      # degraded
    assert prod.aspects == frozenset({icrp103})   # carried — out of scope


def test_case_1d_round_trip_restores():
    _, _, icrp103, dose_eq = _radsafe()
    a = Number(2.0, units.gray, kind=dose_eq, aspects=[icrp103])
    t = units.second(2)
    with use(ucon.active_system(), strict=False):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            back = (a * t) / t
    assert back.quantity == 2.0
    assert back.aspects == frozenset({icrp103})


def test_case_1e_refusal_survives_degradation():
    """Two products whose kinds both degraded to None still refuse to
    add: the aspect verdict never depended on the kinds."""
    _, icrp60, icrp103, dose_eq = _radsafe()
    a = Number(2.0, units.gray, kind=dose_eq, aspects=[icrp103])
    c = Number(3.0, units.gray, kind=dose_eq, aspects=[icrp60])
    t = units.second(2)
    with use(ucon.active_system(), strict=False):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            p1, p2 = a * t, c * t
        assert p1.kind is None and p2.kind is None
        with pytest.raises(AspectRefused):
            p1 + p2


def test_dimensionless_ratio_carries():
    _, _, icrp103, dose_eq = _radsafe()
    a = Number(2.0, units.gray, kind=dose_eq, aspects=[icrp103])
    b = Number(4.0, units.gray, kind=dose_eq, aspects=[icrp103])
    ratio = a / b
    assert not ratio.unit.dimension
    assert ratio.aspects == frozenset({icrp103})


def test_ratio_evaluate_carries():
    _, k2 = _coverage()
    num = Number(1.0, units.meter, aspects=[k2])
    assert Ratio(num, units.second(2)).evaluate().aspects == frozenset({k2})


# ---------- single-operand threading ----------

def test_scalar_ops_thread():
    _, k2 = _coverage()
    n = Number(0.1, units.meter, aspects=[k2])
    assert (n * 3).aspects == frozenset({k2})
    assert (n / 3).aspects == frozenset({k2})


def test_pow_threads():
    _, k2 = _coverage()
    n = Number(0.1, units.meter, aspects=[k2])
    assert (n ** 2).aspects == frozenset({k2})


def test_to_threads():
    _, k2 = _coverage()
    n = Number(5.0, units.meter, aspects=[k2])
    assert n.to("km").aspects == frozenset({k2})
    assert n.to("km").quantity == 0.005


def test_simplify_and_to_base_thread():
    _, k2 = _coverage()
    from ucon import Scale
    km = Scale.kilo * units.meter
    n = Number(5.0, km, aspects=[k2])
    assert n.simplify().aspects == frozenset({k2})
    assert n.to_base().aspects == frozenset({k2})


def test_adopt_threads():
    _, k2 = _coverage()
    s = ucon.active_system()
    n = Number(5.0, s.units["meter"], aspects=[k2])
    assert s.adopt(n).aspects == frozenset({k2})


def test_identity_bridge_threads():
    _, k2 = _coverage()
    s = ucon.active_system()
    n = Number(5.0, s.units["meter"], aspects=[k2])
    assert Bridge(src=s, dst=s).apply(n).aspects == frozenset({k2})


def test_unaspected_arithmetic_untouched():
    """Zero-aspect operations produce zero-aspect results with no
    resolution machinery in the way."""
    total = units.meter(2) + units.meter(3)
    assert total.aspects == frozenset()
    assert repr(total) == "<5 m>"

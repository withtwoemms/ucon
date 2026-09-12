# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for Number.aspects (A3 of the aspect stratum, #296).

The field is additive — ``Number.kind`` and every existing idiom are
untouched — and ``applies_to`` is enforced at construction, the one
sanctioned kind-read in the aspect layer (ADR 008 §5): a false claim
refuses at the moment it is made.
"""

from __future__ import annotations

import pytest

from ucon import Aspect, AspectNotApplicable, Number, units
from ucon.dimension import LENGTH, MASS, TIME
from ucon.kinds import Kind

ENERGY_DIM = (LENGTH ** 2) * MASS / (TIME ** 2)
SPECIFIC_ENERGY_DIM = (LENGTH ** 2) / (TIME ** 2)


def _weighting_family():
    family = Aspect("weighting_standard",
                    applies_to=frozenset({"dose_equivalent"}))
    return family, Aspect("icrp103", parent=family)


# ---------- attachment ----------

def test_defaults_to_empty_frozenset():
    n = Number(5.0, units.meter)
    assert n.aspects == frozenset()
    assert isinstance(n.aspects, frozenset)


def test_iterable_coerced_to_frozenset():
    calibrated = Aspect("calibrated")
    n = Number(5.0, units.meter, aspects=[calibrated])
    assert isinstance(n.aspects, frozenset)
    assert n.aspects == frozenset({calibrated})


def test_kind_and_aspect_together():
    """The overwhelming case: aspects qualify a kinded quantity."""
    _, icrp103 = _weighting_family()
    dose_eq = Kind("dose_equivalent", dimension=SPECIFIC_ENERGY_DIM)
    n = Number(2.0, units.gray, kind=dose_eq, aspects=[icrp103])
    assert n.kind is dose_eq
    assert icrp103 in n.aspects


def test_wildcard_family_attaches_to_unkinded():
    """applies_to = {'*'}: kind-independent (coverage factor)."""
    coverage = Aspect("coverage", applies_to=frozenset({"*"}))
    k2 = Aspect("k2", parent=coverage)
    n = Number(5.0, units.meter, aspects=[k2])
    assert n.kind is None
    assert k2 in n.aspects


def test_unrestricted_family_attaches_anywhere():
    """An empty applies_to means the author declared no restriction."""
    calibrated = Aspect("calibrated")
    n = Number(5.0, units.meter, aspects=[calibrated])
    assert calibrated in n.aspects


# ---------- applies_to refusals ----------

def test_restricted_family_on_wrong_kind_refuses():
    """ADR case 1f: a weighting standard on absorbed dose asserts
    something false, and the error fires when the claim is made."""
    family, icrp103 = _weighting_family()
    absorbed = Kind("absorbed_dose", dimension=SPECIFIC_ENERGY_DIM)
    with pytest.raises(AspectNotApplicable) as exc_info:
        Number(1.5, units.gray, kind=absorbed, aspects=[icrp103])
    exc = exc_info.value
    assert exc.family is family
    assert exc.kind is absorbed
    assert "weighting_standard" in str(exc)
    assert "absorbed_dose" in str(exc)


def test_restricted_family_on_unkinded_refuses():
    _, icrp103 = _weighting_family()
    with pytest.raises(AspectNotApplicable) as exc_info:
        Number(1.5, units.gray, aspects=[icrp103])
    assert exc_info.value.kind is None
    assert "<unkinded>" in str(exc_info.value)


def test_child_attachment_checked_against_family_root():
    """The restriction lives on the root; deep children inherit it."""
    family = Aspect("weighting_standard",
                    applies_to=frozenset({"dose_equivalent"}))
    icrp = Aspect("icrp", parent=family)
    icrp103 = Aspect("icrp103", parent=icrp)
    with pytest.raises(AspectNotApplicable):
        Number(1.0, units.gray, aspects=[icrp103])


# ---------- untouched neighbors ----------

def test_kind_dimension_mismatch_still_fires_first():
    from ucon.core.exceptions import KindDimensionMismatch
    energy = Kind("energy", dimension=ENERGY_DIM)
    with pytest.raises(KindDimensionMismatch):
        Number(1.0, units.meter, kind=energy)


def test_repr_appends_sorted_aspect_tokens():
    cov = Aspect("coverage", applies_to=frozenset({"*"}))
    k2 = Aspect("k2", parent=cov)
    calibrated = Aspect("calibrated")
    n = Number(5.0, units.meter, aspects=[k2, calibrated])
    assert repr(n) == "<5.0 m #calibrated #k2>"


def test_repr_unchanged_without_aspects():
    n = Number(2.5, units.meter) / Number(1.0, units.second)
    assert repr(n) == "<2.5 m/s>"

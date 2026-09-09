# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Regression guard for mechanical-CGS base_forms (issue #283).

``base_form is None`` historically conflated three unrelated causes:
chart structure (celsius, dB — no factorization exists), basis scoping
(dyne — an exact factorization exists but was never recorded), and
pseudo-dimensions (degree). The resolution: populate exact SI-factored
base_forms for the purely multiplicative CGS-mechanical units, so that
``None`` carries meaning (no factorization exists, or the factorization
is dimensionally ill-typed across bases) rather than accident.

The electromagnetic CGS units stay ``None`` deliberately: their
dimensional exponents differ from SI's, and conversion routes through
``RebasedUnit`` edges.
"""

import pytest

from ucon import Number, units


# name -> (prefactor, {base unit name: exponent}) — all exact by definition
MECHANICAL_CGS = {
    "dyne":    (1e-05,   {"meter": 1.0, "kilogram": 1.0, "second": -2.0}),
    "erg":     (1e-07,   {"meter": 2.0, "kilogram": 1.0, "second": -2.0}),
    "poise":   (0.1,     {"kilogram": 1.0, "meter": -1.0, "second": -1.0}),
    "stokes":  (0.0001,  {"meter": 2.0, "second": -1.0}),
    "barye":   (0.1,     {"kilogram": 1.0, "meter": -1.0, "second": -2.0}),
    "galileo": (0.01,    {"meter": 1.0, "second": -2.0}),
    "kayser":  (100.0,   {"meter": -1.0}),
    "langley": (41840.0, {"kilogram": 1.0, "second": -2.0}),
}

# EM CGS units whose base_form must STAY None (cross-basis scoping)
EM_CGS_NULL = (
    "gauss", "maxwell", "oersted", "statvolt", "statohm", "statampere",
    "statcoulomb", "statfarad", "abvolt", "abohm", "abcoulomb", "abfarad",
    "abhenry", "biot", "gilbert", "debye",
)


@pytest.mark.parametrize("name", sorted(MECHANICAL_CGS))
def test_mechanical_cgs_base_form_exact(name):
    prefactor, factors = MECHANICAL_CGS[name]
    bf = getattr(units, name).base_form
    assert bf is not None, f"{name} should carry an SI-factored base_form"
    assert bf.prefactor == prefactor
    assert {u.name: e for u, e in bf.factors} == factors


@pytest.mark.parametrize("name", EM_CGS_NULL)
def test_em_cgs_base_form_stays_none(name):
    unit = getattr(units, name, None)
    if unit is None:
        pytest.skip(f"{name} not in catalog")
    assert unit.base_form is None, (
        f"{name} is a cross-basis EM unit; its base_form must stay None "
        "(conversion routes through RebasedUnit edges)"
    )


def test_dyne_conversion_unchanged():
    """The graph edge route that always worked keeps working."""
    result = Number(1, units.dyne).to(units.newton)
    assert result.quantity == pytest.approx(1e-05, rel=1e-12)


def test_affine_and_log_units_stay_none():
    """Chart-structural None is untouched."""
    for name in ("celsius", "fahrenheit", "decibel", "pH"):
        assert getattr(units, name).base_form is None

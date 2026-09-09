# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Regression guard for customary-unit prefactors (issue #278).

Every US-customary / imperial prefactor in the catalog must equal the value
derived from four exact seeds — inch 0.0254 m, pound 0.45359237 kg (both
fixed by the 1959 international yard-and-pound agreement), the US gallon
231 in^3, and the imperial gallon 4.54609e-3 m^3 — composed in ``Fraction``
and converted to float exactly once. The catalog historically stored
independently sourced literals per unit, which drifted in families (a
corrupted seed propagates to everything derived from it); deriving here
means any future drift fails this test naming the exact unit.
"""

import os
import sys
from fractions import Fraction as F

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# ---- exact seeds -----------------------------------------------------------
INCH = F(254, 10000)                      # 1959 yard-and-pound agreement
POUND = F(45359237, 100000000)            # 1959 yard-and-pound agreement
US_GALLON = 231 * INCH**3                 # statutory definition
IMP_GALLON = F(454609, 100000000)         # UK Weights and Measures Act 1985
G0 = F(980665, 100000)                    # standard gravity, exact by definition

FOOT = 12 * INCH
YARD = 36 * INCH
MILE = 63360 * INCH
LBF = POUND * G0

# unit name -> exact SI value of one unit, as a Fraction
EXACT = {
    # length
    "inch": INCH,
    "foot": FOOT,
    "yard": YARD,
    "mile": MILE,
    "mil": INCH / 1000,
    "hand": 4 * INCH,
    "fathom": 6 * FOOT,
    "chain": 66 * FOOT,
    "furlong": 660 * FOOT,
    "league": 3 * MILE,
    "point": INCH / 72,
    "pica": INCH / 6,
    "nautical_mile": F(1852),
    "cable": F(1852) / 10,
    # mass
    "pound": POUND,
    "ounce": POUND / 16,
    "dram": POUND / 256,
    "grain": POUND / 7000,
    "pennyweight": 24 * POUND / 7000,
    "stone": 14 * POUND,
    "short_ton": 2000 * POUND,
    "long_ton": 2240 * POUND,
    "slug": LBF / FOOT,
    # US volume
    "gallon": US_GALLON,
    "quart": US_GALLON / 4,
    "pint": US_GALLON / 8,
    "cup": US_GALLON / 16,
    "gill": US_GALLON / 32,
    "fluid_ounce": US_GALLON / 128,
    "tablespoon": US_GALLON / 256,
    "teaspoon": US_GALLON / 768,
    "minim": US_GALLON / 61440,
    "barrel": 42 * US_GALLON,
    # imperial volume
    "imperial_gallon": IMP_GALLON,
    "imperial_pint": IMP_GALLON / 8,
    # area / derived
    "acre": 43560 * FOOT**2,
    "square_foot": FOOT**2,
    "cubic_foot": FOOT**3,
    "cubic_inch": INCH**3,
    # force / pressure / energy
    "pound_force": LBF,
    "poundal": POUND * FOOT,
    "psi": LBF / INCH**2,
    "ksi": 1000 * LBF / INCH**2,
    "kip": 1000 * LBF,
    "foot_pound": LBF * FOOT,
}

# edges whose factor is derivable from the same seeds:
# factor = SI value of one src, expressed in dst
_SI_ANCHORS = {
    "meter": F(1), "kilogram": F(1), "liter": F(1, 1000),
    "newton": F(1), "pascal": F(1), "joule": F(1),
}


def _catalog():
    path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir,
                        "ucon", "comprehensive.ucon.toml")
    with open(path, "rb") as f:
        return tomllib.load(f)


_DATA = _catalog()
_UNITS = {u["name"]: u for u in _DATA.get("units", [])}
_PRESENT = sorted(set(EXACT) & set(_UNITS))


@pytest.mark.parametrize("name", _PRESENT)
def test_prefactor_matches_exact_derivation(name):
    base_form = _UNITS[name].get("base_form")
    assert base_form is not None, f"{name} has no base_form in the catalog"
    expected = float(EXACT[name])
    assert base_form["prefactor"] == expected, (
        f"{name}: catalog ships {base_form['prefactor']!r}, exact derivation "
        f"from seeds gives {expected!r}"
    )


def test_all_expected_units_present():
    # If a customary unit is renamed or removed, surface it here rather than
    # silently shrinking coverage.
    missing = sorted(set(_PRESENT) ^ (set(EXACT) & set(_UNITS)))
    assert not missing


def test_edge_factors_match_exact_derivation():
    values = dict(EXACT)
    values.update(_SI_ANCHORS)
    checked = 0
    for edge in _DATA.get("edges", []):
        src, dst = edge.get("src"), edge.get("dst")
        if src in values and dst in values:
            expected = float(values[src] / values[dst])
            assert edge["factor"] == pytest.approx(expected, rel=1e-15, abs=0.0), (
                f"edge {src} -> {dst}: catalog ships {edge['factor']!r}, "
                f"exact derivation gives {expected!r}"
            )
            checked += 1
    assert checked >= 30  # the customary web is well-connected; keep it audited


def test_seed_values_are_the_statutory_ones():
    # The four seeds, spelled out so a typo in EXACT itself cannot hide.
    assert float(INCH) == 0.0254
    assert float(POUND) == 0.45359237
    assert float(US_GALLON) == 0.003785411784
    assert float(IMP_GALLON) == 0.00454609

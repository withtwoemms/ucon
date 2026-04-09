# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for BaseForm, UnitProduct.to_base_form(), and the arithmetic
regressions that motivated the base-unit decomposition feature.

In v1.3.0, ``BaseForm`` is *definitional*: it is set on each ``Unit`` at
construction time in ``ucon/units.py`` and never mutated thereafter.
The previous v1.2.x behavior populated this field lazily by walking the
``ConversionGraph`` after import; that mechanism (and the ``_ensure_graph``
autouse fixture it required) is gone.

The ``TestNoGraphInit`` class below proves the new property: arithmetic
on quantities works *without* the default ``ConversionGraph`` ever being
materialized.
"""

import math
import subprocess
import sys

import pytest

from ucon import Scale, Number, Ratio
from ucon import units
from ucon.core import BaseForm, UnitProduct, UnitFactor


# -----------------------------------------------------------------------
# TestNoGraphInit — graph independence regression net
# -----------------------------------------------------------------------

class TestNoGraphInit:
    """Verify that base_form works WITHOUT initializing the default graph.

    These tests prove that v1.3.0's definitional ``base_form`` is independent
    of the conversion graph. They monkeypatch out the cached default graph
    and assert that core arithmetic still works.
    """

    def test_kilogram_base_form_no_graph(self, monkeypatch):
        from ucon import graph as graph_mod
        monkeypatch.setattr(graph_mod, '_default_graph', None, raising=False)
        assert units.kilogram.base_form is not None
        assert units.kilogram.base_form.prefactor == 1.0

    def test_canonical_magnitude_no_graph(self, monkeypatch):
        from ucon import graph as graph_mod
        monkeypatch.setattr(graph_mod, '_default_graph', None, raising=False)
        n = units.gram(1000)
        assert abs(n._canonical_magnitude - 1.0) < 1e-12

    def test_arithmetic_no_graph(self, monkeypatch):
        from ucon import graph as graph_mod
        monkeypatch.setattr(graph_mod, '_default_graph', None, raising=False)
        n = units.newton(1)
        d = (Scale.kilo * units.gram * units.meter / units.second ** 2)(1)
        assert n == d  # must work with no graph initialized

    def test_cold_start_subprocess(self):
        """A truly fresh interpreter must not need the default graph for
        ``units.gram(1000) == units.kilogram(1)`` to hold.

        Subprocess isolation guarantees no test-suite import has already
        triggered graph construction as a side effect.
        """
        code = (
            "from ucon import units; "
            "assert units.gram(1000) == units.kilogram(1)"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"cold-start smoke test failed:\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )


# -----------------------------------------------------------------------
# BaseForm field tests
# -----------------------------------------------------------------------

class TestBaseFormField:
    """Verify base_form is set correctly on standard units."""

    def test_kilogram_prefactor(self):
        assert units.kilogram.base_form is not None
        assert units.kilogram.base_form.prefactor == 1.0

    def test_kilogram_factors(self):
        bf = units.kilogram.base_form
        assert len(bf.factors) == 1
        assert bf.factors[0] == (units.kilogram, 1.0)

    def test_gram_prefactor(self):
        bf = units.gram.base_form
        assert bf is not None
        assert abs(bf.prefactor - 0.001) < 1e-12

    def test_meter_prefactor(self):
        bf = units.meter.base_form
        assert bf is not None
        assert bf.prefactor == 1.0

    def test_second_prefactor(self):
        bf = units.second.base_form
        assert bf is not None
        assert bf.prefactor == 1.0

    def test_pascal_prefactor(self):
        bf = units.pascal.base_form
        assert bf is not None
        assert abs(bf.prefactor - 1.0) < 1e-12

    def test_pascal_factors(self):
        bf = units.pascal.base_form
        factor_dict = dict(bf.factors)
        assert abs(factor_dict[units.kilogram] - 1.0) < 1e-12
        assert abs(factor_dict[units.meter] - (-1.0)) < 1e-12
        assert abs(factor_dict[units.second] - (-2.0)) < 1e-12

    def test_bar_prefactor(self):
        bf = units.bar.base_form
        assert bf is not None
        assert abs(bf.prefactor - 100000.0) < 1e-6

    def test_foot_prefactor(self):
        bf = units.foot.base_form
        assert bf is not None
        assert abs(bf.prefactor - 0.3048) < 1e-6

    def test_calorie_prefactor(self):
        bf = units.calorie.base_form
        assert bf is not None
        assert abs(bf.prefactor - 4.184) < 1e-6

    def test_newton_prefactor(self):
        bf = units.newton.base_form
        assert bf is not None
        assert abs(bf.prefactor - 1.0) < 1e-12

    def test_joule_prefactor(self):
        bf = units.joule.base_form
        assert bf is not None
        assert abs(bf.prefactor - 1.0) < 1e-12

    def test_watt_prefactor(self):
        bf = units.watt.base_form
        assert bf is not None
        assert abs(bf.prefactor - 1.0) < 1e-12

    def test_dimensionless_unit_has_no_base_form(self):
        from ucon.core import Unit
        u = Unit()
        assert u.base_form is None

    def test_celsius_has_no_base_form(self):
        """Affine units cannot be expressed as (prefactor, factors)."""
        assert units.celsius.base_form is None

    def test_fahrenheit_has_no_base_form(self):
        assert units.fahrenheit.base_form is None


# -----------------------------------------------------------------------
# to_base_form() tests
# -----------------------------------------------------------------------

class TestToBaseForm:
    """Verify UnitProduct.to_base_form() algebraic expansion."""

    def test_pascal_times_second(self):
        """Pa·s should expand to kg·m⁻¹·s⁻¹ with prefactor 1.0."""
        up = units.pascal * units.second
        base_factors, prefactor = up.to_base_form()
        assert abs(prefactor - 1.0) < 1e-12
        assert abs(base_factors[units.kilogram] - 1.0) < 1e-12
        assert abs(base_factors[units.meter] - (-1.0)) < 1e-12
        assert abs(base_factors[units.second] - (-1.0)) < 1e-12

    def test_kg_m_per_s_squared(self):
        """kg·m/s² should expand to {kg:1, m:1, s:-2} with prefactor 1.0."""
        up = UnitProduct({
            UnitFactor(units.kilogram, Scale.one): 1,
            UnitFactor(units.meter, Scale.one): 1,
            UnitFactor(units.second, Scale.one): -2,
        })
        base_factors, prefactor = up.to_base_form()
        assert abs(prefactor - 1.0) < 1e-12
        assert abs(base_factors[units.kilogram] - 1.0) < 1e-12
        assert abs(base_factors[units.meter] - 1.0) < 1e-12
        assert abs(base_factors[units.second] - (-2.0)) < 1e-12

    def test_bar_times_second(self):
        """bar·s should have prefactor 100000."""
        up = units.bar * units.second
        base_factors, prefactor = up.to_base_form()
        assert abs(prefactor - 100000.0) < 1e-6
        assert abs(base_factors[units.kilogram] - 1.0) < 1e-12
        assert abs(base_factors[units.meter] - (-1.0)) < 1e-12
        assert abs(base_factors[units.second] - (-1.0)) < 1e-12

    def test_kilo_gram_product(self):
        """kilo*gram should have prefactor 1.0 (= 1 kg in base units)."""
        up = Scale.kilo * units.gram
        _, prefactor = up.to_base_form()
        # kilo * gram: scale=kilo (1000), gram base_form prefactor=0.001
        # total = 1000 * 0.001 = 1.0
        assert abs(prefactor - 1.0) < 1e-12


# -----------------------------------------------------------------------
# Arithmetic regression tests (the motivation for this feature)
# -----------------------------------------------------------------------

class TestArithmeticRegressions:
    """Verify that derived ÷ base-unit expression gives correct dimensionless results."""

    def test_newton_div_kg_m_per_s2(self):
        """N ÷ (kg·m/s²) should equal 1.0."""
        n = units.newton(1)
        d = (Scale.kilo * units.gram * units.meter / units.second ** 2)(1)
        result = n / d
        assert abs(result.quantity - 1.0) < 1e-9

    def test_pascal_div_kg_per_m_s2(self):
        """Pa ÷ (kg/(m·s²)) should equal 1.0."""
        n = units.pascal(1)
        d = (Scale.kilo * units.gram / (units.meter * units.second ** 2))(1)
        result = n / d
        assert abs(result.quantity - 1.0) < 1e-9

    def test_joule_div_kg_m2_per_s2(self):
        """J ÷ (kg·m²/s²) should equal 1.0."""
        n = units.joule(1)
        d = (Scale.kilo * units.gram * units.meter ** 2 / units.second ** 2)(1)
        result = n / d
        assert abs(result.quantity - 1.0) < 1e-9

    def test_watt_div_kg_m2_per_s3(self):
        """W ÷ (kg·m²/s³) should equal 1.0."""
        n = units.watt(1)
        d = (Scale.kilo * units.gram * units.meter ** 2 / units.second ** 3)(1)
        result = n / d
        assert abs(result.quantity - 1.0) < 1e-9

    def test_1000g_eq_1kg(self):
        """1000 g == 1 kg (cross-unit equality via _canonical_magnitude)."""
        assert units.gram(1000) == units.kilogram(1)

    def test_1N_eq_1_kg_m_per_s2(self):
        """1 N == 1 kg·m/s² (derived unit identity)."""
        n = units.newton(1)
        d = (Scale.kilo * units.gram * units.meter / units.second ** 2)(1)
        assert n == d

    def test_500g_div_1kg(self):
        """500 g / 1 kg should equal 0.5 (existing behavior preserved)."""
        result = units.gram(500) / units.kilogram(1)
        assert abs(result.quantity - 0.5) < 1e-12

    def test_km_simplify(self):
        """km(5).simplify() should give 5000 m (simplify unchanged)."""
        km = Scale.kilo * units.meter
        result = km(5).simplify()
        assert abs(result.quantity - 5000.0) < 1e-12

    def test_ratio_newton_over_kg_m_s2(self):
        """Ratio(N(1), kg·m/s²(1)).evaluate().quantity should be 1.0."""
        n = units.newton(1)
        d = (Scale.kilo * units.gram * units.meter / units.second ** 2)(1)
        r = Ratio(n, d)
        result = r.evaluate()
        assert abs(result.quantity - 1.0) < 1e-9

    def test_reynolds_number(self):
        """Reynolds number: ρ·v·L / μ for water at standard conditions.

        ρ = 1000 kg/m³, v = 1 m/s, L = 0.1 m, μ = 0.001 Pa·s
        Re = 1000 * 1 * 0.1 / 0.001 = 100000
        """
        rho = (Scale.kilo * units.gram / units.meter ** 3)(1000)
        v = (units.meter / units.second)(1)
        L = units.meter(0.1)
        mu = units.pascal_second(0.001)
        Re = (rho * v * L) / mu
        assert abs(Re.quantity - 100000.0) < 1e-6

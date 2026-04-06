# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for BaseDecomposition, UnitProduct.to_base_form(), and the arithmetic
regressions that motivated the base-unit decomposition feature.
"""

import math
import pytest

from ucon import Scale, Number, Ratio
from ucon import units
from ucon.core import BaseDecomposition, UnitProduct, UnitFactor
from ucon.graph import get_default_graph


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _ensure_graph():
    """Ensure the default graph (and therefore decompositions) is built."""
    get_default_graph()


# -----------------------------------------------------------------------
# BaseDecomposition field tests
# -----------------------------------------------------------------------

class TestBaseDecompositionField:
    """Verify _base_decomposition is set correctly on standard units."""

    def test_kilogram_prefactor(self):
        assert units.kilogram._base_decomposition is not None
        assert units.kilogram._base_decomposition.prefactor == 1.0

    def test_kilogram_factors(self):
        decomp = units.kilogram._base_decomposition
        assert len(decomp.factors) == 1
        assert decomp.factors[0] == (units.kilogram, 1.0)

    def test_gram_prefactor(self):
        decomp = units.gram._base_decomposition
        assert decomp is not None
        assert abs(decomp.prefactor - 0.001) < 1e-12

    def test_meter_prefactor(self):
        decomp = units.meter._base_decomposition
        assert decomp is not None
        assert decomp.prefactor == 1.0

    def test_second_prefactor(self):
        decomp = units.second._base_decomposition
        assert decomp is not None
        assert decomp.prefactor == 1.0

    def test_pascal_prefactor(self):
        decomp = units.pascal._base_decomposition
        assert decomp is not None
        assert abs(decomp.prefactor - 1.0) < 1e-12

    def test_pascal_factors(self):
        decomp = units.pascal._base_decomposition
        factor_dict = dict(decomp.factors)
        assert abs(factor_dict[units.kilogram] - 1.0) < 1e-12
        assert abs(factor_dict[units.meter] - (-1.0)) < 1e-12
        assert abs(factor_dict[units.second] - (-2.0)) < 1e-12

    def test_bar_prefactor(self):
        decomp = units.bar._base_decomposition
        assert decomp is not None
        assert abs(decomp.prefactor - 100000.0) < 1e-6

    def test_foot_prefactor(self):
        decomp = units.foot._base_decomposition
        assert decomp is not None
        assert abs(decomp.prefactor - 0.3048) < 1e-6

    def test_calorie_prefactor(self):
        decomp = units.calorie._base_decomposition
        assert decomp is not None
        assert abs(decomp.prefactor - 4.184) < 1e-6

    def test_newton_prefactor(self):
        decomp = units.newton._base_decomposition
        assert decomp is not None
        assert abs(decomp.prefactor - 1.0) < 1e-12

    def test_joule_prefactor(self):
        decomp = units.joule._base_decomposition
        assert decomp is not None
        assert abs(decomp.prefactor - 1.0) < 1e-12

    def test_watt_prefactor(self):
        decomp = units.watt._base_decomposition
        assert decomp is not None
        assert abs(decomp.prefactor - 1.0) < 1e-12

    def test_dimensionless_unit_has_no_decomposition(self):
        from ucon.core import Unit
        u = Unit()
        assert u._base_decomposition is None


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
        # kilo * gram: scale=kilo (1000), gram decomp prefactor=0.001
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

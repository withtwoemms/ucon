# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for v0.5.x uncertainty propagation.

Tests Number construction with uncertainty, display formatting,
arithmetic propagation, and conversion propagation.
"""

import math
import unittest

from ucon import units, Scale
from ucon.core import Number, UnitProduct


class TestUncertaintyConstruction(unittest.TestCase):
    """Test constructing Numbers with uncertainty."""

    def test_number_with_uncertainty(self):
        n = units.meter(1.234, uncertainty=0.005)
        self.assertEqual(n.value, 1.234)
        self.assertEqual(n.uncertainty, 0.005)

    def test_number_without_uncertainty(self):
        n = units.meter(1.234)
        self.assertEqual(n.value, 1.234)
        self.assertIsNone(n.uncertainty)

    def test_unit_product_callable_with_uncertainty(self):
        km = Scale.kilo * units.meter
        n = km(5.0, uncertainty=0.1)
        self.assertEqual(n.value, 5.0)
        self.assertEqual(n.uncertainty, 0.1)

    def test_composite_unit_with_uncertainty(self):
        mps = units.meter / units.second
        n = mps(10.0, uncertainty=0.5)
        self.assertEqual(n.value, 10.0)
        self.assertEqual(n.uncertainty, 0.5)


class TestUncertaintyDisplay(unittest.TestCase):
    """Test display formatting with uncertainty."""

    def test_repr_with_uncertainty(self):
        n = units.meter(1.234, uncertainty=0.005)
        r = repr(n)
        self.assertIn("1.234", r)
        self.assertIn("±", r)
        self.assertIn("0.005", r)
        self.assertIn("m", r)

    def test_repr_without_uncertainty(self):
        n = units.meter(1.234)
        r = repr(n)
        self.assertIn("1.234", r)
        self.assertNotIn("±", r)

    def test_repr_dimensionless_with_uncertainty(self):
        n = Number(quantity=0.5, uncertainty=0.01)
        r = repr(n)
        self.assertIn("0.5", r)
        self.assertIn("±", r)
        self.assertIn("0.01", r)


class TestAdditionSubtractionPropagation(unittest.TestCase):
    """Test uncertainty propagation through addition and subtraction."""

    def test_addition_both_uncertain(self):
        a = units.meter(10.0, uncertainty=0.3)
        b = units.meter(5.0, uncertainty=0.4)
        c = a + b
        self.assertAlmostEqual(c.value, 15.0, places=9)
        # sqrt(0.3² + 0.4²) = sqrt(0.09 + 0.16) = sqrt(0.25) = 0.5
        self.assertAlmostEqual(c.uncertainty, 0.5, places=9)

    def test_subtraction_both_uncertain(self):
        a = units.meter(10.0, uncertainty=0.3)
        b = units.meter(5.0, uncertainty=0.4)
        c = a - b
        self.assertAlmostEqual(c.value, 5.0, places=9)
        # sqrt(0.3² + 0.4²) = 0.5
        self.assertAlmostEqual(c.uncertainty, 0.5, places=9)

    def test_addition_one_uncertain(self):
        a = units.meter(10.0, uncertainty=0.3)
        b = units.meter(5.0)  # no uncertainty
        c = a + b
        self.assertAlmostEqual(c.value, 15.0, places=9)
        self.assertAlmostEqual(c.uncertainty, 0.3, places=9)

    def test_addition_neither_uncertain(self):
        a = units.meter(10.0)
        b = units.meter(5.0)
        c = a + b
        self.assertAlmostEqual(c.value, 15.0, places=9)
        self.assertIsNone(c.uncertainty)


class TestMultiplicationPropagation(unittest.TestCase):
    """Test uncertainty propagation through multiplication."""

    def test_multiplication_both_uncertain(self):
        a = units.meter(10.0, uncertainty=0.2)  # 2% relative
        b = units.meter(5.0, uncertainty=0.15)  # 3% relative
        c = a * b
        self.assertAlmostEqual(c.value, 50.0, places=9)
        # relative: sqrt((0.2/10)² + (0.15/5)²) = sqrt(0.0004 + 0.0009) = sqrt(0.0013) ≈ 0.0361
        # absolute: 50 * 0.0361 ≈ 1.803
        expected = 50.0 * math.sqrt((0.2/10)**2 + (0.15/5)**2)
        self.assertAlmostEqual(c.uncertainty, expected, places=6)

    def test_multiplication_one_uncertain(self):
        a = units.meter(10.0, uncertainty=0.2)
        b = units.meter(5.0)  # no uncertainty
        c = a * b
        self.assertAlmostEqual(c.value, 50.0, places=9)
        # Only a contributes: |c| * (δa/a) = 50 * 0.02 = 1.0
        expected = 50.0 * (0.2/10)
        self.assertAlmostEqual(c.uncertainty, expected, places=9)

    def test_multiplication_neither_uncertain(self):
        a = units.meter(10.0)
        b = units.meter(5.0)
        c = a * b
        self.assertAlmostEqual(c.value, 50.0, places=9)
        self.assertIsNone(c.uncertainty)


class TestDivisionPropagation(unittest.TestCase):
    """Test uncertainty propagation through division."""

    def test_division_both_uncertain(self):
        a = units.meter(10.0, uncertainty=0.2)  # 2% relative
        b = units.second(2.0, uncertainty=0.04)  # 2% relative
        c = a / b
        self.assertAlmostEqual(c.value, 5.0, places=9)
        # relative: sqrt((0.2/10)² + (0.04/2)²) = sqrt(0.0004 + 0.0004) = sqrt(0.0008) ≈ 0.0283
        # absolute: 5 * 0.0283 ≈ 0.1414
        expected = 5.0 * math.sqrt((0.2/10)**2 + (0.04/2)**2)
        self.assertAlmostEqual(c.uncertainty, expected, places=6)

    def test_division_one_uncertain(self):
        a = units.meter(10.0, uncertainty=0.2)
        b = units.second(2.0)  # no uncertainty
        c = a / b
        self.assertAlmostEqual(c.value, 5.0, places=9)
        expected = 5.0 * (0.2/10)
        self.assertAlmostEqual(c.uncertainty, expected, places=9)

    def test_division_neither_uncertain(self):
        a = units.meter(10.0)
        b = units.second(2.0)
        c = a / b
        self.assertAlmostEqual(c.value, 5.0, places=9)
        self.assertIsNone(c.uncertainty)


class TestScalarOperations(unittest.TestCase):
    """Test uncertainty propagation with scalar multiplication/division."""

    def test_scalar_multiply_number(self):
        a = units.meter(10.0, uncertainty=0.2)
        c = a * 3  # scalar multiplication
        self.assertAlmostEqual(c.value, 30.0, places=9)
        self.assertAlmostEqual(c.uncertainty, 0.6, places=9)

    def test_scalar_divide_number(self):
        a = units.meter(10.0, uncertainty=0.2)
        c = a / 2  # scalar division
        self.assertAlmostEqual(c.value, 5.0, places=9)
        self.assertAlmostEqual(c.uncertainty, 0.1, places=9)


class TestConversionPropagation(unittest.TestCase):
    """Test uncertainty propagation through unit conversion."""

    def test_linear_conversion(self):
        # meter to foot: factor ≈ 3.28084
        length = units.meter(1.0, uncertainty=0.01)
        length_ft = length.to(units.foot)
        self.assertAlmostEqual(length_ft.value, 3.28084, places=4)
        # uncertainty scales by same factor
        self.assertAlmostEqual(length_ft.uncertainty, 0.01 * 3.28084, places=4)

    def test_affine_conversion(self):
        # Celsius to Kelvin: K = C + 273.15
        # Derivative is 1, so uncertainty unchanged
        temp = units.celsius(25.0, uncertainty=0.5)
        temp_k = temp.to(units.kelvin)
        self.assertAlmostEqual(temp_k.value, 298.15, places=9)
        self.assertAlmostEqual(temp_k.uncertainty, 0.5, places=9)

    def test_fahrenheit_to_celsius(self):
        # F to C: C = (F - 32) * 5/9
        # Derivative is 5/9 ≈ 0.5556
        temp = units.fahrenheit(100.0, uncertainty=1.0)
        temp_c = temp.to(units.celsius)
        self.assertAlmostEqual(temp_c.value, 37.7778, places=3)
        self.assertAlmostEqual(temp_c.uncertainty, 1.0 * (5/9), places=6)

    def test_conversion_without_uncertainty(self):
        length = units.meter(1.0)
        length_ft = length.to(units.foot)
        self.assertIsNone(length_ft.uncertainty)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases for uncertainty handling."""

    def test_zero_uncertainty(self):
        a = units.meter(10.0, uncertainty=0.0)
        b = units.meter(5.0, uncertainty=0.0)
        c = a + b
        self.assertAlmostEqual(c.uncertainty, 0.0, places=9)

    def test_very_small_uncertainty(self):
        a = units.meter(10.0, uncertainty=1e-15)
        b = units.meter(5.0, uncertainty=1e-15)
        c = a * b
        self.assertIsNotNone(c.uncertainty)
        self.assertGreater(c.uncertainty, 0)

    def test_uncertainty_preserved_through_simplify(self):
        km = Scale.kilo * units.meter
        n = km(5.0, uncertainty=0.1)
        simplified = n.simplify()
        self.assertAlmostEqual(simplified.value, 5000.0, places=9)
        # uncertainty also scales
        self.assertAlmostEqual(simplified.uncertainty, 100.0, places=9)


class TestMapDerivative(unittest.TestCase):
    """Test Map.derivative() implementations."""

    def test_linear_map_derivative(self):
        from ucon.maps import LinearMap
        m = LinearMap(3.28084)
        self.assertAlmostEqual(m.derivative(0), 3.28084, places=9)
        self.assertAlmostEqual(m.derivative(100), 3.28084, places=9)

    def test_affine_map_derivative(self):
        from ucon.maps import AffineMap
        m = AffineMap(5/9, -32 * 5/9)  # F to C
        self.assertAlmostEqual(m.derivative(0), 5/9, places=9)
        self.assertAlmostEqual(m.derivative(100), 5/9, places=9)

    def test_composed_map_derivative(self):
        from ucon.maps import LinearMap, AffineMap
        # Compose: first scale by 2, then add 10
        inner = LinearMap(2)
        outer = AffineMap(1, 10)
        composed = outer @ inner
        # d/dx [1*(2x) + 10] = 2
        self.assertAlmostEqual(composed.derivative(0), 2, places=9)
        self.assertAlmostEqual(composed.derivative(5), 2, places=9)


if __name__ == "__main__":
    unittest.main()

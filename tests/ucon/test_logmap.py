# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for LogMap and ExpMap classes.

Tests logarithmic and exponential conversion morphisms including
forward transforms, derivatives, inverses, and composition.
"""

import math
import unittest

from ucon.maps import LogMap, ExpMap, AffineMap, ComposedMap


class TestLogMapBasic(unittest.TestCase):
    """Test basic LogMap functionality."""

    def test_default_log10(self):
        m = LogMap()
        self.assertAlmostEqual(m(10), 1.0)
        self.assertAlmostEqual(m(100), 2.0)
        self.assertAlmostEqual(m(1000), 3.0)

    def test_scaled_log_decibel_power(self):
        # 10 * log₁₀(x) — decibels for power ratios
        m = LogMap(scale=10)
        self.assertAlmostEqual(m(10), 10.0)
        self.assertAlmostEqual(m(100), 20.0)
        self.assertAlmostEqual(m(1000), 30.0)

    def test_scaled_log_decibel_amplitude(self):
        # 20 * log₁₀(x) — decibels for amplitude ratios
        m = LogMap(scale=20)
        self.assertAlmostEqual(m(10), 20.0)
        self.assertAlmostEqual(m(100), 40.0)

    def test_negative_scale_ph_style(self):
        # -log₁₀(x) — pH-style
        m = LogMap(scale=-1)
        self.assertAlmostEqual(m(0.1), 1.0)
        self.assertAlmostEqual(m(0.01), 2.0)
        self.assertAlmostEqual(m(0.001), 3.0)
        self.assertAlmostEqual(m(1e-7), 7.0)

    def test_natural_log(self):
        m = LogMap(base=math.e)
        self.assertAlmostEqual(m(math.e), 1.0)
        self.assertAlmostEqual(m(math.e ** 2), 2.0)
        self.assertAlmostEqual(m(1), 0.0)

    def test_with_offset(self):
        m = LogMap(scale=1, base=10, offset=5)
        # log₁₀(100) + 5 = 2 + 5 = 7
        self.assertAlmostEqual(m(100), 7.0)

    def test_log_of_one_is_zero(self):
        m = LogMap()
        self.assertAlmostEqual(m(1), 0.0)


class TestLogMapErrors(unittest.TestCase):
    """Test LogMap error handling."""

    def test_zero_raises_error(self):
        m = LogMap()
        with self.assertRaises(ValueError) as ctx:
            m(0)
        self.assertIn("positive", str(ctx.exception))

    def test_negative_raises_error(self):
        m = LogMap()
        with self.assertRaises(ValueError) as ctx:
            m(-1)
        self.assertIn("positive", str(ctx.exception))

    def test_derivative_at_zero_raises(self):
        m = LogMap()
        with self.assertRaises(ValueError):
            m.derivative(0)

    def test_derivative_at_negative_raises(self):
        m = LogMap()
        with self.assertRaises(ValueError):
            m.derivative(-1)


class TestLogMapDerivative(unittest.TestCase):
    """Test LogMap derivative for uncertainty propagation."""

    def test_derivative_formula(self):
        # d/dx[log₁₀(x)] = 1 / (x * ln(10))
        m = LogMap()
        x = 100
        expected = 1 / (x * math.log(10))
        self.assertAlmostEqual(m.derivative(x), expected)

    def test_derivative_with_scale(self):
        # d/dx[scale * log₁₀(x)] = scale / (x * ln(10))
        m = LogMap(scale=10)
        x = 100
        expected = 10 / (x * math.log(10))
        self.assertAlmostEqual(m.derivative(x), expected)

    def test_derivative_natural_log(self):
        # d/dx[ln(x)] = 1/x
        m = LogMap(base=math.e)
        x = 5
        expected = 1 / x
        self.assertAlmostEqual(m.derivative(x), expected)


class TestLogMapInverse(unittest.TestCase):
    """Test LogMap inverse returns ExpMap."""

    def test_inverse_type(self):
        m = LogMap()
        inv = m.inverse()
        self.assertIsInstance(inv, ExpMap)

    def test_roundtrip(self):
        m = LogMap(scale=2, base=10, offset=3)
        x = 100
        self.assertAlmostEqual(m.inverse()(m(x)), x)

    def test_roundtrip_various_values(self):
        m = LogMap(scale=-1)
        for x in [0.001, 0.1, 1, 10, 100]:
            self.assertAlmostEqual(m.inverse()(m(x)), x, places=9)

    def test_non_invertible_raises(self):
        m = LogMap(scale=0)
        with self.assertRaises(ZeroDivisionError):
            m.inverse()


class TestLogMapProperties(unittest.TestCase):
    """Test LogMap properties."""

    def test_invertible_true(self):
        m = LogMap(scale=1)
        self.assertTrue(m.invertible)

    def test_invertible_false(self):
        m = LogMap(scale=0)
        self.assertFalse(m.invertible)

    def test_is_identity_false(self):
        m = LogMap()
        self.assertFalse(m.is_identity())

    def test_pow_one(self):
        m = LogMap(scale=2)
        self.assertEqual(m ** 1, m)

    def test_pow_minus_one(self):
        m = LogMap(scale=2)
        inv = m ** -1
        self.assertIsInstance(inv, ExpMap)

    def test_pow_other_raises(self):
        m = LogMap()
        with self.assertRaises(ValueError):
            _ = m ** 2


class TestExpMapBasic(unittest.TestCase):
    """Test basic ExpMap functionality."""

    def test_default_exp10(self):
        m = ExpMap()
        self.assertAlmostEqual(m(0), 1.0)
        self.assertAlmostEqual(m(1), 10.0)
        self.assertAlmostEqual(m(2), 100.0)
        self.assertAlmostEqual(m(3), 1000.0)

    def test_with_scale(self):
        m = ExpMap(scale=0.5)
        # 10^(0.5 * 2) = 10^1 = 10
        self.assertAlmostEqual(m(2), 10.0)

    def test_with_offset(self):
        m = ExpMap(scale=1, offset=1)
        # 10^(1*0 + 1) = 10^1 = 10
        self.assertAlmostEqual(m(0), 10.0)

    def test_natural_exp(self):
        m = ExpMap(base=math.e)
        self.assertAlmostEqual(m(0), 1.0)
        self.assertAlmostEqual(m(1), math.e)
        self.assertAlmostEqual(m(2), math.e ** 2)


class TestExpMapDerivative(unittest.TestCase):
    """Test ExpMap derivative."""

    def test_derivative_formula(self):
        # d/dx[10^x] = ln(10) * 10^x
        m = ExpMap()
        x = 2
        expected = math.log(10) * (10 ** x)
        self.assertAlmostEqual(m.derivative(x), expected)

    def test_derivative_with_scale(self):
        # d/dx[10^(scale*x)] = ln(10) * scale * 10^(scale*x)
        m = ExpMap(scale=2)
        x = 1
        expected = math.log(10) * 2 * (10 ** 2)
        self.assertAlmostEqual(m.derivative(x), expected)


class TestExpMapInverse(unittest.TestCase):
    """Test ExpMap inverse returns LogMap."""

    def test_inverse_type(self):
        m = ExpMap()
        inv = m.inverse()
        self.assertIsInstance(inv, LogMap)

    def test_roundtrip(self):
        m = ExpMap(scale=2, base=10, offset=1)
        x = 3
        self.assertAlmostEqual(m.inverse()(m(x)), x)

    def test_non_invertible_raises(self):
        m = ExpMap(scale=0)
        with self.assertRaises(ZeroDivisionError):
            m.inverse()


class TestExpMapProperties(unittest.TestCase):
    """Test ExpMap properties."""

    def test_invertible_true(self):
        m = ExpMap(scale=1)
        self.assertTrue(m.invertible)

    def test_invertible_false(self):
        m = ExpMap(scale=0)
        self.assertFalse(m.invertible)

    def test_is_identity_false(self):
        m = ExpMap()
        self.assertFalse(m.is_identity())


class TestLogMapComposition(unittest.TestCase):
    """Test LogMap composition with other maps."""

    def test_compose_with_affine(self):
        # nines = -log₁₀(1 - x)
        # = LogMap(scale=-1) @ AffineMap(a=-1, b=1)
        nines = LogMap(scale=-1) @ AffineMap(a=-1, b=1)
        self.assertIsInstance(nines, ComposedMap)

    def test_nines_composition_values(self):
        nines = LogMap(scale=-1) @ AffineMap(a=-1, b=1)
        self.assertAlmostEqual(nines(0.9), 1.0)
        self.assertAlmostEqual(nines(0.99), 2.0)
        self.assertAlmostEqual(nines(0.999), 3.0)
        self.assertAlmostEqual(nines(0.9999), 4.0)
        self.assertAlmostEqual(nines(0.99999), 5.0)

    def test_composed_derivative_chain_rule(self):
        # nines'(x) = d/dx[-log₁₀(1-x)]
        #           = 1 / ((1-x) * ln(10))
        nines = LogMap(scale=-1) @ AffineMap(a=-1, b=1)
        x = 0.99999
        expected = 1 / ((1 - x) * math.log(10))
        self.assertAlmostEqual(nines.derivative(x), expected, places=5)

    def test_composed_inverse(self):
        nines = LogMap(scale=-1) @ AffineMap(a=-1, b=1)
        inv = nines.inverse()
        x = 0.99999
        self.assertAlmostEqual(inv(nines(x)), x, places=9)

    def test_nines_inverse_values(self):
        nines = LogMap(scale=-1) @ AffineMap(a=-1, b=1)
        inv = nines.inverse()
        self.assertAlmostEqual(inv(2), 0.99)
        self.assertAlmostEqual(inv(3), 0.999)
        self.assertAlmostEqual(inv(5), 0.99999)


if __name__ == '__main__':
    unittest.main()

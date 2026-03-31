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

from ucon.maps import LogMap, ExpMap, AffineMap, LinearMap, ReciprocalMap, ComposedMap


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


class TestReciprocalMap(unittest.TestCase):
    """Test ReciprocalMap (inversely proportional: y = a/x)."""

    def test_call_scalar(self):
        """ReciprocalMap(c)(x) = c/x."""
        m = ReciprocalMap(300e6)
        self.assertAlmostEqual(m(1.5e14), 300e6 / 1.5e14)

    def test_call_another_value(self):
        """ReciprocalMap works for various inputs."""
        m = ReciprocalMap(100)
        self.assertAlmostEqual(m(4), 25.0)
        self.assertAlmostEqual(m(25), 4.0)

    def test_inverse_is_self(self):
        """ReciprocalMap is self-inverse (roundtrip)."""
        m = ReciprocalMap(299792458.0)
        inv = m.inverse()
        self.assertIsInstance(inv, ReciprocalMap)
        self.assertAlmostEqual(inv(m(42.0)), 42.0)

    def test_matmul_with_linear(self):
        """ReciprocalMap @ LinearMap returns ComposedMap."""
        r = ReciprocalMap(100)
        l = LinearMap(2.0)
        composed = r @ l
        self.assertIsInstance(composed, ComposedMap)
        # composed(5) = ReciprocalMap(100)(LinearMap(2)(5)) = 100 / (2*5) = 10
        self.assertAlmostEqual(composed(5.0), 10.0)

    def test_matmul_non_map_returns_not_implemented(self):
        """ReciprocalMap @ non-Map returns NotImplemented."""
        r = ReciprocalMap(100)
        result = r.__matmul__(42)
        self.assertIs(result, NotImplemented)

    def test_pow_one(self):
        """ReciprocalMap ** 1 returns self."""
        m = ReciprocalMap(100)
        self.assertIs(m ** 1, m)

    def test_pow_neg1(self):
        """ReciprocalMap ** -1 returns inverse."""
        m = ReciprocalMap(100)
        inv = m ** -1
        self.assertIsInstance(inv, ReciprocalMap)

    def test_pow_invalid_raises(self):
        """ReciprocalMap ** 2 raises ValueError."""
        m = ReciprocalMap(100)
        with self.assertRaises(ValueError):
            m ** 2

    def test_derivative(self):
        """ReciprocalMap derivative: -a/x^2."""
        m = ReciprocalMap(100)
        self.assertAlmostEqual(m.derivative(5.0), -100 / 25.0)

    def test_derivative_large_x(self):
        """Derivative at large x is small."""
        m = ReciprocalMap(100)
        self.assertAlmostEqual(m.derivative(1000.0), -100 / 1e6)

    def test_is_identity_false(self):
        """ReciprocalMap is never identity."""
        self.assertFalse(ReciprocalMap(1.0).is_identity())
        self.assertFalse(ReciprocalMap(100).is_identity())

    def test_invertible_true(self):
        """ReciprocalMap is invertible when a != 0."""
        self.assertTrue(ReciprocalMap(100).invertible)

    def test_invertible_false(self):
        """ReciprocalMap is not invertible when a == 0."""
        self.assertFalse(ReciprocalMap(0).invertible)


class TestExpMapComposition(unittest.TestCase):
    """Test ExpMap composition and power branches."""

    def test_matmul_non_map_returns_not_implemented(self):
        """ExpMap @ non-Map returns NotImplemented."""
        e = ExpMap()
        result = e.__matmul__(42)
        self.assertIs(result, NotImplemented)

    def test_matmul_returns_composed_map(self):
        """ExpMap @ LinearMap returns ComposedMap."""
        e = ExpMap()
        l = LinearMap(2.0)
        composed = e @ l
        self.assertIsInstance(composed, ComposedMap)
        # composed(3) = ExpMap()(LinearMap(2)(3)) = 10^(2*3) = 10^6
        self.assertAlmostEqual(composed(3), 1e6)

    def test_pow_1_returns_self(self):
        """ExpMap ** 1 returns self."""
        e = ExpMap()
        self.assertIs(e ** 1, e)

    def test_pow_neg1_returns_inverse(self):
        """ExpMap ** -1 returns inverse LogMap."""
        e = ExpMap()
        inv = e ** -1
        self.assertIsInstance(inv, LogMap)

    def test_pow_invalid_raises(self):
        """ExpMap ** 2 raises ValueError."""
        e = ExpMap()
        with self.assertRaises(ValueError):
            e ** 2


class TestAffineMapComposedFallback(unittest.TestCase):
    """Test AffineMap falls back to ComposedMap for non-linear/affine."""

    def test_affine_matmul_logmap_returns_composed(self):
        """AffineMap @ LogMap returns ComposedMap."""
        a = AffineMap(2.0, 5.0)
        l = LogMap(scale=10)
        composed = a @ l
        self.assertIsInstance(composed, ComposedMap)
        # composed(100) = AffineMap(2,5)(LogMap(10)(100)) = 2 * 20 + 5 = 45
        self.assertAlmostEqual(composed(100), 45.0)

    def test_affine_matmul_reciprocal_returns_composed(self):
        """AffineMap @ ReciprocalMap returns ComposedMap."""
        a = AffineMap(1.0, 10.0)
        r = ReciprocalMap(100)
        composed = a @ r
        self.assertIsInstance(composed, ComposedMap)
        # composed(5) = AffineMap(1,10)(ReciprocalMap(100)(5)) = 1 * 20 + 10 = 30
        self.assertAlmostEqual(composed(5), 30.0)

    def test_affine_matmul_non_map_returns_not_implemented(self):
        """AffineMap @ non-Map returns NotImplemented."""
        a = AffineMap(2.0, 5.0)
        result = a.__matmul__("not a map")
        self.assertIs(result, NotImplemented)


class TestLogMapComposedFallback(unittest.TestCase):
    """Test LogMap falls back to ComposedMap for non-Map."""

    def test_logmap_matmul_non_map_returns_not_implemented(self):
        """LogMap @ non-Map returns NotImplemented."""
        l = LogMap()
        result = l.__matmul__(42)
        self.assertIs(result, NotImplemented)


if __name__ == '__main__':
    unittest.main()

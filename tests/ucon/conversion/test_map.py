# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

import unittest

from ucon.maps import AffineMap, ComposedMap, LinearMap, Map


class TestLinearMap(unittest.TestCase):

    def test_apply(self):
        m = LinearMap(39.37)
        self.assertAlmostEqual(m(1.0), 39.37)
        self.assertAlmostEqual(m(0.0), 0.0)
        self.assertAlmostEqual(m(2.5), 98.425)

    def test_inverse(self):
        m = LinearMap(39.37)
        inv = m.inverse()
        self.assertIsInstance(inv, LinearMap)
        self.assertAlmostEqual(inv.a, 1.0 / 39.37)

    def test_inverse_zero_raises(self):
        m = LinearMap(0)
        with self.assertRaises(ZeroDivisionError):
            m.inverse()

    def test_round_trip(self):
        m = LinearMap(39.37)
        for x in [0.0, 1.0, -5.5, 1000.0]:
            self.assertAlmostEqual(m.inverse()(m(x)), x, places=10)

    def test_compose_closed(self):
        f = LinearMap(39.37)
        g = LinearMap(1.0 / 12.0)
        composed = f @ g
        self.assertIsInstance(composed, LinearMap)
        self.assertAlmostEqual(composed.a, 39.37 / 12.0)

    def test_compose_apply(self):
        f = LinearMap(2.0)
        g = LinearMap(3.0)
        # (f @ g)(x) = f(g(x)) = 2 * (3 * x) = 6x
        self.assertAlmostEqual((f @ g)(5.0), 30.0)

    def test_identity(self):
        ident = LinearMap.identity()
        self.assertAlmostEqual(ident(42.0), 42.0)
        m = LinearMap(7.0)
        self.assertEqual(m @ ident, m)
        self.assertEqual(ident @ m, m)

    def test_invertible(self):
        self.assertTrue(LinearMap(5.0).invertible)
        self.assertFalse(LinearMap(0).invertible)

    def test_eq(self):
        self.assertEqual(LinearMap(3.0), LinearMap(3.0))
        self.assertNotEqual(LinearMap(3.0), LinearMap(4.0))

    def test_repr(self):
        self.assertIn("39.37", repr(LinearMap(39.37)))

    def test_matmul_non_map_returns_not_implemented(self):
        m = LinearMap(2.0)
        result = m.__matmul__(42)
        self.assertIs(result, NotImplemented)


class TestAffineMap(unittest.TestCase):

    def test_apply(self):
        # Celsius to Fahrenheit: F = 1.8 * C + 32
        c_to_f = AffineMap(1.8, 32.0)
        self.assertAlmostEqual(c_to_f(0.0), 32.0)
        self.assertAlmostEqual(c_to_f(100.0), 212.0)
        self.assertAlmostEqual(c_to_f(-40.0), -40.0)

    def test_inverse(self):
        c_to_f = AffineMap(1.8, 32.0)
        f_to_c = c_to_f.inverse()
        self.assertIsInstance(f_to_c, AffineMap)
        self.assertAlmostEqual(f_to_c(32.0), 0.0)
        self.assertAlmostEqual(f_to_c(212.0), 100.0)

    def test_inverse_zero_raises(self):
        m = AffineMap(0, 5.0)
        with self.assertRaises(ZeroDivisionError):
            m.inverse()

    def test_round_trip(self):
        m = AffineMap(1.8, 32.0)
        for x in [0.0, 100.0, -40.0, 37.5]:
            self.assertAlmostEqual(m.inverse()(m(x)), x, places=10)

    def test_compose_closed(self):
        f = AffineMap(2.0, 3.0)
        g = AffineMap(4.0, 5.0)
        composed = f @ g
        self.assertIsInstance(composed, AffineMap)
        # f(g(x)) = 2*(4x+5)+3 = 8x+13
        self.assertAlmostEqual(composed.a, 8.0)
        self.assertAlmostEqual(composed.b, 13.0)

    def test_compose_apply(self):
        f = AffineMap(2.0, 3.0)
        g = AffineMap(4.0, 5.0)
        for x in [0.0, 1.0, -2.0]:
            self.assertAlmostEqual((f @ g)(x), f(g(x)), places=10)

    def test_invertible(self):
        self.assertTrue(AffineMap(1.8, 32.0).invertible)
        self.assertFalse(AffineMap(0, 32.0).invertible)

    def test_eq(self):
        self.assertEqual(AffineMap(1.8, 32.0), AffineMap(1.8, 32.0))
        self.assertNotEqual(AffineMap(1.8, 32.0), AffineMap(1.8, 0.0))

    def test_repr(self):
        r = repr(AffineMap(1.8, 32.0))
        self.assertIn("1.8", r)
        self.assertIn("32.0", r)


class TestComposedMap(unittest.TestCase):

    def test_heterogeneous_composition(self):
        # LinearMap @ AffineMap now returns AffineMap (closed composition)
        # Use ComposedMap directly to test the fallback behavior
        lin = LinearMap(2.0)
        aff = AffineMap(3.0, 1.0)
        composed = ComposedMap(lin, aff)
        # lin(aff(x)) = 2 * (3x + 1) = 6x + 2
        self.assertAlmostEqual(composed(0.0), 2.0)
        self.assertAlmostEqual(composed(1.0), 8.0)

    def test_inverse(self):
        composed = ComposedMap(LinearMap(2.0), AffineMap(3.0, 1.0))
        for x in [0.0, 1.0, -3.0, 10.0]:
            self.assertAlmostEqual(composed.inverse()(composed(x)), x, places=10)

    def test_invertible(self):
        self.assertTrue(ComposedMap(LinearMap(2.0), AffineMap(3.0, 1.0)).invertible)
        self.assertFalse(ComposedMap(LinearMap(0), AffineMap(3.0, 1.0)).invertible)

    def test_non_invertible_raises(self):
        composed = ComposedMap(LinearMap(0), AffineMap(3.0, 1.0))
        with self.assertRaises(ValueError):
            composed.inverse()

    def test_repr(self):
        composed = ComposedMap(LinearMap(2.0), AffineMap(3.0, 1.0))
        r = repr(composed)
        self.assertIn("LinearMap", r)
        self.assertIn("AffineMap", r)


class TestMapABC(unittest.TestCase):

    def test_cannot_instantiate(self):
        with self.assertRaises(TypeError):
            Map()

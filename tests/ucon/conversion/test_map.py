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

    def test_matmul_with_affine(self):
        lin = LinearMap(2.0)
        aff = AffineMap(3.0, 5.0)
        composed = lin @ aff
        # lin(aff(x)) = 2 * (3x + 5) = 6x + 10
        self.assertIsInstance(composed, AffineMap)
        self.assertAlmostEqual(composed.a, 6.0)
        self.assertAlmostEqual(composed.b, 10.0)
        self.assertAlmostEqual(composed(1.0), 16.0)

    def test_pow(self):
        m = LinearMap(3.0)
        squared = m ** 2
        self.assertIsInstance(squared, LinearMap)
        self.assertAlmostEqual(squared.a, 9.0)

    def test_pow_negative(self):
        m = LinearMap(4.0)
        inv = m ** -1
        self.assertIsInstance(inv, LinearMap)
        self.assertAlmostEqual(inv.a, 0.25)

    def test_pow_fractional(self):
        m = LinearMap(4.0)
        sqrt = m ** 0.5
        self.assertIsInstance(sqrt, LinearMap)
        self.assertAlmostEqual(sqrt.a, 2.0)

    def test_is_identity_true(self):
        m = LinearMap(1.0)
        self.assertTrue(m.is_identity())

    def test_is_identity_false(self):
        m = LinearMap(2.0)
        self.assertFalse(m.is_identity())

    def test_is_identity_near_one(self):
        m = LinearMap(1.0 + 1e-10)
        self.assertTrue(m.is_identity())

    def test_hash(self):
        m1 = LinearMap(3.0)
        m2 = LinearMap(3.0)
        self.assertEqual(hash(m1), hash(m2))
        self.assertEqual(len({m1, m2}), 1)


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

    def test_matmul_with_linear(self):
        aff = AffineMap(2.0, 3.0)
        lin = LinearMap(4.0)
        composed = aff @ lin
        # aff(lin(x)) = 2 * (4x) + 3 = 8x + 3
        self.assertIsInstance(composed, AffineMap)
        self.assertAlmostEqual(composed.a, 8.0)
        self.assertAlmostEqual(composed.b, 3.0)
        self.assertAlmostEqual(composed(1.0), 11.0)

    def test_matmul_non_map_returns_not_implemented(self):
        m = AffineMap(1.8, 32.0)
        result = m.__matmul__("not a map")
        self.assertIs(result, NotImplemented)

    def test_pow_one(self):
        m = AffineMap(1.8, 32.0)
        result = m ** 1
        self.assertIs(result, m)

    def test_pow_negative_one(self):
        m = AffineMap(1.8, 32.0)
        result = m ** -1
        inv = m.inverse()
        self.assertEqual(result.a, inv.a)
        self.assertEqual(result.b, inv.b)

    def test_pow_invalid_raises(self):
        m = AffineMap(1.8, 32.0)
        with self.assertRaises(ValueError) as ctx:
            m ** 2
        self.assertIn("only supports exp=1 or exp=-1", str(ctx.exception))

    def test_is_identity_true(self):
        m = AffineMap(1.0, 0.0)
        self.assertTrue(m.is_identity())

    def test_is_identity_false_due_to_offset(self):
        m = AffineMap(1.0, 5.0)
        self.assertFalse(m.is_identity())

    def test_is_identity_false_due_to_scale(self):
        m = AffineMap(2.0, 0.0)
        self.assertFalse(m.is_identity())

    def test_hash(self):
        m1 = AffineMap(1.8, 32.0)
        m2 = AffineMap(1.8, 32.0)
        self.assertEqual(hash(m1), hash(m2))
        self.assertEqual(len({m1, m2}), 1)


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

    def test_matmul(self):
        c1 = ComposedMap(LinearMap(2.0), AffineMap(3.0, 1.0))
        c2 = LinearMap(5.0)
        composed = c1 @ c2
        self.assertIsInstance(composed, ComposedMap)
        # c1(c2(x)) = c1(5x) = 2*(3*5x + 1) = 30x + 2
        self.assertAlmostEqual(composed(1.0), 32.0)
        self.assertAlmostEqual(composed(0.0), 2.0)

    def test_matmul_non_map_returns_not_implemented(self):
        composed = ComposedMap(LinearMap(2.0), AffineMap(3.0, 1.0))
        result = composed.__matmul__(42)
        self.assertIs(result, NotImplemented)

    def test_pow_one(self):
        composed = ComposedMap(LinearMap(2.0), AffineMap(3.0, 1.0))
        result = composed ** 1
        self.assertIs(result, composed)

    def test_pow_negative_one(self):
        composed = ComposedMap(LinearMap(2.0), AffineMap(3.0, 1.0))
        result = composed ** -1
        # Round-trip should be identity
        for x in [0.0, 1.0, 5.0]:
            self.assertAlmostEqual(result(composed(x)), x, places=10)

    def test_pow_invalid_raises(self):
        composed = ComposedMap(LinearMap(2.0), AffineMap(3.0, 1.0))
        with self.assertRaises(ValueError) as ctx:
            composed ** 2
        self.assertIn("only supports exp=1 or exp=-1", str(ctx.exception))

    def test_invertible_both_non_invertible(self):
        composed = ComposedMap(LinearMap(0), LinearMap(0))
        self.assertFalse(composed.invertible)

    def test_invertible_inner_non_invertible(self):
        composed = ComposedMap(LinearMap(2.0), LinearMap(0))
        self.assertFalse(composed.invertible)

    def test_is_identity(self):
        composed = ComposedMap(LinearMap(1.0), LinearMap(1.0))
        self.assertTrue(composed.is_identity())

    def test_is_identity_false(self):
        composed = ComposedMap(LinearMap(2.0), LinearMap(0.5))
        self.assertTrue(composed.is_identity())  # 2 * 0.5 = 1

    def test_is_identity_with_offset(self):
        composed = ComposedMap(LinearMap(1.0), AffineMap(1.0, 5.0))
        self.assertFalse(composed.is_identity())


class TestMapABC(unittest.TestCase):

    def test_cannot_instantiate(self):
        with self.assertRaises(TypeError):
            Map()


class TestCrossTypeComposition(unittest.TestCase):
    """Tests for composition between different Map types."""

    def test_linear_at_affine_at_linear(self):
        """Chain: LinearMap @ AffineMap @ LinearMap"""
        l1 = LinearMap(2.0)
        a = AffineMap(3.0, 1.0)
        l2 = LinearMap(4.0)
        # l1 @ a = AffineMap(6, 2)
        # (l1 @ a) @ l2 = AffineMap(24, 2)
        composed = l1 @ a @ l2
        self.assertIsInstance(composed, AffineMap)
        self.assertAlmostEqual(composed(1.0), 26.0)

    def test_affine_at_linear_at_affine(self):
        """Chain: AffineMap @ LinearMap @ AffineMap"""
        a1 = AffineMap(2.0, 1.0)
        l = LinearMap(3.0)
        a2 = AffineMap(4.0, 5.0)
        # l @ a2 = AffineMap(12, 15)
        # a1 @ (l @ a2) = AffineMap(24, 31)
        composed = a1 @ l @ a2
        self.assertIsInstance(composed, AffineMap)
        self.assertAlmostEqual(composed(1.0), 55.0)

    def test_composed_preserves_semantics(self):
        """Verify f @ g computes f(g(x)) correctly for all type combinations."""
        maps = [
            LinearMap(2.0),
            LinearMap(0.5),
            AffineMap(3.0, 1.0),
            AffineMap(1.0, -5.0),
        ]
        for f in maps:
            for g in maps:
                composed = f @ g
                for x in [0.0, 1.0, -2.0, 10.0]:
                    expected = f(g(x))
                    actual = composed(x)
                    self.assertAlmostEqual(actual, expected, places=10,
                        msg=f"Failed for {type(f).__name__} @ {type(g).__name__} at x={x}")


class TestMapEdgeCases(unittest.TestCase):
    """Edge case tests for Map hierarchy."""

    def test_linear_map_with_negative_scale(self):
        m = LinearMap(-3.0)
        self.assertAlmostEqual(m(5.0), -15.0)
        self.assertAlmostEqual(m.inverse()(m(5.0)), 5.0)

    def test_affine_map_with_negative_scale(self):
        m = AffineMap(-2.0, 10.0)
        self.assertAlmostEqual(m(5.0), 0.0)
        self.assertAlmostEqual(m.inverse()(m(5.0)), 5.0)

    def test_linear_map_very_small_scale(self):
        m = LinearMap(1e-10)
        self.assertAlmostEqual(m(1e10), 1.0)
        self.assertTrue(m.invertible)

    def test_linear_map_very_large_scale(self):
        m = LinearMap(1e10)
        self.assertAlmostEqual(m(1e-10), 1.0)
        self.assertTrue(m.invertible)

    def test_affine_identity(self):
        """AffineMap(1, 0) should be identity."""
        m = AffineMap(1.0, 0.0)
        for x in [0.0, 1.0, -100.0, 1e6]:
            self.assertAlmostEqual(m(x), x)

    def test_linear_identity(self):
        """LinearMap(1) should be identity."""
        m = LinearMap(1.0)
        for x in [0.0, 1.0, -100.0, 1e6]:
            self.assertAlmostEqual(m(x), x)

    def test_composed_map_deep_nesting(self):
        """Test deeply nested ComposedMap."""
        m = LinearMap(2.0)
        for _ in range(5):
            m = ComposedMap(m, LinearMap(1.5))
        # 2 * 1.5^5 = 2 * 7.59375 = 15.1875
        self.assertAlmostEqual(m(1.0), 2.0 * (1.5 ** 5))

    def test_inverse_of_inverse(self):
        """(m.inverse()).inverse() == m"""
        m = LinearMap(7.0)
        self.assertEqual(m.inverse().inverse(), m)

        m2 = AffineMap(3.0, 5.0)
        double_inv = m2.inverse().inverse()
        self.assertAlmostEqual(double_inv.a, m2.a)
        self.assertAlmostEqual(double_inv.b, m2.b)

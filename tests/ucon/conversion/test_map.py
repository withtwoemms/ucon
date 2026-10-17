# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

import marshal
import math
import sys
import unittest

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from ucon import units
from ucon._cache import _CACHE_SCHEMA, _map_to_prim, _prim_to_map
from ucon.contexts import ContextEdge, ConversionContext, using_context
from ucon.core import Number
from ucon.maps import (
    AffineMap,
    ComposedMap,
    LinearMap,
    LogMap,
    Map,
    NonMonotoneOnDomain,
    PolynomialInverseMap,
    PolynomialMap,
)
from ucon.packages import PackageLoadError, _build_map, _find_map_class
from ucon.serialization import _edge_dict


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


class TestRelUncertaintyComposition(unittest.TestCase):
    """Tests that rel_uncertainty propagates correctly through all composition paths."""

    def test_linear_compose_propagates(self):
        import math
        m1 = LinearMap(2.0, rel_uncertainty=3e-5)
        m2 = LinearMap(3.0, rel_uncertainty=4e-5)
        composed = m1 @ m2
        expected = math.sqrt(3e-5**2 + 4e-5**2)
        self.assertAlmostEqual(composed.rel_uncertainty, expected, places=15)

    def test_linear_inverse_preserves(self):
        m = LinearMap(5.0, rel_uncertainty=1.5e-10)
        self.assertEqual(m.inverse().rel_uncertainty, 1.5e-10)

    def test_linear_pow_scales(self):
        m = LinearMap(3.0, rel_uncertainty=1e-5)
        self.assertAlmostEqual((m ** 2).rel_uncertainty, 2e-5, places=15)
        self.assertAlmostEqual((m ** 3).rel_uncertainty, 3e-5, places=15)

    def test_affine_inverse_preserves(self):
        m = AffineMap(1.8, 32.0, rel_uncertainty=2e-8)
        self.assertEqual(m.inverse().rel_uncertainty, 2e-8)

    def test_affine_at_linear_propagates(self):
        import math
        aff = AffineMap(2.0, 3.0, rel_uncertainty=1e-5)
        lin = LinearMap(4.0, rel_uncertainty=2e-5)
        composed = aff @ lin
        expected = math.sqrt(1e-5**2 + 2e-5**2)
        self.assertAlmostEqual(composed.rel_uncertainty, expected, places=15)

    def test_composed_map_property(self):
        import math
        inner = LinearMap(2.0, rel_uncertainty=3e-5)
        outer = AffineMap(1.0, 5.0, rel_uncertainty=4e-5)
        composed = ComposedMap(outer, inner)
        expected = math.sqrt(3e-5**2 + 4e-5**2)
        self.assertAlmostEqual(composed.rel_uncertainty, expected, places=15)

    def test_exact_maps_have_zero(self):
        self.assertEqual(LinearMap(2.0).rel_uncertainty, 0.0)
        self.assertEqual(AffineMap(1.8, 32.0).rel_uncertainty, 0.0)
        self.assertEqual(ComposedMap(LinearMap(2.0), LinearMap(3.0)).rel_uncertainty, 0.0)


# ---------------------------------------------------------------------------
# PolynomialMap
# ---------------------------------------------------------------------------

# IEC 60751 Callendar-Van Dusen coefficients for a PT100 platinum RTD:
#   R(T) = R0 * (1 + A*T + B*T**2),  valid 0..850 degC
PT100_R0 = 100.0
PT100_A = 3.9083e-3
PT100_B = -5.775e-7


def pt100() -> PolynomialMap:
    """The PT100 resistance curve, ascending coefficients, over 0..850 degC."""
    return PolynomialMap(
        (PT100_R0, PT100_R0 * PT100_A, PT100_R0 * PT100_B),
        domain=(0.0, 850.0),
    )


class TestPolynomialMapForward(unittest.TestCase):

    def test_coefficients_are_ascending(self):
        m = PolynomialMap((1.0, 2.0, 3.0), domain=(0.0, 1.0))
        # 1 + 2x + 3x^2 at x=2 is 1 + 4 + 12 = 17 (not 4 + 4 + 3)
        self.assertAlmostEqual(m(2.0), 17.0)

    def test_pt100_table_values(self):
        m = pt100()
        self.assertAlmostEqual(m(0.0), 100.0, places=10)
        self.assertAlmostEqual(m(100.0), 138.5055, places=10)
        self.assertAlmostEqual(m(850.0), 390.481125, places=9)

    def test_degree_strips_leading_zeros(self):
        self.assertEqual(PolynomialMap((1.0, 2.0, 0.0, 0.0), domain=(0.0, 1.0)).degree, 1)
        self.assertEqual(PolynomialMap((0.0, 0.0, 0.0), domain=(0.0, 1.0)).degree, 0)
        self.assertEqual(pt100().degree, 2)

    def test_lists_normalize_to_tuples_and_hash(self):
        m = PolynomialMap([1.0, 2.0], domain=[0.0, 5.0])
        self.assertEqual(m.coefficients, (1.0, 2.0))
        self.assertEqual(m.domain, (0.0, 5.0))
        self.assertEqual(hash(m), hash(PolynomialMap((1.0, 2.0), domain=(0.0, 5.0))))

    def test_call_does_not_enforce_domain(self):
        """Extrapolation is permitted; the domain selects the inverse branch."""
        m = pt100()
        self.assertAlmostEqual(m(-50.0), 100.0 * (1 + PT100_A * -50 + PT100_B * 2500))

    def test_requires_a_coefficient(self):
        with self.assertRaises(ValueError):
            PolynomialMap((), domain=(0.0, 1.0))

    def test_domain_must_be_an_ordered_pair(self):
        with self.assertRaises(ValueError):
            PolynomialMap((1.0, 1.0), domain=(1.0,))
        with self.assertRaises(ValueError):
            PolynomialMap((1.0, 1.0), domain=(5.0, 5.0))
        with self.assertRaises(ValueError):
            PolynomialMap((1.0, 1.0), domain=(5.0, 1.0))

    def test_is_identity(self):
        self.assertTrue(PolynomialMap((0.0, 1.0), domain=(0.0, 1.0)).is_identity())
        self.assertFalse(PolynomialMap((3.0, 1.0), domain=(0.0, 1.0)).is_identity())
        self.assertFalse(pt100().is_identity())


class TestPolynomialMapDerivative(unittest.TestCase):

    def test_analytic_derivative_coefficients(self):
        m = PolynomialMap((5.0, 3.0, 7.0, 2.0), domain=(0.0, 1.0))
        self.assertEqual(m.derivative_coefficients, (3.0, 14.0, 6.0))

    def test_pt100_derivative_is_exact(self):
        m = pt100()
        # dR/dT = R0*A + 2*R0*B*T
        for T in (0.0, 1.0, 100.0, 850.0):
            self.assertAlmostEqual(
                m.derivative(T),
                PT100_R0 * PT100_A + 2 * PT100_R0 * PT100_B * T,
                places=12,
            )

    def test_derivative_beats_a_finite_difference(self):
        """Analytic, not numerical: it is exact where differencing is not."""
        m = pt100()
        h = 1e-6
        numeric = (m(100.0 + h) - m(100.0 - h)) / (2 * h)
        exact = PT100_R0 * PT100_A + 2 * PT100_R0 * PT100_B * 100.0
        self.assertEqual(m.derivative(100.0), exact)
        self.assertNotEqual(numeric, exact)

    def test_constant_has_zero_derivative(self):
        self.assertEqual(PolynomialMap((4.0,), domain=(0.0, 1.0)).derivative(9.0), 0.0)


class TestPolynomialMapInverse(unittest.TestCase):

    def test_inverse_is_a_single_map(self):
        inv = pt100().inverse()
        self.assertIsInstance(inv, Map)
        self.assertIsInstance(inv, PolynomialInverseMap)

    def test_round_trip_to_tolerance(self):
        """Forward-then-back is accurate to 1e-12 relative across the span."""
        m = pt100()
        inv = m.inverse()
        for T in (0.0, 0.5, 1.0, 25.0, 100.0, 420.37, 700.0, 850.0):
            back = inv(m(T))
            self.assertAlmostEqual(back, T, delta=1e-12 * max(1.0, abs(T)))

    def test_round_trip_from_the_resistance_side(self):
        m = pt100()
        inv = m.inverse()
        for R in (100.0, 110.0, 138.5055, 250.0, 390.481125):
            self.assertAlmostEqual(m(inv(R)), R, delta=1e-12 * R)

    def test_inverse_recovers_the_iec_table_point(self):
        self.assertAlmostEqual(pt100().inverse()(138.5055), 100.0, places=9)

    def test_inverse_image_is_the_domain(self):
        inv = pt100().inverse()
        self.assertEqual(inv.domain, (100.0, 390.481125))

    def test_inverse_refuses_outside_the_image(self):
        inv = pt100().inverse()
        with self.assertRaises(ValueError):
            inv(50.0)       # below R(0)
        with self.assertRaises(ValueError):
            inv(1000.0)     # above R(850)

    def test_inverse_derivative_is_the_reciprocal(self):
        m = pt100()
        inv = m.inverse()
        for T in (0.0, 100.0, 500.0):
            self.assertAlmostEqual(
                inv.derivative(m(T)), 1.0 / m.derivative(T), places=12
            )

    def test_inverse_of_inverse_is_the_polynomial(self):
        m = pt100()
        self.assertEqual(m.inverse().inverse(), m)
        self.assertEqual(m.inverse().inverse().inverse(), m.inverse())

    def test_inverse_preserves_rel_uncertainty(self):
        m = PolynomialMap(
            (PT100_R0, PT100_R0 * PT100_A, PT100_R0 * PT100_B),
            domain=(0.0, 850.0),
            rel_uncertainty=1.5e-3,
        )
        self.assertEqual(m.inverse().rel_uncertainty, 1.5e-3)

    def test_boundary_critical_point_still_monotone(self):
        """x**2 on [0, 1] turns at the boundary, not inside it."""
        m = PolynomialMap((0.0, 0.0, 1.0), domain=(0.0, 1.0))
        self.assertTrue(m.invertible)
        self.assertEqual(m.turning_points, ())
        self.assertAlmostEqual(m.inverse()(0.25), 0.5, places=12)
        self.assertAlmostEqual(m.inverse()(2.0 / 3.0), math.sqrt(2.0 / 3.0), places=12)

    def test_higher_degree_round_trip(self):
        """A monotone cubic inverts as well as the quadratic does."""
        m = PolynomialMap((1.0, 2.0, 0.0, 0.5), domain=(-1.0, 3.0))
        self.assertTrue(m.invertible)
        inv = m.inverse()
        for x in (-1.0, -0.25, 0.0, 1.1, 2.3, 3.0):
            self.assertAlmostEqual(inv(m(x)), x, delta=1e-11 * max(1.0, abs(x)))

    def test_decreasing_polynomial_inverts(self):
        m = PolynomialMap((0.0, -3.0, -1.0), domain=(0.0, 10.0))
        self.assertTrue(m.invertible)
        inv = m.inverse()
        self.assertEqual(inv.domain, (m(10.0), m(0.0)))
        for x in (0.0, 2.5, 10.0):
            self.assertAlmostEqual(inv(m(x)), x, delta=1e-11 * max(1.0, abs(x)))


class TestPolynomialMapNonMonotone(unittest.TestCase):

    def test_turning_inside_the_domain_refuses(self):
        m = PolynomialMap((0.0, 0.0, 1.0), domain=(-1.0, 1.0))
        self.assertFalse(m.invertible)
        self.assertEqual(m.turning_points, (0.0,))
        with self.assertRaises(NonMonotoneOnDomain) as ctx:
            m.inverse()
        self.assertIn("not monotone", str(ctx.exception))
        self.assertIn("(-1.0, 1.0)", str(ctx.exception))

    def test_refusal_is_a_value_error(self):
        """Callers already handling ComposedMap non-invertibility need no change."""
        m = PolynomialMap((0.0, 0.0, 1.0), domain=(-1.0, 1.0))
        with self.assertRaises(ValueError):
            m.inverse()

    def test_two_turning_points_are_both_reported(self):
        # x**3 - 3x turns at -1 and +1
        m = PolynomialMap((0.0, -3.0, 0.0, 1.0), domain=(-2.0, 2.0))
        self.assertEqual(len(m.turning_points), 2)
        self.assertAlmostEqual(m.turning_points[0], -1.0, places=9)
        self.assertAlmostEqual(m.turning_points[1], 1.0, places=9)
        self.assertFalse(m.invertible)

    def test_narrowing_the_domain_restores_a_branch(self):
        full = PolynomialMap((0.0, -3.0, 0.0, 1.0), domain=(-2.0, 2.0))
        self.assertFalse(full.invertible)
        branch = PolynomialMap((0.0, -3.0, 0.0, 1.0), domain=(1.0, 2.0))
        self.assertTrue(branch.invertible)
        self.assertAlmostEqual(branch.inverse()(branch(1.7)), 1.7, places=10)

    def test_wrapping_a_non_monotone_polynomial_refuses(self):
        """A deserialized PolynomialInverseMap cannot hold an invalid branch."""
        m = PolynomialMap((0.0, 0.0, 1.0), domain=(-1.0, 1.0))
        with self.assertRaises(NonMonotoneOnDomain):
            PolynomialInverseMap(m)

    def test_inverse_map_rejects_a_non_polynomial(self):
        with self.assertRaises(TypeError):
            PolynomialInverseMap(LinearMap(2.0))


class TestPolynomialMapDegeneracies(unittest.TestCase):

    def test_degree_zero_is_not_invertible(self):
        m = PolynomialMap((7.0,), domain=(0.0, 1.0))
        self.assertEqual(m.degree, 0)
        self.assertFalse(m.invertible)
        with self.assertRaises(NonMonotoneOnDomain) as ctx:
            m.inverse()
        self.assertIn("constant", str(ctx.exception))

    def test_degree_zero_still_evaluates(self):
        m = PolynomialMap((7.0,), domain=(0.0, 1.0))
        self.assertEqual(m(0.0), 7.0)
        self.assertEqual(m(1e6), 7.0)

    def test_degree_one_delegates_to_affine(self):
        """C -> F as a degree-1 polynomial inverts to the AffineMap inverse."""
        m = PolynomialMap((32.0, 1.8), domain=(-273.15, 1000.0))
        inv = m.inverse()
        self.assertIsInstance(inv, AffineMap)
        self.assertAlmostEqual(inv.a, 1.0 / 1.8)
        self.assertAlmostEqual(inv.b, -32.0 / 1.8)
        self.assertAlmostEqual(inv(212.0), 100.0, places=10)

    def test_degree_one_matches_affine_everywhere(self):
        poly = PolynomialMap((32.0, 1.8), domain=(-100.0, 100.0))
        aff = AffineMap(1.8, 32.0)
        for x in (-40.0, 0.0, 37.0, 100.0):
            self.assertAlmostEqual(poly(x), aff(x), places=10)
            self.assertAlmostEqual(poly.derivative(x), aff.derivative(x), places=10)

    def test_degree_one_inverse_carries_uncertainty(self):
        m = PolynomialMap((32.0, 1.8), domain=(-100.0, 100.0), rel_uncertainty=2e-8)
        self.assertEqual(m.inverse().rel_uncertainty, 2e-8)

    def test_trailing_zero_collapses_to_degree_one(self):
        m = PolynomialMap((32.0, 1.8, 0.0), domain=(-100.0, 100.0))
        self.assertIsInstance(m.inverse(), AffineMap)


class TestPolynomialMapComposition(unittest.TestCase):

    def test_polynomial_at_polynomial_is_exact(self):
        outer = PolynomialMap((1.0, 1.0, 1.0), domain=(0.0, 5.0))   # 1 + x + x^2
        inner = PolynomialMap((0.0, 2.0), domain=(0.0, 2.5))        # 2x
        composed = outer @ inner
        self.assertIsInstance(composed, PolynomialMap)
        self.assertEqual(composed.coefficients, (1.0, 2.0, 4.0))
        self.assertEqual(composed.domain, inner.domain)
        for x in (0.0, 0.5, 1.0, 2.5):
            self.assertAlmostEqual(composed(x), outer(inner(x)), places=10)

    def test_polynomial_at_linear_folds(self):
        m = pt100()
        composed = m @ LinearMap(2.0)
        self.assertIsInstance(composed, PolynomialMap)
        self.assertEqual(composed.domain, (0.0, 425.0))
        for x in (0.0, 50.0, 425.0):
            self.assertAlmostEqual(composed(x), m(2.0 * x), places=9)

    def test_polynomial_at_affine_takes_the_preimage_domain(self):
        m = pt100()
        composed = m @ AffineMap(2.0, 10.0)
        self.assertIsInstance(composed, PolynomialMap)
        self.assertEqual(composed.domain, (-5.0, 420.0))
        for x in (-5.0, 0.0, 100.0, 420.0):
            self.assertAlmostEqual(composed(x), m(2.0 * x + 10.0), places=9)

    def test_polynomial_at_negative_slope_affine_orders_the_domain(self):
        m = pt100()
        composed = m @ AffineMap(-1.0, 0.0)
        self.assertEqual(composed.domain, (-850.0, 0.0))

    def test_polynomial_at_degenerate_linear_falls_back(self):
        composed = pt100() @ LinearMap(0.0)
        self.assertIsInstance(composed, ComposedMap)

    def test_composition_propagates_rel_uncertainty(self):
        a = PolynomialMap((0.0, 1.0, 1.0), domain=(0.0, 1.0), rel_uncertainty=3e-5)
        b = PolynomialMap((0.0, 1.0, 1.0), domain=(0.0, 1.0), rel_uncertainty=4e-5)
        self.assertAlmostEqual((a @ b).rel_uncertainty, 5e-5, places=15)

    def test_heterogeneous_composition_falls_back(self):
        composed = pt100() @ LogMap()
        self.assertIsInstance(composed, ComposedMap)
        self.assertAlmostEqual(composed(100.0), pt100()(LogMap()(100.0)), places=10)

    def test_inverse_map_composition_falls_back(self):
        composed = pt100().inverse() @ LinearMap(1.0)
        self.assertIsInstance(composed, ComposedMap)
        self.assertAlmostEqual(composed(138.5055), 100.0, places=9)

    def test_non_map_operand(self):
        self.assertEqual(pt100().__matmul__(3.0), NotImplemented)
        self.assertEqual(pt100().inverse().__matmul__(3.0), NotImplemented)

    def test_composed_round_trip_through_the_graph_identity_check(self):
        """ComposedMap(inverse, forward) is recognized as the identity."""
        m = pt100()
        self.assertTrue(ComposedMap(m.inverse(), m).is_identity())


class TestPolynomialMapPow(unittest.TestCase):

    def test_pow_one_is_self(self):
        m = pt100()
        self.assertIs(m ** 1, m)
        inv = m.inverse()
        self.assertIs(inv ** 1, inv)

    def test_pow_minus_one_is_inverse(self):
        m = pt100()
        self.assertEqual(m ** -1, m.inverse())
        self.assertEqual(m.inverse() ** -1, m)

    def test_other_exponents_refuse(self):
        with self.assertRaises(ValueError):
            pt100() ** 2
        with self.assertRaises(ValueError):
            pt100().inverse() ** 2


class TestPolynomialMapArrays(unittest.TestCase):

    def test_forward_on_an_array(self):
        np = pytest.importorskip("numpy")
        m = pt100()
        xs = np.array([0.0, 100.0, 850.0])
        np.testing.assert_allclose(m(xs), [100.0, 138.5055, 390.481125])

    def test_inverse_on_an_array(self):
        np = pytest.importorskip("numpy")
        m = pt100()
        xs = np.array([0.0, 25.0, 100.0, 850.0])
        np.testing.assert_allclose(m.inverse()(m(xs)), xs, rtol=0, atol=1e-10)

    def test_inverse_derivative_on_an_array(self):
        np = pytest.importorskip("numpy")
        m = pt100()
        xs = np.array([0.0, 100.0, 500.0])
        np.testing.assert_allclose(
            m.inverse().derivative(m(xs)), 1.0 / m.derivative(xs), rtol=1e-10
        )

    def test_inverse_preserves_array_shape(self):
        np = pytest.importorskip("numpy")
        m = pt100()
        xs = np.array([[0.0, 100.0], [400.0, 850.0]])
        out = m.inverse()(m(xs))
        self.assertEqual(out.shape, (2, 2))
        np.testing.assert_allclose(out, xs, rtol=0, atol=1e-10)


class TestPolynomialMapTomlRoundTrip(unittest.TestCase):

    def test_to_dict_shape(self):
        d = pt100().to_dict()
        self.assertEqual(d["type"], "polynomial")
        self.assertEqual(d["coefficients"], list(pt100().coefficients))
        self.assertEqual(d["domain"], [0.0, 850.0])
        self.assertNotIn("rel_uncertainty", d)

    def test_to_dict_emits_rel_uncertainty_when_nonzero(self):
        m = PolynomialMap((1.0, 2.0), domain=(0.0, 1.0), rel_uncertainty=1e-4)
        self.assertEqual(m.to_dict()["rel_uncertainty"], 1e-4)

    def test_edge_dict_uses_the_explicit_map_form(self):
        d = _edge_dict("celsius", "ohm", pt100())
        self.assertEqual(d["map"]["type"], "polynomial")
        self.assertNotIn("factor", d)

    def test_round_trip_through_real_toml_text(self):
        tomli_w = pytest.importorskip("tomli_w")
        m = PolynomialMap(
            (PT100_R0, PT100_R0 * PT100_A, PT100_R0 * PT100_B),
            domain=(0.0, 850.0),
            rel_uncertainty=1.5e-3,
        )
        text = tomli_w.dumps({"edges": [_edge_dict("celsius", "ohm", m)]})
        self.assertIn('type = "polynomial"', text)
        reloaded = _build_map(tomllib.loads(text)["edges"][0]["map"])
        self.assertEqual(reloaded, m)
        self.assertAlmostEqual(reloaded(100.0), 138.5055, places=10)

    def test_inverse_round_trips_through_toml(self):
        tomli_w = pytest.importorskip("tomli_w")
        inv = pt100().inverse()
        text = tomli_w.dumps({"edges": [_edge_dict("ohm", "celsius", inv)]})
        reloaded = _build_map(tomllib.loads(text)["edges"][0]["map"])
        self.assertEqual(reloaded, inv)
        self.assertAlmostEqual(reloaded(138.5055), 100.0, places=9)

    def test_type_is_discoverable(self):
        self.assertIs(_find_map_class("polynomial"), PolynomialMap)
        self.assertIs(_find_map_class("polynomial_inverse"), PolynomialInverseMap)

    def test_invalid_toml_spec_reports_a_load_error(self):
        with self.assertRaises(PackageLoadError):
            _build_map({"type": "polynomial", "coefficients": [1.0, 2.0]})


class TestPolynomialMapCacheRoundTrip(unittest.TestCase):

    def test_schema_is_bumped_for_the_new_shape(self):
        self.assertGreaterEqual(_CACHE_SCHEMA, 4)

    def test_prim_round_trip(self):
        m = pt100()
        self.assertEqual(_prim_to_map(_map_to_prim(m)), m)

    def test_prim_round_trip_with_uncertainty(self):
        m = PolynomialMap((1.0, 2.0, -0.01), domain=(0.0, 10.0), rel_uncertainty=4e-4)
        restored = _prim_to_map(_map_to_prim(m))
        self.assertEqual(restored, m)
        self.assertEqual(restored.rel_uncertainty, 4e-4)

    def test_prim_omits_exact_uncertainty(self):
        self.assertNotIn("u", _map_to_prim(pt100()))

    def test_inverse_prim_round_trip(self):
        inv = pt100().inverse()
        restored = _prim_to_map(_map_to_prim(inv))
        self.assertEqual(restored, inv)
        self.assertAlmostEqual(restored(138.5055), 100.0, places=9)

    def test_prim_survives_marshal(self):
        """The cache is marshal-based, so the primitives must be marshalable."""
        prim = _map_to_prim(pt100().inverse())
        self.assertEqual(marshal.loads(marshal.dumps(prim)), prim)

    def test_nested_in_a_composed_map(self):
        composed = ComposedMap(LinearMap(2.0), pt100())
        restored = _prim_to_map(_map_to_prim(composed))
        self.assertEqual(restored, composed)


class TestPolynomialMapEndToEnd(unittest.TestCase):
    """A PT100 as a real conversion edge: celsius <-> ohm through the graph."""

    def setUp(self):
        self.rtd = ConversionContext(
            name="pt100",
            edges=(
                ContextEdge(src=units.celsius, dst=units.ohm, map=pt100()),
            ),
            description="IEC 60751 Callendar-Van Dusen curve for a PT100 RTD",
        )

    def test_forward_conversion(self):
        with using_context(self.rtd):
            r = Number(quantity=100.0, unit=units.celsius).to(units.ohm)
        self.assertAlmostEqual(r.quantity, 138.5055, places=9)
        self.assertEqual(r.unit, units.ohm)

    def test_reverse_conversion_uses_the_inverse_branch(self):
        with using_context(self.rtd):
            t = Number(quantity=138.5055, unit=units.ohm).to(units.celsius)
        self.assertAlmostEqual(t.quantity, 100.0, places=8)
        self.assertEqual(t.unit, units.celsius)

    def test_graph_stores_a_single_reverse_map(self):
        with using_context(self.rtd) as graph:
            reverse = graph._unit_edges[units.ohm.dimension][units.ohm][units.celsius]
        self.assertIsInstance(reverse, PolynomialInverseMap)

    def test_round_trip_through_the_graph(self):
        with using_context(self.rtd):
            for T in (0.0, 25.0, 100.0, 600.0, 850.0):
                there = Number(quantity=T, unit=units.celsius).to(units.ohm)
                back = there.to(units.celsius)
                self.assertAlmostEqual(back.quantity, T, delta=1e-9 * max(1.0, T))

    def test_uncertainty_transports_through_the_derivative(self):
        """dR = |dR/dT| * dT, with the analytic derivative."""
        with using_context(self.rtd):
            r = Number(quantity=100.0, unit=units.celsius, uncertainty=0.5).to(units.ohm)
        expected = abs(pt100().derivative(100.0)) * 0.5
        self.assertAlmostEqual(r.uncertainty, expected, places=10)

    def test_uncertainty_transports_on_the_reverse_edge(self):
        with using_context(self.rtd):
            t = Number(quantity=138.5055, unit=units.ohm, uncertainty=0.1).to(units.celsius)
        expected = 0.1 / abs(pt100().derivative(100.0))
        self.assertAlmostEqual(t.uncertainty, expected, places=8)

    def test_out_of_range_resistance_refuses(self):
        with using_context(self.rtd):
            with self.assertRaises(ValueError):
                Number(quantity=10.0, unit=units.ohm).to(units.celsius)

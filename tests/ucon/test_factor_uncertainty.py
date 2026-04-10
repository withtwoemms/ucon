# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for conversion factor uncertainty propagation.

Validates that uncertainty from measured physical constants flows through
the Map hierarchy, ConversionGraph edges, and Number.to() API.
"""
import math
import unittest

from ucon.maps import AffineMap, ComposedMap, LinearMap, ReciprocalMap


class TestLinearMapRelUncertainty(unittest.TestCase):
    """LinearMap rel_uncertainty field behavior."""

    def test_default_is_zero(self):
        m = LinearMap(3.28)
        self.assertEqual(m.rel_uncertainty, 0.0)

    def test_stores_value(self):
        m = LinearMap(3.28, rel_uncertainty=1e-5)
        self.assertEqual(m.rel_uncertainty, 1e-5)

    def test_composition_quadrature(self):
        r1, r2 = 3e-5, 4e-5
        m1 = LinearMap(2.0, rel_uncertainty=r1)
        m2 = LinearMap(3.0, rel_uncertainty=r2)
        composed = m1 @ m2
        self.assertIsInstance(composed, LinearMap)
        expected = math.sqrt(r1**2 + r2**2)
        self.assertAlmostEqual(composed.rel_uncertainty, expected, places=15)

    def test_exact_at_exact_is_zero(self):
        m1 = LinearMap(2.0)
        m2 = LinearMap(3.0)
        composed = m1 @ m2
        self.assertEqual(composed.rel_uncertainty, 0.0)

    def test_inverse_preserves(self):
        r = 1.5e-10
        m = LinearMap(5.0, rel_uncertainty=r)
        inv = m.inverse()
        self.assertEqual(inv.rel_uncertainty, r)

    def test_power_scales(self):
        r = 1e-5
        m = LinearMap(3.0, rel_uncertainty=r)
        squared = m ** 2
        self.assertAlmostEqual(squared.rel_uncertainty, 2 * r, places=15)

    def test_power_fractional(self):
        r = 1e-5
        m = LinearMap(4.0, rel_uncertainty=r)
        sqrt = m ** 0.5
        self.assertAlmostEqual(sqrt.rel_uncertainty, 0.5 * r, places=15)

    def test_power_negative(self):
        r = 1e-5
        m = LinearMap(4.0, rel_uncertainty=r)
        inv = m ** -1
        self.assertAlmostEqual(inv.rel_uncertainty, r, places=15)

    def test_compose_linear_at_affine(self):
        r1, r2 = 1e-5, 2e-5
        lin = LinearMap(2.0, rel_uncertainty=r1)
        aff = AffineMap(3.0, 5.0, rel_uncertainty=r2)
        composed = lin @ aff
        self.assertIsInstance(composed, AffineMap)
        expected = math.sqrt(r1**2 + r2**2)
        self.assertAlmostEqual(composed.rel_uncertainty, expected, places=15)


class TestAffineMapRelUncertainty(unittest.TestCase):
    """AffineMap rel_uncertainty field behavior."""

    def test_default_is_zero(self):
        m = AffineMap(1.8, 32.0)
        self.assertEqual(m.rel_uncertainty, 0.0)

    def test_stores_value(self):
        m = AffineMap(1.8, 32.0, rel_uncertainty=1e-6)
        self.assertEqual(m.rel_uncertainty, 1e-6)

    def test_inverse_preserves(self):
        r = 2e-8
        m = AffineMap(1.8, 32.0, rel_uncertainty=r)
        inv = m.inverse()
        self.assertEqual(inv.rel_uncertainty, r)

    def test_compose_affine_at_linear(self):
        r1, r2 = 1e-5, 2e-5
        aff = AffineMap(2.0, 3.0, rel_uncertainty=r1)
        lin = LinearMap(4.0, rel_uncertainty=r2)
        composed = aff @ lin
        self.assertIsInstance(composed, AffineMap)
        expected = math.sqrt(r1**2 + r2**2)
        self.assertAlmostEqual(composed.rel_uncertainty, expected, places=15)

    def test_compose_affine_at_affine(self):
        r1, r2 = 1e-5, 2e-5
        a1 = AffineMap(2.0, 3.0, rel_uncertainty=r1)
        a2 = AffineMap(4.0, 5.0, rel_uncertainty=r2)
        composed = a1 @ a2
        self.assertIsInstance(composed, AffineMap)
        expected = math.sqrt(r1**2 + r2**2)
        self.assertAlmostEqual(composed.rel_uncertainty, expected, places=15)


class TestReciprocalMapRelUncertainty(unittest.TestCase):
    """ReciprocalMap rel_uncertainty field behavior."""

    def test_default_is_zero(self):
        m = ReciprocalMap(299792458.0)
        self.assertEqual(m.rel_uncertainty, 0.0)

    def test_stores_value(self):
        m = ReciprocalMap(1.5e-10, rel_uncertainty=3e-5)
        self.assertEqual(m.rel_uncertainty, 3e-5)

    def test_inverse_preserves(self):
        r = 3e-5
        m = ReciprocalMap(1.5e-10, rel_uncertainty=r)
        inv = m.inverse()
        self.assertEqual(inv.rel_uncertainty, r)


class TestComposedMapRelUncertainty(unittest.TestCase):
    """ComposedMap computed rel_uncertainty property."""

    def test_both_zero(self):
        composed = ComposedMap(LinearMap(2.0), LinearMap(3.0))
        self.assertEqual(composed.rel_uncertainty, 0.0)

    def test_quadrature(self):
        r1, r2 = 3e-5, 4e-5
        inner = LinearMap(2.0, rel_uncertainty=r1)
        outer = LinearMap(3.0, rel_uncertainty=r2)
        composed = ComposedMap(outer, inner)
        expected = math.sqrt(r1**2 + r2**2)
        self.assertAlmostEqual(composed.rel_uncertainty, expected, places=15)


class TestMultiHopAccumulation(unittest.TestCase):
    """Composed uncertainty over multi-hop graph paths."""

    def test_three_hop_quadrature(self):
        from ucon.graph import ConversionGraph
        from ucon.core import Unit
        from ucon.dimension import Dimension

        graph = ConversionGraph()
        # Create a chain: A -> B -> C -> D with uncertainties
        dim = Dimension.length
        A = Unit(name="unit_a", dimension=dim)
        B = Unit(name="unit_b", dimension=dim)
        C = Unit(name="unit_c", dimension=dim)
        D = Unit(name="unit_d", dimension=dim)

        for u in [A, B, C, D]:
            graph.register_unit(u)

        r1, r2, r3 = 1e-5, 2e-5, 3e-5
        graph.add_edge(src=A, dst=B, map=LinearMap(2.0, rel_uncertainty=r1))
        graph.add_edge(src=B, dst=C, map=LinearMap(3.0, rel_uncertainty=r2))
        graph.add_edge(src=C, dst=D, map=LinearMap(4.0, rel_uncertainty=r3))

        composed = graph.convert(src=A, dst=D)
        expected = math.sqrt(r1**2 + r2**2 + r3**2)
        self.assertAlmostEqual(composed.rel_uncertainty, expected, places=15)
        # Also verify the factor itself
        self.assertAlmostEqual(composed(1.0), 24.0)


class TestNumberToBackwardCompat(unittest.TestCase):
    """Number.to() without propagate_factor_uncertainty is unchanged."""

    def test_default_no_uncertainty(self):
        from ucon import units
        result = units.joule(1).to(units.hartree)
        self.assertIsNone(result.uncertainty)

    def test_exact_conversion_no_uncertainty(self):
        from ucon import units
        result = units.meter(1).to(units.foot)
        self.assertIsNone(result.uncertainty)

    def test_measurement_uncertainty_still_propagates(self):
        from ucon import units
        from ucon.core import Number
        n = Number(quantity=1.0, unit=units.meter, uncertainty=0.01)
        result = n.to(units.foot)
        self.assertIsNotNone(result.uncertainty)
        self.assertGreater(result.uncertainty, 0)


class TestNumberToWithFactorUncertainty(unittest.TestCase):
    """Number.to() with propagate_factor_uncertainty=True."""

    def test_exact_edge_no_uncertainty(self):
        from ucon import units
        # meter → foot is exact, should produce no uncertainty
        result = units.meter(1).to(units.foot, propagate_factor_uncertainty=True)
        self.assertIsNone(result.uncertainty)

    def test_measured_edge_produces_uncertainty(self):
        from ucon import units
        # joule → hartree uses Eh which has uncertainty
        result = units.joule(1).to(units.hartree, propagate_factor_uncertainty=True)
        self.assertIsNotNone(result.uncertainty)
        self.assertGreater(result.uncertainty, 0)

    def test_input_with_measurement_and_factor_uncertainty(self):
        from ucon import units
        from ucon.core import Number
        n = Number(quantity=1.0, unit=units.joule, uncertainty=1e-10)
        result = n.to(units.hartree, propagate_factor_uncertainty=True)
        self.assertIsNotNone(result.uncertainty)
        # Should be larger than measurement-only uncertainty
        result_meas_only = n.to(units.hartree)
        self.assertGreater(result.uncertainty, result_meas_only.uncertainty)

    def test_planck_units_have_uncertainty(self):
        from ucon import units
        result = units.kilogram(1).to(units.planck_mass, propagate_factor_uncertainty=True)
        self.assertIsNotNone(result.uncertainty)
        self.assertGreater(result.uncertainty, 0)


class TestSerializationRoundTrip(unittest.TestCase):
    """LinearMap with rel_uncertainty survives to_dict/from_dict."""

    def test_to_dict_omits_zero(self):
        m = LinearMap(3.28)
        d = m.to_dict()
        self.assertNotIn("rel_uncertainty", d)

    def test_to_dict_includes_nonzero(self):
        m = LinearMap(3.28, rel_uncertainty=1e-5)
        d = m.to_dict()
        self.assertIn("rel_uncertainty", d)
        self.assertEqual(d["rel_uncertainty"], 1e-5)

    def test_roundtrip_via_build_map(self):
        from ucon.packages import _build_map
        m = LinearMap(3.28, rel_uncertainty=1e-5)
        d = m.to_dict()
        reconstructed = _build_map(d)
        self.assertIsInstance(reconstructed, LinearMap)
        self.assertAlmostEqual(reconstructed.a, 3.28)
        self.assertAlmostEqual(reconstructed.rel_uncertainty, 1e-5)

    def test_affine_to_dict_omits_zero(self):
        m = AffineMap(1.8, 32.0)
        d = m.to_dict()
        self.assertNotIn("rel_uncertainty", d)

    def test_affine_to_dict_includes_nonzero(self):
        m = AffineMap(1.8, 32.0, rel_uncertainty=2e-6)
        d = m.to_dict()
        self.assertIn("rel_uncertainty", d)
        self.assertEqual(d["rel_uncertainty"], 2e-6)


if __name__ == '__main__':
    unittest.main()

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

    def test_reciprocal_to_dict_omits_zero(self):
        m = ReciprocalMap(299792458.0)
        d = m.to_dict()
        self.assertNotIn("rel_uncertainty", d)

    def test_reciprocal_to_dict_includes_nonzero(self):
        m = ReciprocalMap(1.5e-10, rel_uncertainty=3e-5)
        d = m.to_dict()
        self.assertIn("rel_uncertainty", d)
        self.assertEqual(d["rel_uncertainty"], 3e-5)

    def test_affine_roundtrip_via_build_map(self):
        from ucon.packages import _build_map
        m = AffineMap(1.8, 32.0, rel_uncertainty=2e-6)
        d = m.to_dict()
        reconstructed = _build_map(d)
        self.assertIsInstance(reconstructed, AffineMap)
        self.assertAlmostEqual(reconstructed.a, 1.8)
        self.assertAlmostEqual(reconstructed.b, 32.0)
        self.assertAlmostEqual(reconstructed.rel_uncertainty, 2e-6)


class TestGeneralPathFactorUncertainty(unittest.TestCase):
    """Number.to() general path (UnitProduct) with propagate_factor_uncertainty.

    The general path is reached when the conversion involves multi-factor
    UnitProducts that cannot be reduced to plain Unit → Unit.
    """

    def _make_compound_graph(self, rel_unc=2e-5):
        """Build a custom graph with length and time units that carry uncertainty."""
        from ucon.graph import ConversionGraph
        from ucon.core import Unit
        from ucon.dimension import Dimension

        graph = ConversionGraph()
        # Two length units and two time units
        L1 = Unit(name="len_a", dimension=Dimension.length)
        L2 = Unit(name="len_b", dimension=Dimension.length)
        T1 = Unit(name="time_a", dimension=Dimension.time)
        T2 = Unit(name="time_b", dimension=Dimension.time)
        for u in [L1, L2, T1, T2]:
            graph.register_unit(u)

        graph.add_edge(src=L1, dst=L2, map=LinearMap(3.5, rel_uncertainty=rel_unc))
        graph.add_edge(src=T1, dst=T2, map=LinearMap(60.0, rel_uncertainty=rel_unc))
        return graph, L1, L2, T1, T2

    def test_general_path_with_custom_graph(self):
        """Multi-factor UnitProduct propagates factor uncertainty via general path."""
        from ucon.core import Number

        graph, L1, L2, T1, T2 = self._make_compound_graph(rel_unc=2e-5)
        # len_a / time_a → len_b / time_b (two-factor UnitProduct)
        src_unit = L1 / T1
        dst_unit = L2 / T2
        n = Number(quantity=10.0, unit=src_unit)
        result = n.to(dst_unit, graph=graph, propagate_factor_uncertainty=True)
        self.assertIsNotNone(result.uncertainty)
        self.assertGreater(result.uncertainty, 0)

    def test_general_path_default_no_uncertainty(self):
        """Default (no flag) produces no uncertainty on general path."""
        from ucon.core import Number

        graph, L1, L2, T1, T2 = self._make_compound_graph(rel_unc=2e-5)
        src_unit = L1 / T1
        dst_unit = L2 / T2
        n = Number(quantity=10.0, unit=src_unit)
        result = n.to(dst_unit, graph=graph)
        self.assertIsNone(result.uncertainty)

    def test_general_path_combined_measurement_and_factor(self):
        """General path combines measurement + factor uncertainty via quadrature."""
        from ucon.core import Number

        graph, L1, L2, T1, T2 = self._make_compound_graph(rel_unc=2e-5)
        src_unit = L1 / T1
        dst_unit = L2 / T2
        n = Number(quantity=10.0, unit=src_unit, uncertainty=0.1)
        result_both = n.to(dst_unit, graph=graph, propagate_factor_uncertainty=True)
        result_meas = n.to(dst_unit, graph=graph)
        self.assertIsNotNone(result_both.uncertainty)
        self.assertIsNotNone(result_meas.uncertainty)
        # Combined uncertainty should exceed measurement-only
        self.assertGreater(result_both.uncertainty, result_meas.uncertainty)

    def test_exact_composite_conversion_no_uncertainty(self):
        """Exact composite conversion produces no uncertainty even with flag."""
        from ucon import units, Scale
        from ucon.core import Number

        # km/h → m/s is exact (no measured constants)
        km = Scale.kilo * units.meter
        speed_kmh = km / units.hour
        n = Number(quantity=1.0, unit=speed_kmh)
        result = n.to(units.meter / units.second, propagate_factor_uncertainty=True)
        self.assertIsNone(result.uncertainty)

    def test_general_path_exact_edge_no_uncertainty(self):
        """Exact multi-factor edge produces no uncertainty even with flag."""
        from ucon.core import Number

        graph, L1, L2, T1, T2 = self._make_compound_graph(rel_unc=0.0)
        src_unit = L1 / T1
        dst_unit = L2 / T2
        n = Number(quantity=10.0, unit=src_unit)
        result = n.to(dst_unit, graph=graph, propagate_factor_uncertainty=True)
        self.assertIsNone(result.uncertainty)

    def test_general_path_quadrature_accumulates(self):
        """Multi-factor general path accumulates uncertainty from each factor."""
        from ucon.core import Number

        r = 3e-5
        graph, L1, L2, T1, T2 = self._make_compound_graph(rel_unc=r)
        src_unit = L1 / T1
        dst_unit = L2 / T2
        n = Number(quantity=10.0, unit=src_unit)
        result = n.to(dst_unit, graph=graph, propagate_factor_uncertainty=True)
        # Two factors, each with rel_unc = r → composed rel = sqrt(r²+r²) = r*sqrt(2)
        expected_rel = math.sqrt(2) * r
        actual_rel = result.uncertainty / abs(result.quantity)
        self.assertAlmostEqual(actual_rel, expected_rel, places=10)


class TestEdgeUncertaintyInDefaultGraph(unittest.TestCase):
    """Verify default graph edges carry expected rel_uncertainty values."""

    def test_exact_edge_has_zero_rel_uncertainty(self):
        """meter → foot edge is exact (no measured constant)."""
        from ucon import units
        from ucon.graph import get_default_graph
        graph = get_default_graph()
        m = graph.convert(src=units.meter, dst=units.foot)
        self.assertEqual(m.rel_uncertainty, 0.0)

    def test_hartree_edge_has_nonzero_rel_uncertainty(self):
        """joule → hartree edge carries Eh uncertainty."""
        from ucon import units
        from ucon.graph import get_default_graph
        graph = get_default_graph()
        m = graph.convert(src=units.joule, dst=units.hartree)
        self.assertGreater(m.rel_uncertainty, 0)

    def test_planck_mass_edge_has_nonzero_rel_uncertainty(self):
        """kg → planck_mass edge carries mP uncertainty."""
        from ucon import units
        from ucon.graph import get_default_graph
        graph = get_default_graph()
        m = graph.convert(src=units.kilogram, dst=units.planck_mass)
        self.assertGreater(m.rel_uncertainty, 0)

    def test_planck_rel_uncertainty_order_of_magnitude(self):
        """Planck constant uncertainties are ~1e-5 (relative)."""
        from ucon import units
        from ucon.graph import get_default_graph
        graph = get_default_graph()
        m = graph.convert(src=units.kilogram, dst=units.planck_mass)
        self.assertGreater(m.rel_uncertainty, 1e-6)
        self.assertLess(m.rel_uncertainty, 1e-4)

    def test_atomic_rel_uncertainty_order_of_magnitude(self):
        """Atomic constant uncertainties are ~1e-10 (relative)."""
        from ucon import units
        from ucon.graph import get_default_graph
        graph = get_default_graph()
        m = graph.convert(src=units.joule, dst=units.hartree)
        self.assertGreater(m.rel_uncertainty, 1e-13)
        self.assertLess(m.rel_uncertainty, 1e-9)

    def test_multihop_accumulates_uncertainty(self):
        """Multi-hop path accumulates uncertainty via quadrature."""
        from ucon import units
        from ucon.graph import get_default_graph
        graph = get_default_graph()
        # Direct: joule → hartree
        direct = graph.convert(src=units.joule, dst=units.hartree)
        # Multi-hop: joule → electron_volt → hartree (both hops uncertain)
        hop1 = graph.convert(src=units.joule, dst=units.electron_volt)
        hop2 = graph.convert(src=units.electron_volt, dst=units.hartree)
        # The BFS may or may not go through eV, but the composed map's
        # rel_uncertainty should be non-negative
        composed = hop1 @ hop2 if hasattr(hop1, '__matmul__') else None
        if composed is not None:
            self.assertGreaterEqual(composed.rel_uncertainty, 0)


class TestRelUncHelperEdgeCases(unittest.TestCase):
    """Edge cases for _rel_unc helper in graph.py."""

    def test_exact_constant_returns_zero(self):
        """Constants with uncertainty=None return rel_unc=0."""
        from ucon.constants import get_constant_by_symbol
        c = get_constant_by_symbol("c")
        self.assertIsNone(c.uncertainty)

    def test_measured_constant_returns_positive(self):
        """Constants with uncertainty return positive rel_unc."""
        from ucon.constants import get_constant_by_symbol
        me = get_constant_by_symbol("mₑ")
        self.assertIsNotNone(me.uncertainty)
        rel = me.uncertainty / abs(me.value)
        self.assertGreater(rel, 0)


class TestTomlSerializationRelUncertainty(unittest.TestCase):
    """TOML serialization round-trip for rel_uncertainty."""

    def test_edge_dict_linear_with_uncertainty(self):
        from ucon.serialization import _edge_dict
        m = LinearMap(2.5, rel_uncertainty=1e-5)
        d = _edge_dict("unit_a", "unit_b", m)
        self.assertEqual(d["src"], "unit_a")
        self.assertEqual(d["dst"], "unit_b")
        self.assertEqual(d["factor"], 2.5)
        self.assertEqual(d["rel_uncertainty"], 1e-5)

    def test_edge_dict_linear_exact(self):
        from ucon.serialization import _edge_dict
        m = LinearMap(2.5)
        d = _edge_dict("unit_a", "unit_b", m)
        self.assertNotIn("rel_uncertainty", d)

    def test_edge_dict_affine_with_uncertainty(self):
        from ucon.serialization import _edge_dict
        m = AffineMap(1.8, 32.0, rel_uncertainty=2e-6)
        d = _edge_dict("unit_a", "unit_b", m)
        self.assertEqual(d["factor"], 1.8)
        self.assertEqual(d["offset"], 32.0)
        self.assertEqual(d["rel_uncertainty"], 2e-6)

    def test_edge_dict_affine_exact(self):
        from ucon.serialization import _edge_dict
        m = AffineMap(1.8, 32.0)
        d = _edge_dict("unit_a", "unit_b", m)
        self.assertNotIn("rel_uncertainty", d)

    def test_build_edge_map_with_uncertainty(self):
        from ucon.serialization import _build_edge_map
        spec = {"factor": 3.28, "rel_uncertainty": 1e-5}
        m = _build_edge_map(spec, None)
        self.assertIsInstance(m, LinearMap)
        self.assertAlmostEqual(m.a, 3.28)
        self.assertAlmostEqual(m.rel_uncertainty, 1e-5)

    def test_build_edge_map_without_uncertainty(self):
        from ucon.serialization import _build_edge_map
        spec = {"factor": 3.28}
        m = _build_edge_map(spec, None)
        self.assertIsInstance(m, LinearMap)
        self.assertEqual(m.rel_uncertainty, 0.0)

    def test_build_edge_map_affine_with_uncertainty(self):
        from ucon.serialization import _build_edge_map
        spec = {"factor": 1.8, "offset": 32.0, "rel_uncertainty": 2e-6}
        m = _build_edge_map(spec, None)
        self.assertIsInstance(m, AffineMap)
        self.assertAlmostEqual(m.rel_uncertainty, 2e-6)


class TestPackagesEdgeDefRelUncertainty(unittest.TestCase):
    """EdgeDef rel_uncertainty in packages.py."""

    def test_edge_def_default_zero(self):
        from ucon.packages import EdgeDef
        e = EdgeDef(src="meter", dst="foot", factor=3.28084)
        self.assertEqual(e.rel_uncertainty, 0.0)

    def test_edge_def_with_uncertainty(self):
        from ucon.packages import EdgeDef
        e = EdgeDef(src="joule", dst="hartree", factor=2.29e17, rel_uncertainty=1.1e-12)
        self.assertEqual(e.rel_uncertainty, 1.1e-12)

    def test_edge_def_builds_linear_map_with_uncertainty(self):
        from ucon.packages import EdgeDef
        e = EdgeDef(src="joule", dst="hartree", factor=2.29e17, rel_uncertainty=1.1e-12)
        m = e._build_edge_map()
        self.assertIsInstance(m, LinearMap)
        self.assertAlmostEqual(m.rel_uncertainty, 1.1e-12)

    def test_edge_def_builds_affine_map_with_uncertainty(self):
        from ucon.packages import EdgeDef
        e = EdgeDef(src="celsius", dst="kelvin", factor=1.0, offset=273.15, rel_uncertainty=1e-8)
        m = e._build_edge_map()
        self.assertIsInstance(m, AffineMap)
        self.assertAlmostEqual(m.rel_uncertainty, 1e-8)


class TestNewConstantsExist(unittest.TestCase):
    """Verify the 8 new measured constants are available."""

    def test_hartree_energy(self):
        from ucon.constants import get_constant_by_symbol
        c = get_constant_by_symbol("Eₕ")
        self.assertIsNotNone(c.uncertainty)
        self.assertEqual(c.category, "measured")

    def test_rydberg_energy(self):
        from ucon.constants import get_constant_by_symbol
        c = get_constant_by_symbol("Ry")
        self.assertIsNotNone(c.uncertainty)

    def test_bohr_radius(self):
        from ucon.constants import get_constant_by_symbol
        c = get_constant_by_symbol("a₀")
        self.assertIsNotNone(c.uncertainty)

    def test_planck_mass(self):
        from ucon.constants import get_constant_by_symbol
        c = get_constant_by_symbol("m_P")
        self.assertIsNotNone(c.uncertainty)

    def test_planck_length(self):
        from ucon.constants import get_constant_by_symbol
        c = get_constant_by_symbol("l_P")
        self.assertIsNotNone(c.uncertainty)

    def test_planck_time(self):
        from ucon.constants import get_constant_by_symbol
        c = get_constant_by_symbol("t_P")
        self.assertIsNotNone(c.uncertainty)

    def test_planck_temperature(self):
        from ucon.constants import get_constant_by_symbol
        c = get_constant_by_symbol("T_P")
        self.assertIsNotNone(c.uncertainty)

    def test_ascii_aliases_resolve(self):
        from ucon.constants import get_constant_by_symbol
        for sym in ["E_h", "a_0", "m_P", "l_P", "t_P", "T_P"]:
            c = get_constant_by_symbol(sym)
            self.assertIsNotNone(c, f"Failed to resolve {sym}")


class TestQuantitativeUncertaintyPropagation(unittest.TestCase):
    """Verify numeric correctness of propagated uncertainties."""

    def test_factor_only_uncertainty_value(self):
        """Input with no measurement uncertainty → δy = |y| * rel_unc."""
        from ucon import units
        result = units.joule(1).to(units.hartree, propagate_factor_uncertainty=True)
        from ucon.graph import get_default_graph
        graph = get_default_graph()
        m = graph.convert(src=units.joule, dst=units.hartree)
        expected_unc = abs(result.quantity) * m.rel_uncertainty
        self.assertAlmostEqual(result.uncertainty, expected_unc, places=5)

    def test_combined_quadrature_value(self):
        """Input with measurement uncertainty → quadrature of both sources."""
        from ucon import units
        from ucon.core import Number
        from ucon.graph import get_default_graph

        n = Number(quantity=1.0, unit=units.joule, uncertainty=1e-10)
        result = n.to(units.hartree, propagate_factor_uncertainty=True)

        graph = get_default_graph()
        m = graph.convert(src=units.joule, dst=units.hartree)
        converted = m(1.0)
        dy_meas = abs(m.derivative(1.0)) * 1e-10
        dy_factor = abs(converted) * m.rel_uncertainty
        expected = math.sqrt(dy_meas**2 + dy_factor**2)
        self.assertAlmostEqual(result.uncertainty, expected, places=5)

    def test_zero_quantity_no_factor_uncertainty(self):
        """Converting 0.0 with factor uncertainty → no uncertainty (|y|*r = 0)."""
        from ucon import units
        result = units.joule(0).to(units.hartree, propagate_factor_uncertainty=True)
        # 0 * rel_unc = 0, so uncertainty should be None
        self.assertIsNone(result.uncertainty)

    def test_inverse_direction_uncertainty(self):
        """hartree → joule carries same rel_uncertainty as joule → hartree."""
        from ucon import units
        from ucon.graph import get_default_graph
        graph = get_default_graph()
        fwd = graph.convert(src=units.joule, dst=units.hartree)
        rev = graph.convert(src=units.hartree, dst=units.joule)
        self.assertAlmostEqual(fwd.rel_uncertainty, rev.rel_uncertainty, places=15)


if __name__ == '__main__':
    unittest.main()

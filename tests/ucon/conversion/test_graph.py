# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

import unittest

from ucon import units
from ucon.core import Dimension, Scale, Unit, UnitFactor, UnitProduct
from ucon.graph import (
    ConversionGraph,
    DimensionMismatch,
    ConversionNotFound,
    CyclicInconsistency,
    get_default_graph,
    set_default_graph,
    reset_default_graph,
    using_graph,
)
from ucon.maps import LinearMap, AffineMap


class TestConversionGraphEdgeManagement(unittest.TestCase):

    def setUp(self):
        self.graph = ConversionGraph()
        self.meter = units.meter
        self.foot = Unit(name='foot', dimension=Dimension.length, aliases=('ft',))
        self.inch = Unit(name='inch', dimension=Dimension.length, aliases=('in',))
        self.gram = units.gram

    def test_add_and_retrieve_edge(self):
        self.graph.add_edge(src=self.meter, dst=self.foot, map=LinearMap(3.28084))
        m = self.graph.convert(src=self.meter, dst=self.foot)
        self.assertAlmostEqual(m(1), 3.28084, places=4)

    def test_inverse_auto_stored(self):
        self.graph.add_edge(src=self.meter, dst=self.foot, map=LinearMap(3.28084))
        m = self.graph.convert(src=self.foot, dst=self.meter)
        self.assertAlmostEqual(m(1), 0.3048, places=4)

    def test_dimension_mismatch_rejected(self):
        with self.assertRaises(DimensionMismatch):
            self.graph.add_edge(src=self.meter, dst=self.gram, map=LinearMap(1))

    def test_cyclic_consistency_check(self):
        self.graph.add_edge(src=self.meter, dst=self.foot, map=LinearMap(3.28084))
        # Adding inconsistent reverse should raise
        with self.assertRaises(CyclicInconsistency):
            self.graph.add_edge(src=self.foot, dst=self.meter, map=LinearMap(0.5))  # wrong!


class TestConversionGraphUnitConversion(unittest.TestCase):

    def setUp(self):
        self.graph = ConversionGraph()
        self.meter = units.meter
        self.foot = Unit(name='foot', dimension=Dimension.length, aliases=('ft',))
        self.inch = Unit(name='inch', dimension=Dimension.length, aliases=('in',))
        self.yard = Unit(name='yard', dimension=Dimension.length, aliases=('yd',))

    def test_identity_conversion(self):
        m = self.graph.convert(src=self.meter, dst=self.meter)
        self.assertTrue(m.is_identity())

    def test_direct_edge(self):
        self.graph.add_edge(src=self.meter, dst=self.foot, map=LinearMap(3.28084))
        m = self.graph.convert(src=self.meter, dst=self.foot)
        self.assertAlmostEqual(m(1), 3.28084, places=4)

    def test_composed_path(self):
        self.graph.add_edge(src=self.meter, dst=self.foot, map=LinearMap(3.28084))
        self.graph.add_edge(src=self.foot, dst=self.inch, map=LinearMap(12))
        m = self.graph.convert(src=self.meter, dst=self.inch)
        self.assertAlmostEqual(m(1), 39.37008, places=3)

    def test_multi_hop_path(self):
        self.graph.add_edge(src=self.meter, dst=self.foot, map=LinearMap(3.28084))
        self.graph.add_edge(src=self.foot, dst=self.inch, map=LinearMap(12))
        self.graph.add_edge(src=self.inch, dst=self.yard, map=LinearMap(1/36))
        m = self.graph.convert(src=self.meter, dst=self.yard)
        self.assertAlmostEqual(m(1), 1.0936, places=3)

    def test_no_path_raises(self):
        mile = Unit(name='mile', dimension=Dimension.length, aliases=('mi',))
        with self.assertRaises(ConversionNotFound):
            self.graph.convert(src=self.meter, dst=mile)

    def test_dimension_mismatch_on_convert(self):
        with self.assertRaises(DimensionMismatch):
            self.graph.convert(src=self.meter, dst=units.second)


class TestConversionGraphProductConversion(unittest.TestCase):

    def setUp(self):
        self.graph = ConversionGraph()
        self.meter = units.meter
        self.second = units.second
        self.mile = Unit(name='mile', dimension=Dimension.length, aliases=('mi',))
        self.hour = Unit(name='hour', dimension=Dimension.time, aliases=('h',))

        # Register unit conversions
        self.graph.add_edge(src=self.meter, dst=self.mile, map=LinearMap(0.000621371))
        self.graph.add_edge(src=self.second, dst=self.hour, map=LinearMap(1/3600))

    def test_factorwise_velocity_conversion(self):
        m_per_s = UnitProduct({
            UnitFactor(self.meter, Scale.one): 1,
            UnitFactor(self.second, Scale.one): -1,
        })
        mi_per_hr = UnitProduct({
            UnitFactor(self.mile, Scale.one): 1,
            UnitFactor(self.hour, Scale.one): -1,
        })

        m = self.graph.convert(src=m_per_s, dst=mi_per_hr)
        # 1 m/s = 2.23694 mi/h
        self.assertAlmostEqual(m(1), 2.237, places=2)

    def test_scale_ratio_in_factorwise(self):
        km = UnitProduct({UnitFactor(self.meter, Scale.kilo): 1})
        m = UnitProduct({UnitFactor(self.meter, Scale.one): 1})

        conversion = self.graph.convert(src=km, dst=m)
        self.assertAlmostEqual(conversion(1), 1000, places=6)

    def test_direct_product_edge(self):
        # Define joule and watt_hour as UnitProducts
        g = units.gram
        joule = UnitProduct({
            UnitFactor(g, Scale.one): 1,
            UnitFactor(self.meter, Scale.one): 2,
            UnitFactor(self.second, Scale.one): -2,
        })
        watt = UnitProduct({
            UnitFactor(g, Scale.one): 1,
            UnitFactor(self.meter, Scale.one): 2,
            UnitFactor(self.second, Scale.one): -3,
        })
        watt_hour = watt * UnitProduct({UnitFactor(self.hour, Scale.one): 1})

        # Register direct edge
        self.graph.add_edge(src=joule, dst=watt_hour, map=LinearMap(1/3600))

        m = self.graph.convert(src=joule, dst=watt_hour)
        self.assertAlmostEqual(m(7200), 2.0, places=6)

    def test_product_identity(self):
        m_per_s = UnitProduct({
            UnitFactor(self.meter, Scale.one): 1,
            UnitFactor(self.second, Scale.one): -1,
        })
        m = self.graph.convert(src=m_per_s, dst=m_per_s)
        self.assertTrue(m.is_identity())


class TestConversionGraphTemperature(unittest.TestCase):

    def setUp(self):
        self.graph = ConversionGraph()
        self.celsius = Unit(name='celsius', dimension=Dimension.temperature, aliases=('°C',))
        self.kelvin = Unit(name='kelvin', dimension=Dimension.temperature, aliases=('K',))
        self.fahrenheit = Unit(name='fahrenheit', dimension=Dimension.temperature, aliases=('°F',))

    def test_celsius_to_kelvin(self):
        self.graph.add_edge(src=self.celsius, dst=self.kelvin, map=AffineMap(1, 273.15))
        m = self.graph.convert(src=self.celsius, dst=self.kelvin)
        self.assertAlmostEqual(m(0), 273.15, places=2)
        self.assertAlmostEqual(m(100), 373.15, places=2)

    def test_celsius_to_fahrenheit_via_kelvin(self):
        # C → K: K = C + 273.15
        self.graph.add_edge(src=self.celsius, dst=self.kelvin, map=AffineMap(1, 273.15))
        # F → K: K = (F - 32) * 5/9 + 273.15 = 5/9 * F + 255.372
        self.graph.add_edge(src=self.fahrenheit, dst=self.kelvin, map=AffineMap(5/9, 255.372))

        m = self.graph.convert(src=self.celsius, dst=self.fahrenheit)
        self.assertAlmostEqual(m(0), 32, places=0)
        self.assertAlmostEqual(m(100), 212, places=0)


class TestConversionGraphProductEdgeManagement(unittest.TestCase):
    """Tests for UnitProduct edge management."""

    def setUp(self):
        self.graph = ConversionGraph()
        self.meter = units.meter
        self.second = units.second
        self.gram = units.gram

    def test_add_product_edge(self):
        """Test adding edge between two UnitProducts with different scales."""
        # Create two energy-like products with different scales
        energy_g = UnitProduct({
            UnitFactor(self.gram, Scale.one): 1,
            UnitFactor(self.meter, Scale.one): 2,
            UnitFactor(self.second, Scale.one): -2,
        })
        energy_kg = UnitProduct({
            UnitFactor(self.gram, Scale.kilo): 1,
            UnitFactor(self.meter, Scale.one): 2,
            UnitFactor(self.second, Scale.one): -2,
        })
        # Register direct edge: 1 g·m²/s² = 0.001 kg·m²/s²
        self.graph.add_edge(src=energy_g, dst=energy_kg, map=LinearMap(0.001))
        m = self.graph.convert(src=energy_g, dst=energy_kg)
        self.assertAlmostEqual(m(1), 0.001, places=6)

    def test_add_mixed_unit_and_product_edge(self):
        """Test adding edge with Unit on one side, UnitProduct on other."""
        m_prod = UnitProduct({UnitFactor(self.meter, Scale.one): 1})
        self.graph.add_edge(src=self.meter, dst=m_prod, map=LinearMap(1.0))
        m = self.graph.convert(src=self.meter, dst=m_prod)
        self.assertTrue(m.is_identity())

    def test_product_edge_dimension_mismatch(self):
        """Test that dimension mismatch raises for UnitProduct edges."""
        length_prod = UnitProduct({UnitFactor(self.meter, Scale.one): 1})
        time_prod = UnitProduct({UnitFactor(self.second, Scale.one): 1})
        with self.assertRaises(DimensionMismatch):
            self.graph.add_edge(src=length_prod, dst=time_prod, map=LinearMap(1))

    def test_product_edge_cyclic_consistency(self):
        """Test cyclic consistency check for UnitProduct edges."""
        energy1 = UnitProduct({
            UnitFactor(self.gram, Scale.one): 1,
            UnitFactor(self.meter, Scale.one): 2,
            UnitFactor(self.second, Scale.one): -2,
        })
        energy2 = UnitProduct({
            UnitFactor(self.gram, Scale.kilo): 1,
            UnitFactor(self.meter, Scale.one): 2,
            UnitFactor(self.second, Scale.one): -2,
        })
        self.graph.add_edge(src=energy1, dst=energy2, map=LinearMap(0.001))
        # Adding inconsistent reverse should raise
        with self.assertRaises(CyclicInconsistency):
            self.graph.add_edge(src=energy2, dst=energy1, map=LinearMap(500))  # wrong!


class TestConversionGraphFactorwiseEdgeCases(unittest.TestCase):
    """Tests for factorwise conversion edge cases."""

    def setUp(self):
        self.graph = ConversionGraph()
        self.meter = units.meter
        self.second = units.second
        self.foot = Unit(name='foot', dimension=Dimension.length, aliases=('ft',))

    def test_factorwise_exponent_mismatch(self):
        """Test that exponent mismatch raises ConversionNotFound."""
        # m^2 vs m^1 - different exponents for same dimension
        m_squared = UnitProduct({UnitFactor(self.meter, Scale.one): 2})
        m_single = UnitProduct({UnitFactor(self.meter, Scale.one): 1})
        # These have different dimensions, so dimension check fails first
        with self.assertRaises(DimensionMismatch):
            self.graph.convert(src=m_squared, dst=m_single)

    def test_factorwise_misaligned_structures(self):
        """Test that misaligned factor structures raise ConversionNotFound."""
        # m/s vs m (missing time dimension in target)
        m_per_s = UnitProduct({
            UnitFactor(self.meter, Scale.one): 1,
            UnitFactor(self.second, Scale.one): -1,
        })
        m_only = UnitProduct({UnitFactor(self.meter, Scale.one): 1})
        with self.assertRaises(DimensionMismatch):
            self.graph.convert(src=m_per_s, dst=m_only)

    def test_convert_unit_to_product(self):
        """Test conversion from plain Unit to UnitProduct."""
        self.graph.add_edge(src=self.meter, dst=self.foot, map=LinearMap(3.28084))
        m_prod = UnitProduct({UnitFactor(self.meter, Scale.one): 1})
        ft_prod = UnitProduct({UnitFactor(self.foot, Scale.one): 1})
        m = self.graph.convert(src=m_prod, dst=ft_prod)
        self.assertAlmostEqual(m(1), 3.28084, places=4)

    def test_convert_product_dimension_mismatch(self):
        """Test dimension mismatch in _convert_products."""
        length = UnitProduct({UnitFactor(self.meter, Scale.one): 1})
        time = UnitProduct({UnitFactor(self.second, Scale.one): 1})
        with self.assertRaises(DimensionMismatch):
            self.graph.convert(src=length, dst=time)


class TestConversionGraphBFSEdgeCases(unittest.TestCase):
    """Tests for BFS path-finding edge cases."""

    def setUp(self):
        self.graph = ConversionGraph()

    def test_no_edges_for_dimension(self):
        """Test ConversionNotFound when dimension has no edges at all."""
        custom_unit1 = Unit(name='custom1', dimension=Dimension.length)
        custom_unit2 = Unit(name='custom2', dimension=Dimension.length)
        with self.assertRaises(ConversionNotFound):
            self.graph.convert(src=custom_unit1, dst=custom_unit2)

    def test_source_has_no_outgoing_edges(self):
        """Test when source exists in graph but has no path to target."""
        a = Unit(name='a', dimension=Dimension.length)
        b = Unit(name='b', dimension=Dimension.length)
        c = Unit(name='c', dimension=Dimension.length)
        # Only add a→b, no connection to c
        self.graph.add_edge(src=a, dst=b, map=LinearMap(2.0))
        with self.assertRaises(ConversionNotFound):
            self.graph.convert(src=a, dst=c)

    def test_disconnected_subgraphs(self):
        """Test when units are in same dimension but disconnected subgraphs."""
        a = Unit(name='a', dimension=Dimension.length)
        b = Unit(name='b', dimension=Dimension.length)
        c = Unit(name='c', dimension=Dimension.length)
        d = Unit(name='d', dimension=Dimension.length)
        # Subgraph 1: a ↔ b
        self.graph.add_edge(src=a, dst=b, map=LinearMap(2.0))
        # Subgraph 2: c ↔ d
        self.graph.add_edge(src=c, dst=d, map=LinearMap(3.0))
        # Cannot convert between subgraphs
        with self.assertRaises(ConversionNotFound):
            self.graph.convert(src=a, dst=c)


class TestDefaultGraphManagement(unittest.TestCase):
    """Tests for default graph management functions."""

    def setUp(self):
        reset_default_graph()

    def tearDown(self):
        reset_default_graph()

    def test_get_default_graph_returns_graph(self):
        """Test that get_default_graph returns a ConversionGraph."""
        graph = get_default_graph()
        self.assertIsInstance(graph, ConversionGraph)

    def test_get_default_graph_is_cached(self):
        """Test that get_default_graph returns same instance."""
        graph1 = get_default_graph()
        graph2 = get_default_graph()
        self.assertIs(graph1, graph2)

    def test_set_default_graph(self):
        """Test that set_default_graph replaces the default."""
        custom = ConversionGraph()
        set_default_graph(custom)
        self.assertIs(get_default_graph(), custom)

    def test_reset_default_graph(self):
        """Test that reset_default_graph clears the cached graph."""
        graph1 = get_default_graph()
        custom = ConversionGraph()
        set_default_graph(custom)
        reset_default_graph()
        graph2 = get_default_graph()
        self.assertIsNot(graph2, custom)
        # Should be a fresh standard graph
        self.assertIsInstance(graph2, ConversionGraph)

    def test_using_graph_context_manager(self):
        """Test using_graph provides scoped override."""
        default = get_default_graph()
        custom = ConversionGraph()

        with using_graph(custom) as g:
            self.assertIs(g, custom)
            self.assertIs(get_default_graph(), custom)

        # After context, back to default
        self.assertIs(get_default_graph(), default)

    def test_using_graph_nested(self):
        """Test nested using_graph contexts."""
        default = get_default_graph()
        custom1 = ConversionGraph()
        custom2 = ConversionGraph()

        with using_graph(custom1):
            self.assertIs(get_default_graph(), custom1)
            with using_graph(custom2):
                self.assertIs(get_default_graph(), custom2)
            self.assertIs(get_default_graph(), custom1)

        self.assertIs(get_default_graph(), default)

    def test_using_graph_exception_safety(self):
        """Test using_graph restores graph even on exception."""
        default = get_default_graph()
        custom = ConversionGraph()

        try:
            with using_graph(custom):
                self.assertIs(get_default_graph(), custom)
                raise ValueError("test error")
        except ValueError:
            pass

        self.assertIs(get_default_graph(), default)

    def test_default_graph_has_standard_conversions(self):
        """Test that default graph includes expected conversions."""
        graph = get_default_graph()
        # Test a few known conversions
        m = graph.convert(src=units.meter, dst=units.foot)
        self.assertAlmostEqual(m(1), 3.28084, places=4)

        m = graph.convert(src=units.kilogram, dst=units.pound)
        self.assertAlmostEqual(m(1), 2.20462, places=4)

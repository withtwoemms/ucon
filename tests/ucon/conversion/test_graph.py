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

# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for nines unit conversions.

Tests the 'nines' unit for SRE availability calculations,
including conversions from fraction/percent and uncertainty propagation.
"""

import unittest

from ucon import Dimension, units
from ucon.core import Number
from ucon.graph import DimensionMismatch


class TestNinesUnit(unittest.TestCase):
    """Test nines unit definition."""

    def test_nines_exists(self):
        self.assertIsNotNone(units.nines)

    def test_nines_dimension(self):
        self.assertEqual(units.nines.dimension, Dimension.ratio)

    def test_nines_name(self):
        self.assertEqual(units.nines.name, 'nines')

    def test_nines_aliases(self):
        self.assertIn('9s', units.nines.aliases)


class TestFractionUnit(unittest.TestCase):
    """Test fraction unit definition."""

    def test_fraction_exists(self):
        self.assertIsNotNone(units.fraction)

    def test_fraction_dimension(self):
        self.assertEqual(units.fraction.dimension, Dimension.ratio)

    def test_fraction_name(self):
        self.assertEqual(units.fraction.name, 'fraction')

    def test_fraction_aliases(self):
        self.assertIn('frac', units.fraction.aliases)
        self.assertIn('1', units.fraction.aliases)


class TestFractionToNines(unittest.TestCase):
    """Test conversion from fraction to nines."""

    def test_90_percent_is_1_nine(self):
        avail = Number(0.9, unit=units.fraction)
        result = avail.to(units.nines)
        self.assertAlmostEqual(result.quantity, 1.0, places=9)

    def test_99_percent_is_2_nines(self):
        avail = Number(0.99, unit=units.fraction)
        result = avail.to(units.nines)
        self.assertAlmostEqual(result.quantity, 2.0, places=9)

    def test_99_9_percent_is_3_nines(self):
        avail = Number(0.999, unit=units.fraction)
        result = avail.to(units.nines)
        self.assertAlmostEqual(result.quantity, 3.0, places=9)

    def test_99_99_percent_is_4_nines(self):
        avail = Number(0.9999, unit=units.fraction)
        result = avail.to(units.nines)
        self.assertAlmostEqual(result.quantity, 4.0, places=9)

    def test_99_999_percent_is_5_nines(self):
        avail = Number(0.99999, unit=units.fraction)
        result = avail.to(units.nines)
        self.assertAlmostEqual(result.quantity, 5.0, places=5)

    def test_99_9999_percent_is_6_nines(self):
        avail = Number(0.999999, unit=units.fraction)
        result = avail.to(units.nines)
        self.assertAlmostEqual(result.quantity, 6.0, places=5)


class TestNinesToFraction(unittest.TestCase):
    """Test conversion from nines to fraction."""

    def test_1_nine_to_fraction(self):
        n = Number(1, unit=units.nines)
        result = n.to(units.fraction)
        self.assertAlmostEqual(result.quantity, 0.9, places=9)

    def test_2_nines_to_fraction(self):
        n = Number(2, unit=units.nines)
        result = n.to(units.fraction)
        self.assertAlmostEqual(result.quantity, 0.99, places=9)

    def test_3_nines_to_fraction(self):
        n = Number(3, unit=units.nines)
        result = n.to(units.fraction)
        self.assertAlmostEqual(result.quantity, 0.999, places=9)

    def test_5_nines_to_fraction(self):
        n = Number(5, unit=units.nines)
        result = n.to(units.fraction)
        self.assertAlmostEqual(result.quantity, 0.99999, places=9)


class TestPercentToNines(unittest.TestCase):
    """Test conversion from percent to nines (via fraction)."""

    def test_99_percent_is_2_nines(self):
        uptime = Number(99, unit=units.percent)
        result = uptime.to(units.nines)
        self.assertAlmostEqual(result.quantity, 2.0, places=6)

    def test_99_9_percent_is_3_nines(self):
        uptime = Number(99.9, unit=units.percent)
        result = uptime.to(units.nines)
        self.assertAlmostEqual(result.quantity, 3.0, places=6)

    def test_99_99_percent_is_4_nines(self):
        uptime = Number(99.99, unit=units.percent)
        result = uptime.to(units.nines)
        self.assertAlmostEqual(result.quantity, 4.0, places=6)

    def test_99_999_percent_is_5_nines(self):
        uptime = Number(99.999, unit=units.percent)
        result = uptime.to(units.nines)
        self.assertAlmostEqual(result.quantity, 5.0, places=5)


class TestNinesToPercent(unittest.TestCase):
    """Test conversion from nines to percent."""

    def test_2_nines_to_percent(self):
        n = Number(2, unit=units.nines)
        result = n.to(units.percent)
        self.assertAlmostEqual(result.quantity, 99.0, places=6)

    def test_3_nines_to_percent(self):
        n = Number(3, unit=units.nines)
        result = n.to(units.percent)
        self.assertAlmostEqual(result.quantity, 99.9, places=6)

    def test_5_nines_to_percent(self):
        n = Number(5, unit=units.nines)
        result = n.to(units.percent)
        self.assertAlmostEqual(result.quantity, 99.999, places=5)


class TestNinesRoundTrip(unittest.TestCase):
    """Test round-trip conversions."""

    def test_fraction_nines_fraction(self):
        original = 0.99999
        avail = Number(original, unit=units.fraction)
        nines = avail.to(units.nines)
        back = nines.to(units.fraction)
        self.assertAlmostEqual(back.quantity, original, places=9)

    def test_percent_nines_percent(self):
        original = 99.99
        uptime = Number(original, unit=units.percent)
        nines = uptime.to(units.nines)
        back = nines.to(units.percent)
        self.assertAlmostEqual(back.quantity, original, places=6)

    def test_nines_fraction_nines(self):
        original = 4.0
        n = Number(original, unit=units.nines)
        frac = n.to(units.fraction)
        back = frac.to(units.nines)
        self.assertAlmostEqual(back.quantity, original, places=9)


class TestNinesUncertaintyPropagation(unittest.TestCase):
    """Test uncertainty propagation through nines conversion."""

    def test_uncertainty_is_propagated(self):
        avail = Number(0.99999, unit=units.fraction, uncertainty=0.00001)
        result = avail.to(units.nines)
        self.assertIsNotNone(result.uncertainty)
        self.assertGreater(result.uncertainty, 0)

    def test_high_availability_high_sensitivity(self):
        # At 5 nines, small availability changes → large nines changes
        avail = Number(0.99999, unit=units.fraction, uncertainty=0.00001)
        result = avail.to(units.nines)
        # derivative ≈ 1/((1-0.99999) * ln(10)) ≈ 43429
        # uncertainty ≈ 43429 * 0.00001 ≈ 0.43
        self.assertAlmostEqual(result.uncertainty, 0.43, places=1)

    def test_low_availability_low_sensitivity(self):
        # At 2 nines, sensitivity is lower
        avail = Number(0.99, unit=units.fraction, uncertainty=0.001)
        result = avail.to(units.nines)
        # derivative ≈ 1/((1-0.99) * ln(10)) ≈ 43.4
        # uncertainty ≈ 43.4 * 0.001 ≈ 0.043
        self.assertAlmostEqual(result.uncertainty, 0.043, places=2)

    def test_inverse_uncertainty_propagation(self):
        # Nines to fraction should also propagate uncertainty
        n = Number(5, unit=units.nines, uncertainty=0.1)
        result = n.to(units.fraction)
        self.assertIsNotNone(result.uncertainty)


class TestNinesDimensionMismatch(unittest.TestCase):
    """Test that nines cannot convert to incompatible dimensions."""

    def test_nines_to_length_raises(self):
        n = Number(5, unit=units.nines)
        with self.assertRaises(DimensionMismatch):
            n.to(units.meter)

    def test_nines_to_time_raises(self):
        n = Number(5, unit=units.nines)
        with self.assertRaises(DimensionMismatch):
            n.to(units.second)

    def test_nines_to_angle_raises(self):
        # Even though both are "dimensionless", pseudo-dimensions isolate them
        # DimensionMismatch is raised because ratio and angle are distinct dimensions
        n = Number(5, unit=units.nines)
        with self.assertRaises(DimensionMismatch):
            n.to(units.radian)


class TestNinesEdgeCases(unittest.TestCase):
    """Test edge cases for nines conversion."""

    def test_100_percent_raises(self):
        # 100% availability = log(0) = undefined
        avail = Number(1.0, unit=units.fraction)
        with self.assertRaises(ValueError):
            avail.to(units.nines)

    def test_zero_nines(self):
        # 0 nines = 0% availability (not useful but mathematically valid)
        n = Number(0, unit=units.nines)
        result = n.to(units.fraction)
        self.assertAlmostEqual(result.quantity, 0.0, places=9)

    def test_negative_nines(self):
        # Negative nines = availability < 0 (mathematically valid)
        n = Number(-1, unit=units.nines)
        result = n.to(units.fraction)
        # -1 nine → 1 - 10^(-(-1)) = 1 - 10 = -9
        self.assertAlmostEqual(result.quantity, -9.0, places=6)


class TestNinesCallableSyntax(unittest.TestCase):
    """Test callable syntax for nines unit."""

    def test_nines_callable(self):
        n = units.nines(5)
        self.assertIsInstance(n, Number)
        self.assertEqual(n.quantity, 5)
        self.assertEqual(n.unit, units.nines)

    def test_fraction_callable(self):
        f = units.fraction(0.99999)
        self.assertIsInstance(f, Number)
        self.assertEqual(f.quantity, 0.99999)
        self.assertEqual(f.unit, units.fraction)

    def test_callable_with_uncertainty(self):
        n = units.nines(5, uncertainty=0.1)
        self.assertEqual(n.uncertainty, 0.1)


class TestNinesUnitParsing(unittest.TestCase):
    """Test that nines can be parsed from strings."""

    def test_parse_nines(self):
        from ucon import get_unit_by_name
        unit = get_unit_by_name('nines')
        self.assertEqual(unit, units.nines)

    def test_parse_nines_alias(self):
        from ucon import get_unit_by_name
        unit = get_unit_by_name('9s')
        self.assertEqual(unit, units.nines)


if __name__ == '__main__':
    unittest.main()

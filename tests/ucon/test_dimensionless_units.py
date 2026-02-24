# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for v0.5.0 dimensionless units (pseudo-dimensions).

Tests pseudo-dimension isolation, angle/solid-angle/ratio unit conversions,
and cross-pseudo-dimension conversion failure.
"""

import math
import unittest

from ucon import units
from ucon.dimension import ANGLE, NONE, SOLID_ANGLE, RATIO, LENGTH, ENERGY
from ucon.graph import DimensionMismatch


class TestPseudoDimensionIsolation(unittest.TestCase):
    """Test that pseudo-dimensions are semantically isolated."""

    def test_angle_not_equal_to_none(self):
        self.assertNotEqual(ANGLE, NONE)

    def test_solid_angle_not_equal_to_none(self):
        self.assertNotEqual(SOLID_ANGLE, NONE)

    def test_ratio_not_equal_to_none(self):
        self.assertNotEqual(RATIO, NONE)

    def test_angle_not_equal_to_solid_angle(self):
        self.assertNotEqual(ANGLE, SOLID_ANGLE)

    def test_angle_not_equal_to_ratio(self):
        self.assertNotEqual(ANGLE, RATIO)

    def test_solid_angle_not_equal_to_ratio(self):
        self.assertNotEqual(SOLID_ANGLE, RATIO)

    def test_angle_equal_to_itself(self):
        self.assertEqual(ANGLE, ANGLE)

    def test_none_equal_to_itself(self):
        self.assertEqual(NONE, NONE)

    def test_all_pseudo_dimensions_have_zero_vector(self):
        # All pseudo-dimensions have dimensionless vectors
        self.assertTrue(NONE.vector.is_dimensionless())
        self.assertTrue(ANGLE.vector.is_dimensionless())
        self.assertTrue(SOLID_ANGLE.vector.is_dimensionless())
        self.assertTrue(RATIO.vector.is_dimensionless())


class TestPseudoDimensionHashing(unittest.TestCase):
    """Test that pseudo-dimensions can coexist in sets and dicts."""

    def test_all_pseudo_dimensions_in_set(self):
        dims = {NONE, ANGLE, SOLID_ANGLE, RATIO}
        self.assertEqual(len(dims), 4)

    def test_all_pseudo_dimensions_as_dict_keys(self):
        d = {
            NONE: "none",
            ANGLE: "angle",
            SOLID_ANGLE: "solid_angle",
            RATIO: "ratio",
        }
        self.assertEqual(len(d), 4)
        self.assertEqual(d[ANGLE], "angle")
        self.assertEqual(d[RATIO], "ratio")

    def test_distinct_hashes(self):
        hashes = {
            hash(NONE),
            hash(ANGLE),
            hash(SOLID_ANGLE),
            hash(RATIO),
        }
        self.assertEqual(len(hashes), 4)


class TestAlgebraicResolution(unittest.TestCase):
    """Test that algebraic operations resolve to none, not pseudo-dimensions."""

    def test_length_divided_by_length_is_none(self):
        result = LENGTH / LENGTH
        self.assertEqual(result, NONE)
        self.assertIs(result, NONE)

    def test_energy_divided_by_energy_is_none(self):
        result = ENERGY / ENERGY
        self.assertEqual(result, NONE)
        self.assertIs(result, NONE)

    def test_angle_times_length_is_length(self):
        # Since angle has zero vector, angle * length = length
        result = ANGLE * LENGTH
        self.assertEqual(result, LENGTH)


class TestUnitDimensions(unittest.TestCase):
    """Test that units have correct dimensions."""

    def test_radian_is_angle(self):
        self.assertEqual(units.radian.dimension, ANGLE)

    def test_degree_is_angle(self):
        self.assertEqual(units.degree.dimension, ANGLE)

    def test_steradian_is_solid_angle(self):
        self.assertEqual(units.steradian.dimension, SOLID_ANGLE)

    def test_square_degree_is_solid_angle(self):
        self.assertEqual(units.square_degree.dimension, SOLID_ANGLE)

    def test_percent_is_ratio(self):
        self.assertEqual(units.percent.dimension, RATIO)

    def test_ppm_is_ratio(self):
        self.assertEqual(units.ppm.dimension, RATIO)


class TestAngleConversions(unittest.TestCase):
    """Test angle unit conversions."""

    def test_radian_to_degree(self):
        angle = units.radian(math.pi)
        result = angle.to(units.degree)
        self.assertAlmostEqual(result.value, 180, places=9)

    def test_degree_to_radian(self):
        angle = units.degree(90)
        result = angle.to(units.radian)
        self.assertAlmostEqual(result.value, math.pi / 2, places=9)

    def test_turn_to_degree(self):
        angle = units.turn(1)
        result = angle.to(units.degree)
        self.assertAlmostEqual(result.value, 360, places=9)

    def test_turn_to_radian(self):
        angle = units.turn(1)
        result = angle.to(units.radian)
        self.assertAlmostEqual(result.value, 2 * math.pi, places=9)

    def test_turn_to_gradian(self):
        angle = units.turn(1)
        result = angle.to(units.gradian)
        self.assertAlmostEqual(result.value, 400, places=9)

    def test_degree_to_arcminute(self):
        angle = units.degree(1)
        result = angle.to(units.arcminute)
        self.assertAlmostEqual(result.value, 60, places=9)

    def test_arcminute_to_arcsecond(self):
        angle = units.arcminute(1)
        result = angle.to(units.arcsecond)
        self.assertAlmostEqual(result.value, 60, places=9)

    def test_degree_to_arcsecond_composed(self):
        angle = units.degree(1)
        result = angle.to(units.arcsecond)
        self.assertAlmostEqual(result.value, 3600, places=9)


class TestSolidAngleConversions(unittest.TestCase):
    """Test solid angle unit conversions."""

    def test_steradian_to_square_degree(self):
        solid = units.steradian(1)
        result = solid.to(units.square_degree)
        expected = (180 / math.pi) ** 2
        self.assertAlmostEqual(result.value, expected, places=1)

    def test_square_degree_to_steradian(self):
        solid = units.square_degree(1)
        result = solid.to(units.steradian)
        expected = (math.pi / 180) ** 2
        self.assertAlmostEqual(result.value, expected, places=9)


class TestRatioConversions(unittest.TestCase):
    """Test ratio unit conversions."""

    def test_one_to_percent(self):
        r = units.fraction(0.5)
        result = r.to(units.percent)
        self.assertAlmostEqual(result.value, 50, places=9)

    def test_percent_to_one(self):
        r = units.percent(25)
        result = r.to(units.fraction)
        self.assertAlmostEqual(result.value, 0.25, places=9)

    def test_one_to_ppm(self):
        r = units.fraction(0.001)
        result = r.to(units.ppm)
        self.assertAlmostEqual(result.value, 1000, places=9)

    def test_ppm_to_ppb(self):
        r = units.ppm(1)
        result = r.to(units.ppb)
        self.assertAlmostEqual(result.value, 1000, places=9)

    def test_one_to_permille(self):
        r = units.fraction(0.005)
        result = r.to(units.permille)
        self.assertAlmostEqual(result.value, 5, places=9)

    def test_basis_point_to_percent(self):
        r = units.basis_point(100)
        result = r.to(units.percent)
        self.assertAlmostEqual(result.value, 1, places=9)

    def test_percent_to_basis_point(self):
        r = units.percent(0.25)
        result = r.to(units.basis_point)
        self.assertAlmostEqual(result.value, 25, places=9)


class TestCrossPseudoDimensionFails(unittest.TestCase):
    """Test that cross-pseudo-dimension conversions fail."""

    def test_radian_to_percent_fails(self):
        # Pseudo-dimensions are semantically distinct, so this is DimensionMismatch
        with self.assertRaises(DimensionMismatch):
            units.radian(1).to(units.percent)

    def test_percent_to_degree_fails(self):
        with self.assertRaises(DimensionMismatch):
            units.percent(50).to(units.degree)

    def test_radian_to_steradian_fails(self):
        with self.assertRaises(DimensionMismatch):
            units.radian(1).to(units.steradian)

    def test_steradian_to_percent_fails(self):
        with self.assertRaises(DimensionMismatch):
            units.steradian(1).to(units.percent)

    def test_ppm_to_arcminute_fails(self):
        with self.assertRaises(DimensionMismatch):
            units.ppm(1000).to(units.arcminute)


if __name__ == "__main__":
    unittest.main()

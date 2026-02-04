# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for MCP server tools.

Tests the convert, list_units, list_scales, check_dimensions, and
list_dimensions tools exposed via the MCP server.
"""

import unittest

try:
    from ucon.mcp.server import convert, list_units, list_scales, check_dimensions, list_dimensions
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


@unittest.skipUnless(HAS_MCP, "MCP not installed")
class TestConvert(unittest.TestCase):
    """Test the convert tool."""

    def test_basic_conversion(self):
        result = convert(1000, "m", "km")
        self.assertAlmostEqual(result.quantity, 1.0, places=9)
        self.assertEqual(result.unit, "km")

    def test_returns_target_unit_string(self):
        """Convert should return the target unit string as requested."""
        result = convert(100, "cm", "m")
        self.assertEqual(result.unit, "m")

    def test_ratio_unit_preserved(self):
        """Ratio units like mg/kg should preserve the unit string."""
        result = convert(0.1, "mg/kg", "µg/kg")
        self.assertAlmostEqual(result.quantity, 100.0, places=6)
        self.assertEqual(result.unit, "µg/kg")

    def test_medical_units(self):
        """Medical unit aliases should work."""
        # mcg
        result = convert(500, "mcg", "mg")
        self.assertAlmostEqual(result.quantity, 0.5, places=9)
        self.assertEqual(result.unit, "mg")

        # cc
        result = convert(5, "cc", "mL")
        self.assertAlmostEqual(result.quantity, 5.0, places=9)
        self.assertEqual(result.unit, "mL")

        # min
        result = convert(120, "mL/h", "mL/min")
        self.assertAlmostEqual(result.quantity, 2.0, places=9)
        self.assertEqual(result.unit, "mL/min")


@unittest.skipUnless(HAS_MCP, "MCP not installed")
class TestListUnits(unittest.TestCase):
    """Test the list_units tool."""

    def test_returns_units(self):
        result = list_units()
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_filter_by_dimension(self):
        result = list_units(dimension="length")
        self.assertGreater(len(result), 0)
        for unit in result:
            self.assertEqual(unit.dimension, "length")


@unittest.skipUnless(HAS_MCP, "MCP not installed")
class TestListScales(unittest.TestCase):
    """Test the list_scales tool."""

    def test_returns_scales(self):
        result = list_scales()
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_includes_kilo(self):
        result = list_scales()
        names = [s.name for s in result]
        self.assertIn("kilo", names)


@unittest.skipUnless(HAS_MCP, "MCP not installed")
class TestCheckDimensions(unittest.TestCase):
    """Test the check_dimensions tool."""

    def test_compatible(self):
        result = check_dimensions("m", "ft")
        self.assertTrue(result.compatible)
        self.assertEqual(result.dimension_a, "length")
        self.assertEqual(result.dimension_b, "length")

    def test_incompatible(self):
        result = check_dimensions("m", "s")
        self.assertFalse(result.compatible)


@unittest.skipUnless(HAS_MCP, "MCP not installed")
class TestListDimensions(unittest.TestCase):
    """Test the list_dimensions tool."""

    def test_returns_dimensions(self):
        result = list_dimensions()
        self.assertIsInstance(result, list)
        self.assertIn("length", result)
        self.assertIn("mass", result)
        self.assertIn("time", result)


if __name__ == '__main__':
    unittest.main()

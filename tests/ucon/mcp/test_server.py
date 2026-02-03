# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for ucon MCP server.

Tests the tool functions directly without running the full MCP server.
These tests are skipped if the mcp package is not installed.
"""

import unittest

from ucon import Dimension, units
from ucon.core import Scale


class TestConvertTool(unittest.TestCase):
    """Test the convert tool."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import convert, ConversionResult
            cls.convert = staticmethod(convert)
            cls.ConversionResult = ConversionResult
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")

    def test_simple_conversion(self):
        """Test converting between simple units."""
        result = self.convert(1000, "m", "km")
        self.assertAlmostEqual(result.quantity, 1.0)
        self.assertEqual(result.dimension, "length")

    def test_scaled_unit_source(self):
        """Test conversion from scaled unit."""
        result = self.convert(5, "km", "m")
        self.assertAlmostEqual(result.quantity, 5000.0)

    def test_scaled_unit_target(self):
        """Test conversion to scaled unit."""
        result = self.convert(500, "g", "kg")
        self.assertAlmostEqual(result.quantity, 0.5)

    def test_composite_unit(self):
        """Test conversion with composite units."""
        result = self.convert(1, "m/s", "km/h")
        self.assertAlmostEqual(result.quantity, 3.6)

    def test_composite_ascii_notation(self):
        """Test composite unit with ASCII notation."""
        result = self.convert(9.8, "m/s^2", "m/s^2")
        self.assertAlmostEqual(result.quantity, 9.8)

    def test_returns_conversion_result(self):
        """Test that convert returns ConversionResult model."""
        result = self.convert(100, "cm", "m")
        self.assertIsInstance(result, self.ConversionResult)
        self.assertIsNotNone(result.unit)
        self.assertIsNotNone(result.dimension)

    def test_uncertainty_none_by_default(self):
        """Test that uncertainty is None when not provided."""
        result = self.convert(1, "m", "ft")
        self.assertIsNone(result.uncertainty)


class TestConvertToolErrors(unittest.TestCase):
    """Test error handling in the convert tool."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import convert
            cls.convert = staticmethod(convert)
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")

    def test_unknown_source_unit(self):
        """Test that unknown source unit raises error."""
        from ucon.units import UnknownUnitError
        with self.assertRaises(UnknownUnitError):
            self.convert(1, "foobar", "m")

    def test_unknown_target_unit(self):
        """Test that unknown target unit raises error."""
        from ucon.units import UnknownUnitError
        with self.assertRaises(UnknownUnitError):
            self.convert(1, "m", "bazqux")

    def test_dimension_mismatch(self):
        """Test that incompatible dimensions raise error."""
        from ucon.graph import DimensionMismatch
        with self.assertRaises(DimensionMismatch):
            self.convert(1, "m", "s")


class TestListUnitsTool(unittest.TestCase):
    """Test the list_units tool."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import list_units, UnitInfo
            cls.list_units = staticmethod(list_units)
            cls.UnitInfo = UnitInfo
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")

    def test_returns_list(self):
        """Test that list_units returns a list."""
        result = self.list_units()
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_returns_unit_info(self):
        """Test that list items are UnitInfo objects."""
        result = self.list_units()
        self.assertIsInstance(result[0], self.UnitInfo)

    def test_unit_info_fields(self):
        """Test that UnitInfo has expected fields."""
        result = self.list_units()
        unit = result[0]
        self.assertIsNotNone(unit.name)
        self.assertIsNotNone(unit.shorthand)
        self.assertIsInstance(unit.aliases, list)
        self.assertIsNotNone(unit.dimension)
        self.assertIsInstance(unit.scalable, bool)

    def test_filter_by_dimension(self):
        """Test filtering units by dimension."""
        result = self.list_units(dimension="length")
        self.assertGreater(len(result), 0)
        for unit in result:
            self.assertEqual(unit.dimension, "length")

    def test_filter_excludes_other_dimensions(self):
        """Test that filter excludes other dimensions."""
        length_units = self.list_units(dimension="length")
        time_units = self.list_units(dimension="time")

        length_names = {u.name for u in length_units}
        time_names = {u.name for u in time_units}

        self.assertTrue(length_names.isdisjoint(time_names))

    def test_meter_is_scalable(self):
        """Test that meter is marked as scalable."""
        result = self.list_units(dimension="length")
        meter = next((u for u in result if u.name == "meter"), None)
        self.assertIsNotNone(meter)
        self.assertTrue(meter.scalable)

    def test_no_duplicates(self):
        """Test that unit names are unique."""
        result = self.list_units()
        names = [u.name for u in result]
        self.assertEqual(len(names), len(set(names)))


class TestListScalesTool(unittest.TestCase):
    """Test the list_scales tool."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import list_scales, ScaleInfo
            cls.list_scales = staticmethod(list_scales)
            cls.ScaleInfo = ScaleInfo
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")

    def test_returns_list(self):
        """Test that list_scales returns a list."""
        result = self.list_scales()
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_returns_scale_info(self):
        """Test that list items are ScaleInfo objects."""
        result = self.list_scales()
        self.assertIsInstance(result[0], self.ScaleInfo)

    def test_scale_info_fields(self):
        """Test that ScaleInfo has expected fields."""
        result = self.list_scales()
        scale = result[0]
        self.assertIsNotNone(scale.name)
        self.assertIsNotNone(scale.prefix)
        self.assertIsNotNone(scale.factor)

    def test_includes_kilo(self):
        """Test that kilo is included."""
        result = self.list_scales()
        kilo = next((s for s in result if s.name == "kilo"), None)
        self.assertIsNotNone(kilo)
        self.assertEqual(kilo.prefix, "k")
        self.assertAlmostEqual(kilo.factor, 1000.0)

    def test_includes_milli(self):
        """Test that milli is included."""
        result = self.list_scales()
        milli = next((s for s in result if s.name == "milli"), None)
        self.assertIsNotNone(milli)
        self.assertEqual(milli.prefix, "m")
        self.assertAlmostEqual(milli.factor, 0.001)

    def test_includes_binary_prefixes(self):
        """Test that binary prefixes are included."""
        result = self.list_scales()
        kibi = next((s for s in result if s.name == "kibi"), None)
        self.assertIsNotNone(kibi)
        self.assertEqual(kibi.prefix, "Ki")
        self.assertAlmostEqual(kibi.factor, 1024.0)

    def test_excludes_identity_scale(self):
        """Test that Scale.one is not included."""
        result = self.list_scales()
        one = next((s for s in result if s.name == "one"), None)
        self.assertIsNone(one)

    def test_matches_scale_enum(self):
        """Test that all Scale enum members (except one) are represented."""
        result = self.list_scales()
        result_names = {s.name for s in result}

        for scale in Scale:
            if scale == Scale.one:
                continue
            self.assertIn(scale.name, result_names)


class TestCheckDimensionsTool(unittest.TestCase):
    """Test the check_dimensions tool."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import check_dimensions, DimensionCheck
            cls.check_dimensions = staticmethod(check_dimensions)
            cls.DimensionCheck = DimensionCheck
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")

    def test_compatible_same_unit(self):
        """Test that same unit is compatible."""
        result = self.check_dimensions("m", "m")
        self.assertTrue(result.compatible)
        self.assertEqual(result.dimension_a, "length")
        self.assertEqual(result.dimension_b, "length")

    def test_compatible_different_units_same_dimension(self):
        """Test that different units of same dimension are compatible."""
        result = self.check_dimensions("m", "ft")
        self.assertTrue(result.compatible)

    def test_compatible_scaled_units(self):
        """Test that scaled units of same dimension are compatible."""
        result = self.check_dimensions("km", "mm")
        self.assertTrue(result.compatible)

    def test_incompatible_different_dimensions(self):
        """Test that different dimensions are incompatible."""
        result = self.check_dimensions("m", "s")
        self.assertFalse(result.compatible)
        self.assertEqual(result.dimension_a, "length")
        self.assertEqual(result.dimension_b, "time")

    def test_returns_dimension_check(self):
        """Test that check_dimensions returns DimensionCheck model."""
        result = self.check_dimensions("kg", "g")
        self.assertIsInstance(result, self.DimensionCheck)


class TestListDimensionsTool(unittest.TestCase):
    """Test the list_dimensions tool."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import list_dimensions
            cls.list_dimensions = staticmethod(list_dimensions)
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")

    def test_returns_list(self):
        """Test that list_dimensions returns a list."""
        result = self.list_dimensions()
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_includes_base_dimensions(self):
        """Test that base dimensions are included."""
        result = self.list_dimensions()
        self.assertIn("length", result)
        self.assertIn("mass", result)
        self.assertIn("time", result)

    def test_includes_derived_dimensions(self):
        """Test that derived dimensions are included."""
        result = self.list_dimensions()
        # Check for some common derived dimensions if they exist
        # This depends on what's in the Dimension enum
        self.assertIn("none", result)

    def test_matches_dimension_enum(self):
        """Test that all Dimension enum members are represented."""
        result = self.list_dimensions()
        for dim in Dimension:
            self.assertIn(dim.name, result)

    def test_sorted(self):
        """Test that dimensions are sorted alphabetically."""
        result = self.list_dimensions()
        self.assertEqual(result, sorted(result))


if __name__ == '__main__':
    unittest.main()

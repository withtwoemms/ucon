# © 2026 The Radiativity Company
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
            from ucon.mcp.suggestions import ConversionError
            cls.convert = staticmethod(convert)
            cls.ConversionError = ConversionError
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")

    def test_unknown_source_unit(self):
        """Test that unknown source unit returns ConversionError."""
        result = self.convert(1, "foobar", "m")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "unknown_unit")
        self.assertEqual(result.parameter, "from_unit")

    def test_unknown_target_unit(self):
        """Test that unknown target unit returns ConversionError."""
        result = self.convert(1, "m", "bazqux")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "unknown_unit")
        self.assertEqual(result.parameter, "to_unit")

    def test_dimension_mismatch(self):
        """Test that incompatible dimensions return ConversionError."""
        result = self.convert(1, "m", "s")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "dimension_mismatch")


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


class TestConvertToolSuggestions(unittest.TestCase):
    """Test suggestion features in the convert tool."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import convert
            from ucon.mcp.suggestions import ConversionError
            cls.convert = staticmethod(convert)
            cls.ConversionError = ConversionError
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")

    def test_typo_single_match(self):
        """Test that typo with single high-confidence match gets likely_fix."""
        result = self.convert(100, "meetr", "ft")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "unknown_unit")
        self.assertEqual(result.parameter, "from_unit")
        self.assertIsNotNone(result.likely_fix)
        self.assertIn("meter", result.likely_fix)

    def test_bad_to_unit(self):
        """Test that typo in to_unit position is detected."""
        result = self.convert(100, "meter", "feeet")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.parameter, "to_unit")
        # Should suggest "foot"
        self.assertTrue(
            (result.likely_fix and "foot" in result.likely_fix) or
            any("foot" in h for h in result.hints)
        )

    def test_unrecognizable_no_spurious_matches(self):
        """Test that completely unknown unit doesn't produce spurious matches."""
        result = self.convert(100, "xyzzy", "kg")
        self.assertIsInstance(result, self.ConversionError)
        self.assertIsNone(result.likely_fix)
        self.assertTrue(any("list_units" in h for h in result.hints))

    def test_dimension_mismatch_readable(self):
        """Test that dimension mismatch error uses readable names."""
        result = self.convert(100, "meter", "second")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "dimension_mismatch")
        self.assertEqual(result.got, "length")
        self.assertIn("length", result.error)
        self.assertIn("time", result.error)
        self.assertNotIn("Vector", result.error)

    def test_derived_dimension_readable(self):
        """Test that derived dimension uses readable name in error."""
        result = self.convert(1, "m/s", "kg")
        self.assertIsInstance(result, self.ConversionError)
        self.assertIn("velocity", result.error)
        self.assertNotIn("Vector", result.error)

    def test_unnamed_derived_dimension(self):
        """Test that unnamed derived dimension doesn't show Vector."""
        result = self.convert(1, "m^3/s", "kg")
        self.assertIsInstance(result, self.ConversionError)
        # Should show readable format, not Vector(...)
        self.assertNotIn("Vector", result.error)
        # Should have some dimension info
        self.assertTrue("length" in result.error or "derived(" in result.error)

    def test_pseudo_dimension_explains_isolation(self):
        """Test that pseudo-dimension isolation is explained."""
        result = self.convert(1, "radian", "percent")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "no_conversion_path")
        self.assertEqual(result.got, "angle")
        self.assertEqual(result.expected, "ratio")
        self.assertTrue(
            any("cannot interconvert" in h or "isolated" in h for h in result.hints)
        )

    def test_compatible_units_in_hints(self):
        """Test that dimension mismatch includes compatible units."""
        result = self.convert(100, "meter", "second")
        self.assertIsInstance(result, self.ConversionError)
        # Should suggest compatible length units
        hints_str = str(result.hints)
        self.assertTrue(
            "ft" in hints_str or "in" in hints_str or
            "foot" in hints_str or "inch" in hints_str
        )

    def test_no_vector_in_any_error(self):
        """Test that no error response contains raw Vector representation."""
        cases = [
            ("m^3/s", "kg"),
            ("kg*m/s^2", "A"),
        ]
        for from_u, to_u in cases:
            result = self.convert(1, from_u, to_u)
            if isinstance(result, self.ConversionError):
                self.assertNotIn("Vector(", result.error)
                for h in result.hints:
                    self.assertNotIn("Vector(", h)


class TestCheckDimensionsErrors(unittest.TestCase):
    """Test error handling in the check_dimensions tool."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import check_dimensions
            from ucon.mcp.suggestions import ConversionError
            cls.check_dimensions = staticmethod(check_dimensions)
            cls.ConversionError = ConversionError
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")

    def test_bad_unit_a(self):
        """Test that bad unit_a returns ConversionError."""
        result = self.check_dimensions("meetr", "foot")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.parameter, "unit_a")

    def test_bad_unit_b(self):
        """Test that bad unit_b returns ConversionError."""
        result = self.check_dimensions("meter", "fooot")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.parameter, "unit_b")


class TestListUnitsErrors(unittest.TestCase):
    """Test error handling in the list_units tool."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import list_units
            from ucon.mcp.suggestions import ConversionError
            cls.list_units = staticmethod(list_units)
            cls.ConversionError = ConversionError
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")

    def test_bad_dimension_filter(self):
        """Test that bad dimension filter returns ConversionError."""
        result = self.list_units(dimension="lenth")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.parameter, "dimension")
        # Should suggest "length"
        self.assertTrue(
            (result.likely_fix and "length" in result.likely_fix) or
            any("length" in h for h in result.hints)
        )


class TestParseErrorHandling(unittest.TestCase):
    """Test that malformed unit expressions return structured errors."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import convert, check_dimensions
            from ucon.mcp.suggestions import ConversionError
            cls.convert = staticmethod(convert)
            cls.check_dimensions = staticmethod(check_dimensions)
            cls.ConversionError = ConversionError
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")

    def test_unbalanced_parens_from_unit(self):
        """Test that unbalanced parentheses in from_unit returns parse_error."""
        result = self.convert(1, "W/(m^2*K", "W/(m^2*K)")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "parse_error")
        self.assertEqual(result.parameter, "from_unit")
        self.assertIn("parse", result.error.lower())

    def test_unbalanced_parens_to_unit(self):
        """Test that unbalanced parentheses in to_unit returns parse_error."""
        result = self.convert(1, "W/(m^2*K)", "W/(m^2*K")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "parse_error")
        self.assertEqual(result.parameter, "to_unit")

    def test_parse_error_in_check_dimensions(self):
        """Test that parse errors work in check_dimensions too."""
        result = self.check_dimensions("m/s)", "m/s")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "parse_error")
        self.assertEqual(result.parameter, "unit_a")

    def test_parse_error_hints_helpful(self):
        """Test that parse error hints are helpful."""
        result = self.convert(1, "kg*(m/s^2", "N")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "parse_error")
        # Should have hints about syntax
        hints_str = str(result.hints)
        self.assertTrue(
            "parenthes" in hints_str.lower() or
            "syntax" in hints_str.lower() or
            "parse" in hints_str.lower()
        )


class TestCountDimensionMCP(unittest.TestCase):
    """Test count dimension and each unit in MCP tools."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import (
                convert, list_units, list_dimensions, check_dimensions
            )
            from ucon.mcp.suggestions import ConversionError
            cls.convert = staticmethod(convert)
            cls.list_units = staticmethod(list_units)
            cls.list_dimensions = staticmethod(list_dimensions)
            cls.check_dimensions = staticmethod(check_dimensions)
            cls.ConversionError = ConversionError
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")

    def test_list_units_count_dimension(self):
        """Test that list_units(dimension='count') returns each."""
        result = self.list_units(dimension="count")
        names = [u.name for u in result]
        self.assertIn("each", names)

    def test_list_dimensions_includes_count(self):
        """Test that list_dimensions returns count."""
        result = self.list_dimensions()
        self.assertIn("count", result)

    def test_convert_each_rejected_cross_dimension(self):
        """Test that converting ea to rad returns dimension mismatch."""
        result = self.convert(5, "ea", "rad")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "dimension_mismatch")

    def test_convert_each_to_percent_rejected(self):
        """Test that converting ea to % returns dimension mismatch."""
        result = self.convert(5, "ea", "%")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "dimension_mismatch")

    def test_check_dimensions_ea_vs_rad_incompatible(self):
        """Test that ea and rad are incompatible."""
        result = self.check_dimensions("ea", "rad")
        self.assertFalse(result.compatible)
        self.assertEqual(result.dimension_a, "count")
        self.assertEqual(result.dimension_b, "angle")

    def test_check_dimensions_mg_per_ea_vs_mg_compatible(self):
        """Test that mg/ea and mg are compatible (count cancels dimensionally)."""
        result = self.check_dimensions("mg/ea", "mg")
        self.assertTrue(result.compatible)
        self.assertEqual(result.dimension_a, "mass")
        self.assertEqual(result.dimension_b, "mass")

    def test_each_fuzzy_recovery(self):
        """Test that typo 'eech' suggests each."""
        result = self.convert(5, "eech", "kg")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "unknown_unit")
        # Should suggest 'each' in likely_fix or hints
        suggestions = (result.likely_fix or "") + str(result.hints)
        self.assertTrue(
            "each" in suggestions.lower() or "ea" in suggestions.lower(),
            f"Expected 'each' or 'ea' in suggestions: {suggestions}"
        )


if __name__ == '__main__':
    unittest.main()

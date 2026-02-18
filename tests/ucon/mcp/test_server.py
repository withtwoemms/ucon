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
        """Test that converting ea to rad is rejected (pseudo-dimension isolation)."""
        result = self.convert(5, "ea", "rad")
        self.assertIsInstance(result, self.ConversionError)
        # Pseudo-dimensions have same zero vector but are isolated
        self.assertEqual(result.error_type, "no_conversion_path")

    def test_convert_each_to_percent_rejected(self):
        """Test that converting ea to % is rejected (pseudo-dimension isolation)."""
        result = self.convert(5, "ea", "%")
        self.assertIsInstance(result, self.ConversionError)
        # Pseudo-dimensions have same zero vector but are isolated
        self.assertEqual(result.error_type, "no_conversion_path")

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


class TestComputeTool(unittest.TestCase):
    """Test the compute tool for multi-step factor-label calculations."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import compute, ComputeResult, ComputeStep
            from ucon.mcp.suggestions import ConversionError
            cls.compute = staticmethod(compute)
            cls.ComputeResult = ComputeResult
            cls.ComputeStep = ComputeStep
            cls.ConversionError = ConversionError
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")

    def test_simple_single_factor(self):
        """Test simple single-factor conversion (km to m)."""
        result = self.compute(
            initial_value=5,
            initial_unit="km",
            factors=[
                {"value": 1000, "numerator": "m", "denominator": "km"},
            ]
        )
        self.assertIsInstance(result, self.ComputeResult)
        self.assertAlmostEqual(result.quantity, 5000.0)
        self.assertEqual(result.dimension, "length")

    def test_returns_steps(self):
        """Test that compute returns step trace."""
        result = self.compute(
            initial_value=10,
            initial_unit="m",
            factors=[
                {"value": 100, "numerator": "cm", "denominator": "m"},
            ]
        )
        self.assertIsInstance(result, self.ComputeResult)
        self.assertIsInstance(result.steps, list)
        self.assertEqual(len(result.steps), 2)  # initial + 1 factor
        self.assertIsInstance(result.steps[0], self.ComputeStep)

    def test_initial_step_recorded(self):
        """Test that initial value is recorded as first step."""
        result = self.compute(
            initial_value=100,
            initial_unit="lb",
            factors=[
                {"value": 1, "numerator": "kg", "denominator": "2.205 lb"},
            ]
        )
        self.assertIsInstance(result, self.ComputeResult)
        self.assertIn("100", result.steps[0].factor)
        self.assertIn("lb", result.steps[0].factor)
        self.assertEqual(result.steps[0].dimension, "mass")

    def test_medical_dosage_calculation(self):
        """Test medical dosing calculation: 154 lb patient, 15 mg/kg/day, 3 doses/day."""
        result = self.compute(
            initial_value=154,
            initial_unit="lb",
            factors=[
                {"value": 1, "numerator": "kg", "denominator": "2.205 lb"},
                {"value": 15, "numerator": "mg", "denominator": "kg*day"},
                {"value": 1, "numerator": "day", "denominator": "3 ea"},  # ea = each (dose)
            ]
        )
        self.assertIsInstance(result, self.ComputeResult)
        # 154 lb × (1 kg / 2.205 lb) × (15 mg / kg·day) × (1 day / 3 ea)
        # = 154 / 2.205 × 15 / 3 mg/ea
        # ≈ 69.84 × 5 mg/ea ≈ 349.2 mg/ea
        expected = 154 / 2.205 * 15 / 3
        self.assertAlmostEqual(result.quantity, expected, places=2)
        # Should have mass/ea dimension → mass (count is dimensionless)
        self.assertEqual(len(result.steps), 4)  # initial + 3 factors

    def test_denominator_with_numeric_prefix(self):
        """Test that denominators can have numeric prefixes (e.g., '2.205 lb')."""
        result = self.compute(
            initial_value=100,
            initial_unit="lb",
            factors=[
                {"value": 1, "numerator": "kg", "denominator": "2.205 lb"},
            ]
        )
        self.assertIsInstance(result, self.ComputeResult)
        expected = 100 / 2.205
        self.assertAlmostEqual(result.quantity, expected, places=2)

    def test_multi_factor_unit_cancellation(self):
        """Test that units cancel correctly across multiple factors."""
        # m/s * s/min * min/h → m/h
        result = self.compute(
            initial_value=1,
            initial_unit="m/s",
            factors=[
                {"value": 60, "numerator": "s", "denominator": "min"},
                {"value": 60, "numerator": "min", "denominator": "h"},
            ]
        )
        self.assertIsInstance(result, self.ComputeResult)
        self.assertAlmostEqual(result.quantity, 3600.0)  # 1 m/s = 3600 m/h

    # -------------------------------------------------------------------------
    # Chemical Engineering / Stoichiometry Tests
    # -------------------------------------------------------------------------

    def test_stoichiometry_molar_mass_conversion(self):
        """Test molar mass calculation: grams to moles.

        Example: How many moles in 180 g of glucose (C6H12O6, MW = 180.16 g/mol)?
        180 g × (1 mol / 180.16 g) ≈ 0.999 mol
        """
        result = self.compute(
            initial_value=180,
            initial_unit="g",
            factors=[
                {"value": 1, "numerator": "mol", "denominator": "180.16 g"},
            ]
        )
        self.assertIsInstance(result, self.ComputeResult)
        expected = 180 / 180.16
        self.assertAlmostEqual(result.quantity, expected, places=3)

    def test_stoichiometry_molarity_calculation(self):
        """Test molarity calculation: moles per liter.

        Example: 0.5 mol NaCl in 250 mL water → molarity in mol/L
        0.5 mol × (1000 mL / 1 L) / 250 mL = 2.0 mol/L
        """
        result = self.compute(
            initial_value=0.5,
            initial_unit="mol",
            factors=[
                {"value": 1000, "numerator": "mL", "denominator": "L"},
                {"value": 1, "numerator": "1", "denominator": "250 mL"},  # dimensionless numerator
            ]
        )
        self.assertIsInstance(result, self.ComputeResult)
        expected = 0.5 * 1000 / 250
        self.assertAlmostEqual(result.quantity, expected, places=3)

    def test_stoichiometry_reaction_yield(self):
        """Test reaction stoichiometry with molar ratios.

        Example: 2 H2 + O2 → 2 H2O
        Given 10 mol H2, how many grams of H2O produced?
        10 mol H2 × (2 mol H2O / 2 mol H2) × (18.015 g H2O / 1 mol H2O) = 180.15 g

        Using 'ea' for the stoichiometric ratio since mol cancels.
        """
        result = self.compute(
            initial_value=10,
            initial_unit="mol",
            factors=[
                {"value": 2, "numerator": "ea", "denominator": "2 ea"},  # 2:2 stoich ratio
                {"value": 18.015, "numerator": "g", "denominator": "mol"},
            ]
        )
        self.assertIsInstance(result, self.ComputeResult)
        expected = 10 * (2/2) * 18.015
        self.assertAlmostEqual(result.quantity, expected, places=2)

    # -------------------------------------------------------------------------
    # Multi-Factor Cancellation Tests (6+ factors)
    # -------------------------------------------------------------------------

    def test_six_factor_chain(self):
        """Test 6-factor chain: complex unit conversion.

        Convert 1 mile/hour to cm/s:
        1 mi/h × (5280 ft/mi) × (12 in/ft) × (2.54 cm/in) × (1 h/60 min) × (1 min/60 s)
        = 44.704 cm/s
        """
        result = self.compute(
            initial_value=1,
            initial_unit="mi/h",
            factors=[
                {"value": 5280, "numerator": "ft", "denominator": "mi"},
                {"value": 12, "numerator": "in", "denominator": "ft"},
                {"value": 2.54, "numerator": "cm", "denominator": "in"},
                {"value": 1, "numerator": "h", "denominator": "60 min"},
                {"value": 1, "numerator": "min", "denominator": "60 s"},
            ]
        )
        self.assertIsInstance(result, self.ComputeResult)
        expected = 1 * 5280 * 12 * 2.54 / 60 / 60
        self.assertAlmostEqual(result.quantity, expected, places=2)

    def test_seven_factor_energy_chain(self):
        """Test 7-factor chain: energy unit conversion with intermediates.

        Convert 1 kWh to BTU via joules and calories:
        1 kWh × (1000 W/kW) × (3600 s/h) × (1 J/W·s) × (1 cal/4.184 J) × (1 BTU/252 cal)
        ≈ 3412 BTU

        Simplified version without composite unit parsing issues:
        1 kWh = 3.6e6 J, 1 BTU = 1055.06 J
        So: value × (3.6e6 J / kWh) × (1 BTU / 1055.06 J)
        """
        result = self.compute(
            initial_value=1,
            initial_unit="kWh",
            factors=[
                {"value": 1000, "numerator": "W", "denominator": "kW"},
                {"value": 3600, "numerator": "s", "denominator": "h"},
                {"value": 1, "numerator": "J", "denominator": "W*s"},
                {"value": 1, "numerator": "cal", "denominator": "4.184 J"},
                {"value": 1, "numerator": "BTU", "denominator": "252 cal"},
            ]
        )
        self.assertIsInstance(result, self.ComputeResult)
        expected = 1 * 1000 * 3600 / 4.184 / 252
        self.assertAlmostEqual(result.quantity, expected, places=0)  # ~3412 BTU

    # -------------------------------------------------------------------------
    # Tests for 4+ Base Unit Cancellation
    # -------------------------------------------------------------------------

    def test_four_base_units_cancel(self):
        """Test chain where 4 different base units cancel.

        Power density to force: W/m² × m × s / (m/s) = W·s/m = J/m = N
        This involves: mass (kg), length (m), time (s), and their combinations.

        Simplified: 100 W × 1 s / 1 m = 100 J/m = 100 N
        """
        result = self.compute(
            initial_value=100,
            initial_unit="W",
            factors=[
                {"value": 1, "numerator": "s", "denominator": "1 ea"},  # × 1 s
                {"value": 1, "numerator": "1", "denominator": "1 m"},   # / 1 m
            ]
        )
        self.assertIsInstance(result, self.ComputeResult)
        # W·s/m = J/m = N, so 100 W·s/m = 100 N
        self.assertAlmostEqual(result.quantity, 100.0, places=2)

    def test_pressure_volume_work_calculation(self):
        """Test pressure × volume = energy with multiple unit conversions.

        1 atm × 1 L = 101.325 J
        Using: 1 atm × (101325 Pa/atm) × 1 L × (0.001 m³/L) = 101.325 Pa·m³ = 101.325 J
        """
        result = self.compute(
            initial_value=1,
            initial_unit="atm",
            factors=[
                {"value": 101325, "numerator": "Pa", "denominator": "atm"},
                {"value": 1, "numerator": "L", "denominator": "1 ea"},  # multiply by 1 L
                {"value": 0.001, "numerator": "m^3", "denominator": "L"},
            ]
        )
        self.assertIsInstance(result, self.ComputeResult)
        expected = 1 * 101325 * 1 * 0.001
        self.assertAlmostEqual(result.quantity, expected, places=2)

    def test_flow_rate_mass_transfer(self):
        """Test volumetric flow × density × time = mass.

        10 L/min × 1.0 g/mL × 60 min = 600,000 g = 600 kg

        L/min × g/mL × min:
        - L cancels with mL (factor 1000)
        - min cancels
        - Result: g
        """
        result = self.compute(
            initial_value=10,
            initial_unit="L/min",
            factors=[
                {"value": 1000, "numerator": "mL", "denominator": "L"},  # convert L to mL
                {"value": 1.0, "numerator": "g", "denominator": "mL"},   # density
                {"value": 60, "numerator": "min", "denominator": "1 ea"},  # time
            ]
        )
        self.assertIsInstance(result, self.ComputeResult)
        expected = 10 * 1000 * 1.0 * 60
        self.assertAlmostEqual(result.quantity, expected, places=0)


class TestComputeToolErrors(unittest.TestCase):
    """Test error handling in the compute tool."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import compute
            from ucon.mcp.suggestions import ConversionError
            cls.compute = staticmethod(compute)
            cls.ConversionError = ConversionError
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")

    def test_unknown_initial_unit(self):
        """Test that unknown initial unit returns error."""
        result = self.compute(
            initial_value=100,
            initial_unit="foobar",
            factors=[]
        )
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "unknown_unit")
        self.assertEqual(result.parameter, "initial_unit")

    def test_unknown_numerator_unit(self):
        """Test that unknown numerator returns error with step."""
        result = self.compute(
            initial_value=100,
            initial_unit="m",
            factors=[
                {"value": 1, "numerator": "foobar", "denominator": "m"},
            ]
        )
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "unknown_unit")
        self.assertEqual(result.parameter, "factors[0].numerator")
        self.assertEqual(result.step, 0)

    def test_unknown_denominator_unit(self):
        """Test that unknown denominator returns error with step."""
        result = self.compute(
            initial_value=100,
            initial_unit="m",
            factors=[
                {"value": 1, "numerator": "km", "denominator": "bazqux"},
            ]
        )
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "unknown_unit")
        self.assertEqual(result.parameter, "factors[0].denominator")
        self.assertEqual(result.step, 0)

    def test_error_localization_later_step(self):
        """Test that errors in later steps report correct step number."""
        result = self.compute(
            initial_value=100,
            initial_unit="m",
            factors=[
                {"value": 1000, "numerator": "mm", "denominator": "m"},
                {"value": 1, "numerator": "badunit", "denominator": "mm"},
            ]
        )
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.step, 1)  # Second factor (0-indexed)
        self.assertIn("factors[1]", result.parameter)

    def test_missing_numerator(self):
        """Test that missing numerator returns structured error."""
        result = self.compute(
            initial_value=100,
            initial_unit="m",
            factors=[
                {"value": 1, "denominator": "m"},  # Missing numerator
            ]
        )
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "invalid_input")
        self.assertIn("numerator", result.parameter)
        self.assertEqual(result.step, 0)

    def test_missing_denominator(self):
        """Test that missing denominator returns structured error."""
        result = self.compute(
            initial_value=100,
            initial_unit="m",
            factors=[
                {"value": 1, "numerator": "km"},  # Missing denominator
            ]
        )
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "invalid_input")
        self.assertIn("denominator", result.parameter)

    def test_parse_error_in_factor(self):
        """Test that parse errors in factors are localized."""
        result = self.compute(
            initial_value=100,
            initial_unit="m",
            factors=[
                {"value": 1, "numerator": "kg/(m", "denominator": "s"},  # Unbalanced
            ]
        )
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "parse_error")
        self.assertEqual(result.step, 0)

    def test_empty_factors_returns_initial(self):
        """Test that empty factors list returns initial value unchanged."""
        result = self.compute(
            initial_value=100,
            initial_unit="m",
            factors=[]
        )
        # Should return ComputeResult, not error
        from ucon.mcp.server import ComputeResult
        self.assertIsInstance(result, ComputeResult)
        self.assertAlmostEqual(result.quantity, 100.0)
        self.assertEqual(result.dimension, "length")


class TestSessionTools(unittest.TestCase):
    """Test session management tools: define_unit, define_conversion, reset_session."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import (
                define_unit, define_conversion, reset_session, convert,
                UnitDefinitionResult, ConversionDefinitionResult, SessionResult,
                _reset_session_graph,
            )
            from ucon.mcp.suggestions import ConversionError
            cls.define_unit = staticmethod(define_unit)
            cls.define_conversion = staticmethod(define_conversion)
            cls.reset_session = staticmethod(reset_session)
            cls.convert = staticmethod(convert)
            cls.UnitDefinitionResult = UnitDefinitionResult
            cls.ConversionDefinitionResult = ConversionDefinitionResult
            cls.SessionResult = SessionResult
            cls.ConversionError = ConversionError
            cls._reset_session_graph = staticmethod(_reset_session_graph)
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")
        # Reset session before each test
        self._reset_session_graph()

    def tearDown(self):
        # Clean up session after each test
        if not self.skip_tests:
            self._reset_session_graph()

    def test_define_unit_success(self):
        """Test defining a custom unit successfully."""
        result = self.define_unit(
            name="slug",
            dimension="mass",
            aliases=["slug"],
        )
        self.assertIsInstance(result, self.UnitDefinitionResult)
        self.assertTrue(result.success)
        self.assertEqual(result.name, "slug")
        self.assertEqual(result.dimension, "mass")
        self.assertEqual(result.aliases, ["slug"])

    def test_define_unit_invalid_dimension(self):
        """Test that invalid dimension returns error with suggestions."""
        result = self.define_unit(
            name="badunit",
            dimension="nonexistent",
        )
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.parameter, "dimension")

    def test_define_conversion_success(self):
        """Test defining a conversion edge successfully."""
        # First define the unit
        self.define_unit(name="slug", dimension="mass", aliases=["slug"])

        # Then define the conversion
        result = self.define_conversion(src="slug", dst="kg", factor=14.5939)
        self.assertIsInstance(result, self.ConversionDefinitionResult)
        self.assertTrue(result.success)
        self.assertEqual(result.src, "slug")
        self.assertEqual(result.dst, "kg")
        self.assertAlmostEqual(result.factor, 14.5939)

    def test_define_conversion_unknown_unit(self):
        """Test that conversion with unknown unit returns error."""
        result = self.define_conversion(
            src="nonexistent",
            dst="kg",
            factor=1.0,
        )
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "unknown_unit")

    def test_session_unit_usable_in_convert(self):
        """Test that session-defined unit can be used in convert()."""
        # Define unit and conversion
        self.define_unit(name="slug", dimension="mass", aliases=["slug"])
        self.define_conversion(src="slug", dst="kg", factor=14.5939)

        # Use in convert
        result = self.convert(1, "slug", "kg")
        self.assertNotIsInstance(result, self.ConversionError)
        self.assertAlmostEqual(result.quantity, 14.5939, places=3)

    def test_reset_session_clears_custom_units(self):
        """Test that reset_session() clears custom units."""
        # Define unit and conversion
        self.define_unit(name="slug", dimension="mass", aliases=["slug"])
        self.define_conversion(src="slug", dst="kg", factor=14.5939)

        # Verify it works
        result = self.convert(1, "slug", "kg")
        self.assertNotIsInstance(result, self.ConversionError)

        # Reset session
        reset_result = self.reset_session()
        self.assertIsInstance(reset_result, self.SessionResult)
        self.assertTrue(reset_result.success)

        # Verify unit is no longer available
        result = self.convert(1, "slug", "kg")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "unknown_unit")


class TestInlineParameters(unittest.TestCase):
    """Test inline custom_units and custom_edges parameters."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import convert, compute, _reset_session_graph
            from ucon.mcp.suggestions import ConversionError
            cls.convert = staticmethod(convert)
            cls.compute = staticmethod(compute)
            cls.ConversionError = ConversionError
            cls._reset_session_graph = staticmethod(_reset_session_graph)
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")
        # Reset session to ensure clean state
        self._reset_session_graph()

    def tearDown(self):
        if not self.skip_tests:
            self._reset_session_graph()

    def test_convert_with_inline_units(self):
        """Test convert() with inline custom_units and custom_edges."""
        result = self.convert(
            value=1,
            from_unit="slug",
            to_unit="kg",
            custom_units=[
                {"name": "slug", "dimension": "mass", "aliases": ["slug"]},
            ],
            custom_edges=[
                {"src": "slug", "dst": "kg", "factor": 14.5939},
            ],
        )
        self.assertNotIsInstance(result, self.ConversionError)
        self.assertAlmostEqual(result.quantity, 14.5939, places=3)

    def test_inline_does_not_modify_session(self):
        """Test that inline definitions don't persist to session."""
        # Use inline definition
        result = self.convert(
            value=1,
            from_unit="slug",
            to_unit="kg",
            custom_units=[
                {"name": "slug", "dimension": "mass", "aliases": ["slug"]},
            ],
            custom_edges=[
                {"src": "slug", "dst": "kg", "factor": 14.5939},
            ],
        )
        self.assertNotIsInstance(result, self.ConversionError)

        # Without inline, unit should not be available
        result = self.convert(1, "slug", "kg")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "unknown_unit")

    def test_compute_with_inline_units(self):
        """Test compute() with inline custom_units."""
        result = self.compute(
            initial_value=1,
            initial_unit="slug",
            factors=[
                {"value": 14.5939, "numerator": "kg", "denominator": "slug"},
            ],
            custom_units=[
                {"name": "slug", "dimension": "mass", "aliases": ["slug"]},
            ],
        )
        self.assertNotIsInstance(result, self.ConversionError)
        self.assertAlmostEqual(result.quantity, 14.5939, places=3)

    def test_invalid_inline_unit_dimension(self):
        """Test that invalid dimension in inline unit returns error."""
        result = self.convert(
            value=1,
            from_unit="badunit",
            to_unit="kg",
            custom_units=[
                {"name": "badunit", "dimension": "nonexistent"},
            ],
        )
        self.assertIsInstance(result, self.ConversionError)
        self.assertIn("custom_units", result.parameter)

    def test_invalid_inline_edge_unit(self):
        """Test that invalid unit in inline edge returns error."""
        result = self.convert(
            value=1,
            from_unit="kg",
            to_unit="lb",
            custom_edges=[
                {"src": "nonexistent", "dst": "kg", "factor": 1.0},
            ],
        )
        self.assertIsInstance(result, self.ConversionError)
        self.assertIn("custom_edges", result.parameter)

    def test_recovery_pattern(self):
        """Test agent recovery pattern: unknown_unit error → retry with inline."""
        # First call fails
        result = self.convert(1, "slug", "kg")
        self.assertIsInstance(result, self.ConversionError)
        self.assertEqual(result.error_type, "unknown_unit")

        # Retry with inline definitions succeeds
        result = self.convert(
            value=1,
            from_unit="slug",
            to_unit="kg",
            custom_units=[
                {"name": "slug", "dimension": "mass", "aliases": ["slug"]},
            ],
            custom_edges=[
                {"src": "slug", "dst": "kg", "factor": 14.5939},
            ],
        )
        self.assertNotIsInstance(result, self.ConversionError)
        self.assertAlmostEqual(result.quantity, 14.5939, places=3)


class TestGraphCaching(unittest.TestCase):
    """Test that inline graph compilation is cached."""

    @classmethod
    def setUpClass(cls):
        try:
            from ucon.mcp.server import (
                convert, _inline_graph_cache, _hash_definitions, _reset_session_graph
            )
            cls.convert = staticmethod(convert)
            cls._inline_graph_cache = _inline_graph_cache
            cls._hash_definitions = staticmethod(_hash_definitions)
            cls._reset_session_graph = staticmethod(_reset_session_graph)
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("mcp not installed")
        self._reset_session_graph()
        # Clear cache
        self._inline_graph_cache.clear()

    def tearDown(self):
        if not self.skip_tests:
            self._reset_session_graph()
            self._inline_graph_cache.clear()

    def test_same_definitions_use_cache(self):
        """Test that identical definitions use cached graph."""
        custom_units = [{"name": "slug", "dimension": "mass", "aliases": ["slug"]}]
        custom_edges = [{"src": "slug", "dst": "kg", "factor": 14.5939}]

        # First call
        self.convert(1, "slug", "kg", custom_units=custom_units, custom_edges=custom_edges)
        cache_size_after_first = len(self._inline_graph_cache)

        # Second call with same definitions
        self.convert(2, "slug", "kg", custom_units=custom_units, custom_edges=custom_edges)
        cache_size_after_second = len(self._inline_graph_cache)

        # Cache should not grow (reusing same entry)
        self.assertEqual(cache_size_after_first, cache_size_after_second)
        self.assertEqual(cache_size_after_first, 1)

    def test_different_definitions_create_new_cache(self):
        """Test that different definitions create new cache entries."""
        custom_units_a = [{"name": "unit_a", "dimension": "mass"}]
        custom_units_b = [{"name": "unit_b", "dimension": "length"}]

        # First call
        self.convert(1, "kg", "g", custom_units=custom_units_a)
        cache_size_after_first = len(self._inline_graph_cache)

        # Second call with different definitions
        self.convert(1, "m", "ft", custom_units=custom_units_b)
        cache_size_after_second = len(self._inline_graph_cache)

        # Cache should grow
        self.assertEqual(cache_size_after_second, cache_size_after_first + 1)

    def test_hash_stability(self):
        """Test that hash is stable for same definitions in different order."""
        units_a = [{"name": "a", "dimension": "mass"}, {"name": "b", "dimension": "length"}]
        units_b = [{"name": "b", "dimension": "length"}, {"name": "a", "dimension": "mass"}]

        hash_a = self._hash_definitions(units_a, None)
        hash_b = self._hash_definitions(units_b, None)

        # Same content, different order → same hash (sorted internally)
        self.assertEqual(hash_a, hash_b)

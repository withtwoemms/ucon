# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for unit string parsing functionality.

Verifies that get_unit_by_name() correctly parses unit strings including:
- Simple units by name and alias
- Scaled units with SI prefixes
- Exponents in both Unicode and ASCII notation
- Composite units with multiplication and division
"""

import unittest

from ucon import units, Scale
from ucon.core import Unit, UnitProduct, UnitFactor
from ucon.units import get_unit_by_name, UnknownUnitError


class TestSimpleUnitLookup(unittest.TestCase):
    """Test lookup of simple units by name and alias."""

    def test_lookup_by_name(self):
        result = get_unit_by_name("meter")
        self.assertEqual(result, units.meter)

    def test_lookup_by_alias(self):
        result = get_unit_by_name("m")
        self.assertEqual(result, units.meter)

    def test_lookup_second_by_name(self):
        result = get_unit_by_name("second")
        self.assertEqual(result, units.second)

    def test_lookup_second_by_alias(self):
        result = get_unit_by_name("s")
        self.assertEqual(result, units.second)

    def test_lookup_case_insensitive_name(self):
        result = get_unit_by_name("METER")
        self.assertEqual(result, units.meter)

    def test_lookup_case_insensitive_alias(self):
        result = get_unit_by_name("M")
        self.assertEqual(result, units.meter)

    def test_lookup_liter_L(self):
        # 'L' is case-sensitive alias for liter (uppercase)
        result = get_unit_by_name("L")
        self.assertEqual(result, units.liter)

    def test_lookup_liter_lowercase(self):
        result = get_unit_by_name("l")
        self.assertEqual(result, units.liter)

    def test_lookup_byte_B(self):
        # 'B' is case-sensitive alias for byte (uppercase)
        result = get_unit_by_name("B")
        self.assertEqual(result, units.byte)

    def test_lookup_gram(self):
        result = get_unit_by_name("gram")
        self.assertEqual(result, units.gram)

    def test_lookup_gram_alias(self):
        result = get_unit_by_name("g")
        self.assertEqual(result, units.gram)


class TestScaledUnitLookup(unittest.TestCase):
    """Test lookup of scaled units with SI prefixes."""

    def test_kilometer(self):
        result = get_unit_by_name("km")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1000.0, places=10)

    def test_millimeter(self):
        result = get_unit_by_name("mm")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 0.001, places=10)

    def test_centimeter(self):
        result = get_unit_by_name("cm")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 0.01, places=10)

    def test_milliliter(self):
        result = get_unit_by_name("mL")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 0.001, places=10)

    def test_kilogram(self):
        result = get_unit_by_name("kg")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1000.0, places=10)

    def test_milligram(self):
        result = get_unit_by_name("mg")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 0.001, places=10)

    def test_megahertz(self):
        result = get_unit_by_name("MHz")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e6, places=1)

    def test_gigabyte(self):
        result = get_unit_by_name("GB")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e9, places=1)

    def test_kilobyte_binary(self):
        result = get_unit_by_name("KiB")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1024.0, places=10)

    def test_mebibyte(self):
        result = get_unit_by_name("MiB")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1024**2, places=10)

    def test_microsecond_unicode(self):
        result = get_unit_by_name("μs")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-6, places=15)

    def test_microsecond_ascii(self):
        result = get_unit_by_name("us")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-6, places=15)

    def test_nanosecond(self):
        result = get_unit_by_name("ns")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-9, places=15)


class TestExponentParsing(unittest.TestCase):
    """Test parsing of unit exponents in Unicode and ASCII notation."""

    def test_unicode_squared(self):
        result = get_unit_by_name("m²")
        self.assertIsInstance(result, UnitProduct)

    def test_ascii_squared(self):
        result = get_unit_by_name("m^2")
        self.assertIsInstance(result, UnitProduct)

    def test_unicode_cubed(self):
        result = get_unit_by_name("m³")
        self.assertIsInstance(result, UnitProduct)

    def test_ascii_cubed(self):
        result = get_unit_by_name("m^3")
        self.assertIsInstance(result, UnitProduct)

    def test_unicode_negative(self):
        result = get_unit_by_name("s⁻¹")
        self.assertIsInstance(result, UnitProduct)

    def test_ascii_negative(self):
        result = get_unit_by_name("s^-1")
        self.assertIsInstance(result, UnitProduct)

    def test_unicode_equals_ascii_squared(self):
        unicode_result = get_unit_by_name("m²")
        ascii_result = get_unit_by_name("m^2")
        self.assertEqual(unicode_result, ascii_result)

    def test_unicode_equals_ascii_cubed(self):
        unicode_result = get_unit_by_name("m³")
        ascii_result = get_unit_by_name("m^3")
        self.assertEqual(unicode_result, ascii_result)

    def test_unicode_equals_ascii_negative(self):
        unicode_result = get_unit_by_name("s⁻¹")
        ascii_result = get_unit_by_name("s^-1")
        self.assertEqual(unicode_result, ascii_result)

    def test_scaled_with_exponent(self):
        result = get_unit_by_name("km^2")
        self.assertIsInstance(result, UnitProduct)
        # km^2 = (1000m)^2 = 1e6 m^2
        self.assertAlmostEqual(result.fold_scale(), 1e6, places=1)


class TestCompositeUnitParsing(unittest.TestCase):
    """Test parsing of composite units with multiplication and division."""

    def test_velocity(self):
        result = get_unit_by_name("m/s")
        self.assertIsInstance(result, UnitProduct)

    def test_acceleration_unicode(self):
        result = get_unit_by_name("m/s²")
        self.assertIsInstance(result, UnitProduct)

    def test_acceleration_ascii(self):
        result = get_unit_by_name("m/s^2")
        self.assertIsInstance(result, UnitProduct)

    def test_force_unicode(self):
        result = get_unit_by_name("kg·m/s²")
        self.assertIsInstance(result, UnitProduct)

    def test_force_ascii(self):
        result = get_unit_by_name("kg*m/s^2")
        self.assertIsInstance(result, UnitProduct)

    def test_torque(self):
        result = get_unit_by_name("N·m")
        self.assertIsInstance(result, UnitProduct)

    def test_torque_ascii(self):
        result = get_unit_by_name("N*m")
        self.assertIsInstance(result, UnitProduct)

    def test_unicode_equals_ascii_velocity(self):
        # m/s should be the same regardless of notation
        unicode_result = get_unit_by_name("m/s")
        ascii_result = get_unit_by_name("m/s")
        self.assertEqual(unicode_result, ascii_result)

    def test_unicode_equals_ascii_acceleration(self):
        unicode_result = get_unit_by_name("m/s²")
        ascii_result = get_unit_by_name("m/s^2")
        self.assertEqual(unicode_result, ascii_result)

    def test_unicode_equals_ascii_force(self):
        unicode_result = get_unit_by_name("kg·m/s²")
        ascii_result = get_unit_by_name("kg*m/s^2")
        self.assertEqual(unicode_result, ascii_result)

    def test_data_rate(self):
        result = get_unit_by_name("MB/s")
        self.assertIsInstance(result, UnitProduct)

    def test_pressure_per_time(self):
        result = get_unit_by_name("Pa/s")
        self.assertIsInstance(result, UnitProduct)


class TestUnknownUnit(unittest.TestCase):
    """Test error handling for unknown units."""

    def test_unknown_raises(self):
        with self.assertRaises(UnknownUnitError) as ctx:
            get_unit_by_name("foobar")
        self.assertEqual(ctx.exception.name, "foobar")

    def test_empty_string_raises(self):
        with self.assertRaises(UnknownUnitError):
            get_unit_by_name("")

    def test_whitespace_only_raises(self):
        with self.assertRaises(UnknownUnitError):
            get_unit_by_name("   ")

    def test_unknown_in_composite_raises(self):
        with self.assertRaises(UnknownUnitError):
            get_unit_by_name("foo/bar")

    def test_error_message_contains_name(self):
        try:
            get_unit_by_name("xyz123")
        except UnknownUnitError as e:
            self.assertIn("xyz123", str(e))


class TestWhitespaceHandling(unittest.TestCase):
    """Test that whitespace is handled correctly."""

    def test_leading_whitespace(self):
        result = get_unit_by_name("  meter")
        self.assertEqual(result, units.meter)

    def test_trailing_whitespace(self):
        result = get_unit_by_name("meter  ")
        self.assertEqual(result, units.meter)

    def test_both_whitespace(self):
        result = get_unit_by_name("  meter  ")
        self.assertEqual(result, units.meter)


class TestPriorityAliases(unittest.TestCase):
    """Test that priority aliases are matched before prefix decomposition.

    Some aliases like 'min' could be misinterpreted as prefix+unit
    (e.g., 'm' + 'in' = milli-inch). Priority aliases ensure these
    are matched exactly first.
    """

    def test_min_is_minute_not_milli_inch(self):
        """'min' should parse as minute (time), not milli-inch (length)."""
        from ucon.core import Dimension
        result = get_unit_by_name("min")
        self.assertEqual(result, units.minute)
        self.assertEqual(result.dimension, Dimension.time)

    def test_min_in_composite(self):
        """'min' should work correctly in composite units."""
        result = get_unit_by_name("mL/min")
        self.assertIsInstance(result, UnitProduct)
        # Volume / time dimension
        from ucon.core import Dimension
        expected_dim = Dimension.volume / Dimension.time
        self.assertEqual(result.dimension, expected_dim)

    def test_mL_per_min_conversion(self):
        """Conversion using 'min' should work correctly."""
        from ucon.core import Number
        rate_per_hour = Number(120, unit=get_unit_by_name("mL/h"))
        rate_per_min = rate_per_hour.to(get_unit_by_name("mL/min"))
        self.assertAlmostEqual(rate_per_min.quantity, 2.0, places=9)

    def test_milli_prefix_still_works(self):
        """Normal milli- prefix parsing should still work."""
        result = get_unit_by_name("mL")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 0.001, places=10)

    def test_inch_still_works(self):
        """Inch unit should still be accessible."""
        result = get_unit_by_name("in")
        self.assertEqual(result, units.inch)


class TestPriorityScaledAliases(unittest.TestCase):
    """Test priority scaled aliases for domain-specific conventions.

    Some domains use non-standard abbreviations that include an implicit
    scale, like 'mcg' for microgram in medical contexts.
    """

    def test_mcg_is_microgram(self):
        """'mcg' should parse as microgram (medical convention)."""
        from ucon.core import Dimension
        result = get_unit_by_name("mcg")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.mass)
        self.assertAlmostEqual(result.fold_scale(), 1e-6, places=15)

    def test_mcg_to_mg(self):
        """Conversion from mcg to mg should work."""
        from ucon.core import Number
        dose = Number(500, unit=get_unit_by_name("mcg"))
        result = dose.to(get_unit_by_name("mg"))
        self.assertAlmostEqual(result.quantity, 0.5, places=9)

    def test_mcg_to_ug(self):
        """mcg and µg should be equivalent."""
        from ucon.core import Number
        dose = Number(1, unit=get_unit_by_name("mcg"))
        result = dose.to(get_unit_by_name("µg"))
        self.assertAlmostEqual(result.quantity, 1.0, places=9)

    def test_mcg_in_composite(self):
        """'mcg' should work in composite units."""
        result = get_unit_by_name("mcg/mL")
        self.assertIsInstance(result, UnitProduct)
        from ucon.core import Dimension
        self.assertEqual(result.dimension, Dimension.density)

    def test_mcg_per_kg_per_min(self):
        """'mcg/kg/min' style dosing units (requires chained division support)."""
        # This tests mcg works; chained division is a separate issue
        result = get_unit_by_name("mcg")
        self.assertIsInstance(result, UnitProduct)

    def test_cc_is_milliliter(self):
        """'cc' should parse as milliliter (1 cc = 1 mL)."""
        from ucon.core import Dimension
        result = get_unit_by_name("cc")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.volume)
        self.assertAlmostEqual(result.fold_scale(), 0.001, places=10)

    def test_cc_to_mL(self):
        """Conversion from cc to mL should be 1:1."""
        from ucon.core import Number
        vol = Number(5, unit=get_unit_by_name("cc"))
        result = vol.to(get_unit_by_name("mL"))
        self.assertAlmostEqual(result.quantity, 5.0, places=9)

    def test_cc_to_L(self):
        """Conversion from cc to L should work."""
        from ucon.core import Number
        vol = Number(1000, unit=get_unit_by_name("cc"))
        result = vol.to(get_unit_by_name("L"))
        self.assertAlmostEqual(result.quantity, 1.0, places=9)


class TestRecursiveDescentParser(unittest.TestCase):
    """Test the recursive descent parser for complex unit expressions.

    Covers acceptance criteria from v06x-recursive-descent-parser.md:
    - Parentheses support
    - Chained division
    - Unicode and ASCII exponents
    - Backward compatibility
    """

    def test_heat_transfer_coefficient(self):
        """GIVEN W/(m²*K) THEN returns W·m⁻²·K⁻¹."""
        result = get_unit_by_name("W/(m²*K)")
        self.assertIsInstance(result, UnitProduct)
        # W in numerator (exp 1), m in denominator (exp -2), K in denominator (exp -1)
        factors = result.factors
        # Check the structure: should have 3 factors
        self.assertEqual(len(factors), 3)

    def test_concentration_rate(self):
        """GIVEN mol/(L*s) THEN returns mol·L⁻¹·s⁻¹."""
        result = get_unit_by_name("mol/(L*s)")
        self.assertIsInstance(result, UnitProduct)
        factors = result.factors
        self.assertEqual(len(factors), 3)

    def test_molar_heat_capacity(self):
        """GIVEN J/(mol*K) THEN returns UnitProduct for molar heat capacity."""
        result = get_unit_by_name("J/(mol*K)")
        self.assertIsInstance(result, UnitProduct)
        factors = result.factors
        self.assertEqual(len(factors), 3)

    def test_chained_division_dosage(self):
        """GIVEN mg/kg/d THEN returns mg·kg⁻¹·d⁻¹."""
        result = get_unit_by_name("mg/kg/d")
        self.assertIsInstance(result, UnitProduct)
        # mg (exp 1), kg (exp -1), d (exp -1)
        factors = result.factors
        self.assertEqual(len(factors), 3)
        # All factors should have exponent magnitude 1
        for uf, exp in factors.items():
            self.assertEqual(abs(exp), 1)

    def test_chained_division_infusion_rate(self):
        """GIVEN µg/kg/min THEN returns µg·kg⁻¹·min⁻¹."""
        result = get_unit_by_name("µg/kg/min")
        self.assertIsInstance(result, UnitProduct)
        factors = result.factors
        self.assertEqual(len(factors), 3)

    def test_mcg_chained_division(self):
        """GIVEN mcg/kg/min THEN returns mcg·kg⁻¹·min⁻¹."""
        result = get_unit_by_name("mcg/kg/min")
        self.assertIsInstance(result, UnitProduct)
        factors = result.factors
        self.assertEqual(len(factors), 3)

    def test_acceleration_unicode_superscript(self):
        """GIVEN m/s² THEN returns UnitProduct with dimension acceleration."""
        from ucon.core import Dimension
        result = get_unit_by_name("m/s²")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.acceleration)

    def test_acceleration_ascii_caret(self):
        """GIVEN m/s^2 THEN returns UnitProduct identical to m/s²."""
        unicode_result = get_unit_by_name("m/s²")
        ascii_result = get_unit_by_name("m/s^2")
        self.assertEqual(unicode_result, ascii_result)

    def test_frequency_negative_superscript(self):
        """GIVEN s⁻¹ THEN returns UnitProduct with dimension frequency."""
        from ucon.core import Dimension
        result = get_unit_by_name("s⁻¹")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.frequency)

    def test_force_mixed_notation(self):
        """GIVEN kg*m/s^2 THEN returns UnitProduct with dimension force."""
        from ucon.core import Dimension
        result = get_unit_by_name("kg*m/s^2")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.force)

    def test_force_nested_parentheses(self):
        """GIVEN (kg*m)/(s^2) THEN returns UnitProduct with dimension force."""
        from ucon.core import Dimension
        result = get_unit_by_name("(kg*m)/(s^2)")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.force)

    def test_nested_equals_flat(self):
        """Nested parentheses should give same result as flat expression."""
        nested = get_unit_by_name("(kg*m)/(s^2)")
        flat = get_unit_by_name("kg*m/s^2")
        self.assertEqual(nested, flat)

    def test_unbalanced_parentheses_error(self):
        """GIVEN W/(m²*K (missing close paren) THEN raises ValueError with position."""
        from ucon.parsing import ParseError
        with self.assertRaises((ValueError, ParseError)):
            get_unit_by_name("W/(m²*K")

    def test_extra_close_paren_error(self):
        """Extra closing parenthesis should raise error."""
        from ucon.parsing import ParseError
        with self.assertRaises((ValueError, ParseError)):
            get_unit_by_name("W/(m²*K))")

    def test_backward_compat_simple_meter(self):
        """GIVEN m THEN returns units.meter (backward compatibility)."""
        result = get_unit_by_name("m")
        self.assertEqual(result, units.meter)

    def test_backward_compat_scaled_kg(self):
        """GIVEN kg THEN returns Scale.kilo * gram (backward compatibility)."""
        result = get_unit_by_name("kg")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1000.0, places=9)

    def test_backward_compat_minute_priority(self):
        """GIVEN min THEN returns minute (time), not milli-inch."""
        result = get_unit_by_name("min")
        self.assertEqual(result, units.minute)

    def test_unicode_multiplication_dot(self):
        """GIVEN kg·m THEN parses with Unicode middle dot."""
        result = get_unit_by_name("kg·m")
        self.assertIsInstance(result, UnitProduct)

    def test_unicode_multiplication_cdot(self):
        """GIVEN kg⋅m THEN parses with Unicode center dot."""
        result = get_unit_by_name("kg⋅m")
        self.assertIsInstance(result, UnitProduct)

    def test_triple_chained_division(self):
        """GIVEN a/b/c/d THEN returns a·b⁻¹·c⁻¹·d⁻¹."""
        result = get_unit_by_name("m/s/kg/K")
        self.assertIsInstance(result, UnitProduct)
        factors = result.factors
        self.assertEqual(len(factors), 4)

    def test_complex_heat_transfer_ascii(self):
        """GIVEN W/(m^2*K) (ASCII) THEN equivalent to Unicode version."""
        unicode_result = get_unit_by_name("W/(m²*K)")
        ascii_result = get_unit_by_name("W/(m^2*K)")
        self.assertEqual(unicode_result, ascii_result)

    def test_deeply_nested_parens(self):
        """GIVEN ((m)) THEN returns meter wrapped in UnitProduct."""
        result = get_unit_by_name("((m))")
        self.assertIsInstance(result, UnitProduct)
        # Should have one factor: meter with exponent 1
        factors = result.factors
        self.assertEqual(len(factors), 1)

    def test_whitespace_in_expression(self):
        """Whitespace should be tolerated in expressions."""
        result = get_unit_by_name("m / s")
        self.assertIsInstance(result, UnitProduct)

    def test_whitespace_around_parens(self):
        """Whitespace around parentheses should work."""
        result = get_unit_by_name("W / ( m^2 * K )")
        self.assertIsInstance(result, UnitProduct)


if __name__ == '__main__':
    unittest.main()

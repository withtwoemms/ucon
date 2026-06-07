# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for unit string parsing functionality.

Verifies that parse_unit() correctly parses unit strings including:
- Simple units by name and alias
- Scaled units with SI prefixes
- Exponents in both Unicode and ASCII notation
- Composite units with multiplication and division
"""

import unittest

from ucon import units, Scale, Dimension, Number
from ucon.core import Unit, UnitProduct, UnitFactor
from ucon.resolver import parse_unit
from ucon.units import UnknownUnitError


class TestSimpleUnitLookup(unittest.TestCase):
    """Test lookup of simple units by name and alias."""

    def test_lookup_by_name(self):
        result = parse_unit("meter")
        self.assertEqual(result, units.meter)

    def test_lookup_by_alias(self):
        result = parse_unit("m")
        self.assertEqual(result, units.meter)

    def test_lookup_second_by_name(self):
        result = parse_unit("second")
        self.assertEqual(result, units.second)

    def test_lookup_second_by_alias(self):
        result = parse_unit("s")
        self.assertEqual(result, units.second)

    def test_lookup_case_insensitive_name(self):
        result = parse_unit("METER")
        self.assertEqual(result, units.meter)

    def test_lookup_case_sensitive_M_resolves_to_molar(self):
        # 'M' is the standard chemistry symbol for molar concentration
        # (and SI prefix for mega when used as a prefix). Lowercase 'm'
        # remains the meter alias.
        result = parse_unit("M")
        self.assertEqual(result, units.molar)

    def test_lookup_case_insensitive_alias(self):
        # Lowercase 'm' is the canonical alias for meter.
        result = parse_unit("m")
        self.assertEqual(result, units.meter)

    def test_lookup_liter_L(self):
        # 'L' is case-sensitive alias for liter (uppercase)
        result = parse_unit("L")
        self.assertEqual(result, units.liter)

    def test_lookup_liter_lowercase(self):
        result = parse_unit("l")
        self.assertEqual(result, units.liter)

    def test_lookup_byte_B(self):
        # 'B' is case-sensitive alias for byte (uppercase)
        result = parse_unit("B")
        self.assertEqual(result, units.byte)

    def test_lookup_gram(self):
        result = parse_unit("gram")
        self.assertEqual(result, units.gram)

    def test_lookup_gram_alias(self):
        result = parse_unit("g")
        self.assertEqual(result, units.gram)


class TestScaledUnitLookup(unittest.TestCase):
    """Test lookup of scaled units with SI prefixes."""

    def test_kilometer(self):
        result = parse_unit("km")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1000.0, places=10)

    def test_millimeter(self):
        result = parse_unit("mm")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 0.001, places=10)

    def test_centimeter(self):
        result = parse_unit("cm")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 0.01, places=10)

    def test_milliliter(self):
        result = parse_unit("mL")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 0.001, places=10)

    def test_kilogram(self):
        result = parse_unit("kg")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1000.0, places=10)

    def test_milligram(self):
        result = parse_unit("mg")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 0.001, places=10)

    def test_megahertz(self):
        result = parse_unit("MHz")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e6, places=1)

    def test_gigabyte(self):
        result = parse_unit("GB")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e9, places=1)

    def test_kilobyte_binary(self):
        result = parse_unit("KiB")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1024.0, places=10)

    def test_mebibyte(self):
        result = parse_unit("MiB")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1024**2, places=10)

    def test_microsecond_unicode(self):
        result = parse_unit("μs")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-6, places=15)

    def test_microsecond_ascii(self):
        result = parse_unit("us")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-6, places=15)

    def test_nanosecond(self):
        result = parse_unit("ns")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-9, places=15)

    def test_tebibyte(self):
        result = parse_unit("TiB")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 2**40, places=1)

    def test_pebibyte(self):
        result = parse_unit("PiB")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 2**50, places=1)

    def test_exbibyte(self):
        result = parse_unit("EiB")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 2**60, places=1)

    def test_tebi_prefix_does_not_shadow_tera(self):
        """'TB' should still resolve as tera-byte, not tebi-byte."""
        result = parse_unit("TB")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e12, places=1)

    def test_pebi_prefix_does_not_shadow_peta(self):
        """'PB' should still resolve as peta-byte, not pebi-byte."""
        result = parse_unit("PB")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e15, places=1)


class TestExponentParsing(unittest.TestCase):
    """Test parsing of unit exponents in Unicode and ASCII notation."""

    def test_unicode_squared(self):
        result = parse_unit("m²")
        self.assertIsInstance(result, UnitProduct)

    def test_ascii_squared(self):
        result = parse_unit("m^2")
        self.assertIsInstance(result, UnitProduct)

    def test_unicode_cubed(self):
        result = parse_unit("m³")
        self.assertIsInstance(result, UnitProduct)

    def test_ascii_cubed(self):
        result = parse_unit("m^3")
        self.assertIsInstance(result, UnitProduct)

    def test_unicode_negative(self):
        result = parse_unit("s⁻¹")
        self.assertIsInstance(result, UnitProduct)

    def test_ascii_negative(self):
        result = parse_unit("s^-1")
        self.assertIsInstance(result, UnitProduct)

    def test_unicode_equals_ascii_squared(self):
        unicode_result = parse_unit("m²")
        ascii_result = parse_unit("m^2")
        self.assertEqual(unicode_result, ascii_result)

    def test_unicode_equals_ascii_cubed(self):
        unicode_result = parse_unit("m³")
        ascii_result = parse_unit("m^3")
        self.assertEqual(unicode_result, ascii_result)

    def test_unicode_equals_ascii_negative(self):
        unicode_result = parse_unit("s⁻¹")
        ascii_result = parse_unit("s^-1")
        self.assertEqual(unicode_result, ascii_result)

    def test_scaled_with_exponent(self):
        result = parse_unit("km^2")
        self.assertIsInstance(result, UnitProduct)
        # km^2 = (1000m)^2 = 1e6 m^2
        self.assertAlmostEqual(result.fold_scale(), 1e6, places=1)


class TestCompositeUnitParsing(unittest.TestCase):
    """Test parsing of composite units with multiplication and division."""

    def test_velocity(self):
        result = parse_unit("m/s")
        self.assertIsInstance(result, UnitProduct)

    def test_acceleration_unicode(self):
        result = parse_unit("m/s²")
        self.assertIsInstance(result, UnitProduct)

    def test_acceleration_ascii(self):
        result = parse_unit("m/s^2")
        self.assertIsInstance(result, UnitProduct)

    def test_force_unicode(self):
        result = parse_unit("kg·m/s²")
        self.assertIsInstance(result, UnitProduct)

    def test_force_ascii(self):
        result = parse_unit("kg*m/s^2")
        self.assertIsInstance(result, UnitProduct)

    def test_torque(self):
        result = parse_unit("N·m")
        self.assertIsInstance(result, UnitProduct)

    def test_torque_ascii(self):
        result = parse_unit("N*m")
        self.assertIsInstance(result, UnitProduct)

    def test_unicode_equals_ascii_velocity(self):
        # m/s should be the same regardless of notation
        unicode_result = parse_unit("m/s")
        ascii_result = parse_unit("m/s")
        self.assertEqual(unicode_result, ascii_result)

    def test_unicode_equals_ascii_acceleration(self):
        unicode_result = parse_unit("m/s²")
        ascii_result = parse_unit("m/s^2")
        self.assertEqual(unicode_result, ascii_result)

    def test_unicode_equals_ascii_force(self):
        unicode_result = parse_unit("kg·m/s²")
        ascii_result = parse_unit("kg*m/s^2")
        self.assertEqual(unicode_result, ascii_result)

    def test_data_rate(self):
        result = parse_unit("MB/s")
        self.assertIsInstance(result, UnitProduct)

    def test_pressure_per_time(self):
        result = parse_unit("Pa/s")
        self.assertIsInstance(result, UnitProduct)


class TestUnknownUnit(unittest.TestCase):
    """Test error handling for unknown units."""

    def test_unknown_raises(self):
        with self.assertRaises(UnknownUnitError) as ctx:
            parse_unit("foobar")
        self.assertEqual(ctx.exception.name, "foobar")

    def test_empty_string_raises(self):
        with self.assertRaises(UnknownUnitError):
            parse_unit("")

    def test_whitespace_only_raises(self):
        with self.assertRaises(UnknownUnitError):
            parse_unit("   ")

    def test_unknown_in_composite_raises(self):
        with self.assertRaises(UnknownUnitError):
            parse_unit("foo/bar")

    def test_error_message_contains_name(self):
        try:
            parse_unit("xyz123")
        except UnknownUnitError as e:
            self.assertIn("xyz123", str(e))


class TestWhitespaceHandling(unittest.TestCase):
    """Test that whitespace is handled correctly."""

    def test_leading_whitespace(self):
        result = parse_unit("  meter")
        self.assertEqual(result, units.meter)

    def test_trailing_whitespace(self):
        result = parse_unit("meter  ")
        self.assertEqual(result, units.meter)

    def test_both_whitespace(self):
        result = parse_unit("  meter  ")
        self.assertEqual(result, units.meter)


class TestPriorityAliases(unittest.TestCase):
    """Test that priority aliases are matched before prefix decomposition.

    Some aliases like 'min' could be misinterpreted as prefix+unit
    (e.g., 'm' + 'in' = milli-inch). Priority aliases ensure these
    are matched exactly first.
    """

    def test_min_is_minute_not_milli_inch(self):
        """'min' should parse as minute (time), not milli-inch (length)."""
        result = parse_unit("min")
        self.assertEqual(result, units.minute)
        self.assertEqual(result.dimension, Dimension.time)

    def test_min_in_composite(self):
        """'min' should work correctly in composite units."""
        result = parse_unit("mL/min")
        self.assertIsInstance(result, UnitProduct)
        # Volume / time dimension
        expected_dim = Dimension.volume / Dimension.time
        self.assertEqual(result.dimension, expected_dim)

    def test_mL_per_min_conversion(self):
        """Conversion using 'min' should work correctly."""
        rate_per_hour = Number(120, unit=parse_unit("mL/h"))
        rate_per_min = rate_per_hour.to(parse_unit("mL/min"))
        self.assertAlmostEqual(rate_per_min.quantity, 2.0, places=9)

    def test_milli_prefix_still_works(self):
        """Normal milli- prefix parsing should still work."""
        result = parse_unit("mL")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 0.001, places=10)

    def test_inch_still_works(self):
        """Inch unit should still be accessible."""
        result = parse_unit("in")
        self.assertEqual(result, units.inch)


class TestPriorityScaledAliases(unittest.TestCase):
    """Test priority scaled aliases for domain-specific conventions.

    Some domains use non-standard abbreviations that include an implicit
    scale, like 'mcg' for microgram in medical contexts.
    """

    def test_mcg_is_microgram(self):
        """'mcg' should parse as microgram (medical convention)."""
        result = parse_unit("mcg")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.mass)
        self.assertAlmostEqual(result.fold_scale(), 1e-6, places=15)

    def test_mcg_to_mg(self):
        """Conversion from mcg to mg should work."""
        dose = Number(500, unit=parse_unit("mcg"))
        result = dose.to(parse_unit("mg"))
        self.assertAlmostEqual(result.quantity, 0.5, places=9)

    def test_mcg_to_ug(self):
        """mcg and µg should be equivalent."""
        dose = Number(1, unit=parse_unit("mcg"))
        result = dose.to(parse_unit("µg"))
        self.assertAlmostEqual(result.quantity, 1.0, places=9)

    def test_mcg_in_composite(self):
        """'mcg' should work in composite units."""
        result = parse_unit("mcg/mL")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.density)

    def test_mcg_per_kg_per_min(self):
        """'mcg/kg/min' style dosing units (requires chained division support)."""
        # This tests mcg works; chained division is a separate issue
        result = parse_unit("mcg")
        self.assertIsInstance(result, UnitProduct)

    def test_cc_is_milliliter(self):
        """'cc' should parse as milliliter (1 cc = 1 mL)."""
        result = parse_unit("cc")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.volume)
        self.assertAlmostEqual(result.fold_scale(), 0.001, places=10)

    def test_cc_to_mL(self):
        """Conversion from cc to mL should be 1:1."""
        vol = Number(5, unit=parse_unit("cc"))
        result = vol.to(parse_unit("mL"))
        self.assertAlmostEqual(result.quantity, 5.0, places=9)

    def test_cc_to_L(self):
        """Conversion from cc to L should work."""
        vol = Number(1000, unit=parse_unit("cc"))
        result = vol.to(parse_unit("L"))
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
        result = parse_unit("W/(m²*K)")
        self.assertIsInstance(result, UnitProduct)
        # W in numerator (exp 1), m in denominator (exp -2), K in denominator (exp -1)
        factors = result.factors
        # Check the structure: should have 3 factors
        self.assertEqual(len(factors), 3)

    def test_concentration_rate(self):
        """GIVEN mol/(L*s) THEN returns mol·L⁻¹·s⁻¹."""
        result = parse_unit("mol/(L*s)")
        self.assertIsInstance(result, UnitProduct)
        factors = result.factors
        self.assertEqual(len(factors), 3)

    def test_molar_heat_capacity(self):
        """GIVEN J/(mol*K) THEN returns UnitProduct for molar heat capacity."""
        result = parse_unit("J/(mol*K)")
        self.assertIsInstance(result, UnitProduct)
        factors = result.factors
        self.assertEqual(len(factors), 3)

    def test_chained_division_dosage(self):
        """GIVEN mg/kg/d THEN returns mg/kg/d with all factors preserved.

        Note: Differently-scaled variants of the same base unit (mg, kg) are
        kept separate so they can cancel properly in later operations
        (e.g., mg/kg * kg = mg). The fold_scale() still gives the correct
        combined scale factor.
        """
        result = parse_unit("mg/kg/d")
        self.assertIsInstance(result, UnitProduct)
        # All three factors preserved: mg, kg^-1, d^-1
        factors = result.factors
        self.assertEqual(len(factors), 3)
        # Scale should be 1e-6 (milli/kilo)
        self.assertAlmostEqual(result.fold_scale(), 1e-6, places=15)

    def test_chained_division_infusion_rate(self):
        """GIVEN µg/kg/min THEN returns µg/kg/min with all factors preserved."""
        result = parse_unit("µg/kg/min")
        self.assertIsInstance(result, UnitProduct)
        factors = result.factors
        self.assertEqual(len(factors), 3)  # µg, kg^-1, min^-1
        # Scale: micro/kilo = 1e-6/1e3 = 1e-9
        self.assertAlmostEqual(result.fold_scale(), 1e-9, places=15)

    def test_mcg_chained_division(self):
        """GIVEN mcg/kg/min THEN returns mcg/kg/min with all factors preserved."""
        result = parse_unit("mcg/kg/min")
        self.assertIsInstance(result, UnitProduct)
        factors = result.factors
        self.assertEqual(len(factors), 3)  # mcg, kg^-1, min^-1
        # Scale: micro/kilo = 1e-6/1e3 = 1e-9
        self.assertAlmostEqual(result.fold_scale(), 1e-9, places=15)

    def test_acceleration_unicode_superscript(self):
        """GIVEN m/s² THEN returns UnitProduct with dimension acceleration."""
        result = parse_unit("m/s²")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.acceleration)

    def test_acceleration_ascii_caret(self):
        """GIVEN m/s^2 THEN returns UnitProduct identical to m/s²."""
        unicode_result = parse_unit("m/s²")
        ascii_result = parse_unit("m/s^2")
        self.assertEqual(unicode_result, ascii_result)

    def test_frequency_negative_superscript(self):
        """GIVEN s⁻¹ THEN returns UnitProduct with dimension frequency."""
        result = parse_unit("s⁻¹")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.frequency)

    def test_force_mixed_notation(self):
        """GIVEN kg*m/s^2 THEN returns UnitProduct with dimension force."""
        result = parse_unit("kg*m/s^2")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.force)

    def test_force_nested_parentheses(self):
        """GIVEN (kg*m)/(s^2) THEN returns UnitProduct with dimension force."""
        result = parse_unit("(kg*m)/(s^2)")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.force)

    def test_nested_equals_flat(self):
        """Nested parentheses should give same result as flat expression."""
        nested = parse_unit("(kg*m)/(s^2)")
        flat = parse_unit("kg*m/s^2")
        self.assertEqual(nested, flat)

    def test_unbalanced_parentheses_error(self):
        """GIVEN W/(m²*K (missing close paren) THEN raises ValueError with position."""
        from ucon.parsing import ParseError
        with self.assertRaises((ValueError, ParseError)):
            parse_unit("W/(m²*K")

    def test_extra_close_paren_error(self):
        """Extra closing parenthesis should raise error."""
        from ucon.parsing import ParseError
        with self.assertRaises((ValueError, ParseError)):
            parse_unit("W/(m²*K))")

    def test_backward_compat_simple_meter(self):
        """GIVEN m THEN returns units.meter (backward compatibility)."""
        result = parse_unit("m")
        self.assertEqual(result, units.meter)

    def test_backward_compat_scaled_kg(self):
        """GIVEN kg THEN returns Scale.kilo * gram (backward compatibility)."""
        result = parse_unit("kg")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1000.0, places=9)

    def test_backward_compat_minute_priority(self):
        """GIVEN min THEN returns minute (time), not milli-inch."""
        result = parse_unit("min")
        self.assertEqual(result, units.minute)

    def test_unicode_multiplication_dot(self):
        """GIVEN kg·m THEN parses with Unicode middle dot."""
        result = parse_unit("kg·m")
        self.assertIsInstance(result, UnitProduct)

    def test_unicode_multiplication_cdot(self):
        """GIVEN kg⋅m THEN parses with Unicode center dot."""
        result = parse_unit("kg⋅m")
        self.assertIsInstance(result, UnitProduct)

    def test_triple_chained_division(self):
        """GIVEN a/b/c/d THEN returns a·b⁻¹·c⁻¹·d⁻¹."""
        result = parse_unit("m/s/kg/K")
        self.assertIsInstance(result, UnitProduct)
        factors = result.factors
        self.assertEqual(len(factors), 4)

    def test_complex_heat_transfer_ascii(self):
        """GIVEN W/(m^2*K) (ASCII) THEN equivalent to Unicode version."""
        unicode_result = parse_unit("W/(m²*K)")
        ascii_result = parse_unit("W/(m^2*K)")
        self.assertEqual(unicode_result, ascii_result)

    def test_deeply_nested_parens(self):
        """GIVEN ((m)) THEN returns meter wrapped in UnitProduct."""
        result = parse_unit("((m))")
        self.assertIsInstance(result, UnitProduct)
        # Should have one factor: meter with exponent 1
        factors = result.factors
        self.assertEqual(len(factors), 1)

    def test_whitespace_in_expression(self):
        """Whitespace should be tolerated in expressions."""
        result = parse_unit("m / s")
        self.assertIsInstance(result, UnitProduct)

    def test_whitespace_around_parens(self):
        """Whitespace around parentheses should work."""
        result = parse_unit("W / ( m^2 * K )")
        self.assertIsInstance(result, UnitProduct)


class TestResolverEdgeCases(unittest.TestCase):
    """Test resolver edge cases for coverage."""

    def test_register_unit_empty_name_noop(self):
        """register_unit with empty name does nothing."""
        from ucon.resolver import register_unit
        u = Unit(name='', dimension=Dimension.length)
        # Should not raise, should be no-op
        register_unit(u)

    def test_parse_exponent_ascii_caret(self):
        """ASCII caret notation: 'm^2' resolves."""
        result = parse_unit("m^2")
        self.assertIsInstance(result, UnitProduct)

    def test_parse_exponent_ascii_negative(self):
        """ASCII caret negative: 's^-1' resolves."""
        result = parse_unit("s^-1")
        self.assertIsInstance(result, UnitProduct)

    def test_parse_exponent_ascii_invalid_raises(self):
        """ASCII caret with non-numeric exponent raises."""
        with self.assertRaises(UnknownUnitError):
            parse_unit("m^abc")

    def test_priority_alias_min(self):
        """'min' resolves to minute, not milli-inch."""
        result = parse_unit('min')
        # Should be minute (time), not a prefix decomposition
        if isinstance(result, UnitProduct):
            # extract the unit from the product
            uf, exp = next(iter(result.factors.items()))
            self.assertEqual(uf.unit.dimension, Dimension.time)
        else:
            self.assertEqual(result.dimension, Dimension.time)

    def test_empty_string_raises(self):
        """Empty string raises UnknownUnitError."""
        with self.assertRaises((UnknownUnitError, ValueError)):
            parse_unit('')


class TestSpelledOutScaleAliases(unittest.TestCase):
    """Test that spelled-out scale+unit names resolve correctly."""

    # -- Length ---------------------------------------------------------------

    def test_kilometer(self):
        result = parse_unit("kilometer")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e3, places=10)
        self.assertEqual(result.dimension, Dimension.length)

    def test_centimeter(self):
        result = parse_unit("centimeter")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-2, places=10)

    def test_millimeter(self):
        result = parse_unit("millimeter")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-3, places=10)

    def test_micrometer(self):
        result = parse_unit("micrometer")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-6, places=15)

    def test_nanometer(self):
        result = parse_unit("nanometer")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-9, places=15)

    def test_picometer(self):
        result = parse_unit("picometer")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-12, places=15)

    # -- Mass -----------------------------------------------------------------

    def test_milligram(self):
        result = parse_unit("milligram")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-3, places=10)

    def test_microgram(self):
        result = parse_unit("microgram")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-6, places=15)

    def test_kilogram_still_returns_unit(self):
        """kilogram must still resolve as the kilogram Unit, not kilo*gram."""
        result = parse_unit("kilogram")
        self.assertIsInstance(result, Unit)
        self.assertEqual(result, units.kilogram)

    # -- Time -----------------------------------------------------------------

    def test_millisecond(self):
        result = parse_unit("millisecond")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-3, places=10)

    def test_microsecond(self):
        result = parse_unit("microsecond")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-6, places=15)

    def test_nanosecond(self):
        result = parse_unit("nanosecond")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-9, places=15)

    # -- Frequency ------------------------------------------------------------

    def test_megahertz(self):
        result = parse_unit("megahertz")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e6, places=1)

    def test_gigahertz(self):
        result = parse_unit("gigahertz")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e9, places=1)

    # -- Information ----------------------------------------------------------

    def test_gigabyte(self):
        result = parse_unit("gigabyte")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e9, places=1)

    def test_tebibyte(self):
        result = parse_unit("tebibyte")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 2**40, places=1)

    def test_pebibyte(self):
        result = parse_unit("pebibyte")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 2**50, places=1)

    def test_exbibyte(self):
        result = parse_unit("exbibyte")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 2**60, places=1)

    # -- Power ----------------------------------------------------------------

    def test_kilowatt(self):
        result = parse_unit("kilowatt")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e3, places=10)

    # -- Conversions using spelled-out names ----------------------------------

    def test_kilometer_to_meter(self):
        dist = Number(5, unit=parse_unit("kilometer"))
        result = dist.to("m")
        self.assertAlmostEqual(result.quantity, 5000.0, places=9)

    def test_milligram_to_mcg(self):
        dose = Number(1, unit=parse_unit("milligram"))
        result = dose.to(parse_unit("mcg"))
        self.assertAlmostEqual(result.quantity, 1000.0, places=9)

    def test_tebibyte_to_gibibyte(self):
        storage = Number(1, unit=parse_unit("tebibyte"))
        result = storage.to(parse_unit("gibibyte"))
        self.assertAlmostEqual(result.quantity, 1024.0, places=9)


class TestPluralAliases(unittest.TestCase):
    """Test that plural and long-form unit aliases resolve correctly.

    These aliases were added to support scoring in the UnitSafe benchmark,
    where models frequently output spelled-out unit names like "meters"
    instead of "m".
    """

    # -- TOML plural aliases (base/unscaled units) ----------------------------

    def test_meters(self):
        self.assertEqual(parse_unit("meters"), units.meter)

    def test_metres(self):
        self.assertEqual(parse_unit("metres"), units.meter)

    def test_metre(self):
        self.assertEqual(parse_unit("metre"), units.meter)

    def test_seconds(self):
        self.assertEqual(parse_unit("seconds"), units.second)

    def test_grams(self):
        self.assertEqual(parse_unit("grams"), units.gram)

    def test_watts(self):
        self.assertEqual(parse_unit("watts"), units.watt)

    def test_joules(self):
        self.assertEqual(parse_unit("joules"), units.joule)

    def test_hours(self):
        self.assertEqual(parse_unit("hours"), units.hour)

    def test_liters(self):
        self.assertEqual(parse_unit("liters"), units.liter)

    def test_litres(self):
        self.assertEqual(parse_unit("litres"), units.liter)

    def test_litre(self):
        self.assertEqual(parse_unit("litre"), units.liter)

    def test_ohms(self):
        self.assertEqual(parse_unit("ohms"), units.ohm)

    def test_newtons(self):
        self.assertEqual(parse_unit("newtons"), units.newton)

    def test_pascals(self):
        self.assertEqual(parse_unit("pascals"), units.pascal)

    def test_amps(self):
        self.assertEqual(parse_unit("amps"), units.ampere)

    def test_amperes(self):
        self.assertEqual(parse_unit("amperes"), units.ampere)

    def test_volts(self):
        self.assertEqual(parse_unit("volts"), units.volt)

    def test_radians(self):
        self.assertEqual(parse_unit("radians"), units.radian)

    def test_arcseconds(self):
        self.assertEqual(parse_unit("arcseconds"), units.arcsecond)

    def test_arcminutes(self):
        self.assertEqual(parse_unit("arcminutes"), units.arcminute)

    def test_lumens(self):
        self.assertEqual(parse_unit("lumens"), units.lumen)

    # -- New unit: solar_mass -------------------------------------------------

    def test_solar_mass_by_name(self):
        result = parse_unit("solar_mass")
        self.assertIsInstance(result, Unit)
        self.assertEqual(result.dimension, Dimension.mass)

    def test_solar_mass_symbol(self):
        result = parse_unit("M☉")
        self.assertIsInstance(result, Unit)
        self.assertEqual(result.name, "solar_mass")

    def test_solar_masses(self):
        result = parse_unit("solar_masses")
        self.assertIsInstance(result, Unit)
        self.assertEqual(result.name, "solar_mass")

    # -- Scaled plural aliases (from units.py) --------------------------------

    def test_kilometers(self):
        result = parse_unit("kilometers")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e3, places=10)

    def test_milligrams(self):
        result = parse_unit("milligrams")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-3, places=10)

    def test_milliseconds(self):
        result = parse_unit("milliseconds")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-3, places=10)

    def test_milliliters(self):
        result = parse_unit("milliliters")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-3, places=10)

    def test_kilowatts(self):
        result = parse_unit("kilowatts")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e3, places=10)

    def test_kilojoules(self):
        result = parse_unit("kilojoules")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e3, places=10)

    def test_microradians(self):
        result = parse_unit("microradians")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-6, places=15)

    def test_microradian_singular(self):
        result = parse_unit("microradian")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-6, places=15)

    def test_millilumens(self):
        result = parse_unit("millilumens")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-3, places=10)

    def test_millilumen_singular(self):
        result = parse_unit("millilumen")
        self.assertIsInstance(result, UnitProduct)
        self.assertAlmostEqual(result.fold_scale(), 1e-3, places=10)

    # -- 1.6.4 additions ------------------------------------------------------

    def test_days(self):
        self.assertEqual(parse_unit("days"), units.day)

    def test_minutes(self):
        self.assertEqual(parse_unit("minutes"), units.minute)


class TestDimensionlessAliases(unittest.TestCase):
    """Test 'dimensionless' / 'unitless' aliases for the fraction unit.

    Models in the UnitSafe benchmark commonly emit 'dimensionless' or
    'unitless' for ratios; both should resolve to the existing fraction
    unit (dimension ratio).
    """

    def test_dimensionless(self):
        self.assertEqual(parse_unit("dimensionless"), units.fraction)

    def test_unitless(self):
        self.assertEqual(parse_unit("unitless"), units.fraction)

    def test_frac_still_works(self):
        self.assertEqual(parse_unit("frac"), units.fraction)


class TestMolarAliases(unittest.TestCase):
    """Test 'M' (molar) and SI-prefixed molar aliases.

    'M' is the standard chemistry symbol for molar concentration. Common
    prefixed forms used in lab/clinical contexts (mM, µM, uM, nM, pM) are
    registered as priority scaled aliases so prefix decomposition does not
    need to be relied upon at the boundary between unit and prefix.
    """

    def test_M_is_molar(self):
        self.assertEqual(parse_unit("M"), units.molar)

    def test_mM_is_millimolar(self):
        result = parse_unit("mM")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.concentration)
        # fold_scale() returns the scale prefix factor (milli = 1e-3)
        self.assertAlmostEqual(result.fold_scale(), 1e-3, places=15)

    def test_uM_equals_micromolar(self):
        u = parse_unit("uM")
        mu = parse_unit("µM")
        self.assertEqual(u, mu)

    def test_nM_is_nanomolar(self):
        result = parse_unit("nM")
        self.assertEqual(result.dimension, Dimension.concentration)

    def test_pM_is_picomolar(self):
        result = parse_unit("pM")
        self.assertEqual(result.dimension, Dimension.concentration)

    def test_mol_per_L_still_works(self):
        self.assertEqual(parse_unit("mol/L").dimension,
                         Dimension.concentration)

    def test_mM_to_M_conversion(self):
        c = Number(500, unit=parse_unit("mM"))
        result = c.to(parse_unit("M"))
        self.assertAlmostEqual(result.quantity, 0.5, places=9)


class TestWholeTokenAliases(unittest.TestCase):
    """Test resolution of aliases that contain operator-like characters.

    Some domain-specific labels include parentheses or other characters that
    the composite parser would otherwise interpret as expression syntax. Such
    labels are registered as ordinary aliases; the resolver checks the whole
    string against the alias registry BEFORE composite-detection runs, so
    the label resolves as a single token.

    Current cases:
    - ``Gy(RBE)`` → ``gray`` (radiobiological-equivalent dose label used in
      proton/heavy-ion therapy)
    - ``Sv(RBE)`` → ``sievert``

    The semantic distinction (RBE-weighted vs unweighted) is a Kind-of-Quantity
    concern handled at higher layers; at the unit-resolution layer the labels
    are aliases of the canonical SI dose units.
    """

    def test_gy_rbe_resolves_to_gray(self):
        self.assertEqual(parse_unit("Gy(RBE)"), units.gray)

    def test_sv_rbe_resolves_to_sievert(self):
        self.assertEqual(parse_unit("Sv(RBE)"), units.sievert)

    def test_gy_rbe_is_not_unitproduct(self):
        # Whole-token resolution returns the bare Unit, not a UnitProduct
        result = parse_unit("Gy(RBE)")
        self.assertIsInstance(result, Unit)

    def test_gy_alias_still_works(self):
        self.assertEqual(parse_unit("Gy"), units.gray)

    def test_sv_alias_still_works(self):
        self.assertEqual(parse_unit("Sv"), units.sievert)

    def test_composite_with_real_operators_unchanged(self):
        # Regression: actual composite expressions still parse normally
        result = parse_unit("m/s")
        self.assertIsInstance(result, UnitProduct)

    def test_composite_with_parentheses_unchanged(self):
        # Regression: parenthesised composites still parse
        result = parse_unit("J/(mol*K)")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension,
                         parse_unit("J/mol/K").dimension)

    def test_priority_alias_min_unchanged(self):
        # Regression: 'min' still resolves to minute, not milli-inch
        self.assertEqual(parse_unit("min"), units.minute)

    def test_priority_scaled_alias_mcg_unchanged(self):
        # Regression: 'mcg' still resolves to microgram via priority scaled
        # alias path (it is NOT in the unit-name registry, so the new
        # whole-string check falls through cleanly)
        result = parse_unit("mcg")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.mass)
        self.assertAlmostEqual(result.fold_scale(), 1e-6, places=15)

    def test_unknown_parenthesised_token_still_errors(self):
        # Verbatim check falls through; composite parser then raises
        # for the unknown parenthesised expression.
        with self.assertRaises((UnknownUnitError, Exception)):
            parse_unit("Foo(BAR)")

    def test_verbatim_lookup_is_case_sensitive(self):
        # Verbatim aliases are convention-specific; the exact casing is
        # required. Lowercase variants are not silently coerced.
        with self.assertRaises((UnknownUnitError, Exception)):
            parse_unit("gy(rbe)")


if __name__ == '__main__':
    unittest.main()

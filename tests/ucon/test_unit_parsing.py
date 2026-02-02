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


if __name__ == '__main__':
    unittest.main()

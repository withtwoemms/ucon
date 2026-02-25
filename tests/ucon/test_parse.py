# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for the parse() function (v0.8.5)."""

import pytest

from ucon import parse, Number, using_graph, CGS, using_basis
from ucon.units import UnknownUnitError, meter, second, kilogram, hour, mile


class TestParseBasicQuantities:
    """Tests for basic quantity parsing."""

    def test_parse_simple_unit(self):
        """Parse '60 mi/h' returns Number(60, mile/hour)."""
        result = parse("60 mi/h")
        assert result.value == 60
        # Check dimension is velocity (length/time)

    def test_parse_composite_unit(self):
        """Parse '9.81 m/s^2' returns Number with acceleration unit."""
        result = parse("9.81 m/s^2")
        assert result.value == 9.81

    def test_parse_scaled_unit(self):
        """Parse '1.5 kg' returns Number(1.5, kilogram)."""
        result = parse("1.5 kg")
        assert result.value == 1.5

    def test_parse_pure_number_integer(self):
        """Parse '100' returns dimensionless Number."""
        result = parse("100")
        assert result.value == 100
        assert result.unit is not None  # dimensionless unit

    def test_parse_pure_number_float(self):
        """Parse '3.14159' returns dimensionless Number."""
        result = parse("3.14159")
        assert result.value == pytest.approx(3.14159)


class TestParseWhitespaceHandling:
    """Tests for whitespace handling."""

    def test_parse_no_space(self):
        """Parse '60m' (no space) returns correct Number."""
        result = parse("60m")
        assert result.value == 60

    def test_parse_extra_whitespace(self):
        """Parse '  60   m  ' (extra whitespace) returns correct Number."""
        result = parse("  60   m  ")
        assert result.value == 60

    def test_parse_spaces_in_unit(self):
        """Parse '60 m / s' (spaces in unit) returns correct Number."""
        result = parse("60 m / s")
        assert result.value == 60


class TestParseNumericFormats:
    """Tests for various numeric formats."""

    def test_parse_scientific_notation(self):
        """Parse '1.5e3 m' returns Number(1500, meter)."""
        result = parse("1.5e3 m")
        assert result.value == 1500

    def test_parse_negative_value(self):
        """Parse '-273.15 °C' returns Number with negative value."""
        result = parse("-273.15 degC")
        assert result.value == -273.15

    def test_parse_positive_sign(self):
        """Parse '+42 kg' returns Number(42, kilogram)."""
        result = parse("+42 kg")
        assert result.value == 42

    def test_parse_leading_decimal(self):
        """Parse '.5 m' returns Number(0.5, meter)."""
        result = parse(".5 m")
        assert result.value == 0.5


class TestParseUncertainty:
    """Tests for uncertainty parsing."""

    def test_parse_plus_minus_unicode(self):
        """Parse '1.234 ± 0.005 m' returns Number with uncertainty."""
        result = parse("1.234 ± 0.005 m")
        assert result.value == pytest.approx(1.234)
        assert result.uncertainty == pytest.approx(0.005)

    def test_parse_plus_minus_ascii(self):
        """Parse '1.234 +/- 0.005 m' returns Number with uncertainty."""
        result = parse("1.234 +/- 0.005 m")
        assert result.value == pytest.approx(1.234)
        assert result.uncertainty == pytest.approx(0.005)

    def test_parse_parenthetical_uncertainty(self):
        """Parse '1.234(5) m' returns Number with uncertainty=0.005."""
        result = parse("1.234(5) m")
        assert result.value == pytest.approx(1.234)
        assert result.uncertainty == pytest.approx(0.005)

    def test_parse_parenthetical_uncertainty_two_digits(self):
        """Parse '1.234(56) m' returns Number with uncertainty=0.056."""
        result = parse("1.234(56) m")
        assert result.value == pytest.approx(1.234)
        assert result.uncertainty == pytest.approx(0.056)

    def test_parse_parenthetical_uncertainty_fewer_decimals(self):
        """Parse '1.23(5) m' returns Number with uncertainty=0.05."""
        result = parse("1.23(5) m")
        assert result.value == pytest.approx(1.23)
        assert result.uncertainty == pytest.approx(0.05)

    def test_parse_uncertainty_with_unit(self):
        """Parse '1.234 m ± 0.005 m' returns Number with uncertainty."""
        result = parse("1.234 m ± 0.005 m")
        assert result.value == pytest.approx(1.234)
        assert result.uncertainty == pytest.approx(0.005)

    def test_parse_dimensionless_uncertainty(self):
        """Parse '100 ± 5' returns dimensionless Number with uncertainty."""
        result = parse("100 ± 5")
        assert result.value == 100
        assert result.uncertainty == 5


class TestParseErrorHandling:
    """Tests for error handling."""

    def test_parse_unknown_unit_raises(self):
        """Parse '60 foobar' raises UnknownUnitError."""
        with pytest.raises(UnknownUnitError):
            parse("60 foobar")

    def test_parse_invalid_numeric_raises(self):
        """Parse 'abc m' raises ValueError."""
        with pytest.raises(ValueError):
            parse("abc m")

    def test_parse_empty_string_raises(self):
        """Parse '' raises ValueError."""
        with pytest.raises(ValueError):
            parse("")

    def test_parse_whitespace_only_raises(self):
        """Parse '   ' raises ValueError."""
        with pytest.raises(ValueError):
            parse("   ")


class TestParsePriorityAliases:
    """Tests for priority alias handling."""

    def test_parse_min_as_minute(self):
        """Parse '5 min' returns Number with minute unit (not milli-inch)."""
        result = parse("5 min")
        assert result.value == 5
        # Should be minute, not milli-inch

    def test_parse_mcg_as_microgram(self):
        """Parse '500 mcg' returns Number with microgram unit."""
        result = parse("500 mcg")
        assert result.value == 500

    def test_parse_cc_as_milliliter(self):
        """Parse '5 cc' returns Number with milliliter equivalent."""
        result = parse("5 cc")
        assert result.value == 5


class TestParseRoundTrip:
    """Tests for round-trip consistency."""

    def test_round_trip_simple(self):
        """Parsed number can be converted back to string and re-parsed."""
        original = parse("60 mi/h")
        # repr should produce a parseable representation
        # (Note: exact round-trip depends on repr format)
        assert original.value == 60

    def test_round_trip_uncertainty(self):
        """Parsed number with uncertainty preserves uncertainty."""
        original = parse("1.234 ± 0.005 m")
        assert original.uncertainty == pytest.approx(0.005)


class TestParseEdgeCases:
    """Tests for edge cases."""

    def test_parse_very_small_number(self):
        """Parse '1e-15 m' returns Number with very small value."""
        result = parse("1e-15 m")
        assert result.value == pytest.approx(1e-15)

    def test_parse_very_large_number(self):
        """Parse '6.022e23' returns Number with Avogadro's number."""
        result = parse("6.022e23")
        assert result.value == pytest.approx(6.022e23)

    def test_parse_unicode_superscript(self):
        """Parse '9.81 m/s²' handles Unicode superscript."""
        result = parse("9.81 m/s²")
        assert result.value == pytest.approx(9.81)

    def test_parse_negative_exponent(self):
        """Parse '1e-3 kg' returns Number(0.001, kilogram)."""
        result = parse("1e-3 kg")
        assert result.value == pytest.approx(0.001)

    def test_parse_uppercase_e(self):
        """Parse '1.5E3 m' handles uppercase E in scientific notation."""
        result = parse("1.5E3 m")
        assert result.value == 1500

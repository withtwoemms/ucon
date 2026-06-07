# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Tests for ucon.parse_dimension.

Covers the three input forms supported by the v1.7.0 public parser:
1. Component symbols of the active basis (M, L, T, ...).
2. Component / dimension names (mass, length, velocity, force, ...).
3. Algebraic expressions (M*L/T^2, L/T, 1/T, M.L/T^2, ...).
"""

import unittest

from ucon import Dimension, parse_dimension
from ucon.basis.builtin import SI


class TestParseDimensionSymbols(unittest.TestCase):
    """Bare component symbols of the default (SI) basis."""

    def test_mass_symbol(self):
        self.assertEqual(parse_dimension("M"), Dimension.mass)

    def test_length_symbol(self):
        self.assertEqual(parse_dimension("L"), Dimension.length)

    def test_time_symbol(self):
        self.assertEqual(parse_dimension("T"), Dimension.time)

    def test_current_symbol(self):
        self.assertEqual(parse_dimension("I"), Dimension.current)

    def test_temperature_symbol(self):
        self.assertEqual(parse_dimension("\u0398"), Dimension.temperature)

    def test_luminous_intensity_symbol(self):
        self.assertEqual(parse_dimension("J"), Dimension.luminous_intensity)

    def test_amount_of_substance_symbol(self):
        self.assertEqual(parse_dimension("N"), Dimension.amount_of_substance)

    def test_information_symbol(self):
        self.assertEqual(parse_dimension("B"), Dimension.information)


class TestParseDimensionNames(unittest.TestCase):
    """Bare dimension names (canonical and component-name variants)."""

    def test_mass_name(self):
        self.assertEqual(parse_dimension("mass"), Dimension.mass)

    def test_length_name(self):
        self.assertEqual(parse_dimension("length"), Dimension.length)

    def test_velocity_name(self):
        self.assertEqual(parse_dimension("velocity"), Dimension.velocity)

    def test_force_name(self):
        self.assertEqual(parse_dimension("force"), Dimension.force)

    def test_energy_name(self):
        self.assertEqual(parse_dimension("energy"), Dimension.energy)

    def test_frequency_name(self):
        self.assertEqual(parse_dimension("frequency"), Dimension.frequency)


class TestParseDimensionExpressions(unittest.TestCase):
    """Algebraic expressions over component symbols."""

    def test_velocity_from_symbols(self):
        self.assertEqual(parse_dimension("L/T"), Dimension.velocity)

    def test_force_from_symbols_caret(self):
        self.assertEqual(parse_dimension("M*L/T^2"), Dimension.force)

    def test_force_from_symbols_middle_dot(self):
        self.assertEqual(parse_dimension("M\u00b7L/T^2"), Dimension.force)

    def test_force_from_symbols_dot_operator(self):
        self.assertEqual(parse_dimension("M\u22c5L/T^2"), Dimension.force)

    def test_force_from_symbols_unicode_superscript(self):
        # M·L/T²
        self.assertEqual(parse_dimension("M\u00b7L/T\u00b2"), Dimension.force)

    def test_area_from_symbols(self):
        self.assertEqual(parse_dimension("L^2"), Dimension.area)

    def test_volume_from_symbols(self):
        self.assertEqual(parse_dimension("L^3"), Dimension.volume)

    def test_frequency_from_reciprocal_time(self):
        self.assertEqual(parse_dimension("1/T"), Dimension.frequency)

    def test_parenthesised_expression(self):
        # M / (L * T^2) is *not* force (force = M*L/T^2). Test grouping works.
        result = parse_dimension("M/(L*T^2)")
        expected = Dimension.mass / (Dimension.length * (Dimension.time ** 2))
        self.assertEqual(result, expected)

    def test_mixed_symbols_and_names(self):
        # mass * length / time^2 should equal force
        self.assertEqual(parse_dimension("mass*length/time^2"), Dimension.force)


class TestParseDimensionEdgeCases(unittest.TestCase):
    """Edge cases and error reporting."""

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            parse_dimension("")

    def test_whitespace_only_raises(self):
        with self.assertRaises(ValueError):
            parse_dimension("   ")

    def test_unknown_identifier_raises(self):
        with self.assertRaises(ValueError):
            parse_dimension("nonsense_xyz")

    def test_unbalanced_paren_raises(self):
        with self.assertRaises(ValueError):
            parse_dimension("M*(L/T")

    def test_trailing_garbage_raises(self):
        with self.assertRaises(ValueError):
            parse_dimension("M garbage")

    def test_leading_whitespace_tolerated(self):
        self.assertEqual(parse_dimension("  M  "), Dimension.mass)


class TestParseDimensionExplicitBasis(unittest.TestCase):
    """Passing an explicit basis argument."""

    def test_explicit_si_basis(self):
        self.assertEqual(parse_dimension("M", basis=SI), Dimension.mass)

    def test_explicit_basis_expression(self):
        self.assertEqual(parse_dimension("L/T", basis=SI), Dimension.velocity)


if __name__ == "__main__":
    unittest.main()

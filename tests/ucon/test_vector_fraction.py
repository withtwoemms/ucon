# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for Vector with Fraction exponents.

Verifies backward compatibility with integer exponents and
correct behavior with fractional exponents for BasisTransform support.
"""

import unittest
from fractions import Fraction

from ucon.algebra import Vector


class TestVectorIntegerBackwardCompatibility(unittest.TestCase):
    """Verify existing integer-based code works unchanged."""

    def test_integer_construction(self):
        v = Vector(1, 0, -2, 0, 0, 0, 0, 0)
        self.assertEqual(tuple(v), (1, 0, -2, 0, 0, 0, 0, 0))

    def test_integer_addition(self):
        v1 = Vector(1, 0, 0, 0, 0, 0, 0, 0)
        v2 = Vector(0, 2, 0, 0, 0, 0, 0, 0)
        result = v1 + v2
        self.assertEqual(result, Vector(1, 2, 0, 0, 0, 0, 0, 0))

    def test_integer_subtraction(self):
        v1 = Vector(2, 1, 0, 0, 0, 0, 0, 0)
        v2 = Vector(1, 1, 0, 0, 0, 0, 0, 0)
        result = v1 - v2
        self.assertEqual(result, Vector(1, 0, 0, 0, 0, 0, 0, 0))

    def test_integer_scalar_multiplication(self):
        v = Vector(1, -2, 0, 0, 0, 0, 3, 0)
        result = v * 2
        self.assertEqual(result, Vector(2, -4, 0, 0, 0, 0, 6, 0))

    def test_integer_equality(self):
        v1 = Vector(1, 0, 0, 0, 0, 0, 0, 0)
        v2 = Vector(1, 0, 0, 0, 0, 0, 0, 0)
        self.assertEqual(v1, v2)

    def test_integer_hash_consistency(self):
        v1 = Vector(1, 0, 0, 0, 0, 0, 0, 0)
        v2 = Vector(1, 0, 0, 0, 0, 0, 0, 0)
        self.assertEqual(hash(v1), hash(v2))
        self.assertEqual(len({v1, v2}), 1)


class TestVectorFractionConstruction(unittest.TestCase):
    """Test Vector construction with Fraction values."""

    def test_fraction_construction(self):
        v = Vector(Fraction(3, 2), Fraction(1, 2), Fraction(-1), 0, 0, 0, 0, 0)
        self.assertEqual(v.T, Fraction(3, 2))
        self.assertEqual(v.L, Fraction(1, 2))
        self.assertEqual(v.M, Fraction(-1))

    def test_mixed_int_fraction_construction(self):
        v = Vector(1, Fraction(1, 2), 0, 0, 0, 0, 0, 0)
        self.assertEqual(v.T, Fraction(1))
        self.assertEqual(v.L, Fraction(1, 2))

    def test_float_converted_to_fraction(self):
        v = Vector(0.5, 0, 0, 0, 0, 0, 0, 0)
        self.assertEqual(v.T, Fraction(1, 2))

    def test_default_values_are_fraction_zero(self):
        v = Vector()
        self.assertEqual(v.T, Fraction(0))
        self.assertEqual(v.L, Fraction(0))


class TestVectorFractionEquality(unittest.TestCase):
    """Test equality across int and Fraction representations."""

    def test_int_equals_fraction(self):
        v1 = Vector(1, 0, 0, 0, 0, 0, 0, 0)
        v2 = Vector(Fraction(1), Fraction(0), Fraction(0), Fraction(0),
                    Fraction(0), Fraction(0), Fraction(0), Fraction(0))
        self.assertEqual(v1, v2)

    def test_int_fraction_hash_equality(self):
        v1 = Vector(1, 0, -2, 0, 0, 0, 0, 0)
        v2 = Vector(Fraction(1), Fraction(0), Fraction(-2), Fraction(0),
                    Fraction(0), Fraction(0), Fraction(0), Fraction(0))
        self.assertEqual(hash(v1), hash(v2))

    def test_int_fraction_in_set(self):
        v1 = Vector(1, 0, 0, 0, 0, 0, 0, 0)
        v2 = Vector(Fraction(1), 0, 0, 0, 0, 0, 0, 0)
        s = {v1, v2}
        self.assertEqual(len(s), 1)


class TestVectorFractionArithmetic(unittest.TestCase):
    """Test arithmetic with Fraction exponents."""

    def test_fraction_addition(self):
        v1 = Vector(Fraction(1, 2), 0, 0, 0, 0, 0, 0, 0)
        v2 = Vector(Fraction(1, 2), 0, 0, 0, 0, 0, 0, 0)
        result = v1 + v2
        self.assertEqual(result.T, Fraction(1))

    def test_fraction_subtraction(self):
        v1 = Vector(Fraction(3, 2), 0, 0, 0, 0, 0, 0, 0)
        v2 = Vector(Fraction(1, 2), 0, 0, 0, 0, 0, 0, 0)
        result = v1 - v2
        self.assertEqual(result.T, Fraction(1))

    def test_fraction_scalar_multiply(self):
        v = Vector(Fraction(1, 2), 0, 0, 0, 0, 0, 0, 0)
        result = v * 2
        self.assertEqual(result.T, Fraction(1))

    def test_fraction_scalar_multiply_by_fraction(self):
        v = Vector(1, 0, 0, 0, 0, 0, 0, 0)
        result = v * Fraction(1, 2)
        self.assertEqual(result.T, Fraction(1, 2))

    def test_no_floating_point_drift(self):
        # 1/3 * 3 should equal exactly 1, not 0.9999...
        v = Vector(Fraction(1, 3), 0, 0, 0, 0, 0, 0, 0)
        result = v * 3
        self.assertEqual(result.T, Fraction(1))
        self.assertEqual(result, Vector(1, 0, 0, 0, 0, 0, 0, 0))

    def test_complex_fraction_arithmetic(self):
        # CGS-ESU charge dimension: M^(1/2) · L^(3/2) · T^(-1)
        esu_charge = Vector(
            T=-1,
            L=Fraction(3, 2),
            M=Fraction(1, 2),
        )
        # Multiply by 2 (squaring the unit)
        squared = esu_charge * 2
        self.assertEqual(squared.T, Fraction(-2))
        self.assertEqual(squared.L, Fraction(3))
        self.assertEqual(squared.M, Fraction(1))


class TestVectorIterationWithFraction(unittest.TestCase):
    """Test iteration and length with Fraction values."""

    def test_iteration_returns_fractions(self):
        v = Vector(Fraction(1, 2), 1, 0, 0, 0, 0, 0, 0)
        components = list(v)
        self.assertEqual(components[0], Fraction(1, 2))
        self.assertEqual(components[1], Fraction(1))

    def test_length_unchanged(self):
        v = Vector(Fraction(1, 2), 0, 0, 0, 0, 0, 0, 0)
        self.assertEqual(len(v), 8)


class TestVectorNegation(unittest.TestCase):
    """Test vector negation with Fraction values."""

    def test_negation_with_fractions(self):
        v = Vector(Fraction(1, 2), Fraction(-3, 4), 0, 0, 0, 0, 0, 0)
        neg = -v
        self.assertEqual(neg.T, Fraction(-1, 2))
        self.assertEqual(neg.L, Fraction(3, 4))


class TestVectorRightMultiply(unittest.TestCase):
    """Test right multiplication (scalar * vector)."""

    def test_rmul_integer(self):
        v = Vector(Fraction(1, 2), 0, 0, 0, 0, 0, 0, 0)
        result = 2 * v
        self.assertEqual(result.T, Fraction(1))

    def test_rmul_fraction(self):
        v = Vector(1, 0, 0, 0, 0, 0, 0, 0)
        result = Fraction(1, 2) * v
        self.assertEqual(result.T, Fraction(1, 2))


if __name__ == "__main__":
    unittest.main()

# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for Exponent class.

Note: Legacy Vector tests have been removed. Vector is now in ucon.basis
and has a different API. See tests/ucon/test_basis.py for Vector tests.
"""

import math
from unittest import TestCase

from ucon.core import Exponent


class TestExponent(TestCase):

    thousand = Exponent(10, 3)
    thousandth = Exponent(10, -3)
    kibibyte = Exponent(2, 10)
    mebibyte = Exponent(2, 20)

    def test___init__(self):
        with self.assertRaises(ValueError):
            Exponent(5, 3)  # no support for base 5 logarithms

    def test_parts(self):
        self.assertEqual((10, 3), self.thousand.parts())
        self.assertEqual((10, -3), self.thousandth.parts())

    def test_evaluated_property(self):
        self.assertEqual(1000, self.thousand.evaluated)
        self.assertAlmostEqual(0.001, self.thousandth.evaluated)
        self.assertEqual(1024, self.kibibyte.evaluated)
        self.assertEqual(1048576, self.mebibyte.evaluated)

    def test___truediv__(self):
         # same base returns a new Exponent
        ratio = self.thousand / self.thousandth
        self.assertIsInstance(ratio, Exponent)
        self.assertEqual(ratio.base, 10)
        self.assertEqual(ratio.power, 6)
        self.assertEqual(ratio.evaluated, 1_000_000)

        # different base returns numeric float
        val = self.thousand / self.kibibyte
        self.assertIsInstance(val, float)
        self.assertAlmostEqual(1000 / 1024, val)

    def test___mul__(self):
        product = self.kibibyte * self.mebibyte
        self.assertIsInstance(product, Exponent)
        self.assertEqual(product.base, 2)
        self.assertEqual(product.power, 30)
        self.assertEqual(product.evaluated, 2**30)

        # cross-base multiplication returns numeric
        val = self.kibibyte * self.thousand
        self.assertIsInstance(val, float)
        self.assertAlmostEqual(1024 * 1000, val)

    def test___hash__(self):
        a = Exponent(10, 3)
        b = Exponent(10, 3)
        self.assertEqual(hash(a), hash(b))
        self.assertEqual(len({a, b}), 1) # both should hash to same value

    def test___float__(self):
        self.assertEqual(float(self.thousand), 1000.0)

    def test___int__(self):
        self.assertEqual(int(self.thousand), 1000)

    def test_comparisons(self):
        self.assertTrue(self.thousand > self.thousandth)
        self.assertTrue(self.thousandth < self.thousand)
        self.assertTrue(self.kibibyte < self.mebibyte)
        self.assertTrue(self.kibibyte == Exponent(2, 10))

        with self.assertRaises(TypeError):
            _ = self.thousand == 1000  # comparison to non-Exponent

    def test___repr__(self):
        self.assertIn("Exponent", repr(Exponent(10, -3)))

    def test___str__(self):
        self.assertEqual(str(self.thousand), '10^3')
        self.assertEqual(str(self.thousandth), '10^-3')

    def test_to_base(self):
        e = Exponent(2, 10)
        converted = e.to_base(10)
        self.assertIsInstance(converted, Exponent)
        self.assertEqual(converted.base, 10)
        self.assertAlmostEqual(converted.power, math.log10(1024), places=10)

        with self.assertRaises(ValueError):
            e.to_base(5)


class TestExponentEdgeCases(TestCase):

    def test_extreme_powers(self):
        e = Exponent(10, 308)
        self.assertTrue(math.isfinite(e.evaluated))
        e_small = Exponent(10, -308)
        self.assertGreater(e.evaluated, e_small.evaluated)

    def test_precision_rounding_in_hash(self):
        a = Exponent(10, 6)
        b = Exponent(10, 6 + 1e-16)
        # rounding in hash avoids floating drift
        self.assertEqual(hash(a), hash(b))

    def test_negative_and_zero_power(self):
        e0 = Exponent(10, 0)
        e_neg = Exponent(10, -1)
        self.assertEqual(e0.evaluated, 1.0)
        self.assertEqual(e_neg.evaluated, 0.1)
        self.assertLess(e_neg, e0)

    def test_valid_exponent_evaluates_correctly(self):
        base, power = 10, 3
        e = Exponent(base, power)
        self.assertEqual(e.evaluated, 1000)
        self.assertEqual(e.parts(), (base, power))
        self.assertEqual(f'{base}^{power}', str(e))
        self.assertEqual(f'Exponent(base={base}, power={power})', repr(e))

    def test_invalid_base_raises_value_error(self):
        with self.assertRaises(ValueError):
            Exponent(5, 2)

    def test_exponent_comparisons(self):
        e1 = Exponent(10, 2)
        e2 = Exponent(10, 3)
        self.assertTrue(e1 < e2)
        self.assertTrue(e2 > e1)
        self.assertFalse(e1 == e2)

    def test_division_returns_exponent(self):
        e1 = Exponent(10, 3)
        e2 = Exponent(10, 2)
        self.assertEqual(e1 / e2, Exponent(10, 1))

    def test_equality_with_different_type(self):
        with self.assertRaises(TypeError):
            Exponent(10, 2) == "10^2"

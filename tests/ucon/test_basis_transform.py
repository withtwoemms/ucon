# (c) 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for BasisTransform.

Verifies matrix-based dimensional basis transformations,
invertibility detection, and exact Fraction arithmetic.
"""

import unittest
from fractions import Fraction

from ucon.core import (
    BasisTransform,
    Dimension,
    NonInvertibleTransform,
    Unit,
    UnitSystem,
)
from ucon import units


class TestBasisTransformConstruction(unittest.TestCase):
    """Test BasisTransform construction and validation."""

    def setUp(self):
        self.si = UnitSystem(
            name="SI",
            bases={
                Dimension.length: units.meter,
                Dimension.mass: units.kilogram,
                Dimension.time: units.second,
            }
        )
        self.custom = UnitSystem(
            name="Custom",
            bases={
                Dimension.length: units.foot,
                Dimension.mass: units.pound,
                Dimension.time: units.second,
            }
        )

    def test_valid_construction(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((1,),),
        )
        self.assertEqual(bt.src, self.custom)
        self.assertEqual(bt.dst, self.si)

    def test_matrix_converted_to_fraction(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length, Dimension.mass),
            dst_dimensions=(Dimension.length, Dimension.mass),
            matrix=((1, 0), (0, 1)),
        )
        self.assertIsInstance(bt.matrix[0][0], Fraction)
        self.assertIsInstance(bt.matrix[1][1], Fraction)

    def test_dimension_count_mismatch_rows(self):
        with self.assertRaises(ValueError) as ctx:
            BasisTransform(
                src=self.custom,
                dst=self.si,
                src_dimensions=(Dimension.length,),
                dst_dimensions=(Dimension.length, Dimension.mass),  # 2 dims
                matrix=((1,),),  # only 1 row
            )
        self.assertIn("row", str(ctx.exception).lower())

    def test_dimension_count_mismatch_cols(self):
        with self.assertRaises(ValueError) as ctx:
            BasisTransform(
                src=self.custom,
                dst=self.si,
                src_dimensions=(Dimension.length, Dimension.mass),  # 2 dims
                dst_dimensions=(Dimension.length,),
                matrix=((1,),),  # only 1 column
            )
        self.assertIn("column", str(ctx.exception).lower())


class TestBasisTransformSquareMatrix(unittest.TestCase):
    """Test BasisTransform with square matrices."""

    def setUp(self):
        self.si = UnitSystem(
            name="SI",
            bases={
                Dimension.length: units.meter,
                Dimension.mass: units.kilogram,
                Dimension.time: units.second,
            }
        )
        self.custom = UnitSystem(
            name="Custom",
            bases={
                Dimension.length: units.foot,
                Dimension.mass: units.pound,
                Dimension.time: units.second,
            }
        )

    def test_1x1_identity_transform(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((1,),),
        )
        self.assertTrue(bt.is_square)
        self.assertTrue(bt.is_invertible)

    def test_2x2_identity_transform(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length, Dimension.mass),
            dst_dimensions=(Dimension.length, Dimension.mass),
            matrix=((1, 0), (0, 1)),
        )
        self.assertTrue(bt.is_square)
        self.assertTrue(bt.is_invertible)

    def test_2x2_singular_not_invertible(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length, Dimension.mass),
            dst_dimensions=(Dimension.length, Dimension.mass),
            matrix=((1, 2), (2, 4)),  # Rows are linearly dependent
        )
        self.assertTrue(bt.is_square)
        self.assertFalse(bt.is_invertible)

    def test_3x3_invertible(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length, Dimension.mass, Dimension.time),
            dst_dimensions=(Dimension.length, Dimension.mass, Dimension.time),
            matrix=(
                (1, 0, 0),
                (0, 1, 0),
                (0, 0, 1),
            ),
        )
        self.assertTrue(bt.is_square)
        self.assertTrue(bt.is_invertible)

    def test_determinant_2x2(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length, Dimension.mass),
            dst_dimensions=(Dimension.length, Dimension.mass),
            matrix=((2, 3), (1, 4)),  # det = 2*4 - 3*1 = 5
        )
        # Access internal _determinant method for testing
        self.assertEqual(bt._determinant(), Fraction(5))


class TestBasisTransformInverse(unittest.TestCase):
    """Test BasisTransform inverse computation."""

    def setUp(self):
        self.si = UnitSystem(
            name="SI",
            bases={
                Dimension.length: units.meter,
                Dimension.mass: units.kilogram,
                Dimension.time: units.second,
            }
        )
        self.custom = UnitSystem(
            name="Custom",
            bases={
                Dimension.length: units.foot,
                Dimension.mass: units.pound,
                Dimension.time: units.second,
            }
        )

    def test_1x1_inverse(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((2,),),  # scale by 2
        )
        inv = bt.inverse()
        self.assertEqual(inv.matrix, ((Fraction(1, 2),),))
        self.assertEqual(inv.src, self.si)
        self.assertEqual(inv.dst, self.custom)

    def test_2x2_inverse(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length, Dimension.mass),
            dst_dimensions=(Dimension.length, Dimension.mass),
            matrix=((1, 0), (0, 1)),
        )
        inv = bt.inverse()
        self.assertEqual(inv.matrix, ((Fraction(1), Fraction(0)), (Fraction(0), Fraction(1))))

    def test_inverse_of_inverse_equals_original(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length, Dimension.mass),
            dst_dimensions=(Dimension.length, Dimension.mass),
            matrix=((2, 1), (1, 1)),  # det = 2*1 - 1*1 = 1
        )
        inv = bt.inverse()
        inv_inv = inv.inverse()
        self.assertEqual(bt.matrix, inv_inv.matrix)

    def test_non_invertible_raises(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length, Dimension.mass),
            dst_dimensions=(Dimension.length, Dimension.mass),
            matrix=((1, 2), (2, 4)),  # Singular
        )
        with self.assertRaises(NonInvertibleTransform):
            bt.inverse()


class TestBasisTransformNonSquare(unittest.TestCase):
    """Test BasisTransform with non-square (surjective) matrices."""

    def setUp(self):
        self.si = UnitSystem(
            name="SI",
            bases={
                Dimension.length: units.meter,
                Dimension.mass: units.kilogram,
                Dimension.time: units.second,
            }
        )
        self.reduced = UnitSystem(
            name="Reduced",
            bases={
                Dimension.length: units.meter,
                Dimension.mass: units.kilogram,
            }
        )

    def test_2x3_not_square(self):
        bt = BasisTransform(
            src=self.si,
            dst=self.reduced,
            src_dimensions=(Dimension.length, Dimension.mass, Dimension.time),
            dst_dimensions=(Dimension.length, Dimension.mass),
            matrix=(
                (1, 0, 0),
                (0, 1, 0),
            ),
        )
        self.assertFalse(bt.is_square)
        self.assertFalse(bt.is_invertible)

    def test_non_square_inverse_raises(self):
        bt = BasisTransform(
            src=self.si,
            dst=self.reduced,
            src_dimensions=(Dimension.length, Dimension.mass, Dimension.time),
            dst_dimensions=(Dimension.length, Dimension.mass),
            matrix=(
                (1, 0, 0),
                (0, 1, 0),
            ),
        )
        with self.assertRaises(NonInvertibleTransform):
            bt.inverse()


class TestBasisTransformTransform(unittest.TestCase):
    """Test the transform() method for vector transformation."""

    def setUp(self):
        self.si = UnitSystem(
            name="SI",
            bases={
                Dimension.length: units.meter,
                Dimension.mass: units.kilogram,
                Dimension.time: units.second,
            }
        )
        self.custom = UnitSystem(
            name="Custom",
            bases={
                Dimension.length: units.foot,
                Dimension.mass: units.pound,
                Dimension.time: units.second,
            }
        )

    def test_identity_transform_vector(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((1,),),
        )
        # Transform the length dimension vector
        src_vector = Dimension.length.value
        result = bt.transform(src_vector)
        self.assertEqual(result, Dimension.length.value)

    def test_scaling_transform_vector(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((2,),),
        )
        src_vector = Dimension.length.vector
        result = bt.transform(src_vector)
        # Length component should be doubled
        # Access via index (1 = length in SI basis: T, L, M, I, Θ, J, N, B)
        self.assertEqual(result["length"], Fraction(2))

    def test_mixed_transform_vector(self):
        # Transform where mass includes contributions from multiple src dimensions
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length, Dimension.mass),
            dst_dimensions=(Dimension.length, Dimension.mass),
            matrix=(
                (1, 0),
                (1, 1),  # dst_mass = src_length + src_mass
            ),
        )
        # Input: pure length (L=1, M=0)
        src_vector = Dimension.length.vector
        result = bt.transform(src_vector)
        self.assertEqual(result["length"], Fraction(1))
        self.assertEqual(result["mass"], Fraction(1))  # Contribution from length


class TestBasisTransformValidateEdge(unittest.TestCase):
    """Test validate_edge() for cross-basis edge validation."""

    def setUp(self):
        self.si = UnitSystem(
            name="SI",
            bases={
                Dimension.length: units.meter,
                Dimension.mass: units.kilogram,
                Dimension.time: units.second,
            }
        )
        self.custom = UnitSystem(
            name="Custom",
            bases={
                Dimension.length: units.foot,
                Dimension.mass: units.pound,
                Dimension.time: units.second,
            }
        )

    def test_valid_edge_same_dimension(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((1,),),
        )
        # foot (length) -> meter (length) should be valid
        self.assertTrue(bt.validate_edge(units.foot, units.meter))

    def test_invalid_edge_different_dimension(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((1,),),
        )
        # foot (length) -> kilogram (mass) should be invalid
        self.assertFalse(bt.validate_edge(units.foot, units.kilogram))


class TestBasisTransformFractionArithmetic(unittest.TestCase):
    """Test that Fraction arithmetic is exact throughout."""

    def setUp(self):
        self.si = UnitSystem(
            name="SI",
            bases={
                Dimension.length: units.meter,
                Dimension.mass: units.kilogram,
                Dimension.time: units.second,
            }
        )
        self.custom = UnitSystem(
            name="Custom",
            bases={
                Dimension.length: units.foot,
                Dimension.mass: units.pound,
                Dimension.time: units.second,
            }
        )

    def test_fraction_matrix_entries(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length, Dimension.mass),
            dst_dimensions=(Dimension.length, Dimension.mass),
            matrix=(
                (Fraction(1, 3), Fraction(2, 3)),
                (Fraction(1, 2), Fraction(1, 2)),
            ),
        )
        self.assertEqual(bt.matrix[0][0], Fraction(1, 3))
        self.assertEqual(bt.matrix[0][1], Fraction(2, 3))

    def test_inverse_preserves_fractions(self):
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length, Dimension.mass),
            dst_dimensions=(Dimension.length, Dimension.mass),
            matrix=((3, 0), (0, 2)),
        )
        inv = bt.inverse()
        self.assertEqual(inv.matrix[0][0], Fraction(1, 3))
        self.assertEqual(inv.matrix[1][1], Fraction(1, 2))

    def test_no_floating_point_drift(self):
        # 1/3 inverse should give exactly 3, not 2.9999...
        bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((Fraction(1, 3),),),
        )
        inv = bt.inverse()
        self.assertEqual(inv.matrix[0][0], Fraction(3))
        # Double inverse should be exactly original
        inv_inv = inv.inverse()
        self.assertEqual(inv_inv.matrix[0][0], Fraction(1, 3))


class TestBasisTransformHashEquality(unittest.TestCase):
    """Test BasisTransform equality and hashing."""

    def setUp(self):
        self.si = UnitSystem(
            name="SI",
            bases={
                Dimension.length: units.meter,
                Dimension.mass: units.kilogram,
                Dimension.time: units.second,
            }
        )
        self.custom = UnitSystem(
            name="Custom",
            bases={
                Dimension.length: units.foot,
                Dimension.mass: units.pound,
                Dimension.time: units.second,
            }
        )

    def test_equal_transforms(self):
        bt1 = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((1,),),
        )
        bt2 = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((1,),),
        )
        self.assertEqual(bt1, bt2)

    def test_hashable(self):
        bt1 = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((1,),),
        )
        bt2 = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((1,),),
        )
        self.assertEqual(hash(bt1), hash(bt2))
        self.assertEqual(len({bt1, bt2}), 1)


if __name__ == "__main__":
    unittest.main()

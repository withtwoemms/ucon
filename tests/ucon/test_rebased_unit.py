# (c) 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for RebasedUnit.

Verifies that units transformed by a BasisTransform preserve
provenance while exposing the rebased dimension.
"""

import unittest
from fractions import Fraction

from ucon.core import (
    BasisTransform,
    Dimension,
    RebasedUnit,
    Unit,
    UnitSystem,
)
from ucon import units


class TestRebasedUnitConstruction(unittest.TestCase):
    """Test RebasedUnit construction."""

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
        self.bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((1,),),
        )

    def test_valid_construction(self):
        rebased = RebasedUnit(
            original=units.foot,
            rebased_dimension=Dimension.length,
            basis_transform=self.bt,
        )
        self.assertEqual(rebased.original, units.foot)
        self.assertEqual(rebased.rebased_dimension, Dimension.length)
        self.assertEqual(rebased.basis_transform, self.bt)

    def test_dimension_property(self):
        rebased = RebasedUnit(
            original=units.foot,
            rebased_dimension=Dimension.length,
            basis_transform=self.bt,
        )
        self.assertEqual(rebased.dimension, Dimension.length)

    def test_name_property(self):
        rebased = RebasedUnit(
            original=units.foot,
            rebased_dimension=Dimension.length,
            basis_transform=self.bt,
        )
        self.assertEqual(rebased.name, "foot")


class TestRebasedUnitEquality(unittest.TestCase):
    """Test RebasedUnit equality and hashing."""

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
        self.bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((1,),),
        )

    def test_equal_rebased_units(self):
        r1 = RebasedUnit(
            original=units.foot,
            rebased_dimension=Dimension.length,
            basis_transform=self.bt,
        )
        r2 = RebasedUnit(
            original=units.foot,
            rebased_dimension=Dimension.length,
            basis_transform=self.bt,
        )
        self.assertEqual(r1, r2)

    def test_hashable(self):
        r1 = RebasedUnit(
            original=units.foot,
            rebased_dimension=Dimension.length,
            basis_transform=self.bt,
        )
        r2 = RebasedUnit(
            original=units.foot,
            rebased_dimension=Dimension.length,
            basis_transform=self.bt,
        )
        self.assertEqual(hash(r1), hash(r2))
        self.assertEqual(len({r1, r2}), 1)

    def test_different_original_not_equal(self):
        r1 = RebasedUnit(
            original=units.foot,
            rebased_dimension=Dimension.length,
            basis_transform=self.bt,
        )
        r2 = RebasedUnit(
            original=units.inch,
            rebased_dimension=Dimension.length,
            basis_transform=self.bt,
        )
        self.assertNotEqual(r1, r2)


class TestRebasedUnitImmutability(unittest.TestCase):
    """Test that RebasedUnit is immutable."""

    def setUp(self):
        self.si = UnitSystem(
            name="SI",
            bases={
                Dimension.length: units.meter,
            }
        )
        self.custom = UnitSystem(
            name="Custom",
            bases={
                Dimension.length: units.foot,
            }
        )
        self.bt = BasisTransform(
            src=self.custom,
            dst=self.si,
            src_dimensions=(Dimension.length,),
            dst_dimensions=(Dimension.length,),
            matrix=((1,),),
        )

    def test_frozen_dataclass(self):
        rebased = RebasedUnit(
            original=units.foot,
            rebased_dimension=Dimension.length,
            basis_transform=self.bt,
        )
        with self.assertRaises(AttributeError):
            rebased.original = units.meter


if __name__ == "__main__":
    unittest.main()

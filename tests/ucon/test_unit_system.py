# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for UnitSystem.

Verifies construction, validation, and query methods for named
unit system definitions.
"""

import unittest

from ucon import units
from ucon.core import Dimension, Unit, UnitSystem, DimensionNotCovered


class TestUnitSystemConstruction(unittest.TestCase):
    """Test UnitSystem construction and validation."""

    def test_valid_construction(self):
        system = UnitSystem(
            name="SI",
            bases={
                Dimension.length: units.meter,
                Dimension.mass: units.kilogram,
                Dimension.time: units.second,
            }
        )
        self.assertEqual(system.name, "SI")
        self.assertEqual(len(system.bases), 3)

    def test_single_base_allowed(self):
        system = UnitSystem(
            name="length-only",
            bases={Dimension.length: units.meter}
        )
        self.assertEqual(len(system.bases), 1)

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            UnitSystem(name="", bases={Dimension.length: units.meter})
        self.assertIn("name", str(ctx.exception).lower())

    def test_empty_bases_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            UnitSystem(name="empty", bases={})
        self.assertIn("base", str(ctx.exception).lower())

    def test_mismatched_dimension_rejected(self):
        # meter has Dimension.length, but we declare it as mass
        with self.assertRaises(ValueError) as ctx:
            UnitSystem(
                name="bad",
                bases={Dimension.mass: units.meter}
            )
        self.assertIn("dimension", str(ctx.exception).lower())

    def test_partial_system_allowed(self):
        # Imperial doesn't need mole or candela
        system = UnitSystem(
            name="Imperial",
            bases={
                Dimension.length: units.foot,
                Dimension.mass: units.pound,
                Dimension.time: units.second,
            }
        )
        self.assertEqual(len(system.bases), 3)


class TestUnitSystemQueries(unittest.TestCase):
    """Test UnitSystem query methods."""

    def setUp(self):
        self.si = UnitSystem(
            name="SI",
            bases={
                Dimension.length: units.meter,
                Dimension.mass: units.kilogram,
                Dimension.time: units.second,
                Dimension.temperature: units.kelvin,
            }
        )

    def test_covers_returns_true_for_covered(self):
        self.assertTrue(self.si.covers(Dimension.length))
        self.assertTrue(self.si.covers(Dimension.mass))
        self.assertTrue(self.si.covers(Dimension.time))

    def test_covers_returns_false_for_uncovered(self):
        self.assertFalse(self.si.covers(Dimension.current))
        self.assertFalse(self.si.covers(Dimension.luminous_intensity))

    def test_base_for_returns_correct_unit(self):
        self.assertEqual(self.si.base_for(Dimension.length), units.meter)
        self.assertEqual(self.si.base_for(Dimension.mass), units.kilogram)
        self.assertEqual(self.si.base_for(Dimension.time), units.second)

    def test_base_for_raises_for_uncovered(self):
        with self.assertRaises(DimensionNotCovered) as ctx:
            self.si.base_for(Dimension.current)
        self.assertIn("current", str(ctx.exception).lower())

    def test_dimensions_property(self):
        dims = self.si.dimensions
        self.assertIsInstance(dims, set)
        self.assertEqual(len(dims), 4)
        self.assertIn(Dimension.length, dims)
        self.assertIn(Dimension.mass, dims)


class TestUnitSystemEquality(unittest.TestCase):
    """Test UnitSystem equality and hashing."""

    def test_same_systems_equal(self):
        s1 = UnitSystem(
            name="SI",
            bases={Dimension.length: units.meter}
        )
        s2 = UnitSystem(
            name="SI",
            bases={Dimension.length: units.meter}
        )
        self.assertEqual(s1, s2)

    def test_different_names_not_equal(self):
        s1 = UnitSystem(name="SI", bases={Dimension.length: units.meter})
        s2 = UnitSystem(name="CGS", bases={Dimension.length: units.meter})
        self.assertNotEqual(s1, s2)

    def test_different_bases_not_equal(self):
        s1 = UnitSystem(name="test", bases={Dimension.length: units.meter})
        s2 = UnitSystem(name="test", bases={Dimension.length: units.foot})
        self.assertNotEqual(s1, s2)

    def test_hashable(self):
        s1 = UnitSystem(name="SI", bases={Dimension.length: units.meter})
        s2 = UnitSystem(name="SI", bases={Dimension.length: units.meter})
        self.assertEqual(hash(s1), hash(s2))
        self.assertEqual(len({s1, s2}), 1)


class TestUnitSystemImmutability(unittest.TestCase):
    """Test that UnitSystem is immutable."""

    def test_frozen_dataclass(self):
        system = UnitSystem(
            name="SI",
            bases={Dimension.length: units.meter}
        )
        with self.assertRaises(AttributeError):
            system.name = "changed"


class TestPredefinedSystems(unittest.TestCase):
    """Test predefined unit systems in ucon.units."""

    def test_si_system_exists(self):
        from ucon.units import si
        self.assertEqual(si.name, "SI")
        self.assertTrue(si.covers(Dimension.length))
        self.assertTrue(si.covers(Dimension.mass))
        self.assertTrue(si.covers(Dimension.time))

    def test_imperial_system_exists(self):
        from ucon.units import imperial
        self.assertEqual(imperial.name, "Imperial")
        self.assertTrue(imperial.covers(Dimension.length))
        self.assertTrue(imperial.covers(Dimension.mass))


if __name__ == "__main__":
    unittest.main()

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
from ucon.dimension import (
    LENGTH, MASS, TIME, TEMPERATURE, CURRENT, LUMINOUS_INTENSITY,
)


class TestUnitSystemConstruction(unittest.TestCase):
    """Test UnitSystem construction and validation."""

    def test_valid_construction(self):
        system = UnitSystem(
            name="SI",
            bases={
                LENGTH: units.meter,
                MASS: units.kilogram,
                TIME: units.second,
            }
        )
        self.assertEqual(system.name, "SI")
        self.assertEqual(len(system.bases), 3)

    def test_single_base_allowed(self):
        system = UnitSystem(
            name="length-only",
            bases={LENGTH: units.meter}
        )
        self.assertEqual(len(system.bases), 1)

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            UnitSystem(name="", bases={LENGTH: units.meter})
        self.assertIn("name", str(ctx.exception).lower())

    def test_empty_bases_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            UnitSystem(name="empty", bases={})
        self.assertIn("base", str(ctx.exception).lower())

    def test_mismatched_dimension_rejected(self):
        # meter has LENGTH, but we declare it as mass
        with self.assertRaises(ValueError) as ctx:
            UnitSystem(
                name="bad",
                bases={MASS: units.meter}
            )
        self.assertIn("dimension", str(ctx.exception).lower())

    def test_partial_system_allowed(self):
        # Imperial doesn't need mole or candela
        system = UnitSystem(
            name="Imperial",
            bases={
                LENGTH: units.foot,
                MASS: units.pound,
                TIME: units.second,
            }
        )
        self.assertEqual(len(system.bases), 3)


class TestUnitSystemQueries(unittest.TestCase):
    """Test UnitSystem query methods."""

    def setUp(self):
        self.si = UnitSystem(
            name="SI",
            bases={
                LENGTH: units.meter,
                MASS: units.kilogram,
                TIME: units.second,
                TEMPERATURE: units.kelvin,
            }
        )

    def test_covers_returns_true_for_covered(self):
        self.assertTrue(self.si.covers(LENGTH))
        self.assertTrue(self.si.covers(MASS))
        self.assertTrue(self.si.covers(TIME))

    def test_covers_returns_false_for_uncovered(self):
        self.assertFalse(self.si.covers(CURRENT))
        self.assertFalse(self.si.covers(LUMINOUS_INTENSITY))

    def test_base_for_returns_correct_unit(self):
        self.assertEqual(self.si.base_for(LENGTH), units.meter)
        self.assertEqual(self.si.base_for(MASS), units.kilogram)
        self.assertEqual(self.si.base_for(TIME), units.second)

    def test_base_for_raises_for_uncovered(self):
        with self.assertRaises(DimensionNotCovered) as ctx:
            self.si.base_for(CURRENT)
        self.assertIn("current", str(ctx.exception).lower())

    def test_dimensions_property(self):
        dims = self.si.dimensions
        self.assertIsInstance(dims, set)
        self.assertEqual(len(dims), 4)
        self.assertIn(LENGTH, dims)
        self.assertIn(MASS, dims)


class TestUnitSystemEquality(unittest.TestCase):
    """Test UnitSystem equality and hashing."""

    def test_same_systems_equal(self):
        s1 = UnitSystem(
            name="SI",
            bases={LENGTH: units.meter}
        )
        s2 = UnitSystem(
            name="SI",
            bases={LENGTH: units.meter}
        )
        self.assertEqual(s1, s2)

    def test_different_names_not_equal(self):
        s1 = UnitSystem(name="SI", bases={LENGTH: units.meter})
        s2 = UnitSystem(name="CGS", bases={LENGTH: units.meter})
        self.assertNotEqual(s1, s2)

    def test_different_bases_not_equal(self):
        s1 = UnitSystem(name="test", bases={LENGTH: units.meter})
        s2 = UnitSystem(name="test", bases={LENGTH: units.foot})
        self.assertNotEqual(s1, s2)

    def test_hashable(self):
        s1 = UnitSystem(name="SI", bases={LENGTH: units.meter})
        s2 = UnitSystem(name="SI", bases={LENGTH: units.meter})
        self.assertEqual(hash(s1), hash(s2))
        self.assertEqual(len({s1, s2}), 1)


class TestUnitSystemImmutability(unittest.TestCase):
    """Test that UnitSystem is immutable."""

    def test_frozen_dataclass(self):
        system = UnitSystem(
            name="SI",
            bases={LENGTH: units.meter}
        )
        with self.assertRaises(AttributeError):
            system.name = "changed"


class TestPredefinedSystems(unittest.TestCase):
    """Test predefined unit systems in ucon.units."""

    def test_si_system_exists(self):
        from ucon.units import si
        self.assertEqual(si.name, "SI")
        self.assertTrue(si.covers(LENGTH))
        self.assertTrue(si.covers(MASS))
        self.assertTrue(si.covers(TIME))

    def test_imperial_system_exists(self):
        from ucon.units import imperial
        self.assertEqual(imperial.name, "Imperial")
        self.assertTrue(imperial.covers(LENGTH))
        self.assertTrue(imperial.covers(MASS))


if __name__ == "__main__":
    unittest.main()

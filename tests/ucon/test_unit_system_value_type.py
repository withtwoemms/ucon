# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for the v1.8 ``ucon.system.UnitSystem`` value type and its
``use`` / ``active`` context-var plumbing.

Phase 2 introduces the type and its construction surface but wires no
callers; these tests verify the shape directly.
"""

import unittest

from ucon.system import (
    AlgebraCache,
    BaseUnits,
    UnitSystem,
    active,
    use,
)


class TestAlgebraCache(unittest.TestCase):
    def test_default_construction_empty(self):
        cache = AlgebraCache()
        self.assertEqual(cache.mul, {})
        self.assertEqual(cache.div, {})
        self.assertEqual(cache.pow, {})

    def test_clear_empties_all_subcaches(self):
        cache = AlgebraCache()
        cache.mul["a"] = 1
        cache.div["b"] = 2
        cache.pow["c"] = 3
        cache.clear()
        self.assertEqual(cache.mul, {})
        self.assertEqual(cache.div, {})
        self.assertEqual(cache.pow, {})

    def test_independent_instances(self):
        c1 = AlgebraCache()
        c2 = AlgebraCache()
        c1.mul["x"] = 99
        self.assertNotIn("x", c2.mul)


class TestUnitSystemFromGlobals(unittest.TestCase):
    def test_from_globals_returns_unitsystem(self):
        system = UnitSystem.from_globals()
        self.assertIsInstance(system, UnitSystem)

    def test_from_globals_populates_required_fields(self):
        system = UnitSystem.from_globals()
        # Type-level checks; the actual concrete types live in modules
        # that import each other in nontrivial ways.
        self.assertIsNotNone(system.basis)
        self.assertIsInstance(system.units, dict)
        self.assertIsInstance(system.dimensions, dict)
        self.assertIsInstance(system.base_units, BaseUnits)
        self.assertIsNotNone(system.conversions)
        self.assertIsNotNone(system.basis_graph)
        self.assertIsInstance(system.contexts, dict)
        self.assertIsInstance(system.constants, dict)
        self.assertIsInstance(system._algebra_cache, AlgebraCache)

    def test_base_units_field_is_baseunits(self):
        system = UnitSystem.from_globals()
        self.assertIsInstance(system.base_units, BaseUnits)
        self.assertEqual(system.base_units.name, "SI")

    def test_from_globals_contains_meter_in_units(self):
        system = UnitSystem.from_globals()
        self.assertIn("meter", system.units)


class TestUnitSystemValueSemantics(unittest.TestCase):
    def test_two_snapshots_are_equal(self):
        s1 = UnitSystem.from_globals()
        s2 = UnitSystem.from_globals()
        # Same global registries -> equal
        self.assertEqual(s1, s2)

    def test_equal_systems_share_hash(self):
        s1 = UnitSystem.from_globals()
        s2 = UnitSystem.from_globals()
        self.assertEqual(hash(s1), hash(s2))

    def test_hashable(self):
        # Must be usable in a set
        s = UnitSystem.from_globals()
        bucket = {s}
        self.assertIn(s, bucket)

    def test_frozen_assignment_raises(self):
        s = UnitSystem.from_globals()
        with self.assertRaises(Exception):
            s.basis = None

    def test_unequal_to_non_unitsystem(self):
        s = UnitSystem.from_globals()
        self.assertNotEqual(s, "not a system")
        self.assertNotEqual(s, 42)


class TestActiveAndUse(unittest.TestCase):
    def test_active_returns_unitsystem(self):
        system = active()
        self.assertIsInstance(system, UnitSystem)

    def test_active_snapshots_when_no_use_block(self):
        # Two calls outside a `use` block should each produce equal snapshots.
        s1 = active()
        s2 = active()
        self.assertEqual(s1, s2)

    def test_use_sets_active_inside_block(self):
        custom = UnitSystem.from_globals()
        with use(custom):
            self.assertIs(active(), custom)

    def test_use_restores_active_on_exit(self):
        # Outside the block, active() must not return the custom system
        # (it returns a fresh snapshot).
        custom = UnitSystem.from_globals()
        with use(custom):
            pass
        # After exit, no custom system is bound: active() yields a snapshot,
        # not `custom` by identity.
        self.assertIsNot(active(), custom)

    def test_use_nested_blocks_unwind_correctly(self):
        outer = UnitSystem.from_globals()
        inner = UnitSystem.from_globals()
        with use(outer):
            self.assertIs(active(), outer)
            with use(inner):
                self.assertIs(active(), inner)
            self.assertIs(active(), outer)
        self.assertIsNot(active(), outer)


class TestPublicSurface(unittest.TestCase):
    def test_baseunits_importable_from_ucon_system(self):
        from ucon.system import BaseUnits as BU  # noqa: F401
        self.assertIs(BU, BaseUnits)

    def test_unitsystem_importable_from_ucon_system(self):
        from ucon.system import UnitSystem as US  # noqa: F401
        self.assertIs(US, UnitSystem)

    def test_use_and_active_importable_from_ucon_system(self):
        from ucon.system import active as a, use as u  # noqa: F401
        self.assertTrue(callable(a))
        self.assertTrue(callable(u))


if __name__ == "__main__":
    unittest.main()

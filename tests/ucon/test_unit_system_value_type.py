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


class TestFromGlobalsOverride(unittest.TestCase):
    """Cover the ``base_units`` keyword override path in ``from_globals``."""

    def test_default_base_units_is_si(self):
        from ucon import units as _units_module
        system = UnitSystem.from_globals()
        self.assertIs(system.base_units, _units_module.si)

    def test_override_base_units_is_used_verbatim(self):
        from ucon import Dimension, units as _units_module
        custom = BaseUnits(
            name="length-only", bases={Dimension.length: _units_module.meter}
        )
        system = UnitSystem.from_globals(base_units=custom)
        self.assertIs(system.base_units, custom)
        self.assertEqual(system.base_units.name, "length-only")

    def test_override_does_not_affect_other_fields(self):
        from ucon import Dimension, units as _units_module
        custom = BaseUnits(
            name="length-only", bases={Dimension.length: _units_module.meter}
        )
        baseline = UnitSystem.from_globals()
        overridden = UnitSystem.from_globals(base_units=custom)
        self.assertIs(overridden.units, baseline.units)
        self.assertIs(overridden.dimensions, baseline.dimensions)
        self.assertIs(overridden.conversions, baseline.conversions)
        self.assertIs(overridden.basis_graph, baseline.basis_graph)


class TestUnitSystemDifferentialEquality(unittest.TestCase):
    """Each field's contribution to UnitSystem ``__eq__`` semantics."""

    def _twin(self, base, **overrides):
        kwargs = {
            "basis": base.basis,
            "units": base.units,
            "dimensions": base.dimensions,
            "base_units": base.base_units,
            "conversions": base.conversions,
            "basis_graph": base.basis_graph,
            "contexts": base.contexts,
            "constants": base.constants,
        }
        kwargs.update(overrides)
        return UnitSystem(**kwargs)

    def test_eq_returns_notimplemented_for_non_unitsystem(self):
        s = UnitSystem.from_globals()
        # Direct __eq__ call to confirm the sentinel return; `!=` would
        # collapse it to True via Python's fallback machinery.
        self.assertIs(s.__eq__("not a system"), NotImplemented)
        self.assertIs(s.__eq__(42), NotImplemented)
        self.assertIs(s.__eq__(None), NotImplemented)

    def test_different_base_units_not_equal(self):
        from ucon import Dimension, units as _units_module
        s = UnitSystem.from_globals()
        twin = self._twin(
            s,
            base_units=BaseUnits(
                name="other", bases={Dimension.length: _units_module.meter}
            ),
        )
        self.assertNotEqual(s, twin)

    def test_different_basis_not_equal(self):
        from ucon.basis.types import Basis
        s = UnitSystem.from_globals()
        twin = self._twin(s, basis=Basis("Synthetic", ["x", "y"]))
        self.assertNotEqual(s, twin)

    def test_units_field_uses_identity_not_value(self):
        s = UnitSystem.from_globals()
        # Same content, different dict instance -> not equal.
        twin = self._twin(s, units=dict(s.units))
        self.assertNotEqual(s, twin)

    def test_dimensions_field_uses_identity_not_value(self):
        s = UnitSystem.from_globals()
        twin = self._twin(s, dimensions=dict(s.dimensions))
        self.assertNotEqual(s, twin)

    def test_contexts_field_uses_identity_not_value(self):
        s = UnitSystem.from_globals()
        twin = self._twin(s, contexts=dict(s.contexts))
        self.assertNotEqual(s, twin)

    def test_constants_field_uses_identity_not_value(self):
        s = UnitSystem.from_globals()
        twin = self._twin(s, constants=dict(s.constants))
        self.assertNotEqual(s, twin)

    def test_conversions_field_uses_identity_not_value(self):
        s = UnitSystem.from_globals()
        twin = self._twin(s, conversions=object())
        self.assertNotEqual(s, twin)

    def test_basis_graph_field_uses_identity_not_value(self):
        s = UnitSystem.from_globals()
        twin = self._twin(s, basis_graph=object())
        self.assertNotEqual(s, twin)


class TestUnitSystemAlgebraCacheSemantics(unittest.TestCase):
    """``_algebra_cache`` is a per-instance ledger, excluded from value identity."""

    def test_distinct_snapshots_have_distinct_caches(self):
        s1 = UnitSystem.from_globals()
        s2 = UnitSystem.from_globals()
        self.assertIsNot(s1._algebra_cache, s2._algebra_cache)

    def test_cache_contents_excluded_from_equality(self):
        s1 = UnitSystem.from_globals()
        s2 = UnitSystem.from_globals()
        s1._algebra_cache.mul[("a", "b")] = "anything"
        s1._algebra_cache.div[("c", "d")] = "anything"
        s1._algebra_cache.pow[("e", 2)] = "anything"
        # Cache divergence does not break equality or hash.
        self.assertEqual(s1, s2)
        self.assertEqual(hash(s1), hash(s2))

    def test_cache_excluded_from_repr(self):
        s = UnitSystem.from_globals()
        self.assertNotIn("_algebra_cache", repr(s))

    def test_cache_starts_empty(self):
        s = UnitSystem.from_globals()
        self.assertEqual(s._algebra_cache.mul, {})
        self.assertEqual(s._algebra_cache.div, {})
        self.assertEqual(s._algebra_cache.pow, {})


class TestUseExceptionSafety(unittest.TestCase):
    """``use`` must restore the previous active system on every exit path."""

    def test_use_restores_on_exception(self):
        class _Boom(RuntimeError):
            pass

        custom = UnitSystem.from_globals()
        with self.assertRaises(_Boom):
            with use(custom):
                self.assertIs(active(), custom)
                raise _Boom("failure inside use-block")
        # active() falls back to a snapshot, not the leaked custom system.
        self.assertIsNot(active(), custom)

    def test_nested_use_restores_outer_on_inner_exception(self):
        class _Boom(RuntimeError):
            pass

        outer = UnitSystem.from_globals()
        inner = UnitSystem.from_globals()
        with use(outer):
            with self.assertRaises(_Boom):
                with use(inner):
                    raise _Boom("inner failure")
            # Outer must be the active system once inner unwinds.
            self.assertIs(active(), outer)


class TestBaseUnitsHashOrderStability(unittest.TestCase):
    """``BaseUnits.__hash__`` must be invariant under bases insertion order."""

    def test_hash_independent_of_insertion_order(self):
        from ucon import Dimension, units as _units_module
        s1 = BaseUnits(name="X", bases={
            Dimension.length: _units_module.meter,
            Dimension.mass: _units_module.kilogram,
            Dimension.time: _units_module.second,
        })
        s2 = BaseUnits(name="X", bases={
            Dimension.time: _units_module.second,
            Dimension.length: _units_module.meter,
            Dimension.mass: _units_module.kilogram,
        })
        self.assertEqual(s1, s2)
        self.assertEqual(hash(s1), hash(s2))
        self.assertEqual(len({s1, s2}), 1)


if __name__ == "__main__":
    unittest.main()

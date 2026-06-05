# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
test_relations
==============

Tests for the :class:`UnitSystem` relation surface:

- :meth:`UnitSystem.subsystem_of`
- :meth:`UnitSystem.compatible_with`
- :meth:`UnitSystem.diff` (returns :class:`SystemDiff`)
- :meth:`UnitSystem.shared_units`
- :meth:`UnitSystem.shared_dimensions`

Fixtures are derived from the eagerly-initialised active ``UnitSystem``
via :meth:`UnitSystem.restrict` and a local ``_with_unit_replaced``
helper that constructs conflict scenarios without monkey-patching the
production type.
"""

import dataclasses
import unittest

import ucon
from ucon import ContextEdge
from ucon.maps import LinearMap
from ucon.system import BaseUnits, RegistryDiff, SystemDiff, UnitSystem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _active() -> UnitSystem:
    return ucon.active_system()


def _restrict_to(system: UnitSystem, dim_name: str) -> UnitSystem:
    return system.restrict(dimensions=[system.dimensions[dim_name]])


def _with_unit_replaced(system: UnitSystem, name: str, new_unit) -> UnitSystem:
    """Build a derivative system whose ``units[name]`` is replaced by
    ``new_unit``. Bypasses :meth:`UnitSystem.with_unit`'s conflict check
    by hand-rolling construction; useful only for conflict-setup.
    """
    new_units = dict(system.units)
    new_units[name] = new_unit
    new_graph = system.conversion_graph.copy()
    new_graph.register_unit(new_unit)
    return UnitSystem(
        basis=system.basis,
        units=new_units,
        dimensions=dict(system.dimensions),
        base_units=system.base_units,
        conversion_graph=new_graph,
        basis_graph=system.basis_graph,
        contexts=dict(system.contexts),
        constants=dict(system.constants),
    )


def _with_dimension_replaced(system: UnitSystem, name: str, new_dim) -> UnitSystem:
    """Build a derivative system whose ``dimensions[name]`` is replaced by
    ``new_dim``. Useful for constructing dimension-mismatch scenarios.
    """
    new_dims = dict(system.dimensions)
    new_dims[name] = new_dim
    return UnitSystem(
        basis=system.basis,
        units=dict(system.units),
        dimensions=new_dims,
        base_units=system.base_units,
        conversion_graph=system.conversion_graph.copy(),
        basis_graph=system.basis_graph,
        contexts=dict(system.contexts),
        constants=dict(system.constants),
    )


def _with_base_units_replaced(system: UnitSystem, new_base_units) -> UnitSystem:
    return UnitSystem(
        basis=system.basis,
        units=dict(system.units),
        dimensions=dict(system.dimensions),
        base_units=new_base_units,
        conversion_graph=system.conversion_graph.copy(),
        basis_graph=system.basis_graph,
        contexts=dict(system.contexts),
        constants=dict(system.constants),
    )


# ---------------------------------------------------------------------------
# subsystem_of
# ---------------------------------------------------------------------------


class TestSubsystemOf(unittest.TestCase):

    def test_reflexive(self):
        s = _active()
        self.assertTrue(s.subsystem_of(s))

    def test_restriction_is_subsystem(self):
        s = _active()
        length = _restrict_to(s, "length")
        self.assertTrue(length.subsystem_of(s))

    def test_superset_is_not_subsystem(self):
        s = _active()
        length = _restrict_to(s, "length")
        # The full active system is *not* a subsystem of a length-only slice.
        self.assertFalse(s.subsystem_of(length))

    def test_redefined_unit_breaks_subsystem(self):
        from ucon.core import Unit as _Unit
        s = _active()
        meter = s.units["meter"]
        rebadged = _Unit(
            name=meter.name,
            dimension=meter.dimension,
            aliases=("zzz",),
        )
        other = _with_unit_replaced(s, "meter", rebadged)
        # 'other' has every unit name s has, but 'meter' is redefined,
        # so s is not a subsystem of other.
        self.assertFalse(s.subsystem_of(other))

    def test_redefined_dimension_breaks_subsystem(self):
        s = _active()
        length = s.dimensions["length"]
        # Re-tag the dimension so name matches but the value does not.
        retagged = dataclasses.replace(length, tag="alt_tag")
        other = _with_dimension_replaced(s, "length", retagged)
        self.assertFalse(s.subsystem_of(other))

    def test_redefined_base_units_breaks_subsystem(self):
        s = _active()
        length = s.dimensions["length"]
        foot = s.units["foot"]
        new_bases = dict(s.base_units.bases)
        new_bases[length] = foot
        other = _with_base_units_replaced(
            s, BaseUnits(name=s.base_units.name, bases=new_bases)
        )
        # Same units and dimensions, but length's base unit differs.
        self.assertFalse(s.subsystem_of(other))

    def test_missing_conversion_edge_breaks_subsystem(self):
        from ucon.core import Unit as _Unit
        s = _active()
        length = s.dimensions["length"]
        a = _Unit(name="ucon_rel_a", dimension=length, aliases=())
        b = _Unit(name="ucon_rel_b", dimension=length, aliases=())
        staged = s.with_unit(a).with_unit(b)
        with_edge = staged.with_conversion(
            ContextEdge(src=a, dst=b, map=LinearMap(2.0))
        )
        # ``with_edge`` carries an edge that ``staged`` lacks → not a
        # subsystem of ``staged``.
        self.assertFalse(with_edge.subsystem_of(staged))


# ---------------------------------------------------------------------------
# compatible_with
# ---------------------------------------------------------------------------


class TestCompatibleWith(unittest.TestCase):

    def test_reflexive(self):
        s = _active()
        self.assertTrue(s.compatible_with(s))

    def test_disjoint_restrictions_are_compatible(self):
        s = _active()
        length = _restrict_to(s, "length")
        mass = _restrict_to(s, "mass")
        self.assertTrue(length.compatible_with(mass))
        self.assertTrue(mass.compatible_with(length))

    def test_restriction_is_compatible_with_parent(self):
        s = _active()
        length = _restrict_to(s, "length")
        self.assertTrue(length.compatible_with(s))
        self.assertTrue(s.compatible_with(length))

    def test_redefined_unit_makes_incompatible(self):
        from ucon.core import Unit as _Unit
        s = _active()
        meter = s.units["meter"]
        rebadged = _Unit(
            name=meter.name,
            dimension=meter.dimension,
            aliases=("qqq",),
        )
        other = _with_unit_replaced(s, "meter", rebadged)
        self.assertFalse(s.compatible_with(other))
        self.assertFalse(other.compatible_with(s))

    def test_redefined_dimension_makes_incompatible(self):
        s = _active()
        length = s.dimensions["length"]
        retagged = dataclasses.replace(length, tag="alt_tag")
        other = _with_dimension_replaced(s, "length", retagged)
        self.assertFalse(s.compatible_with(other))
        self.assertFalse(other.compatible_with(s))

    def test_redefined_base_units_makes_incompatible(self):
        s = _active()
        length = s.dimensions["length"]
        foot = s.units["foot"]
        new_bases = dict(s.base_units.bases)
        new_bases[length] = foot
        other = _with_base_units_replaced(
            s, BaseUnits(name=s.base_units.name, bases=new_bases)
        )
        self.assertFalse(s.compatible_with(other))
        self.assertFalse(other.compatible_with(s))

    def test_disagreeing_conversion_edge_makes_incompatible(self):
        from ucon.core import Unit as _Unit
        s = _active()
        length = s.dimensions["length"]
        a = _Unit(name="ucon_rel_compat_a", dimension=length, aliases=())
        b = _Unit(name="ucon_rel_compat_b", dimension=length, aliases=())
        staged = s.with_unit(a).with_unit(b)
        lhs = staged.with_conversion(ContextEdge(src=a, dst=b, map=LinearMap(2.0)))
        rhs = staged.with_conversion(ContextEdge(src=a, dst=b, map=LinearMap(3.0)))
        # Same (src, dst) pair, different maps → not compatible.
        self.assertFalse(lhs.compatible_with(rhs))
        self.assertFalse(rhs.compatible_with(lhs))


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------


class TestDiff(unittest.TestCase):

    def test_diff_self_is_empty(self):
        s = _active()
        d = s.diff(s)
        self.assertIsInstance(d, SystemDiff)
        self.assertTrue(d.is_empty())

    def test_diff_returns_systemdiff(self):
        s = _active()
        length = _restrict_to(s, "length")
        d = s.diff(length)
        self.assertIsInstance(d, SystemDiff)
        for fname in (
            "units", "dimensions", "base_units",
            "conversions", "contexts", "constants",
        ):
            self.assertIsInstance(getattr(d, fname), RegistryDiff)

    def test_diff_removed_when_other_is_restricted(self):
        s = _active()
        length = _restrict_to(s, "length")
        d = s.diff(length)
        # Going from s to a length-only slice: every non-length unit is
        # "removed" in the s -> length direction.
        self.assertFalse(d.is_empty())
        self.assertTrue(len(d.units.removed) >= 1)
        self.assertEqual(d.units.added, frozenset())

    def test_diff_added_when_other_is_superset(self):
        s = _active()
        length = _restrict_to(s, "length")
        # Going from length to s: non-length units appear as "added".
        d = length.diff(s)
        self.assertFalse(d.is_empty())
        self.assertTrue(len(d.units.added) >= 1)
        self.assertEqual(d.units.removed, frozenset())

    def test_diff_redefined_when_unit_replaced(self):
        from ucon.core import Unit as _Unit
        s = _active()
        meter = s.units["meter"]
        rebadged = _Unit(
            name=meter.name,
            dimension=meter.dimension,
            aliases=("diff_redef_marker",),
        )
        other = _with_unit_replaced(s, "meter", rebadged)
        d = s.diff(other)
        # 'meter' shows up as redefined in units, not added/removed.
        self.assertIn("meter", d.units.redefined)
        self.assertNotIn("meter", d.units.added)
        self.assertNotIn("meter", d.units.removed)

    def test_diff_dimensions_redefined_only_when_unequal(self):
        s = _active()
        d = s.diff(s)
        # Same system on both sides: no dimensions redefined.
        self.assertEqual(d.dimensions.redefined, frozenset())
        self.assertEqual(d.dimensions.added, frozenset())
        self.assertEqual(d.dimensions.removed, frozenset())

    def test_diff_base_units_tracks_dimension_keys(self):
        s = _active()
        length = _restrict_to(s, "length")
        d = s.diff(length)
        # Other base_units dimensions present in s but not in length show
        # up as removed entries.
        self.assertNotIn("length", d.base_units.removed)
        # Mass / time / etc. are removed when restricting to length.
        self.assertTrue(len(d.base_units.removed) >= 1)


# ---------------------------------------------------------------------------
# shared_units / shared_dimensions
# ---------------------------------------------------------------------------


class TestSharedSets(unittest.TestCase):

    def test_shared_units_with_self_is_all_units(self):
        s = _active()
        shared = s.shared_units(s)
        self.assertEqual(shared, frozenset(s.units.keys()))

    def test_shared_units_is_frozenset(self):
        s = _active()
        self.assertIsInstance(s.shared_units(s), frozenset)

    def test_shared_units_symmetric(self):
        s = _active()
        length = _restrict_to(s, "length")
        self.assertEqual(s.shared_units(length), length.shared_units(s))

    def test_shared_units_is_intersection(self):
        s = _active()
        length = _restrict_to(s, "length")
        mass = _restrict_to(s, "mass")
        # Disjoint by construction (no unit has both length and mass).
        self.assertEqual(length.shared_units(mass), frozenset())

    def test_shared_dimensions_with_self_is_all_dimensions(self):
        s = _active()
        shared = s.shared_dimensions(s)
        self.assertEqual(shared, frozenset(s.dimensions.keys()))

    def test_shared_dimensions_symmetric(self):
        s = _active()
        length = _restrict_to(s, "length")
        self.assertEqual(
            s.shared_dimensions(length), length.shared_dimensions(s)
        )

    def test_shared_dimensions_is_intersection(self):
        s = _active()
        length = _restrict_to(s, "length")
        mass = _restrict_to(s, "mass")
        self.assertEqual(length.shared_dimensions(mass), frozenset())

    def test_shared_dimensions_contains_restricted_name(self):
        s = _active()
        length = _restrict_to(s, "length")
        self.assertIn("length", s.shared_dimensions(length))


if __name__ == "__main__":
    unittest.main()

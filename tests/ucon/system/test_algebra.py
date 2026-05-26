# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
test_algebra
============

Tests for :meth:`UnitSystem.extend`, :meth:`restrict`, :meth:`merge`,
and the ``with_*`` incremental constructors introduced in v2.0 (§3.1 of
the v2.0 implementation plan).

The tests use the eagerly-initialised active ``UnitSystem`` as the base
fixture and derive subsystems and overlays via the new algebra; no
fresh ``Graph`` / ``BaseUnits`` constructors are required.
"""

import unittest

import ucon
from ucon import ContextEdge
from ucon.maps import LinearMap
from ucon.system import (
    ExtendConflict,
    UnitSystem,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _active():
    return ucon.active()


def _length_only(system):
    """Return the active system restricted to the length dimension."""
    return system.restrict(dimensions=[system.dimensions["length"]])


def _mass_only(system):
    return system.restrict(dimensions=[system.dimensions["mass"]])


def _with_unit_replaced(system, name, new_unit):
    """Build a derivative ``UnitSystem`` that replaces ``units[name]`` with
    ``new_unit``. Bypasses :meth:`UnitSystem.with_unit`'s conflict check
    by hand-rolling the construction; only useful here for setting up
    conflict scenarios.
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


# ---------------------------------------------------------------------------
# extend()
# ---------------------------------------------------------------------------


class TestExtend(unittest.TestCase):

    def test_extend_self_under_prefer_self_preserves_registries(self):
        s = _active()
        result = s.extend(s, on_conflict="prefer-self")
        self.assertEqual(set(result.units.keys()), set(s.units.keys()))
        self.assertEqual(set(result.dimensions.keys()), set(s.dimensions.keys()))

    def test_extend_disjoint_unions_registries(self):
        s = _active()
        length = _length_only(s)
        mass = _mass_only(s)
        merged = length.extend(mass)
        self.assertTrue(set(length.units.keys()) <= set(merged.units.keys()))
        self.assertTrue(set(mass.units.keys()) <= set(merged.units.keys()))
        self.assertIn("length", merged.dimensions)
        self.assertIn("mass", merged.dimensions)

    def test_extend_raise_on_conflict_in_units(self):
        s = _active()
        # Build a conflict by overriding the existing 'meter' definition.
        meter = s.units["meter"]
        from ucon.core import Unit as _Unit
        clashing = _Unit(
            name=meter.name,
            dimension=meter.dimension,
            aliases=("not_a_meter",),
        )
        other = _with_unit_replaced(s, "meter", clashing)
        with self.assertRaises(ExtendConflict) as cm:
            s.extend(other, on_conflict="raise")
        self.assertEqual(cm.exception.registry, "units")
        self.assertEqual(cm.exception.key, "meter")

    def test_extend_prefer_self_keeps_lhs(self):
        s = _active()
        meter = s.units["meter"]
        from ucon.core import Unit as _Unit
        clashing = _Unit(
            name=meter.name,
            dimension=meter.dimension,
            aliases=("foo",),
        )
        other = _with_unit_replaced(s, "meter", clashing)
        result = s.extend(other, on_conflict="prefer-self")
        self.assertEqual(result.units["meter"], meter)

    def test_extend_prefer_other_takes_rhs(self):
        s = _active()
        meter = s.units["meter"]
        from ucon.core import Unit as _Unit
        clashing = _Unit(
            name=meter.name,
            dimension=meter.dimension,
            aliases=("bar",),
        )
        other = _with_unit_replaced(s, "meter", clashing)
        result = s.extend(other, on_conflict="prefer-other")
        self.assertEqual(result.units["meter"], clashing)
        self.assertNotEqual(result.units["meter"], meter)

    def test_extend_returns_new_unitsystem(self):
        s = _active()
        out = s.extend(s, on_conflict="prefer-self")
        self.assertIsInstance(out, UnitSystem)

    def test_invalid_conflict_policy_rejected(self):
        s = _active()
        with self.assertRaises(ValueError):
            s.extend(s, on_conflict="bogus")  # type: ignore[arg-type]

    def test_extend_preserves_self_basis(self):
        s = _active()
        out = s.extend(s, on_conflict="prefer-self")
        self.assertEqual(out.basis, s.basis)
        self.assertIs(out.basis_graph, s.basis_graph)


# ---------------------------------------------------------------------------
# restrict()
# ---------------------------------------------------------------------------


class TestRestrict(unittest.TestCase):

    def test_restrict_by_dimension_keeps_only_listed_dimensions(self):
        s = _active()
        length = s.dimensions["length"]
        r = s.restrict(dimensions=[length])
        self.assertEqual(set(r.dimensions.keys()), {"length"})
        for u in r.units.values():
            self.assertEqual(u.dimension, length)

    def test_restrict_by_units_keeps_only_listed_unit_names(self):
        s = _active()
        r = s.restrict(units=["meter"])
        self.assertEqual(set(r.units.keys()), {"meter"})

    def test_restrict_both_filters_intersect(self):
        s = _active()
        length = s.dimensions["length"]
        # asking for foot (length) AND units list does not include foot
        r = s.restrict(dimensions=[length], units=["meter"])
        self.assertEqual(set(r.units.keys()), {"meter"})

    def test_restrict_preserves_basis_and_basis_graph(self):
        s = _active()
        r = s.restrict(units=["meter"])
        self.assertEqual(r.basis, s.basis)
        self.assertIs(r.basis_graph, s.basis_graph)

    def test_restrict_base_units_pruned_consistently(self):
        s = _active()
        length = s.dimensions["length"]
        r = s.restrict(dimensions=[length])
        self.assertEqual(set(r.base_units.bases.keys()), {length})

    def test_restrict_conversion_graph_drops_pruned_edges(self):
        s = _active()
        r = s.restrict(units=["meter"])
        # meter has no in-graph edge to anything still-kept; the graph
        # should be empty of unit edges.
        for _dim, srcs in r.conversion_graph._unit_edges.items():
            for src, dsts in srcs.items():
                self.assertEqual(src.name, "meter")
                for dst in dsts:
                    self.assertEqual(dst.name, "meter")

    def test_restrict_with_none_filters_is_identity_like(self):
        s = _active()
        r = s.restrict()
        self.assertEqual(set(r.units.keys()), set(s.units.keys()))
        self.assertEqual(set(r.dimensions.keys()), set(s.dimensions.keys()))


# ---------------------------------------------------------------------------
# merge()
# ---------------------------------------------------------------------------


class TestMerge(unittest.TestCase):

    def test_merge_resolver_called_only_on_conflict(self):
        s = _active()
        meter = s.units["meter"]
        from ucon.core import Unit as _Unit
        rhs_meter = _Unit(
            name=meter.name,
            dimension=meter.dimension,
            aliases=("alt",),
        )
        other = _with_unit_replaced(s, "meter", rhs_meter)

        calls = []

        def resolver(a, b):
            calls.append((a, b))
            return b  # take RHS

        result = s.merge(other, resolver)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], meter)
        self.assertEqual(calls[0][1], rhs_meter)
        self.assertEqual(result.units["meter"], rhs_meter)

    def test_merge_no_resolver_call_when_equal(self):
        s = _active()
        calls = []

        def resolver(a, b):
            calls.append((a, b))
            return a

        s.merge(s, resolver)
        self.assertEqual(calls, [])

    def test_merge_uses_prefer_self_for_other_registries(self):
        # merge's resolver is unit-only. Conflicts in dimensions or
        # base_units fall through to prefer-self semantics.
        s = _active()
        # Same system on both sides → no conflicts, result agrees with s.
        result = s.merge(s, lambda a, b: a)
        self.assertEqual(set(result.dimensions.keys()), set(s.dimensions.keys()))


# ---------------------------------------------------------------------------
# with_unit / with_conversion / with_basis / with_basis_graph
# ---------------------------------------------------------------------------


class TestWithUnit(unittest.TestCase):

    def test_with_unit_adds_to_registry(self):
        from ucon.core import Unit as _Unit
        s = _active()
        length = s.dimensions["length"]
        # Use a name guaranteed not to clash with existing units.
        novel = _Unit(name="ucon_test_unit", dimension=length, aliases=())
        out = s.with_unit(novel)
        self.assertIn("ucon_test_unit", out.units)
        self.assertNotIn("ucon_test_unit", s.units)  # immutability

    def test_with_unit_idempotent_on_equal_definition(self):
        s = _active()
        meter = s.units["meter"]
        out = s.with_unit(meter)
        self.assertIs(out, s)

    def test_with_unit_conflict_raises(self):
        from ucon.core import Unit as _Unit
        s = _active()
        meter = s.units["meter"]
        clashing = _Unit(
            name=meter.name,
            dimension=meter.dimension,
            aliases=("xyz",),
        )
        with self.assertRaises(ExtendConflict):
            s.with_unit(clashing)


class TestWithConversion(unittest.TestCase):

    def test_with_conversion_registers_edge(self):
        from ucon.core import Unit as _Unit
        s = _active()
        length = s.dimensions["length"]
        a = _Unit(name="ucon_test_a", dimension=length, aliases=())
        b = _Unit(name="ucon_test_b", dimension=length, aliases=())
        staged = s.with_unit(a).with_unit(b)
        edge = ContextEdge(src=a, dst=b, map=LinearMap(2.0))
        out = staged.with_conversion(edge)
        # Edge should be discoverable in the new graph.
        edges = []
        for _dim, srcs in out.conversion_graph._unit_edges.items():
            for src, dsts in srcs.items():
                for dst in dsts:
                    if src.name == "ucon_test_a" and dst.name == "ucon_test_b":
                        edges.append((src, dst))
        self.assertEqual(len(edges), 1)


class TestWithBasis(unittest.TestCase):

    def test_with_basis_same_is_identity(self):
        s = _active()
        self.assertIs(s.with_basis(s.basis), s)

    def test_with_basis_different_creates_new(self):
        s = _active()
        # Find any other basis in the basis graph.
        other_basis = None
        for src in s.basis_graph._edges.keys():
            if src != s.basis:
                other_basis = src
                break
        if other_basis is None:
            self.skipTest("active basis_graph contains no alternative basis")
        out = s.with_basis(other_basis)
        self.assertEqual(out.basis, other_basis)
        self.assertNotEqual(out.basis, s.basis)


class TestWithBasisGraph(unittest.TestCase):

    def test_with_basis_graph_same_is_identity(self):
        s = _active()
        self.assertIs(s.with_basis_graph(s.basis_graph), s)


if __name__ == "__main__":
    unittest.main()

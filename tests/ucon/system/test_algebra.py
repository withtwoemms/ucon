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
    BaseUnits,
    ConflictPolicy,
    ExtendConflict,
    UnitSystem,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _active():
    return ucon.active_system()


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


def _with_base_units_replaced(system, new_base_units):
    """Build a derivative ``UnitSystem`` whose ``base_units`` mapping is
    ``new_base_units``. Used to construct base-unit conflict scenarios.
    """
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
# extend()
# ---------------------------------------------------------------------------


class TestExtend(unittest.TestCase):

    def test_extend_self_under_prefer_self_preserves_registries(self):
        s = _active()
        result = s.extend(s, on_conflict=ConflictPolicy.PREFER_SELF)
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
            s.extend(other, on_conflict=ConflictPolicy.RAISE)
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
        result = s.extend(other, on_conflict=ConflictPolicy.PREFER_SELF)
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
        result = s.extend(other, on_conflict=ConflictPolicy.PREFER_OTHER)
        self.assertEqual(result.units["meter"], clashing)
        self.assertNotEqual(result.units["meter"], meter)

    def test_extend_returns_new_unitsystem(self):
        s = _active()
        out = s.extend(s, on_conflict=ConflictPolicy.PREFER_SELF)
        self.assertIsInstance(out, UnitSystem)

    def test_non_enum_conflict_policy_rejected(self):
        s = _active()
        with self.assertRaises(TypeError):
            s.extend(s, on_conflict="prefer-self")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            s.extend(s, on_conflict="bogus")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            s.extend(s, on_conflict=None)  # type: ignore[arg-type]

    def test_extend_preserves_self_basis(self):
        s = _active()
        out = s.extend(s, on_conflict=ConflictPolicy.PREFER_SELF)
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

    def test_restrict_by_non_base_unit_falls_back_to_existing_base(self):
        # 'foot' is a length unit but not the canonical base unit for
        # length (meter is). Restricting to {foot} leaves base_units
        # otherwise unsatisfiable; the helper preserves one base entry
        # to keep BaseUnits' non-empty invariant.
        s = _active()
        r = s.restrict(units=["foot"])
        self.assertEqual(set(r.units.keys()), {"foot"})
        # At least one base-unit entry survives (the fallback path).
        self.assertGreaterEqual(len(r.base_units.bases), 1)


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

    def test_merge_adopts_rhs_only_unit_without_invoking_resolver(self):
        from ucon.core import Unit as _Unit
        s = _active()
        length = s.dimensions["length"]
        novel = _Unit(name="ucon_merge_rhs_only", dimension=length, aliases=())
        # Stage the novel unit into the RHS without touching LHS.
        rhs = s.with_unit(novel)

        calls = []

        def resolver(a, b):
            calls.append((a, b))
            return a

        out = s.merge(rhs, resolver)
        self.assertIn("ucon_merge_rhs_only", out.units)
        self.assertNotIn("ucon_merge_rhs_only", s.units)
        # rhs-only names take the additive branch; the resolver never runs.
        self.assertEqual(calls, [])


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


# ---------------------------------------------------------------------------
# extend() — conflict branches in base_units and conversion edges
# ---------------------------------------------------------------------------


class TestExtendBaseUnitsConflict(unittest.TestCase):
    """Exercise :func:`_merge_base_units` conflict branches.

    Self maps ``length -> meter`` (the default base). The conflicting
    RHS maps ``length -> foot`` for the same dimension, which forces the
    helper through its policy-dependent branches.
    """

    def _conflicting_pair(self):
        s = _active()
        length = s.dimensions["length"]
        foot = s.units["foot"]
        # New BaseUnits with the same set of dimensions but length -> foot
        # (instead of meter).
        new_bases = dict(s.base_units.bases)
        new_bases[length] = foot
        rhs = _with_base_units_replaced(
            s, BaseUnits(name=s.base_units.name, bases=new_bases)
        )
        return s, rhs

    def test_raise_on_base_units_conflict(self):
        s, rhs = self._conflicting_pair()
        with self.assertRaises(ExtendConflict) as cm:
            s.extend(rhs, on_conflict=ConflictPolicy.RAISE)
        self.assertEqual(cm.exception.registry, "base_units")
        self.assertEqual(cm.exception.key, "length")

    def test_prefer_self_keeps_lhs_base(self):
        s, rhs = self._conflicting_pair()
        out = s.extend(rhs, on_conflict=ConflictPolicy.PREFER_SELF)
        length = s.dimensions["length"]
        self.assertEqual(out.base_units.bases[length], s.units["meter"])

    def test_prefer_other_takes_rhs_base(self):
        s, rhs = self._conflicting_pair()
        out = s.extend(rhs, on_conflict=ConflictPolicy.PREFER_OTHER)
        length = s.dimensions["length"]
        self.assertEqual(out.base_units.bases[length], s.units["foot"])


class TestExtendConversionEdgeConflict(unittest.TestCase):
    """Exercise :func:`_merge_conversion_graphs` conflict branches.

    Two systems carry the same fresh ``(a, b)`` pair of units but
    register different :class:`LinearMap` factors between them. Merging
    forces the policy-dependent branch.
    """

    def _conflicting_pair(self):
        from ucon.core import Unit as _Unit
        s = _active()
        length = s.dimensions["length"]
        a = _Unit(name="ucon_edge_a", dimension=length, aliases=())
        b = _Unit(name="ucon_edge_b", dimension=length, aliases=())
        staged = s.with_unit(a).with_unit(b)
        lhs = staged.with_conversion(ContextEdge(src=a, dst=b, map=LinearMap(2.0)))
        rhs = staged.with_conversion(ContextEdge(src=a, dst=b, map=LinearMap(3.0)))
        return lhs, rhs

    def test_raise_on_conversion_edge_conflict(self):
        lhs, rhs = self._conflicting_pair()
        with self.assertRaises(ExtendConflict) as cm:
            lhs.extend(rhs, on_conflict=ConflictPolicy.RAISE)
        self.assertEqual(cm.exception.registry, "conversions")
        self.assertEqual(cm.exception.key, "ucon_edge_a->ucon_edge_b")

    def test_prefer_self_keeps_lhs_edge(self):
        lhs, rhs = self._conflicting_pair()
        out = lhs.extend(rhs, on_conflict=ConflictPolicy.PREFER_SELF)
        # Walk the merged graph and confirm the LHS map (factor 2) survived.
        for _dim, srcs in out.conversion_graph._unit_edges.items():
            for src, dsts in srcs.items():
                if src.name != "ucon_edge_a":
                    continue
                for dst, m in dsts.items():
                    if dst.name == "ucon_edge_b":
                        self.assertEqual(m, LinearMap(2.0))
                        return
        self.fail("expected ucon_edge_a -> ucon_edge_b edge in merged graph")

    def test_prefer_other_takes_rhs_edge(self):
        lhs, rhs = self._conflicting_pair()
        out = lhs.extend(rhs, on_conflict=ConflictPolicy.PREFER_OTHER)
        # Walk the merged graph and confirm the RHS map (factor 3) survived.
        for _dim, srcs in out.conversion_graph._unit_edges.items():
            for src, dsts in srcs.items():
                if src.name != "ucon_edge_a":
                    continue
                for dst, m in dsts.items():
                    if dst.name == "ucon_edge_b":
                        self.assertEqual(m, LinearMap(3.0))
                        return
        self.fail("expected ucon_edge_a -> ucon_edge_b edge in merged graph")


class TestWithBasisGraph(unittest.TestCase):

    def test_with_basis_graph_same_is_identity(self):
        s = _active()
        self.assertIs(s.with_basis_graph(s.basis_graph), s)

    def test_with_basis_graph_different_returns_new_system(self):
        from ucon.basis import BasisGraph
        s = _active()
        other_graph = BasisGraph()
        out = s.with_basis_graph(other_graph)
        self.assertIsNot(out, s)
        self.assertIs(out.basis_graph, other_graph)
        # Other fields are preserved.
        self.assertEqual(out.basis, s.basis)
        self.assertEqual(set(out.units.keys()), set(s.units.keys()))


if __name__ == "__main__":
    unittest.main()

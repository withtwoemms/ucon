# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for ``[[contexts]]`` in package TOML.

``ConversionContext`` is the one mechanism for conditional, scoped,
constant-licensed conversion *between* dimensions — the thing a domain
package most needs to distribute. It round-tripped through graph-level TOML
already; what it could not do was ship inside a ``UnitPackage`` (#282).

The distinguishing property, asserted throughout: a context's edges are
**registered, not inserted**. Loading a package makes the context available;
its edges only convert while ``using_context`` has it active. An
unconditional ``[[edges]]`` entry would apply always, which for a
cross-dimensional equivalence licensed by a physical constant is wrong.
"""
import tempfile
import unittest
from pathlib import Path

from ucon import (
    PackageLoadError,
    load_package,
    parse_unit,
    using_conversion_graph,
)
from ucon.contexts import ConversionContext, using_context
from ucon.conversion import DimensionMismatch
from ucon.maps import LinearMap, ReciprocalMap
from ucon.packages import ContextDef, EdgeDef, UnitPackage
from ucon.system import active_system


# A package whose context is licensed by a constant the package declares.
# Endpoints are plain units: context edges resolve between plain units, not
# through scaled or composite endpoints (a pre-existing limit of
# `_convert_products`, unrelated to packaging).
DOSING_TOML = """
[package]
name = "dosing"
version = "1.0.0"

[[units]]
name = "dose_unit"
dimension = "none"
aliases = ["DU"]

[[constants]]
symbol = "k_d"
name = "mass per dose unit"
value = 0.25
unit = "gram"

[[contexts]]
name = "dosing-basis"
description = "Dose units carry a mass only given a formulation constant"

  [[contexts.edges]]
  src = "dose_unit"
  dst = "gram"
  factor = "k_d"
"""


def _write(toml: str) -> Path:
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".ucon.toml", delete=False
    )
    handle.write(toml)
    handle.close()
    return Path(handle.name)


class TestContextDefParsing(unittest.TestCase):
    def test_package_exposes_contexts(self):
        pkg = load_package(_write(DOSING_TOML))
        self.assertEqual(len(pkg.contexts), 1)
        self.assertIsInstance(pkg.contexts[0], ContextDef)

    def test_name_and_description_survive(self):
        ctx = load_package(_write(DOSING_TOML)).contexts[0]
        self.assertEqual(ctx.name, "dosing-basis")
        self.assertIn("formulation constant", ctx.description)

    def test_edges_are_edgedefs(self):
        """Reusing EdgeDef is what gives context edges map specs and
        constant-licensed factors for free."""
        ctx = load_package(_write(DOSING_TOML)).contexts[0]
        self.assertEqual(len(ctx.edges), 1)
        self.assertIsInstance(ctx.edges[0], EdgeDef)
        self.assertEqual(ctx.edges[0].src, "dose_unit")
        self.assertEqual(ctx.edges[0].dst, "gram")

    def test_a_constant_licensed_factor_is_resolved(self):
        """`factor = "k_d"` becomes the declared constant's value."""
        ctx = load_package(_write(DOSING_TOML)).contexts[0]
        self.assertAlmostEqual(ctx.edges[0].factor, 0.25)

    def test_a_package_without_contexts_gets_an_empty_tuple(self):
        pkg = load_package(_write("""
[package]
name = "bare"
[[units]]
name = "widget"
dimension = "none"
"""))
        self.assertEqual(pkg.contexts, ())

    def test_a_context_without_a_name_is_refused(self):
        with self.assertRaises(PackageLoadError) as caught:
            load_package(_write("""
[package]
name = "nameless"
[[contexts]]
description = "no name here"
"""))
        self.assertIn("name", str(caught.exception))

    def test_an_explicit_map_spec_is_accepted(self):
        pkg = load_package(_write("""
[package]
name = "spectro-ish"
[[contexts]]
name = "inverse"
  [[contexts.edges]]
  src = "meter"
  dst = "hertz"
  map = { type = "reciprocal", a = 299792458.0 }
"""))
        edge = pkg.contexts[0].edges[0]
        self.assertIsNotNone(edge.map_spec)
        self.assertEqual(edge.map_spec["type"], "reciprocal")


class TestContextMaterialization(unittest.TestCase):
    def test_with_package_registers_the_context(self):
        pkg = load_package(_write(DOSING_TOML))
        graph = active_system().conversion_graph.with_package(pkg)
        self.assertIn("dosing-basis", graph._contexts)
        self.assertIsInstance(graph._contexts["dosing-basis"], ConversionContext)

    def test_materialized_edges_carry_the_resolved_map(self):
        pkg = load_package(_write(DOSING_TOML))
        graph = active_system().conversion_graph.with_package(pkg)
        edge = graph._contexts["dosing-basis"].edges[0]
        self.assertIsInstance(edge.map, LinearMap)
        self.assertAlmostEqual(edge.map.a, 0.25)

    def test_an_explicit_map_spec_materializes(self):
        pkg = load_package(_write("""
[package]
name = "spectro-ish"
[[contexts]]
name = "inverse"
  [[contexts.edges]]
  src = "meter"
  dst = "hertz"
  map = { type = "reciprocal", a = 299792458.0 }
"""))
        graph = active_system().conversion_graph.with_package(pkg)
        self.assertIsInstance(graph._contexts["inverse"].edges[0].map, ReciprocalMap)

    def test_registration_does_not_insert_the_edge(self):
        """The whole point of a context. Loading the package must not make
        the conversion unconditionally available."""
        pkg = load_package(_write(DOSING_TOML))
        graph = active_system().conversion_graph.with_package(pkg)
        with using_conversion_graph(graph):
            src, dst = parse_unit("dose_unit"), parse_unit("gram")
            with self.assertRaises(DimensionMismatch):
                graph.convert(src=src, dst=dst)

    def test_activating_the_context_makes_it_convert(self):
        pkg = load_package(_write(DOSING_TOML))
        graph = active_system().conversion_graph.with_package(pkg)
        with using_conversion_graph(graph):
            src, dst = parse_unit("dose_unit"), parse_unit("gram")
            with using_context(graph._contexts["dosing-basis"]) as scoped:
                mapping = scoped.convert(src=src, dst=dst)
                self.assertAlmostEqual(mapping(4), 1.0)

    def test_an_unresolvable_endpoint_is_refused_by_name(self):
        pkg = load_package(_write("""
[package]
name = "broken"
[[contexts]]
name = "bad"
  [[contexts.edges]]
  src = "no_such_unit_xyz"
  dst = "gram"
  factor = 1.0
"""))
        with self.assertRaises(PackageLoadError) as caught:
            active_system().conversion_graph.with_package(pkg)
        message = str(caught.exception)
        self.assertIn("no_such_unit_xyz", message)
        self.assertIn("bad", message)

    def test_contexts_register_after_units_and_constants(self):
        """Ordering matters: an endpoint or factor may name something the
        package itself introduces, so both must already exist."""
        pkg = load_package(_write(DOSING_TOML))
        graph = active_system().conversion_graph.with_package(pkg)
        # The endpoint is a package unit and the factor a package constant;
        # both resolved, so registration ran last.
        edge = graph._contexts["dosing-basis"].edges[0]
        self.assertEqual(edge.src.name, "dose_unit")
        self.assertAlmostEqual(edge.map.a, 0.25)

    def test_the_source_graph_is_not_mutated(self):
        pkg = load_package(_write(DOSING_TOML))
        base = active_system().conversion_graph
        before = set(base._contexts)
        base.with_package(pkg)
        self.assertEqual(set(base._contexts), before)


class TestContextDefDirectly(unittest.TestCase):
    """ContextDef is constructible in Python, not only via TOML."""

    def test_defaults(self):
        ctx = ContextDef(name="empty")
        self.assertEqual(ctx.edges, ())
        self.assertEqual(ctx.description, "")

    def test_materialize_returns_a_conversion_context(self):
        ctx = ContextDef(
            name="hand-built",
            edges=(EdgeDef(src="meter", dst="hertz", factor=2.0),),
            description="constructed in Python",
        )
        materialized = ctx.materialize(active_system().conversion_graph)
        self.assertIsInstance(materialized, ConversionContext)
        self.assertEqual(materialized.name, "hand-built")
        self.assertEqual(materialized.description, "constructed in Python")
        self.assertEqual(len(materialized.edges), 1)

    def test_a_package_can_be_built_without_touching_toml(self):
        pkg = UnitPackage(
            name="programmatic",
            contexts=(
                ContextDef(
                    name="p",
                    edges=(EdgeDef(src="meter", dst="hertz", factor=2.0),),
                ),
            ),
        )
        graph = active_system().conversion_graph.with_package(pkg)
        self.assertIn("p", graph._contexts)


if __name__ == "__main__":
    unittest.main()

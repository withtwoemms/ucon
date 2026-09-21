# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for ``ConversionContext.contingent``.

A context edge encodes either a **definitional** relation — `spectroscopy`
and `boltzmann` are licensed by c, h, and k_B, exact by SI — or a
**contingent** one, a dated table that could have been otherwise.

Composing definitional edges derives a fact. Composing edges from two
different *contingent* contexts invents a figure neither table published: it
cannot be cited, will not match a directly quoted rate, and carries no date
of its own. The rule this pins:

    A path may draw on at most one contingent context.
    Definitional contexts and ordinary edges are unrestricted.

Composition *within* one contingent context is deliberately allowed — it is
what ADR 011's star-topology convention relies on, where a rate package
quotes every currency against one base and the cross-rates are derived.
"""
import unittest

from ucon import (
    ContingentCompositionRefused,
    Number,
    Unit,
    units as U,
)
from ucon.contexts import (
    ContextEdge,
    ConversionContext,
    boltzmann,
    spectroscopy,
    using_context,
)
from ucon.conversion import using_conversion_graph
from ucon.dimension import all_dimensions
from ucon.maps import LinearMap
from ucon.system import active_system

COUNT = next(d for d in all_dimensions() if str(d) == "Dimension(count)")


def _money_graph():
    """A graph with three currency units registered, no rate edges."""
    usd = Unit(name="USD", dimension=COUNT)
    eur = Unit(name="EUR", dimension=COUNT)
    gbp = Unit(name="GBP", dimension=COUNT)
    graph = active_system().conversion_graph.copy()
    for unit in (usd, eur, gbp):
        graph.register_unit(unit)
    return graph, usd, eur, gbp


def _tariff(usd) -> ConversionContext:
    """A dated energy price. Contingent: it could have been otherwise."""
    return ConversionContext(
        name="tariff-2026-09",
        contingent=True,
        edges=(ContextEdge(src=U.joule, dst=usd, map=LinearMap(8.3e-8)),),
    )


def _fx(usd, eur, gbp) -> ConversionContext:
    """A dated rate table, star topology: everything against USD."""
    return ConversionContext(
        name="fx-2026-09-10",
        contingent=True,
        edges=(
            ContextEdge(src=usd, dst=eur, map=LinearMap(0.9214)),
            ContextEdge(src=usd, dst=gbp, map=LinearMap(0.7891)),
        ),
    )


class TestDefaultIsDefinitional(unittest.TestCase):
    def test_contingent_defaults_false(self):
        """Existing contexts keep composing; nothing shipped changes."""
        self.assertFalse(spectroscopy.contingent)
        self.assertFalse(boltzmann.contingent)
        self.assertFalse(ConversionContext(name="x", edges=()).contingent)

    def test_definitional_edges_chain_within_a_context(self):
        """`meter -> reciprocal_meter` is not declared; it composes through
        `joule`. This worked before the flag and must keep working."""
        declared = {
            (getattr(e.src, "name", None), getattr(e.dst, "name", None))
            for e in spectroscopy.edges
        }
        self.assertNotIn(("meter", "reciprocal_meter"), declared)
        with using_context(spectroscopy) as graph:
            self.assertIsNotNone(
                graph.convert(src=U.meter, dst=U.reciprocal_meter)
            )

    def test_definitional_edges_chain_across_contexts(self):
        """Photon wavelength to equivalent temperature, via two exact
        licenses. Sound because neither is dated."""
        with using_context(spectroscopy, boltzmann) as graph:
            self.assertIsNotNone(graph.convert(src=U.meter, dst=U.kelvin))


class TestOneContingentContextComposes(unittest.TestCase):
    def test_a_single_contingent_edge_resolves(self):
        graph, usd, _, _ = _money_graph()
        with using_conversion_graph(graph), using_context(_tariff(usd)):
            self.assertAlmostEqual(
                Number(1, U.joule).to(usd).quantity, 8.3e-8
            )

    def test_cross_rates_derive_through_the_base(self):
        """ADR 011's star topology: EUR -> GBP is not declared, and must be
        derived through USD. Both hops come from one dated table."""
        graph, usd, eur, gbp = _money_graph()
        fx = _fx(usd, eur, gbp)
        declared = {(e.src.name, e.dst.name) for e in fx.edges}
        self.assertNotIn(("EUR", "GBP"), declared)

        with using_conversion_graph(graph), using_context(fx):
            result = Number(1, eur).to(gbp)
        self.assertAlmostEqual(result.quantity, 0.7891 / 0.9214, places=9)

    def test_a_definitional_context_may_feed_a_contingent_one(self):
        """One dated table in the path, so the date is well defined."""
        graph, usd, _, _ = _money_graph()
        with using_conversion_graph(graph), using_context(
            spectroscopy, _tariff(usd)
        ):
            self.assertIsNotNone(Number(1, U.meter).to(usd))


class TestTwoContingentContextsRefuse(unittest.TestCase):
    def test_chaining_two_dated_tables_is_refused(self):
        """A tariff plus an FX rate would yield a EUR energy price nobody
        quoted. Reachable before this change."""
        graph, usd, eur, gbp = _money_graph()
        with using_conversion_graph(graph), using_context(
            _tariff(usd), _fx(usd, eur, gbp)
        ):
            with self.assertRaises(ContingentCompositionRefused):
                Number(1, U.joule).to(eur)

    def test_the_refusal_names_both_tables(self):
        graph, usd, eur, gbp = _money_graph()
        with using_conversion_graph(graph), using_context(
            _tariff(usd), _fx(usd, eur, gbp)
        ):
            with self.assertRaises(ContingentCompositionRefused) as caught:
                Number(1, U.joule).to(eur)

        error = caught.exception
        self.assertEqual(
            set(error.contexts), {"tariff-2026-09", "fx-2026-09-10"}
        )
        message = str(error)
        self.assertIn("tariff-2026-09", message)
        self.assertIn("fx-2026-09-10", message)
        self.assertIn("dated", message)

    def test_each_table_alone_still_resolves_its_own_edges(self):
        """The refusal is about mixing, not about either table."""
        graph, usd, eur, gbp = _money_graph()
        with using_conversion_graph(graph), using_context(_tariff(usd)):
            self.assertIsNotNone(Number(1, U.joule).to(usd))
        with using_conversion_graph(graph), using_context(_fx(usd, eur, gbp)):
            self.assertIsNotNone(Number(1, usd).to(eur))

    def test_refusal_is_distinct_from_no_path(self):
        """A declined path and an absent one are different facts, so they
        are different exceptions."""
        from ucon.conversion import ConversionNotFound

        graph, usd, eur, gbp = _money_graph()
        # No context at all: genuinely unreachable.
        with using_conversion_graph(graph):
            with self.assertRaises((ConversionNotFound, Exception)) as caught:
                Number(1, U.joule).to(eur)
            self.assertNotIsInstance(
                caught.exception, ContingentCompositionRefused
            )


class TestProvenanceBookkeeping(unittest.TestCase):
    def test_definitional_contexts_record_nothing(self):
        """No attribution means no restriction, and no cost when unused."""
        with using_context(spectroscopy) as graph:
            self.assertEqual(graph._contingent_edges, {})

    def test_contingent_contexts_record_both_directions(self):
        """The inverse edge is inserted too, so it needs the same license."""
        graph, usd, eur, gbp = _money_graph()
        with using_conversion_graph(graph), using_context(_fx(usd, eur, gbp)) as scoped:
            self.assertEqual(scoped._contingent_edges[(usd, eur)], "fx-2026-09-10")
            self.assertEqual(scoped._contingent_edges[(eur, usd)], "fx-2026-09-10")

    def test_copy_carries_provenance(self):
        graph, usd, eur, gbp = _money_graph()
        with using_conversion_graph(graph), using_context(_fx(usd, eur, gbp)) as scoped:
            duplicate = scoped.copy()
        self.assertEqual(duplicate._contingent_edges, scoped._contingent_edges)


if __name__ == "__main__":
    unittest.main()

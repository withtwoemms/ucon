# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""Path resolution through composite (UnitProduct) edge endpoints (#280).

A package may bind a unit to a composite SI expression (edge dst =
"meter^3"). Such product edges were invisible to unit-level BFS, so an
edge to ``meter^3`` was unreachable from ``liter`` even though the direct
``meter^3 → liter`` conversion succeeded: one hop worked, two hops through
the composite node did not. The fix unifies a product node with any
registered unit sharing its base-form signature (same factors, prefactor
ratio as the map), and falls back from unit-level BFS into product space.

Narrow by design: only ``ConversionNotFound`` outcomes may become
successes. ``__eq__`` across the Unit/UnitProduct boundary is untouched
(full identity unification is scheduled for the next major).
"""

import unittest

from ucon import Number, units
from ucon.core import Unit, UnitProduct
from ucon.dimension import Dimension
from ucon.graph import (
    ConversionNotFound,
    get_default_graph,
    using_conversion_graph,
)
from ucon.maps import LinearMap
from ucon.resolver import parse_unit

US_GALLON_M3 = 0.003785411784  # 231 in³, exact


class TestCompositeEndpointPaths(unittest.TestCase):
    """The issue-#280 reproduction: an edge bound to meter^3."""

    def setUp(self):
        self.graph = get_default_graph().copy()
        self.gallon = Unit(
            name='us_gallon', dimension=Dimension.volume, aliases=('us_gal',))
        self.graph.register_unit(self.gallon)
        self.m3 = parse_unit('meter^3')
        self.graph.add_edge(
            src=self.gallon, dst=self.m3, map=LinearMap(US_GALLON_M3))

    def test_edge_to_composite_still_converts_directly(self):
        with using_conversion_graph(self.graph):
            result = Number(1, self.gallon).to(self.m3)
        self.assertAlmostEqual(result.quantity, US_GALLON_M3, places=15)

    def test_path_through_composite_reaches_named_unit(self):
        """us_gallon → meter^3 → liter: the previously-failing two-hop path."""
        with using_conversion_graph(self.graph):
            result = Number(1, self.gallon).to(units.liter)
        self.assertAlmostEqual(result.quantity, US_GALLON_M3 * 1000, places=12)

    def test_inverse_path_from_named_unit(self):
        with using_conversion_graph(self.graph):
            result = Number(US_GALLON_M3 * 1000, units.liter).to(self.gallon)
        self.assertAlmostEqual(result.quantity, 1.0, places=12)

    def test_direct_product_conversion_unchanged(self):
        """Regression: the one-hop base-form path that always worked."""
        with using_conversion_graph(self.graph):
            result = Number(1, self.m3).to(units.liter)
        self.assertAlmostEqual(result.quantity, 1000.0, places=12)

    def test_equality_untouched(self):
        """The narrow fix does not change __eq__ across the type boundary."""
        self.assertFalse(self.m3 == units.liter)
        self.assertTrue(self.m3.dimension == units.liter.dimension)

    def test_unreachable_pair_still_refuses(self):
        """Only failures become successes: a genuinely unconnected unit
        still raises ConversionNotFound."""
        orphan = Unit(
            name='orphan_vol', dimension=Dimension.volume, aliases=('ov',))
        self.graph.register_unit(orphan)
        with using_conversion_graph(self.graph):
            with self.assertRaises(ConversionNotFound):
                Number(1, orphan).to(units.liter)

    def test_refusal_preserves_unit_level_message(self):
        """When both searches fail, the original unit-level error is
        re-raised — not the product-space one."""
        orphan = Unit(
            name='orphan_vol2', dimension=Dimension.volume, aliases=('ov2',))
        self.graph.register_unit(orphan)
        with using_conversion_graph(self.graph):
            with self.assertRaises(ConversionNotFound) as ctx:
                Number(1, orphan).to(units.liter)
        self.assertIn('No path from', str(ctx.exception))
        self.assertNotIn('No product path', str(ctx.exception))

    def test_dimension_mismatch_not_swallowed_by_fallback(self):
        """The fallback fires only on ConversionNotFound; dimension errors
        propagate untouched."""
        from ucon.graph import DimensionMismatch
        with using_conversion_graph(self.graph):
            with self.assertRaises(DimensionMismatch):
                self.graph.convert(src=self.gallon, dst=units.kilogram)

    def test_fallback_result_is_cached(self):
        """A conversion found via the product-space fallback is cached:
        the second lookup returns the same Map object."""
        with using_conversion_graph(self.graph):
            first = self.graph.convert(src=self.gallon, dst=units.liter)
            second = self.graph.convert(src=self.gallon, dst=units.liter)
        self.assertIs(first, second)

    def test_three_hop_path_mixing_all_edge_kinds(self):
        """barrel → us_gallon (unit edge) → meter³ (product edge) → liter
        (base-form sibling): the search composes all three link kinds."""
        barrel = Unit(
            name='oil_barrel', dimension=Dimension.volume, aliases=('bbl',))
        self.graph.register_unit(barrel)
        self.graph.add_edge(src=barrel, dst=self.gallon, map=LinearMap(42))
        with using_conversion_graph(self.graph):
            result = Number(1, barrel).to(units.liter)
        self.assertAlmostEqual(
            result.quantity, 42 * US_GALLON_M3 * 1000, places=9)

    def test_search_continues_past_non_target_siblings(self):
        """The target sits one unit-edge beyond a sibling, so every sibling
        of meter³ is a non-terminal expansion the search must queue and
        continue through: us_gallon → meter³ → sibling → unit edge → dst."""
        beyond = Unit(
            name='beyond_liter', dimension=Dimension.volume, aliases=('byl',))
        self.graph.register_unit(beyond)
        self.graph.add_edge(src=units.liter, dst=beyond, map=LinearMap(2.0))
        with using_conversion_graph(self.graph):
            result = Number(1, self.gallon).to(beyond)
        self.assertAlmostEqual(
            result.quantity, US_GALLON_M3 * 1000 * 2.0, places=9)

    def test_sibling_link_serves_composites_without_product_edges(self):
        """meter³ happens to have a catalog product edge to liter, so the
        original reproduction resolves through product edges alone. A
        composite with NO catalog product edge — kilometer³ — is reachable
        only through the base-form sibling link; this pins the sibling
        mechanism end-to-end."""
        km3 = parse_unit('kilometer^3')
        vast = Unit(
            name='vast_vol', dimension=Dimension.volume, aliases=('vv',))
        self.graph.register_unit(vast)
        self.graph.add_edge(src=vast, dst=km3, map=LinearMap(0.5))
        with using_conversion_graph(self.graph):
            result = Number(1, vast).to(units.liter)
        # 0.5 km³ = 0.5e9 m³ = 0.5e12 L
        self.assertAlmostEqual(result.quantity / 0.5e12, 1.0, places=9)

    def test_bfs_direct_product_edge_short_circuit(self):
        """_bfs_product_path returns a direct product edge without search."""
        direct = self.graph._bfs_product_path(
            src=UnitProduct.from_unit(self.gallon), dst=self.m3)
        self.assertAlmostEqual(direct(1.0), US_GALLON_M3, places=15)

    def test_unreconstructable_product_node_degrades_gracefully(self):
        """A product edge whose endpoint contains an unregistered unit
        yields a node the search cannot expand further; the search skips
        it and refuses rather than crashing."""
        hidden = Unit(
            name='hidden_vol', dimension=Dimension.volume, aliases=('hv',))
        # deliberately NOT registered in the name registry
        start = Unit(
            name='start_vol', dimension=Dimension.volume, aliases=('sv',))
        self.graph.register_unit(start)
        self.graph.add_edge(
            src=start, dst=UnitProduct.from_unit(hidden), map=LinearMap(3.0))
        with using_conversion_graph(self.graph):
            with self.assertRaises(ConversionNotFound):
                Number(1, start).to(units.liter)


class TestBaseFormSiblings(unittest.TestCase):
    """The unification primitive: product ↔ same-signature unit."""

    def test_meter_cubed_sibling_is_liter(self):
        graph = get_default_graph().copy()
        m3 = parse_unit('meter^3')
        siblings = dict(graph._base_form_siblings(m3))
        self.assertIn(units.liter, siblings)
        self.assertAlmostEqual(siblings[units.liter](1.0), 1000.0, places=9)

    def test_product_from_key_round_trips(self):
        graph = get_default_graph().copy()
        m3 = parse_unit('meter^3')
        key = graph._product_key(m3)
        rebuilt = graph._product_from_key(key)
        self.assertIsNotNone(rebuilt)
        self.assertEqual(graph._product_key(rebuilt), key)

    def test_product_from_key_unknown_unit_returns_none(self):
        """A key naming a unit absent from the registry cannot be
        reconstructed — the search degrades gracefully instead of raising."""
        graph = get_default_graph().copy()
        m3 = parse_unit('meter^3')
        (name, dim, scale, exp), = graph._product_key(m3)
        fake_key = (('not_a_registered_unit', dim, scale, exp),)
        self.assertIsNone(graph._product_from_key(fake_key))

    def test_siblings_of_undecomposable_product_is_empty(self):
        """A product containing a base_form-less unit cannot decompose;
        the sibling generator yields nothing rather than raising."""
        graph = get_default_graph().copy()
        bare = Unit(
            name='bare_volume', dimension=Dimension.volume, aliases=('bv',))
        graph.register_unit(bare)
        product = UnitProduct.from_unit(bare)
        self.assertEqual(list(graph._base_form_siblings(product)), [])

    def test_siblings_guard_on_malformed_product(self):
        """The generator's decomposition guard: an object whose
        to_base_form raises yields nothing (parity with the identical
        guard in _convert_via_base_form)."""
        graph = get_default_graph().copy()

        class _Broken:
            def to_base_form(self):
                raise TypeError("malformed")

        self.assertEqual(list(graph._base_form_siblings(_Broken())), [])

    def test_scaled_product_sibling_ratio(self):
        """kilometer³ decomposes with prefactor 1e9; the liter sibling map
        must carry the full ×1e12 ratio."""
        graph = get_default_graph().copy()
        km3 = parse_unit('kilometer^3')
        siblings = dict(graph._base_form_siblings(km3))
        self.assertIn(units.liter, siblings)
        self.assertAlmostEqual(
            siblings[units.liter](1.0) / 1e12, 1.0, places=9)


if __name__ == '__main__':
    unittest.main()

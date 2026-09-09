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


if __name__ == '__main__':
    unittest.main()

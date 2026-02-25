# (c) 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for ConversionGraph integration with BasisTransform.

Verifies cross-basis edge handling, RebasedUnit creation,
and conversion paths that span dimensional bases.
"""

import unittest
from fractions import Fraction

from ucon.basis import Basis, BasisComponent, BasisTransform
from ucon.core import RebasedUnit, Unit
from ucon.graph import ConversionGraph
from ucon.maps import LinearMap
from ucon import Dimension, units
from ucon.bases import SI


class TestGraphAddEdgeWithBasisTransform(unittest.TestCase):
    """Test add_edge with basis_transform parameter."""

    def setUp(self):
        # Create a simple identity transform within SI basis
        # This is used to mark an edge as cross-basis even though
        # the units are in the same dimensional system
        self.bt = BasisTransform.identity(SI)
        self.graph = ConversionGraph()

    def test_add_edge_with_basis_transform(self):
        # foot -> meter with basis transform
        self.graph.add_edge(
            src=units.foot,
            dst=units.meter,
            map=LinearMap(0.3048),
            basis_transform=self.bt,
        )
        # Verify the rebased unit was created
        self.assertIn(units.foot, self.graph._rebased)
        rebased = self.graph._rebased[units.foot]
        self.assertIsInstance(rebased, RebasedUnit)
        self.assertEqual(rebased.original, units.foot)
        self.assertEqual(rebased.rebased_dimension, Dimension.length)

    def test_add_edge_without_basis_transform_requires_same_dimension(self):
        # foot and meter both have Dimension.length, so this should work
        self.graph.add_edge(
            src=units.foot,
            dst=units.meter,
            map=LinearMap(0.3048),
        )
        # Verify no rebased unit was created (normal edge)
        self.assertNotIn(units.foot, self.graph._rebased)


class TestGraphConvertWithBasisTransform(unittest.TestCase):
    """Test convert() with cross-basis edges."""

    def setUp(self):
        self.bt = BasisTransform.identity(SI)
        self.graph = ConversionGraph()
        # Add edge with basis transform
        self.graph.add_edge(
            src=units.foot,
            dst=units.meter,
            map=LinearMap(0.3048),
            basis_transform=self.bt,
        )

    def test_convert_uses_rebased_path(self):
        # Convert via the rebased edge
        map = self.graph.convert(src=units.foot, dst=units.meter)
        # 1 foot = 0.3048 meters
        self.assertAlmostEqual(map(1), 0.3048, places=5)

    def test_convert_inverse_works(self):
        # The inverse edge should also be available
        map = self.graph.convert(src=units.meter, dst=units.foot)
        # 1 meter ≈ 3.28084 feet
        self.assertAlmostEqual(map(1), 1/0.3048, places=5)


class TestGraphConnectSystems(unittest.TestCase):
    """Test connect_systems convenience method."""

    def setUp(self):
        self.bt = BasisTransform.identity(SI)
        self.graph = ConversionGraph()

    def test_connect_systems_bulk_adds_edges(self):
        self.graph.connect_systems(
            basis_transform=self.bt,
            edges={
                (units.foot, units.meter): LinearMap(0.3048),
                (units.pound, units.kilogram): LinearMap(0.453592),
            }
        )
        # Both should be converted
        length_map = self.graph.convert(src=units.foot, dst=units.meter)
        self.assertAlmostEqual(length_map(1), 0.3048, places=5)

        mass_map = self.graph.convert(src=units.pound, dst=units.kilogram)
        self.assertAlmostEqual(mass_map(1), 0.453592, places=5)


class TestGraphListTransforms(unittest.TestCase):
    """Test introspection methods for transforms."""

    def setUp(self):
        self.bt = BasisTransform.identity(SI)
        self.graph = ConversionGraph()
        self.graph.add_edge(
            src=units.foot,
            dst=units.meter,
            map=LinearMap(0.3048),
            basis_transform=self.bt,
        )

    def test_list_rebased_units(self):
        rebased = self.graph.list_rebased_units()
        self.assertEqual(len(rebased), 1)
        self.assertIn(units.foot, rebased)
        self.assertIsInstance(rebased[units.foot], RebasedUnit)

    def test_list_transforms(self):
        transforms = self.graph.list_transforms()
        self.assertEqual(len(transforms), 1)
        self.assertEqual(transforms[0], self.bt)

    def test_edges_for_transform(self):
        edges = self.graph.edges_for_transform(self.bt)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0], (units.foot, units.meter))

    def test_list_transforms_multiple(self):
        # Add another edge with a different transform instance
        # (same matrix, but different object)
        bt2 = BasisTransform.identity(SI)
        self.graph.add_edge(
            src=units.pound,
            dst=units.kilogram,
            map=LinearMap(0.453592),
            basis_transform=bt2,
        )
        transforms = self.graph.list_transforms()
        self.assertEqual(len(transforms), 2)


if __name__ == "__main__":
    unittest.main()

# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for graph-local unit name resolution (v0.7.3).

Verifies that:
- Units registered on a graph are resolvable within using_graph()
- Graph-local units are isolated from other graphs
- Global registry provides fallback
- Graph copy preserves name registries
"""
import unittest

from ucon import (
    Unit,
    get_default_graph,
    get_unit_by_name,
    using_graph,
)
from ucon import Dimension
from ucon.graph import ConversionGraph, _get_parsing_graph
from ucon.units import UnknownUnitError


class TestGraphLocalResolution(unittest.TestCase):
    """Test graph-local unit name resolution."""

    def test_register_unit_basic(self):
        """register_unit() adds unit to graph's name registry."""
        graph = ConversionGraph()
        custom = Unit(name='slug', dimension=Dimension.mass, aliases=('slug',))

        graph.register_unit(custom)

        self.assertIn('slug', graph._name_registry)
        self.assertIn('slug', graph._name_registry_cs)
        self.assertEqual(graph._name_registry['slug'], custom)

    def test_register_unit_with_aliases(self):
        """register_unit() registers aliases in both registries."""
        graph = ConversionGraph()
        custom = Unit(
            name='nautical_mile',
            dimension=Dimension.length,
            aliases=('nmi', 'NM'),
        )

        graph.register_unit(custom)

        # Aliases in case-sensitive registry
        self.assertIn('nmi', graph._name_registry_cs)
        self.assertIn('NM', graph._name_registry_cs)
        # Name in case-insensitive registry
        self.assertIn('nautical_mile', graph._name_registry)
        # Shorthand (first alias) in case-sensitive registry
        self.assertIn(custom.shorthand, graph._name_registry_cs)

    def test_resolve_unit_case_sensitive_first(self):
        """resolve_unit() checks case-sensitive registry first."""
        graph = ConversionGraph()
        custom = Unit(name='MyUnit', dimension=Dimension.length, aliases=('MU',))

        graph.register_unit(custom)

        # Case-sensitive match
        result = graph.resolve_unit('MU')
        self.assertIsNotNone(result)
        self.assertEqual(result[0], custom)

    def test_resolve_unit_case_sensitive_only(self):
        """resolve_unit() only matches case-sensitively."""
        graph = ConversionGraph()
        custom = Unit(name='slug', dimension=Dimension.mass, aliases=('slug',))

        graph.register_unit(custom)

        # Exact case matches
        self.assertIsNotNone(graph.resolve_unit('slug'))

        # Different case returns None — lets global resolver handle it
        # (prevents 'GB' matching 'Gb' and shadowing giga-byte)
        self.assertIsNone(graph.resolve_unit('SLUG'))
        self.assertIsNone(graph.resolve_unit('Slug'))

    def test_resolve_unit_not_found(self):
        """resolve_unit() returns None for unknown units."""
        graph = ConversionGraph()
        result = graph.resolve_unit('nonexistent')
        self.assertIsNone(result)

    def test_using_graph_scopes_parsing(self):
        """using_graph() makes graph-local units resolvable via get_unit_by_name()."""
        custom = Unit(name='zorkmid', dimension=Dimension.mass, aliases=('zk',))
        graph = get_default_graph().copy()
        graph.register_unit(custom)

        # Outside context, zorkmid is unknown
        with self.assertRaises(UnknownUnitError):
            get_unit_by_name('zorkmid')

        # Inside context, zorkmid resolves
        with using_graph(graph):
            resolved = get_unit_by_name('zorkmid')
            self.assertEqual(resolved, custom)

        # Outside context again, zorkmid is unknown
        with self.assertRaises(UnknownUnitError):
            get_unit_by_name('zorkmid')

    def test_graph_isolation(self):
        """Units registered on one graph are not visible in another."""
        custom = Unit(name='smoot', dimension=Dimension.length, aliases=('smoot',))

        graph_a = ConversionGraph()
        graph_b = ConversionGraph()

        graph_a.register_unit(custom)

        # Visible in graph_a
        self.assertIsNotNone(graph_a.resolve_unit('smoot'))

        # Not visible in graph_b
        self.assertIsNone(graph_b.resolve_unit('smoot'))

    def test_global_fallback(self):
        """Graph-local resolution falls back to global registry."""
        graph = get_default_graph().copy()

        with using_graph(graph):
            # Standard unit 'meter' should resolve via graph (which has standard units)
            resolved = get_unit_by_name('meter')
            self.assertEqual(resolved.name, 'meter')

    def test_graph_local_takes_precedence(self):
        """Graph-local unit takes precedence over global registry."""
        # Create a custom 'meter' (obviously you wouldn't do this in practice)
        custom_meter = Unit(name='meter', dimension=Dimension.time)  # Wrong dimension!
        graph = ConversionGraph()
        graph.register_unit(custom_meter)

        with using_graph(graph):
            resolved = get_unit_by_name('meter')
            # Should get the graph-local custom_meter, not the global one
            self.assertEqual(resolved.dimension, Dimension.time)

    def test_copy_preserves_name_registry(self):
        """graph.copy() preserves name registries."""
        custom = Unit(name='slug', dimension=Dimension.mass, aliases=('slug',))
        original = ConversionGraph()
        original.register_unit(custom)

        copied = original.copy()

        # Both should have the unit
        self.assertIsNotNone(original.resolve_unit('slug'))
        self.assertIsNotNone(copied.resolve_unit('slug'))

    def test_copy_is_independent(self):
        """Changes to copied graph don't affect original."""
        original = ConversionGraph()
        copied = original.copy()

        # Add unit to copy only
        custom = Unit(name='slug', dimension=Dimension.mass, aliases=('slug',))
        copied.register_unit(custom)

        # Original should NOT have the unit
        self.assertIsNone(original.resolve_unit('slug'))
        # Copy should have it
        self.assertIsNotNone(copied.resolve_unit('slug'))

    def test_default_graph_has_standard_units(self):
        """Default graph has all standard units registered."""
        graph = get_default_graph()

        # Check a few standard units
        self.assertIsNotNone(graph.resolve_unit('meter'))
        self.assertIsNotNone(graph.resolve_unit('kilogram'))
        self.assertIsNotNone(graph.resolve_unit('second'))
        self.assertIsNotNone(graph.resolve_unit('ampere'))

    def test__get_parsing_graph_outside_context(self):
        """_get_parsing_graph() returns None outside using_graph()."""
        result = _get_parsing_graph()
        self.assertIsNone(result)

    def test__get_parsing_graph_inside_context(self):
        """_get_parsing_graph() returns the graph inside using_graph()."""
        graph = ConversionGraph()

        with using_graph(graph):
            result = _get_parsing_graph()
            self.assertIs(result, graph)

    def test_nested_using_graph(self):
        """Nested using_graph() contexts work correctly."""
        outer_graph = ConversionGraph()
        inner_graph = ConversionGraph()

        outer_unit = Unit(name='outer_unit', dimension=Dimension.mass)
        inner_unit = Unit(name='inner_unit', dimension=Dimension.length)

        outer_graph.register_unit(outer_unit)
        inner_graph.register_unit(inner_unit)

        with using_graph(outer_graph):
            self.assertIs(_get_parsing_graph(), outer_graph)
            self.assertIsNotNone(outer_graph.resolve_unit('outer_unit'))

            with using_graph(inner_graph):
                self.assertIs(_get_parsing_graph(), inner_graph)
                self.assertIsNotNone(inner_graph.resolve_unit('inner_unit'))
                # Outer unit not visible in inner graph
                self.assertIsNone(inner_graph.resolve_unit('outer_unit'))

            # Back to outer graph
            self.assertIs(_get_parsing_graph(), outer_graph)

        # Outside both contexts
        self.assertIsNone(_get_parsing_graph())


class TestScalePrefixShadowing(unittest.TestCase):
    """Regression tests: graph-local case-insensitive matching must not
    shadow scale-prefix decomposition (e.g. 'GB' ≠ 'Gb', 'nm' ≠ 'nmi')."""

    def test_GB_resolves_to_gigabyte_not_gilbert(self):
        """'GB' is giga-byte (information), not gilbert (Gb, cgs_emu_current)."""
        graph = get_default_graph()

        with using_graph(graph):
            unit = get_unit_by_name('GB')
            self.assertEqual(unit.dimension.name, 'information',
                             f"'GB' resolved to {unit.dimension.name!r} instead of 'information'")

    def test_Gb_still_resolves_to_gilbert(self):
        """'Gb' (case-sensitive) is gilbert — the fix must not break this."""
        graph = get_default_graph()

        with using_graph(graph):
            unit = get_unit_by_name('Gb')
            self.assertEqual(unit.dimension.name, 'cgs_emu_current')

    def test_nm_resolves_to_nanometer_not_nautical_mile(self):
        """'nm' is nano-meter (length via n+m), not nautical mile (alias NM)."""
        graph = get_default_graph()

        with using_graph(graph):
            unit = get_unit_by_name('nm')
            self.assertEqual(unit.dimension.name, 'length')
            # Verify it's nanometer (scaled), not nautical_mile
            # nautical_mile shorthand is 'nmi', nanometer shorthand is 'nm'
            shorthand = getattr(unit, 'shorthand', None) or str(unit)
            self.assertIn('nm', shorthand)
            self.assertNotIn('nmi', shorthand)

    def test_nmi_still_resolves_to_nautical_mile(self):
        """'nmi' (case-sensitive alias) is nautical mile — the fix must not break this."""
        graph = get_default_graph()

        with using_graph(graph):
            unit = get_unit_by_name('nmi')
            self.assertEqual(unit.name, 'nautical_mile')

    def test_NM_still_resolves_to_nautical_mile(self):
        """'NM' (case-sensitive alias) is nautical mile — the fix must not break this."""
        graph = get_default_graph()

        with using_graph(graph):
            unit = get_unit_by_name('NM')
            self.assertEqual(unit.name, 'nautical_mile')

    def test_MB_resolves_to_megabyte(self):
        """'MB' is mega-byte (information), not any CGS unit."""
        graph = get_default_graph()

        with using_graph(graph):
            unit = get_unit_by_name('MB')
            self.assertEqual(unit.dimension.name, 'information')

    def test_kB_resolves_to_kilobyte(self):
        """'kB' is kilo-byte (information)."""
        graph = get_default_graph()

        with using_graph(graph):
            unit = get_unit_by_name('kB')
            self.assertEqual(unit.dimension.name, 'information')


if __name__ == '__main__':
    unittest.main()

# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for ucon.packages module.

Verifies:
- UnitDef and EdgeDef dataclasses
- UnitPackage loading from TOML
- ConversionGraph.with_package() composition
"""
import tempfile
import unittest
from pathlib import Path

from tests.ucon import EXAMPLE_UNIT_EXTENSIONS_PATH
from ucon import (
    Dimension,
    get_default_graph,
    get_unit_by_name,
    load_package,
    using_graph,
    EdgeDef,
    PackageLoadError,
    UnitDef,
    UnitPackage,
)
from ucon.graph import ConversionGraph


class TestUnitDef(unittest.TestCase):
    """Test UnitDef dataclass."""

    def test_unit_def_creation(self):
        """UnitDef can be created with valid attributes."""
        unit_def = UnitDef(
            name='slug',
            dimension='mass',
            aliases=('slug',),
        )
        self.assertEqual(unit_def.name, 'slug')
        self.assertEqual(unit_def.dimension, 'mass')
        self.assertEqual(unit_def.aliases, ('slug',))

    def test_unit_def_materialize(self):
        """UnitDef.materialize() creates a Unit object."""
        unit_def = UnitDef(name='slug', dimension='mass', aliases=('slug',))
        unit = unit_def.materialize()

        self.assertEqual(unit.name, 'slug')
        self.assertEqual(unit.dimension, Dimension.mass)
        self.assertEqual(unit.aliases, ('slug',))

    def test_unit_def_invalid_dimension(self):
        """UnitDef.materialize() raises for invalid dimension."""
        unit_def = UnitDef(name='bad', dimension='nonexistent')

        with self.assertRaises(PackageLoadError) as ctx:
            unit_def.materialize()
        self.assertIn('nonexistent', str(ctx.exception))


class TestEdgeDef(unittest.TestCase):
    """Test EdgeDef dataclass."""

    def test_edge_def_creation(self):
        """EdgeDef can be created with valid attributes."""
        edge_def = EdgeDef(src='meter', dst='foot', factor=3.28084)
        self.assertEqual(edge_def.src, 'meter')
        self.assertEqual(edge_def.dst, 'foot')
        self.assertEqual(edge_def.factor, 3.28084)

    def test_edge_def_materialize(self):
        """EdgeDef.materialize() adds edge to graph."""
        graph = get_default_graph().copy()
        edge_def = EdgeDef(src='meter', dst='foot', factor=3.28084)

        # Edge already exists in default graph, but materialize should work
        edge_def.materialize(graph)

    def test_edge_def_unknown_src(self):
        """EdgeDef.materialize() raises for unknown source unit."""
        graph = ConversionGraph()
        edge_def = EdgeDef(src='nonexistent', dst='meter', factor=1.0)

        with self.assertRaises(PackageLoadError) as ctx:
            edge_def.materialize(graph)
        self.assertIn('nonexistent', str(ctx.exception))


class TestEdgeDefAffine(unittest.TestCase):
    """Test EdgeDef affine (offset) support."""

    def test_edge_def_creation_with_offset(self):
        """EdgeDef stores offset field."""
        edge_def = EdgeDef(src='celsius', dst='kelvin', factor=1.0, offset=273.15)
        self.assertEqual(edge_def.offset, 273.15)

    def test_edge_def_default_offset_zero(self):
        """EdgeDef defaults offset to 0.0 for backward compatibility."""
        edge_def = EdgeDef(src='meter', dst='foot', factor=3.28084)
        self.assertEqual(edge_def.offset, 0.0)

    def test_edge_def_materialize_affine(self):
        """EdgeDef.materialize() uses AffineMap when offset is non-zero."""
        from ucon.maps import AffineMap

        pkg = UnitPackage(
            name='test_affine',
            units=(UnitDef(name='rankine', dimension='temperature', aliases=('Ra',)),),
            edges=(EdgeDef(src='rankine', dst='kelvin', factor=5/9, offset=0.0),),
        )

        # Use a non-zero offset edge
        graph = get_default_graph().with_package(pkg)

        # Now add an affine edge manually via EdgeDef
        edge_def = EdgeDef(src='celsius', dst='kelvin', factor=1.0, offset=273.15)
        edge_def.materialize(graph)

        # Verify the map type on the graph edge
        with using_graph(graph):
            celsius = get_unit_by_name('celsius')
            kelvin = get_unit_by_name('kelvin')
            m = graph.convert(src=celsius, dst=kelvin)
            self.assertIsInstance(m, AffineMap)
            # 0°C → 273.15 K
            self.assertAlmostEqual(m(0), 273.15, places=2)
            # 100°C → 373.15 K
            self.assertAlmostEqual(m(100), 373.15, places=2)

    def test_load_package_with_affine_edge(self):
        """load_package() reads offset field from TOML."""
        toml_content = '''
[package]
name = "affine_test"
version = "1.0.0"

[[units]]
name = "custom_temp"
dimension = "temperature"
aliases = ["ct"]

[[edges]]
src = "custom_temp"
dst = "kelvin"
factor = 1.0
offset = 100.0
'''
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.toml', delete=False
        ) as f:
            f.write(toml_content)
            f.flush()
            path = Path(f.name)

        try:
            pkg = load_package(path)
            self.assertEqual(len(pkg.edges), 1)
            self.assertEqual(pkg.edges[0].offset, 100.0)
        finally:
            path.unlink()

    def test_with_package_affine_conversion(self):
        """End-to-end: load package with affine edge, convert through graph."""
        toml_content = '''
[package]
name = "affine_e2e"
version = "1.0.0"

[[units]]
name = "custom_temp"
dimension = "temperature"
aliases = ["ct"]

[[edges]]
src = "custom_temp"
dst = "kelvin"
factor = 1.0
offset = 100.0
'''
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.toml', delete=False
        ) as f:
            f.write(toml_content)
            f.flush()
            path = Path(f.name)

        try:
            pkg = load_package(path)
            graph = get_default_graph().with_package(pkg)

            with using_graph(graph):
                ct = get_unit_by_name('ct')
                kelvin = get_unit_by_name('kelvin')
                m = graph.convert(src=ct, dst=kelvin)
                # 0 ct → 100.0 K (factor=1.0, offset=100.0)
                self.assertAlmostEqual(m(0), 100.0, places=2)
                # 50 ct → 150.0 K
                self.assertAlmostEqual(m(50), 150.0, places=2)
        finally:
            path.unlink()


class TestUnitPackage(unittest.TestCase):
    """Test UnitPackage dataclass."""

    def test_unit_package_creation(self):
        """UnitPackage can be created with valid attributes."""
        pkg = UnitPackage(
            name='test',
            version='1.0.0',
            units=(UnitDef(name='slug', dimension='mass'),),
            edges=(EdgeDef(src='slug', dst='kilogram', factor=14.5939),),
        )
        self.assertEqual(pkg.name, 'test')
        self.assertEqual(len(pkg.units), 1)
        self.assertEqual(len(pkg.edges), 1)

    def test_unit_package_invalid_dimension_raises(self):
        """UnitPackage raises on invalid dimension in __post_init__."""
        with self.assertRaises(PackageLoadError) as ctx:
            UnitPackage(
                name='bad',
                units=(UnitDef(name='bad', dimension='nonexistent'),),
            )
        self.assertIn('nonexistent', str(ctx.exception))


class TestLoadPackage(unittest.TestCase):
    """Test load_package() function."""

    def test_load_valid_package(self):
        """load_package() parses valid TOML file."""
        toml_content = '''
[package]
name = "test"
version = "1.0.0"

[[units]]
name = "slug"
dimension = "mass"
aliases = ["slug"]

[[edges]]
src = "slug"
dst = "kilogram"
factor = 14.5939
'''
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.toml', delete=False
        ) as f:
            f.write(toml_content)
            f.flush()
            path = Path(f.name)

        try:
            pkg = load_package(path)
            self.assertEqual(pkg.name, 'test')
            self.assertEqual(pkg.version, '1.0.0')
            self.assertEqual(len(pkg.units), 1)
            self.assertEqual(len(pkg.edges), 1)
            self.assertEqual(pkg.units[0].name, 'slug')
        finally:
            path.unlink()

    def test_load_missing_file(self):
        """load_package() raises for missing file."""
        with self.assertRaises(PackageLoadError) as ctx:
            load_package('/nonexistent/path.toml')
        self.assertIn('not found', str(ctx.exception))

    def test_load_invalid_toml(self):
        """load_package() raises for invalid TOML."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.toml', delete=False
        ) as f:
            f.write('this is not [valid toml')
            f.flush()
            path = Path(f.name)

        try:
            with self.assertRaises(PackageLoadError) as ctx:
                load_package(path)
            self.assertIn('Invalid TOML', str(ctx.exception))
        finally:
            path.unlink()

    def test_load_aerospace_example(self):
        """load_package() loads the aerospace example."""
        example_path = EXAMPLE_UNIT_EXTENSIONS_PATH / 'aerospace.ucon.toml'
        if not example_path.exists():
            self.skipTest(f'aerospace.ucon.toml not found at {example_path}')

        pkg = load_package(example_path)
        self.assertEqual(pkg.name, 'aerospace')
        self.assertGreater(len(pkg.units), 0)
        self.assertGreater(len(pkg.edges), 0)


class TestWithPackage(unittest.TestCase):
    """Test ConversionGraph.with_package() method."""

    def test_with_package_registers_units(self):
        """with_package() registers package units in graph."""
        pkg = UnitPackage(
            name='test',
            units=(UnitDef(name='slug', dimension='mass', aliases=('slug',)),),
        )

        graph = get_default_graph().with_package(pkg)

        # Unit should be resolvable in the new graph
        with using_graph(graph):
            resolved = get_unit_by_name('slug')
            self.assertEqual(resolved.name, 'slug')

    def test_with_package_adds_edges(self):
        """with_package() adds conversion edges."""
        pkg = UnitPackage(
            name='test',
            units=(UnitDef(name='slug', dimension='mass', aliases=('slug',)),),
            edges=(EdgeDef(src='slug', dst='kilogram', factor=14.5939),),
        )

        graph = get_default_graph().with_package(pkg)

        # Conversion should work
        with using_graph(graph):
            slug = get_unit_by_name('slug')
            kg = get_unit_by_name('kilogram')
            m = graph.convert(src=slug, dst=kg)
            self.assertAlmostEqual(m(1), 14.5939, places=3)

    def test_with_package_does_not_modify_original(self):
        """with_package() returns new graph, original unchanged."""
        pkg = UnitPackage(
            name='test',
            units=(UnitDef(name='zorkmid', dimension='mass', aliases=('zk',)),),
        )

        original = get_default_graph()
        extended = original.with_package(pkg)

        # zorkmid should NOT be in original
        self.assertIsNone(original.resolve_unit('zorkmid'))

        # zorkmid should be in extended
        self.assertIsNotNone(extended.resolve_unit('zorkmid'))

    def test_with_package_composition(self):
        """Multiple with_package() calls compose correctly."""
        pkg1 = UnitPackage(
            name='pkg1',
            units=(UnitDef(name='unit1', dimension='mass'),),
        )
        pkg2 = UnitPackage(
            name='pkg2',
            units=(UnitDef(name='unit2', dimension='length'),),
        )

        graph = get_default_graph().with_package(pkg1).with_package(pkg2)

        # Both units should be resolvable
        self.assertIsNotNone(graph.resolve_unit('unit1'))
        self.assertIsNotNone(graph.resolve_unit('unit2'))

    def test_with_package_aerospace(self):
        """End-to-end test with aerospace package."""
        example_path = EXAMPLE_UNIT_EXTENSIONS_PATH / 'aerospace.ucon.toml'
        if not example_path.exists():
            self.skipTest(f'aerospace.ucon.toml not found at {example_path}')

        pkg = load_package(example_path)
        graph = get_default_graph().with_package(pkg)

        with using_graph(graph):
            # Test slug → kg conversion
            slug = get_unit_by_name('slug')
            kg = get_unit_by_name('kg')
            m = graph.convert(src=slug, dst=kg)
            self.assertAlmostEqual(m(1), 14.5939, places=3)

            # Test nautical mile → meter
            nmi = get_unit_by_name('nmi')
            meter = get_unit_by_name('m')
            m = graph.convert(src=nmi, dst=meter)
            self.assertAlmostEqual(m(1), 1852, places=0)


class TestParseFactorEdgeCases(unittest.TestCase):
    """Test _parse_factor edge cases."""

    def test_parse_factor_int(self):
        """_parse_factor handles plain int."""
        from ucon.packages import _parse_factor
        self.assertEqual(_parse_factor(42), 42.0)

    def test_parse_factor_float(self):
        """_parse_factor handles plain float."""
        from ucon.packages import _parse_factor
        self.assertEqual(_parse_factor(3.14), 3.14)

    def test_parse_factor_expression_division(self):
        """_parse_factor handles division expression."""
        from ucon.packages import _parse_factor
        result = _parse_factor("1852 / 3600")
        self.assertAlmostEqual(result, 1852 / 3600)

    def test_parse_factor_expression_multiplication(self):
        """_parse_factor handles multiplication expression."""
        from ucon.packages import _parse_factor
        result = _parse_factor("2 * 3")
        self.assertEqual(result, 6.0)

    def test_parse_factor_unary_negation(self):
        """_parse_factor handles unary negation: '-1.5'."""
        from ucon.packages import _parse_factor
        result = _parse_factor("-1.5")
        self.assertEqual(result, -1.5)

    def test_parse_factor_invalid_type_raises(self):
        """_parse_factor raises for non-numeric non-string."""
        from ucon.packages import _parse_factor
        with self.assertRaises(PackageLoadError):
            _parse_factor([1, 2, 3])

    def test_parse_factor_unsupported_op_raises(self):
        """_parse_factor raises for unsupported operator (addition)."""
        from ucon.packages import _parse_factor
        with self.assertRaises(PackageLoadError):
            _parse_factor("1 + 2")

    def test_parse_factor_syntax_error_raises(self):
        """_parse_factor raises for unparseable string."""
        from ucon.packages import _parse_factor
        with self.assertRaises(PackageLoadError):
            _parse_factor("not a number @#$")

    def test_parse_factor_variable_name_raises(self):
        """_parse_factor raises for variable names."""
        from ucon.packages import _parse_factor
        with self.assertRaises(PackageLoadError):
            _parse_factor("x * y")


class TestEdgeDefUnknownDst(unittest.TestCase):
    """Test EdgeDef.materialize() with unknown destination unit."""

    def test_unknown_dst_raises(self):
        """EdgeDef.materialize() raises for unknown destination unit."""
        graph = get_default_graph().copy()
        edge_def = EdgeDef(src='meter', dst='nonexistent_unit_xyz', factor=1.0)
        with self.assertRaises(PackageLoadError) as ctx:
            edge_def.materialize(graph)
        self.assertIn("destination", str(ctx.exception).lower())


class TestUnitDefShorthand(unittest.TestCase):
    """Test UnitDef shorthand field."""

    def test_shorthand_none_uses_first_alias(self):
        """When shorthand is None, Unit.shorthand is the first alias."""
        unit_def = UnitDef(name='nautical_mile', dimension='length', aliases=('nmi', 'NM'))
        unit = unit_def.materialize()
        self.assertEqual(unit.shorthand, 'nmi')

    def test_shorthand_explicit(self):
        """Explicit shorthand becomes Unit.shorthand (first alias)."""
        unit_def = UnitDef(
            name='nautical_mile', dimension='length',
            aliases=('NM',), shorthand='nmi',
        )
        unit = unit_def.materialize()
        self.assertEqual(unit.shorthand, 'nmi')
        self.assertIn('NM', unit.aliases)

    def test_shorthand_already_in_aliases(self):
        """Shorthand that duplicates an alias is not added twice."""
        unit_def = UnitDef(
            name='slug', dimension='mass',
            aliases=('slug',), shorthand='slug',
        )
        unit = unit_def.materialize()
        self.assertEqual(unit.aliases.count('slug'), 1)

    def test_shorthand_no_aliases(self):
        """Shorthand with empty aliases creates a single alias."""
        unit_def = UnitDef(name='slug', dimension='mass', shorthand='sl')
        unit = unit_def.materialize()
        self.assertEqual(unit.shorthand, 'sl')
        self.assertEqual(unit.aliases, ('sl',))

    def test_shorthand_from_toml(self):
        """load_package reads shorthand from TOML."""
        toml_content = '''
[package]
name = "shorthand_test"

[[units]]
name = "nautical_mile"
dimension = "length"
shorthand = "nmi"
aliases = ["NM"]

[[edges]]
src = "nautical_mile"
dst = "meter"
factor = 1852
'''
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.toml', delete=False
        ) as f:
            f.write(toml_content)
            f.flush()
            path = Path(f.name)

        try:
            pkg = load_package(path)
            self.assertEqual(pkg.units[0].shorthand, 'nmi')
            unit = pkg.units[0].materialize()
            self.assertEqual(unit.shorthand, 'nmi')
        finally:
            path.unlink()


class TestPackageRequires(unittest.TestCase):
    """Test UnitPackage requires validation."""

    def test_no_requires_loads_fine(self):
        """Package with no requires loads without issue."""
        pkg = UnitPackage(
            name='standalone',
            units=(UnitDef(name='slug', dimension='mass', aliases=('slug',)),),
        )
        graph = get_default_graph().with_package(pkg)
        self.assertIsNotNone(graph.resolve_unit('slug'))

    def test_satisfied_requires(self):
        """Package loads when all requires are satisfied."""
        base = UnitPackage(
            name='aerospace',
            units=(UnitDef(name='slug', dimension='mass', aliases=('slug',)),),
        )
        ext = UnitPackage(
            name='aerospace-extended',
            requires=('aerospace',),
            units=(UnitDef(name='poundal', dimension='force', aliases=('pdl',)),),
        )
        graph = get_default_graph().with_package(base).with_package(ext)
        self.assertIsNotNone(graph.resolve_unit('slug'))
        self.assertIsNotNone(graph.resolve_unit('poundal'))

    def test_missing_requires_raises(self):
        """Package raises when requires are not satisfied."""
        pkg = UnitPackage(
            name='aerospace-extended',
            requires=('aerospace',),
            units=(UnitDef(name='poundal', dimension='force'),),
        )
        with self.assertRaises(PackageLoadError) as ctx:
            get_default_graph().with_package(pkg)
        self.assertIn('aerospace', str(ctx.exception))

    def test_multiple_missing_requires(self):
        """Error message lists all missing requires."""
        pkg = UnitPackage(
            name='multi-dep',
            requires=('aerospace', 'medical'),
            units=(),
        )
        with self.assertRaises(PackageLoadError) as ctx:
            get_default_graph().with_package(pkg)
        msg = str(ctx.exception)
        self.assertIn('aerospace', msg)
        self.assertIn('medical', msg)

    def test_loaded_packages_tracked(self):
        """Graph tracks loaded package names across with_package calls."""
        pkg1 = UnitPackage(name='pkg1', units=())
        pkg2 = UnitPackage(name='pkg2', units=())
        graph = get_default_graph().with_package(pkg1).with_package(pkg2)
        self.assertIn('pkg1', graph._loaded_packages)
        self.assertIn('pkg2', graph._loaded_packages)

    def test_requires_from_toml(self):
        """load_package reads requires from [package] table."""
        toml_content = '''
[package]
name = "ext"
requires = ["aerospace"]

[[units]]
name = "test_unit"
dimension = "mass"
'''
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.toml', delete=False
        ) as f:
            f.write(toml_content)
            f.flush()
            path = Path(f.name)

        try:
            pkg = load_package(path)
            self.assertEqual(pkg.requires, ('aerospace',))
        finally:
            path.unlink()


if __name__ == '__main__':
    unittest.main()

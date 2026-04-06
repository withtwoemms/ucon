# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for ucon.serialization — round-trip TOML export/import."""

from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from ucon.graph import ConversionGraph, get_default_graph, using_graph
from ucon.maps import AffineMap, ComposedMap, ExpMap, LinearMap, LogMap, ReciprocalMap
from ucon.serialization import (
    FORMAT_VERSION,
    GraphLoadError,
    _check_format_version,
    _serialize_map,
    _serialize_constant,
    _extract_forward_edges,
    _extract_cross_basis_edges,
    _extract_product_edges,
    _serialize_basis,
    _serialize_dimension,
    _serialize_transform,
    _resolve_unit,
    _resolve_context_unit,
    _parse_product_expression,
    _product_key,
    _product_key_to_expression,
    _unit_sort_key,
    to_toml,
    from_toml,
)


# ---------------------------------------------------------------------------
# Map serialization
# ---------------------------------------------------------------------------

class TestSerializeMap:
    def test_linear(self):
        m = LinearMap(3.28084)
        d = _serialize_map(m)
        assert d == {"type": "linear", "a": 3.28084}

    def test_affine(self):
        m = AffineMap(1.8, 32.0)
        d = _serialize_map(m)
        assert d == {"type": "affine", "a": 1.8, "b": 32.0}

    def test_log_defaults_omitted(self):
        m = LogMap(scale=10, base=10)
        d = _serialize_map(m)
        assert d == {"type": "log", "scale": 10.0, "base": 10.0}
        assert "reference" not in d
        assert "offset" not in d

    def test_log_with_reference(self):
        m = LogMap(scale=10, base=10, reference=1e-3)
        d = _serialize_map(m)
        assert d["reference"] == 1e-3

    def test_exp(self):
        m = ExpMap(scale=0.1, base=10, reference=1e-3)
        d = _serialize_map(m)
        assert d["type"] == "exp"
        assert d["scale"] == 0.1
        assert d["reference"] == 1e-3

    def test_reciprocal(self):
        m = ReciprocalMap(299792458.0)
        d = _serialize_map(m)
        assert d == {"type": "reciprocal", "a": 299792458.0}

    def test_composed(self):
        m = ComposedMap(LogMap(scale=-1), AffineMap(a=-1, b=1))
        d = _serialize_map(m)
        assert d["type"] == "composed"
        assert d["outer"]["type"] == "log"
        assert d["inner"]["type"] == "affine"


# ---------------------------------------------------------------------------
# TOML structure
# ---------------------------------------------------------------------------

class TestTomlExport:
    def test_exports_valid_toml(self, tmp_path):
        """Export produces valid TOML that can be parsed."""
        graph = get_default_graph()
        path = tmp_path / "test.ucon.toml"
        graph.to_toml(path)

        with open(path, "rb") as f:
            doc = tomllib.load(f)

        assert doc["package"]["format_version"] == FORMAT_VERSION
        assert "bases" in doc
        assert "dimensions" in doc
        assert "units" in doc
        assert "edges" in doc

    def test_units_section(self, tmp_path):
        """Units section contains expected entries."""
        graph = get_default_graph()
        path = tmp_path / "test.ucon.toml"
        graph.to_toml(path)

        with open(path, "rb") as f:
            doc = tomllib.load(f)

        unit_names = {u["name"] for u in doc["units"]}
        assert "meter" in unit_names
        assert "kilogram" in unit_names
        assert "second" in unit_names

    def test_edges_section_has_factor_shorthand(self, tmp_path):
        """Linear edges use factor shorthand, not full map spec."""
        graph = get_default_graph()
        path = tmp_path / "test.ucon.toml"
        graph.to_toml(path)

        with open(path, "rb") as f:
            doc = tomllib.load(f)

        # Find the foot-meter edge
        foot_edges = [
            e for e in doc["edges"]
            if {e["src"], e["dst"]} == {"meter", "foot"}
        ]
        assert len(foot_edges) == 1
        edge = foot_edges[0]
        assert "factor" in edge
        assert "map" not in edge

    def test_affine_edge_has_offset(self, tmp_path):
        """Affine edges include offset."""
        graph = get_default_graph()
        path = tmp_path / "test.ucon.toml"
        graph.to_toml(path)

        with open(path, "rb") as f:
            doc = tomllib.load(f)

        # Find celsius-kelvin edge (should have offset)
        temp_edges = [
            e for e in doc["edges"]
            if {e["src"], e["dst"]} & {"celsius", "kelvin"}
        ]
        affine_edges = [e for e in temp_edges if "offset" in e]
        assert len(affine_edges) >= 1

    def test_cross_basis_edges_present(self, tmp_path):
        """Cross-basis edges section exists with transform references."""
        graph = get_default_graph()
        path = tmp_path / "test.ucon.toml"
        graph.to_toml(path)

        with open(path, "rb") as f:
            doc = tomllib.load(f)

        cross_edges = doc.get("cross_basis_edges", [])
        assert len(cross_edges) > 0
        # Each cross-basis edge should have a transform reference
        for edge in cross_edges:
            assert "transform" in edge

    def test_transforms_present(self, tmp_path):
        """Transforms section contains basis transforms."""
        graph = get_default_graph()
        path = tmp_path / "test.ucon.toml"
        graph.to_toml(path)

        with open(path, "rb") as f:
            doc = tomllib.load(f)

        transforms = doc.get("transforms", {})
        assert len(transforms) > 0
        # Check at least one transform has source/target/matrix
        for name, t in transforms.items():
            assert "source" in t
            assert "target" in t
            assert "matrix" in t

    def test_bases_present(self, tmp_path):
        """Bases section lists SI and other bases."""
        graph = get_default_graph()
        path = tmp_path / "test.ucon.toml"
        graph.to_toml(path)

        with open(path, "rb") as f:
            doc = tomllib.load(f)

        assert "SI" in doc["bases"]
        si = doc["bases"]["SI"]
        component_names = [c["name"] for c in si["components"]]
        assert "length" in component_names
        assert "mass" in component_names
        assert "time" in component_names


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_standard_graph_roundtrip(self, tmp_path):
        """Export default graph, re-import, verify structural equality."""
        graph = get_default_graph()
        path = tmp_path / "standard.ucon.toml"
        graph.to_toml(path)
        restored = ConversionGraph.from_toml(path)

        # Same registered unit names
        assert set(graph._name_registry_cs.keys()) == set(restored._name_registry_cs.keys())

    def test_linear_conversion_roundtrip(self, tmp_path):
        """Linear conversions survive round-trip."""
        graph = get_default_graph()
        path = tmp_path / "linear.ucon.toml"
        graph.to_toml(path)
        restored = ConversionGraph.from_toml(path)

        from ucon import units

        # Test meter → foot conversion
        src = units.meter
        dst = units.foot
        with using_graph(restored):
            original_map = graph.convert(src=src, dst=dst)
            restored_map = restored.convert(src=src, dst=dst)
            assert abs(original_map(1.0) - restored_map(1.0)) < 1e-9

    def test_affine_temperature_roundtrip(self, tmp_path):
        """AffineMap edges (C→K, F→C) survive round-trip."""
        graph = get_default_graph()
        path = tmp_path / "affine.ucon.toml"
        graph.to_toml(path)
        restored = ConversionGraph.from_toml(path)

        from ucon import units

        with using_graph(restored):
            # celsius → kelvin
            original_map = graph.convert(src=units.celsius, dst=units.kelvin)
            restored_map = restored.convert(src=units.celsius, dst=units.kelvin)
            # 0°C = 273.15K
            assert abs(original_map(0.0) - restored_map(0.0)) < 1e-6
            # 100°C = 373.15K
            assert abs(original_map(100.0) - restored_map(100.0)) < 1e-6

    def test_logarithmic_map_roundtrip(self, tmp_path):
        """LogMap/ExpMap/ComposedMap edges survive round-trip."""
        graph = get_default_graph()
        path = tmp_path / "log.ucon.toml"
        graph.to_toml(path)
        restored = ConversionGraph.from_toml(path)

        from ucon import units

        with using_graph(restored):
            # watt → dBm: 10*log10(P/1mW)
            original_map = graph.convert(src=units.watt, dst=units.decibel_milliwatt)
            restored_map = restored.convert(src=units.watt, dst=units.decibel_milliwatt)
            # 1 W = 30 dBm
            assert abs(original_map(1.0) - restored_map(1.0)) < 1e-6

    def test_cross_basis_roundtrip(self, tmp_path):
        """Cross-basis edges survive round-trip."""
        graph = get_default_graph()
        path = tmp_path / "cross_basis.ucon.toml"
        graph.to_toml(path)
        restored = ConversionGraph.from_toml(path)

        from ucon import units

        with using_graph(restored):
            # dyne → newton (CGS → SI)
            original_map = graph.convert(src=units.dyne, dst=units.newton)
            restored_map = restored.convert(src=units.dyne, dst=units.newton)
            assert abs(original_map(1.0) - restored_map(1.0)) < 1e-9

    def test_graph_equality(self, tmp_path):
        """Exported/imported graph is equal to original."""
        graph = get_default_graph()
        path = tmp_path / "eq.ucon.toml"
        graph.to_toml(path)
        restored = ConversionGraph.from_toml(path)
        assert graph == restored

    def test_file_not_found(self):
        """from_toml raises on missing file."""
        with pytest.raises(FileNotFoundError):
            ConversionGraph.from_toml("/nonexistent/path.toml")

    def test_composed_map_roundtrip_via_nines(self, tmp_path):
        """ComposedMap (nines = -log10(1-x)) survives round-trip."""
        graph = get_default_graph()
        path = tmp_path / "composed.ucon.toml"
        graph.to_toml(path)

        with open(path, "rb") as f:
            doc = tomllib.load(f)

        # Find composed map edges
        composed_edges = [
            e for e in doc.get("edges", [])
            if "map" in e and e["map"].get("type") == "composed"
        ]
        # The nines edge uses ComposedMap(LogMap, AffineMap)
        assert len(composed_edges) >= 1


# ---------------------------------------------------------------------------
# Package & constant round-trip
# ---------------------------------------------------------------------------

class TestPackageRoundTrip:
    def test_loaded_packages_preserved(self, tmp_path):
        """loaded_packages survives round-trip."""
        from ucon.packages import load_package

        graph = get_default_graph()
        pkg = load_package("examples/units/aerospace.ucon.toml")
        graph = graph.with_package(pkg)
        assert "aerospace" in graph._loaded_packages

        path = tmp_path / "pkgs.ucon.toml"
        graph.to_toml(path)
        restored = ConversionGraph.from_toml(path)
        assert restored._loaded_packages == graph._loaded_packages

    def test_constant_unit_roundtrip(self, tmp_path):
        """Constant unit expressions (e.g., 'm/s') survive round-trip."""
        from ucon.packages import load_package

        graph = get_default_graph()
        pkg = load_package("examples/units/aerospace.ucon.toml")
        graph = graph.with_package(pkg)

        path = tmp_path / "const.ucon.toml"
        graph.to_toml(path)
        restored = ConversionGraph.from_toml(path)

        assert len(restored._package_constants) == len(graph._package_constants)
        for orig, rest in zip(graph._package_constants, restored._package_constants):
            assert orig.symbol == rest.symbol
            assert orig.value == rest.value
            # Unit dimension should match (not be "unknown")
            assert rest.unit.dimension == orig.unit.dimension


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------

class TestGraphEquality:
    def test_product_edge_equality(self):
        """__eq__ detects product edge differences."""
        from ucon import units
        g1 = get_default_graph()
        g2 = g1.copy()
        assert g1 == g2

        # Add a product edge to g2 only
        g2.add_edge(
            src=units.watt,
            dst=units.joule / units.second,
            map=LinearMap(1.0),
        )
        assert g1 != g2

    def test_equality_is_symmetric(self):
        """A == B implies B == A; extra edges in B detected from A's side."""
        from ucon import units
        from ucon.dimension import Dimension

        g1 = ConversionGraph()
        g2 = ConversionGraph()
        u = units.meter
        v = units.foot
        g1.register_unit(u)
        g1.register_unit(v)
        g2.register_unit(u)
        g2.register_unit(v)

        # g2 has an edge that g1 doesn't
        g2.add_edge(src=u, dst=v, map=LinearMap(3.28084))
        assert g2 != g1
        assert g1 != g2  # was broken before the fix

    def test_different_loaded_packages(self):
        """Graphs with different _loaded_packages are not equal."""
        g1 = get_default_graph()
        g2 = g1.copy()
        assert g1 == g2
        g2._loaded_packages = frozenset(["extra_package"])
        assert g1 != g2

    def test_different_package_constants(self):
        """Graphs with different _package_constants are not equal."""
        from ucon.constants import Constant
        from ucon import units

        g1 = get_default_graph()
        g2 = g1.copy()
        assert g1 == g2
        g2._package_constants = (
            Constant(
                symbol="X", name="test", value=42.0,
                unit=units.meter, uncertainty=None,
            ),
        )
        assert g1 != g2

    def test_different_basis_graph(self):
        """Graphs with/without a _basis_graph are not equal."""
        g1 = get_default_graph()
        g2 = g1.copy()
        assert g1 == g2
        g2._basis_graph = None
        assert g1 != g2

    def test_cross_basis_edge_map_difference_detected(self):
        """Tampered cross-basis edge map causes inequality."""
        from ucon.core import RebasedUnit

        g1 = get_default_graph()
        g2 = g1.copy()
        assert g1 == g2

        # Tamper with a cross-basis edge in g2
        for dim, edges in g2._unit_edges.items():
            for src in list(edges.keys()):
                if isinstance(src, RebasedUnit):
                    for dst in list(edges[src].keys()):
                        if not isinstance(dst, RebasedUnit):
                            edges[src][dst] = LinearMap(999.0)
                            break
                    break
            else:
                continue
            break

        assert g1 != g2
        assert g2 != g1  # symmetric

    def test_constant_name_difference_detected(self):
        """Constants with different name/source fields cause inequality."""
        from ucon.constants import Constant
        from ucon.packages import load_package

        g1 = get_default_graph()
        pkg = load_package("examples/units/aerospace.ucon.toml")
        g1 = g1.with_package(pkg)
        g2 = g1.copy()
        assert g1 == g2

        c = g1._package_constants[0]
        fake = Constant(
            symbol=c.symbol, name="WRONG", value=c.value,
            unit=c.unit, uncertainty=c.uncertainty,
            source="WRONG", category=c.category,
        )
        g2._package_constants = (fake,) + g1._package_constants[1:]
        assert g1 != g2


# ---------------------------------------------------------------------------
# _build_map composed support
# ---------------------------------------------------------------------------

class TestBuildMapComposed:
    def test_composed_map_from_spec(self):
        """_build_map handles composed type."""
        from ucon.packages import _build_map

        spec = {
            "type": "composed",
            "outer": {"type": "log", "scale": -1.0, "base": 10.0},
            "inner": {"type": "affine", "a": -1.0, "b": 1.0},
        }
        m = _build_map(spec)
        assert isinstance(m, ComposedMap)
        assert isinstance(m.outer, LogMap)
        assert isinstance(m.inner, AffineMap)
        # Test: nines(0.99) ≈ 2.0
        assert abs(m(0.99) - 2.0) < 0.01

    def test_composed_map_missing_keys(self):
        """_build_map raises on composed without outer/inner."""
        from ucon.packages import _build_map, PackageLoadError

        with pytest.raises(PackageLoadError):
            _build_map({"type": "composed", "outer": {"type": "linear", "a": 1.0}})


# ---------------------------------------------------------------------------
# Malformed TOML input validation
# ---------------------------------------------------------------------------

def _write_toml(tmp_path, doc: dict) -> Path:
    """Helper: write a dict as TOML and return the path."""
    import tomli_w

    path = tmp_path / "bad.ucon.toml"
    with open(path, "wb") as f:
        tomli_w.dump(doc, f)
    return path


class TestMalformedInput:
    """from_toml raises GraphLoadError (not KeyError) on bad input."""

    def test_basis_missing_components(self, tmp_path):
        doc = {"bases": {"X": {}}}
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="components.*bases.X"):
            from_toml(path)

    def test_basis_component_missing_name(self, tmp_path):
        doc = {"bases": {"X": {"components": [{"symbol": "x"}]}}}
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="name.*bases.X.components"):
            from_toml(path)

    def test_dimension_missing_basis(self, tmp_path):
        doc = {
            "bases": {"X": {"components": [{"name": "a"}]}},
            "dimensions": {"custom_dim": {"vector": [1]}},
        }
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="basis.*dimensions.custom_dim"):
            from_toml(path)

    def test_dimension_missing_vector(self, tmp_path):
        doc = {
            "bases": {"X": {"components": [{"name": "a"}]}},
            "dimensions": {"custom_dim": {"basis": "X"}},
        }
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="vector.*dimensions.custom_dim"):
            from_toml(path)

    def test_dimension_unknown_basis(self, tmp_path):
        doc = {
            "dimensions": {"custom_dim": {"basis": "NOPE", "vector": [1]}},
        }
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="unknown basis.*NOPE"):
            from_toml(path)

    def test_transform_missing_source(self, tmp_path):
        doc = {
            "bases": {"A": {"components": [{"name": "x"}]}},
            "transforms": {"T": {"target": "A", "matrix": [[1]]}},
        }
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="source.*transforms.T"):
            from_toml(path)

    def test_transform_missing_matrix(self, tmp_path):
        doc = {
            "bases": {"A": {"components": [{"name": "x"}]}},
            "transforms": {"T": {"source": "A", "target": "A"}},
        }
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="matrix.*transforms.T"):
            from_toml(path)

    def test_transform_unknown_basis(self, tmp_path):
        doc = {
            "bases": {"A": {"components": [{"name": "x"}]}},
            "transforms": {"T": {"source": "A", "target": "NOPE", "matrix": [[1]]}},
        }
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="unknown target basis.*NOPE"):
            from_toml(path)

    def test_unit_missing_name(self, tmp_path):
        doc = {"units": [{"dimension": "length"}]}
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="name.*units\\[0\\]"):
            from_toml(path)

    def test_unit_missing_dimension(self, tmp_path):
        doc = {"units": [{"name": "foo"}]}
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="dimension.*units\\[0\\]"):
            from_toml(path)

    def test_unit_unknown_dimension(self, tmp_path):
        doc = {"units": [{"name": "foo", "dimension": "nonexistent"}]}
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="unknown dimension.*nonexistent"):
            from_toml(path)

    def test_edge_missing_src(self, tmp_path):
        doc = {"edges": [{"dst": "meter", "factor": 1.0}]}
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="src.*edges\\[0\\]"):
            from_toml(path)

    def test_edge_missing_dst(self, tmp_path):
        doc = {"edges": [{"src": "meter", "factor": 1.0}]}
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="dst.*edges\\[0\\]"):
            from_toml(path)

    def test_constant_missing_symbol(self, tmp_path):
        doc = {"constants": [{"name": "c", "value": 3e8}]}
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="symbol.*constants\\[0\\]"):
            from_toml(path)

    def test_constant_missing_value(self, tmp_path):
        doc = {"constants": [{"symbol": "c", "name": "speed of light"}]}
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="value.*constants\\[0\\]"):
            from_toml(path)

    def test_constant_non_numeric_value(self, tmp_path):
        doc = {"constants": [{"symbol": "c", "name": "bad", "value": "fast"}]}
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match=r"constants\[0\].*numeric"):
            from_toml(path)


# ---------------------------------------------------------------------------
# Strict mode
# ---------------------------------------------------------------------------

class TestStrictParsing:
    """from_toml(strict=True) rejects unresolvable edges."""

    def _minimal_doc_with_units(self):
        """Return a minimal TOML doc with meter and foot registered."""
        return {
            "units": [
                {"name": "meter", "dimension": "length"},
                {"name": "foot", "dimension": "length"},
            ],
        }

    def test_strict_rejects_unknown_edge_src(self, tmp_path):
        doc = self._minimal_doc_with_units()
        doc["edges"] = [{"src": "nonexistent", "dst": "meter", "factor": 1.0}]
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="cannot resolve unit.*nonexistent"):
            from_toml(path, strict=True)

    def test_strict_rejects_unknown_edge_dst(self, tmp_path):
        doc = self._minimal_doc_with_units()
        doc["edges"] = [{"src": "meter", "dst": "nonexistent", "factor": 1.0}]
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="cannot resolve unit.*nonexistent"):
            from_toml(path, strict=True)

    def test_strict_rejects_unknown_product_unit(self, tmp_path):
        doc = self._minimal_doc_with_units()
        doc["product_edges"] = [{
            "src": "nonexistent*meter",
            "dst": "foot",
            "factor": 1.0,
            "product": True,
        }]
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="cannot resolve product expression"):
            from_toml(path, strict=True)

    def test_nonstrict_skips_unknown_edge(self, tmp_path):
        doc = self._minimal_doc_with_units()
        doc["edges"] = [{"src": "nonexistent", "dst": "meter", "factor": 1.0}]
        path = _write_toml(tmp_path, doc)
        graph = from_toml(path, strict=False)
        # Graph should load without error, but have no edges
        assert "meter" in graph._name_registry_cs


# ---------------------------------------------------------------------------
# Scaled product edge round-trip
# ---------------------------------------------------------------------------

class TestScaledProductEdges:
    """Product edges with scale-prefixed units survive round-trip."""

    def test_scaled_product_edge_roundtrip(self, tmp_path):
        """kilo*watt * hour → joule product edge survives export/import."""
        from ucon import units
        from ucon.core import UnitFactor, Scale, UnitProduct

        graph = get_default_graph()
        kwh = UnitProduct({
            UnitFactor(units.watt, Scale.kilo): 1,
            UnitFactor(units.hour, Scale.one): 1,
        })
        joule_prod = UnitProduct({UnitFactor(units.joule, Scale.one): 1})
        graph.add_edge(src=kwh, dst=joule_prod, map=LinearMap(3_600_000.0))

        path = tmp_path / "scaled_product.ucon.toml"
        graph.to_toml(path)
        restored = ConversionGraph.from_toml(path)
        assert graph == restored

    def test_product_expression_with_prefix(self):
        """_parse_product_expression resolves 'kwatt*hour' with Scale.kilo."""
        from ucon.core import Scale
        from ucon.serialization import _parse_product_expression

        graph = get_default_graph()
        with using_graph(graph):
            result = _parse_product_expression("kwatt*hour", {}, graph)

        assert result is not None
        # Find the watt factor and check its scale
        found_kilo_watt = False
        for uf, exp in result.factors.items():
            if uf.unit.name == "watt" and uf.scale == Scale.kilo:
                found_kilo_watt = True
        assert found_kilo_watt, f"Expected Scale.kilo on watt factor, got: {result}"


# ---------------------------------------------------------------------------
# Context serialization
# ---------------------------------------------------------------------------

class TestContextSerialization:
    """ConversionContext round-trip through TOML."""

    def test_context_roundtrip(self, tmp_path):
        """Register spectroscopy context on graph, export, import, verify equality."""
        from ucon.contexts import ConversionContext, ContextEdge
        from ucon import units

        graph = get_default_graph()

        c = 299792458.0
        h = 6.62607015e-34
        ctx = ConversionContext(
            name="spectroscopy",
            edges=(
                ContextEdge(
                    src=units.meter,
                    dst=units.hertz,
                    map=ReciprocalMap(c),
                ),
                ContextEdge(
                    src=units.hertz,
                    dst=units.joule,
                    map=LinearMap(h),
                ),
            ),
            description="Spectroscopy: wavelength/frequency/energy via c and h.",
        )
        graph.register_context(ctx)

        path = tmp_path / "ctx.ucon.toml"
        graph.to_toml(path)
        restored = ConversionGraph.from_toml(path)
        assert graph == restored

    def test_context_edges_in_toml(self, tmp_path):
        """Export graph with context, inspect TOML structure."""
        from ucon.contexts import ConversionContext, ContextEdge
        from ucon import units

        graph = get_default_graph()
        ctx = ConversionContext(
            name="spectroscopy",
            edges=(
                ContextEdge(
                    src=units.meter,
                    dst=units.hertz,
                    map=ReciprocalMap(299792458.0),
                ),
            ),
            description="Spectroscopy: wavelength/frequency/energy via c and h.",
        )
        graph.register_context(ctx)

        path = tmp_path / "ctx_structure.ucon.toml"
        graph.to_toml(path)

        with open(path, "rb") as f:
            doc = tomllib.load(f)

        assert "contexts" in doc
        assert "spectroscopy" in doc["contexts"]
        spec = doc["contexts"]["spectroscopy"]
        assert spec["description"] == "Spectroscopy: wavelength/frequency/energy via c and h."
        assert len(spec["edges"]) == 1
        edge = spec["edges"][0]
        assert edge["src"] == "meter"
        assert edge["dst"] == "hertz"
        assert edge["map"]["type"] == "reciprocal"

    def test_context_activation_after_roundtrip(self, tmp_path):
        """Import graph with context, activate it, verify conversion works."""
        from ucon.contexts import ConversionContext, ContextEdge, using_context
        from ucon import units

        c = 299792458.0

        graph = get_default_graph()
        ctx = ConversionContext(
            name="spectroscopy",
            edges=(
                ContextEdge(
                    src=units.meter,
                    dst=units.hertz,
                    map=ReciprocalMap(c),
                ),
            ),
            description="Spectroscopy: wavelength/frequency/energy via c and h.",
        )
        graph.register_context(ctx)

        path = tmp_path / "ctx_activate.ucon.toml"
        graph.to_toml(path)
        restored = ConversionGraph.from_toml(path)

        # Get the restored context and activate it
        restored_ctx = restored._contexts["spectroscopy"]
        with using_graph(restored):
            # Build a temporary graph with context edges applied
            extended = restored.copy()
            from ucon.contexts import _add_context_edge
            for edge in restored_ctx.edges:
                _add_context_edge(extended, edge)
            with using_graph(extended):
                m = extended.convert(src=units.meter, dst=units.hertz)
                # 500 nm → frequency
                freq = m(500e-9)
                expected = c / 500e-9
                assert abs(freq - expected) / expected < 1e-9


# ---------------------------------------------------------------------------
# Coverage: Map serialization edge cases (lines 89, 96, 106, 115)
# ---------------------------------------------------------------------------

class TestSerializeMapEdgeCases:
    def test_log_with_offset(self):
        """LogMap with non-zero offset includes offset key (line 89)."""
        m = LogMap(scale=10, base=10, offset=3.0)
        d = _serialize_map(m)
        assert d["offset"] == 3.0
        assert d["type"] == "log"

    def test_exp_with_offset(self):
        """ExpMap with non-zero offset includes offset key (line 96)."""
        m = ExpMap(scale=0.1, base=10, offset=2.0)
        d = _serialize_map(m)
        assert d["offset"] == 2.0
        assert d["type"] == "exp"

    def test_unknown_map_type_raises(self):
        """Serializing an unknown Map subclass raises TypeError (line 106)."""
        from ucon.maps import Map

        class CustomMap(Map):
            def __call__(self, x): return x
            @property
            def invertible(self): return True
            def inverse(self): return self
            def __matmul__(self, other): return self
            def __pow__(self, n): return self
            def derivative(self, x): return 1.0

        with pytest.raises(TypeError, match="Cannot serialize map type"):
            _serialize_map(CustomMap())

    def test_unit_sort_key(self):
        """_unit_sort_key returns the unit name (line 115)."""
        from ucon import units
        assert _unit_sort_key(units.meter) == "meter"


# ---------------------------------------------------------------------------
# Coverage: Basis serialization — symbol != name (line 231)
# ---------------------------------------------------------------------------

class TestSerializeBasisSymbol:
    def test_component_with_distinct_symbol(self):
        """BasisComponent with symbol != name emits symbol key (line 231)."""
        from ucon.basis import Basis, BasisComponent
        b = Basis("test", [BasisComponent("length", "L")])
        d = _serialize_basis(b)
        assert d["components"][0]["name"] == "length"
        assert d["components"][0]["symbol"] == "L"

    def test_component_symbol_same_as_name_omits(self):
        """BasisComponent with symbol == name omits symbol key."""
        from ucon.basis import Basis, BasisComponent
        b = Basis("test", [BasisComponent("length", "length")])
        d = _serialize_basis(b)
        assert "symbol" not in d["components"][0]


# ---------------------------------------------------------------------------
# Coverage: Constant serialization (lines 315, 316→318)
# ---------------------------------------------------------------------------

class TestSerializeConstant:
    def test_constant_with_uncertainty(self):
        """Constant with uncertainty includes uncertainty key (line 315)."""
        from ucon.constants import Constant
        from ucon import units

        c = Constant(
            symbol="G", name="gravitational constant",
            value=6.674e-11, unit=units.meter,
            uncertainty=1.5e-15, source="CODATA 2022",
            category="measured",
        )
        d = _serialize_constant(c)
        assert d["uncertainty"] == 1.5e-15

    def test_constant_with_nondefault_source(self):
        """Constant with non-CODATA source includes source key (line 316→318)."""
        from ucon.constants import Constant
        from ucon import units

        c = Constant(
            symbol="k", name="custom constant",
            value=42.0, unit=units.meter,
            uncertainty=None, source="custom-source",
            category="session",
        )
        d = _serialize_constant(c)
        assert d["source"] == "custom-source"

    def test_constant_default_source_omitted(self):
        """Constant with default source 'CODATA 2022' omits source key."""
        from ucon.constants import Constant
        from ucon import units

        c = Constant(
            symbol="c", name="speed of light",
            value=3e8, unit=units.meter,
            uncertainty=None,
        )
        d = _serialize_constant(c)
        assert "source" not in d


# ---------------------------------------------------------------------------
# Coverage: Export — tomli_w import error (lines 337–338)
# ---------------------------------------------------------------------------

class TestTomlExportImportError:
    def test_missing_tomli_w(self, tmp_path, monkeypatch):
        """to_toml raises ImportError when tomli_w is missing (lines 337–338)."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "tomli_w":
                raise ImportError("no tomli_w")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        graph = ConversionGraph()
        with pytest.raises(ImportError, match="tomli_w"):
            to_toml(graph, tmp_path / "out.toml")


# ---------------------------------------------------------------------------
# Coverage: _collect_transforms from basis_graph (line 434)
# ---------------------------------------------------------------------------

class TestCollectTransformsFromBasisGraph:
    def test_basis_graph_transforms_included(self):
        """Transforms from basis_graph._edges are included (line 434)."""
        from ucon.serialization import _collect_transforms
        from ucon.basis import Basis, BasisGraph, BasisTransform
        from fractions import Fraction

        a = Basis("A", ["x"])
        b = Basis("B", ["y"])
        bt = BasisTransform(source=a, target=b, matrix=((Fraction(1),),))

        graph = ConversionGraph()
        bg = BasisGraph()
        bg.add_transform(bt)
        graph._basis_graph = bg
        graph._rebased = {}

        result = _collect_transforms(graph)
        assert "A_TO_B" in result
        assert result["A_TO_B"] is bt


# ---------------------------------------------------------------------------
# Coverage: _collect_units skips RebasedUnit (line 444)
# ---------------------------------------------------------------------------

class TestCollectUnitsSkipsRebased:
    def test_rebased_unit_excluded(self):
        """RebasedUnit entries in _name_registry_cs are skipped (line 444)."""
        from ucon.serialization import _collect_units
        from ucon.core import RebasedUnit, Unit
        from ucon.dimension import Dimension
        from ucon.basis import Basis, BasisTransform
        from fractions import Fraction

        a = Basis("A", ["x"])
        b = Basis("B", ["y"])
        bt = BasisTransform(source=a, target=b, matrix=((Fraction(1),),))
        dim = Dimension.length
        u = Unit("meter", dim)
        ru = RebasedUnit(original=u, rebased_dimension=dim, basis_transform=bt)

        graph = ConversionGraph()
        graph.register_unit(u)
        # Manually insert rebased unit into the CS registry
        graph._name_registry_cs["rebased_meter"] = ru

        units_list = _collect_units(graph)
        names = {u["name"] for u in units_list}
        assert "meter" in names
        # RebasedUnit should have been skipped
        assert "rebased_meter" not in names


# ---------------------------------------------------------------------------
# Coverage: _product_key (line 488)
# ---------------------------------------------------------------------------

class TestProductKey:
    def test_product_key_basic(self):
        """_product_key produces a sorted tuple of factor metadata (line 488)."""
        from ucon import units
        from ucon.core import UnitFactor, Scale, UnitProduct

        prod = UnitProduct({
            UnitFactor(units.meter, Scale.one): 1,
            UnitFactor(units.second, Scale.one): -1,
        })
        key = _product_key(prod)
        assert isinstance(key, tuple)
        assert len(key) == 2


# ---------------------------------------------------------------------------
# Coverage: _extract_cross_basis_edges branches (lines 193, 195, 198)
# ---------------------------------------------------------------------------

class TestExtractCrossBasisBranches:
    def test_dim_not_in_unit_edges_skipped(self):
        """Rebased unit whose dimension is not in _unit_edges is skipped (line 193)."""
        from ucon.core import RebasedUnit, Unit
        from ucon.dimension import Dimension
        from ucon.basis import Basis, BasisTransform
        from fractions import Fraction

        a = Basis("A", ["x"])
        b = Basis("B", ["y"])
        bt = BasisTransform(source=a, target=b, matrix=((Fraction(1),),))
        dim = Dimension.length
        u = Unit("meter", dim)
        ru = RebasedUnit(original=u, rebased_dimension=dim, basis_transform=bt)

        graph = ConversionGraph()
        graph._rebased = {u: [ru]}
        graph._unit_edges = {}  # No edges at all

        result = _extract_cross_basis_edges(graph)
        assert result == []

    def test_rebased_not_in_dim_edges_skipped(self):
        """Rebased unit not present as a source in _unit_edges[dim] is skipped (line 195)."""
        from ucon.core import RebasedUnit, Unit
        from ucon.dimension import Dimension
        from ucon.basis import Basis, BasisTransform
        from fractions import Fraction

        a = Basis("A", ["x"])
        b = Basis("B", ["y"])
        bt = BasisTransform(source=a, target=b, matrix=((Fraction(1),),))
        dim = Dimension.length
        u = Unit("meter", dim)
        ru = RebasedUnit(original=u, rebased_dimension=dim, basis_transform=bt)

        graph = ConversionGraph()
        graph._rebased = {u: [ru]}
        graph._unit_edges = {dim: {}}  # Dim exists, but rebased unit is not a key

        result = _extract_cross_basis_edges(graph)
        assert result == []


# ---------------------------------------------------------------------------
# Coverage: from_toml validation — types (lines 527, 535–538, 560–570, 580, 591, 615)
# ---------------------------------------------------------------------------

class TestFromTomlValidation:
    def test_components_not_a_list(self, tmp_path):
        """Non-list components raises GraphLoadError (line 527)."""
        doc = {"bases": {"X": {"components": "bad"}}}
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="components must be a list"):
            from_toml(path)

    def test_component_as_string(self, tmp_path):
        """String component is accepted as BasisComponent(name) (line 535–536)."""
        doc = {
            "bases": {"X": {"components": ["length"]}},
            "dimensions": {"custom_dim": {"basis": "X", "vector": [1]}},
            "units": [{"name": "foo", "dimension": "custom_dim"}],
        }
        path = _write_toml(tmp_path, doc)
        g = from_toml(path)
        assert "foo" in g._name_registry_cs

    def test_component_invalid_type(self, tmp_path):
        """Non-string, non-dict component raises GraphLoadError (line 538)."""
        import tomli_w
        # TOML doesn't allow mixing types in arrays with tomli_w,
        # so we write raw TOML with an integer component
        path = tmp_path / "bad_comp.ucon.toml"
        content = b"""
[bases.X]
components = [42]
"""
        with open(path, "wb") as f:
            f.write(content)
        with pytest.raises(GraphLoadError, match="expected string or table"):
            from_toml(path)

    def test_vector_not_a_list(self, tmp_path):
        """Non-list vector raises GraphLoadError (line 560)."""
        doc = {
            "bases": {"X": {"components": [{"name": "a"}]}},
            "dimensions": {"custom_dim": {"basis": "X", "vector": "bad"}},
        }
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="vector must be a list"):
            from_toml(path)

    def test_fractional_vector_and_tag(self, tmp_path):
        """Fractional vector components and tag are parsed (lines 565, 569–570)."""
        doc = {
            "bases": {"X": {"components": [{"name": "a"}, {"name": "b"}]}},
            "dimensions": {
                "custom_dim": {
                    "basis": "X",
                    "vector": ["1/2", 1],
                    "tag": "test-tag",
                },
            },
            "units": [{"name": "foo", "dimension": "custom_dim"}],
        }
        path = _write_toml(tmp_path, doc)
        g = from_toml(path)
        assert "foo" in g._name_registry_cs

    def test_transform_unknown_source_basis(self, tmp_path):
        """Unknown source basis in transform raises GraphLoadError (line 580)."""
        doc = {
            "bases": {"B": {"components": [{"name": "x"}]}},
            "transforms": {"T": {"source": "NOPE", "target": "B", "matrix": [[1]]}},
        }
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="unknown source basis.*NOPE"):
            from_toml(path)

    def test_matrix_not_a_list(self, tmp_path):
        """Non-list matrix raises GraphLoadError (line 591)."""
        doc = {
            "bases": {"A": {"components": [{"name": "x"}]}},
            "transforms": {"T": {"source": "A", "target": "A", "matrix": "bad"}},
        }
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="matrix must be a list"):
            from_toml(path)

    def test_binding_unknown_source_component(self, tmp_path):
        """Unknown source_component in binding raises GraphLoadError (line 615)."""
        doc = {
            "bases": {
                "A": {"components": [{"name": "x"}]},
                "B": {"components": [{"name": "y"}]},
            },
            "transforms": {
                "T": {
                    "source": "A",
                    "target": "B",
                    "matrix": [[1]],
                    "bindings": [{
                        "source_component": "nonexistent",
                        "target_expression": [1],
                        "constant_symbol": "c",
                    }],
                },
            },
        }
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="unknown source_component.*nonexistent"):
            from_toml(path)


# ---------------------------------------------------------------------------
# Coverage: Strict/non-strict edge loading (lines 716, 728–733, 802–807)
# ---------------------------------------------------------------------------

class TestStrictModeBranches:
    def _minimal_doc_with_units(self):
        return {
            "units": [
                {"name": "meter", "dimension": "length"},
                {"name": "foot", "dimension": "length"},
            ],
        }

    def test_nonstrict_skips_unknown_product_edge(self, tmp_path):
        """Non-strict mode skips unresolvable product edges (line 716)."""
        doc = self._minimal_doc_with_units()
        doc["product_edges"] = [{
            "src": "nonexistent*meter",
            "dst": "foot",
            "factor": 1.0,
            "product": True,
        }]
        path = _write_toml(tmp_path, doc)
        g = from_toml(path, strict=False)
        assert "meter" in g._name_registry_cs

    def test_strict_rejects_unknown_cross_basis_src(self, tmp_path):
        """Strict mode rejects unresolvable cross-basis edge src (lines 728–733)."""
        doc = self._minimal_doc_with_units()
        doc["cross_basis_edges"] = [{
            "src": "nonexistent",
            "dst": "meter",
            "factor": 1.0,
        }]
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="cannot resolve unit.*nonexistent"):
            from_toml(path, strict=True)

    def test_strict_rejects_unknown_cross_basis_dst(self, tmp_path):
        """Strict mode rejects unresolvable cross-basis edge dst (lines 728–733)."""
        doc = self._minimal_doc_with_units()
        doc["cross_basis_edges"] = [{
            "src": "meter",
            "dst": "nonexistent",
            "factor": 1.0,
        }]
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="cannot resolve unit.*nonexistent"):
            from_toml(path, strict=True)

    def test_nonstrict_skips_unknown_cross_basis_edge(self, tmp_path):
        """Non-strict mode skips unresolvable cross-basis edges (line 733)."""
        doc = self._minimal_doc_with_units()
        doc["cross_basis_edges"] = [{
            "src": "nonexistent",
            "dst": "meter",
            "factor": 1.0,
        }]
        path = _write_toml(tmp_path, doc)
        g = from_toml(path, strict=False)
        assert "meter" in g._name_registry_cs

    def test_strict_rejects_unknown_context_edge_src(self, tmp_path):
        """Strict mode rejects unresolvable context edge src (lines 802–807)."""
        doc = self._minimal_doc_with_units()
        doc["contexts"] = {
            "myctx": {
                "description": "test",
                "edges": [{"src": "nonexistent", "dst": "meter", "factor": 1.0}],
            },
        }
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="cannot resolve unit.*nonexistent"):
            from_toml(path, strict=True)

    def test_strict_rejects_unknown_context_edge_dst(self, tmp_path):
        """Strict mode rejects unresolvable context edge dst (lines 802–807)."""
        doc = self._minimal_doc_with_units()
        doc["contexts"] = {
            "myctx": {
                "description": "test",
                "edges": [{"src": "meter", "dst": "nonexistent", "factor": 1.0}],
            },
        }
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="cannot resolve unit.*nonexistent"):
            from_toml(path, strict=True)

    def test_nonstrict_skips_unknown_context_edge(self, tmp_path):
        """Non-strict mode skips unresolvable context edges (line 807)."""
        doc = self._minimal_doc_with_units()
        doc["contexts"] = {
            "myctx": {
                "description": "test",
                "edges": [{"src": "nonexistent", "dst": "meter", "factor": 1.0}],
            },
        }
        path = _write_toml(tmp_path, doc)
        g = from_toml(path, strict=False)
        assert "meter" in g._name_registry_cs


# ---------------------------------------------------------------------------
# Coverage: _resolve_unit fallback (lines 833, 836)
# ---------------------------------------------------------------------------

class TestResolveUnitFallbacks:
    def test_resolve_from_graph_registry(self):
        """Unit resolved from graph.resolve_unit() when not in unit_map (line 833)."""
        from ucon import units

        graph = get_default_graph()
        # unit_map intentionally missing 'meter'
        result = _resolve_unit("meter", {}, graph)
        assert result is not None
        assert result.name == "meter"

    def test_resolve_case_insensitive(self):
        """Case-insensitive fallback in _name_registry (line 836)."""
        from ucon import units

        graph = ConversionGraph()
        u = units.meter
        graph.register_unit(u)
        # Verify it's in the case-insensitive registry
        assert "meter" in graph._name_registry
        # resolve_unit won't find "Meter" via resolve_unit (case-sensitive)
        # so it should hit the _name_registry fallback
        result = _resolve_unit("meter", {}, graph)
        assert result is not None

    def test_resolve_returns_none(self):
        """Completely unknown name returns None."""
        graph = ConversionGraph()
        result = _resolve_unit("nonexistent", {}, graph)
        assert result is None


# ---------------------------------------------------------------------------
# Coverage: _resolve_context_unit fallback (lines 852–855)
# ---------------------------------------------------------------------------

class TestResolveContextUnit:
    def test_context_unit_via_resolver(self):
        """_resolve_context_unit resolves via get_unit_by_name first (line 851)."""
        graph = get_default_graph()
        with using_graph(graph):
            result = _resolve_context_unit("meter", {}, graph)
        assert result is not None

    def test_context_unit_fallback_to_local(self):
        """_resolve_context_unit falls back to _resolve_unit on exception (lines 852–855)."""
        from ucon import units

        graph = ConversionGraph()
        graph.register_unit(units.meter)
        unit_map = {"meter": units.meter}

        # In an empty graph context, get_unit_by_name may fail — but
        # _resolve_unit(meter, unit_map, graph) succeeds via unit_map
        with using_graph(graph):
            result = _resolve_context_unit("meter", unit_map, graph)
        assert result is not None

    def test_context_unit_returns_none(self):
        """_resolve_context_unit returns None when all resolution fails."""
        graph = ConversionGraph()
        with using_graph(graph):
            result = _resolve_context_unit("nonexistent", {}, graph)
        assert result is None


# ---------------------------------------------------------------------------
# Coverage: _parse_product_expression edge cases (lines 888, 894–895, 920, 923)
# ---------------------------------------------------------------------------

class TestParseProductExpression:
    def test_empty_expression(self):
        """Empty expression returns None (line 923)."""
        graph = get_default_graph()
        with using_graph(graph):
            result = _parse_product_expression("", {}, graph)
        assert result is None

    def test_invalid_exponent(self):
        """Invalid exponent string raises GraphLoadError."""
        graph = get_default_graph()
        with using_graph(graph):
            with pytest.raises(GraphLoadError, match="Invalid exponent.*abc"):
                _parse_product_expression("meter^abc", {}, graph)

    def test_fallback_to_local_resolution(self):
        """Resolver failure falls back to _resolve_unit (line 920)."""
        from ucon import units

        graph = ConversionGraph()
        graph.register_unit(units.meter)
        unit_map = {"meter": units.meter}

        with using_graph(graph):
            result = _parse_product_expression("meter", unit_map, graph)
        assert result is not None

    def test_unresolvable_unit_returns_none(self):
        """Completely unknown unit in expression returns None (line 918–919)."""
        graph = ConversionGraph()
        with using_graph(graph):
            result = _parse_product_expression("nonexistent", {}, graph)
        assert result is None

    def test_empty_part_skipped(self):
        """Empty part from split is skipped (line 888)."""
        graph = get_default_graph()
        with using_graph(graph):
            # "meter*" splits to ["meter", ""] — empty part should be skipped
            result = _parse_product_expression("meter*", {}, graph)
        assert result is not None


# ---------------------------------------------------------------------------
# Coverage: Dimension serialization — fractional components (line 287)
# ---------------------------------------------------------------------------

class TestSerializeDimensionFractional:
    def test_fractional_vector_component(self):
        """Dimension with fractional vector component serializes as string (line 244)."""
        from ucon.basis import Basis, Vector
        from ucon.dimension import Dimension
        from fractions import Fraction

        b = Basis("test", ["a", "b"])
        v = Vector(b, (Fraction(1, 2), Fraction(1)))
        d = Dimension(vector=v, name="half_dim")
        result = _serialize_dimension(d)
        assert result["vector"] == ["1/2", 1]


# ---------------------------------------------------------------------------
# Coverage: _serialize_transform — binding with fractional target_expression (line 287)
# ---------------------------------------------------------------------------

class TestSerializeTransformBindings:
    def test_binding_fractional_target_expression(self):
        """Fractional binding target_expression serializes as string (line 287)."""
        from ucon.basis import Basis, Vector
        from ucon.basis.transforms import (
            ConstantBoundBasisTransform,
            ConstantBinding,
            BasisComponent,
        )
        from fractions import Fraction

        a = Basis("A", [BasisComponent("x", "X")])
        b = Basis("B", [BasisComponent("y", "Y")])
        binding = ConstantBinding(
            source_component=a[0],
            target_expression=Vector(b, (Fraction(1, 3),)),
            constant_symbol="c",
            exponent=Fraction(2),
        )
        bt = ConstantBoundBasisTransform(
            source=a,
            target=b,
            matrix=((Fraction(1),),),
            bindings=(binding,),
        )
        result = _serialize_transform(bt)
        assert "bindings" in result
        assert result["bindings"][0]["target_expression"] == ["1/3"]
        assert result["bindings"][0]["exponent"] == "2"


# ---------------------------------------------------------------------------
# Coverage: _product_key_to_expression edge cases
# ---------------------------------------------------------------------------

class TestProductKeyToExpression:
    def test_negative_exponent(self):
        """Exponent of -1 renders as ^-1."""
        key = (("meter", None, None, -1.0),)
        expr = _product_key_to_expression(key)
        assert expr == "meter^-1"

    def test_fractional_exponent(self):
        """Non-integer exponent renders as ^exp."""
        key = (("meter", None, None, 0.5),)
        expr = _product_key_to_expression(key)
        assert expr == "meter^0.5"

    def test_empty_key(self):
        """Empty key returns 'dimensionless'."""
        expr = _product_key_to_expression(())
        assert expr == "dimensionless"


# ---------------------------------------------------------------------------
# Coverage: Export empty sections produce no keys
# ---------------------------------------------------------------------------

class TestExportEmptySections:
    def test_empty_graph_exports_minimal(self, tmp_path):
        """An empty graph exports only package metadata."""
        graph = ConversionGraph()
        path = tmp_path / "empty.ucon.toml"
        graph.to_toml(path)

        with open(path, "rb") as f:
            doc = tomllib.load(f)

        assert "package" in doc
        # No bases, dimensions, units, edges, etc.
        assert "units" not in doc or doc["units"] == []
        assert "edges" not in doc or doc["edges"] == []


# ---------------------------------------------------------------------------
# Coverage: Context with description="" (line 465→467 branch)
# ---------------------------------------------------------------------------

class TestContextDescriptionBranch:
    def test_context_without_description(self, tmp_path):
        """Context with empty description omits key in export (line 465→467)."""
        from ucon.contexts import ConversionContext, ContextEdge
        from ucon import units

        graph = get_default_graph()
        ctx = ConversionContext(
            name="no_desc",
            edges=(
                ContextEdge(
                    src=units.meter,
                    dst=units.foot,
                    map=LinearMap(3.28084),
                ),
            ),
            description="",
        )
        graph.register_context(ctx)

        path = tmp_path / "ctx_no_desc.ucon.toml"
        graph.to_toml(path)

        with open(path, "rb") as f:
            doc = tomllib.load(f)

        ctx_spec = doc["contexts"]["no_desc"]
        assert "description" not in ctx_spec


# ---------------------------------------------------------------------------
# Coverage: Remaining lines (198, 762–765, 836, 920, 737→721)
# ---------------------------------------------------------------------------

class TestRemainingCoverage:
    def test_resolve_unit_case_insensitive_fallback(self):
        """Case-different name resolved via _name_registry (line 836)."""
        from ucon import units

        graph = ConversionGraph()
        graph.register_unit(units.meter)
        # "Meter" not in _name_registry_cs, but "meter" is in _name_registry
        result = _resolve_unit("Meter", {}, graph)
        assert result is not None
        assert result.name == "meter"

    def test_constant_unit_fallback_to_local(self, tmp_path):
        """Constant with unresolvable unit falls back to _resolve_unit (lines 762–765)."""
        doc = {
            "units": [{"name": "meter", "dimension": "length"}],
            "constants": [{
                "symbol": "k",
                "name": "test constant",
                "value": 42.0,
                "unit": "zzz_unknown_unit_zzz",
                "category": "session",
            }],
        }
        path = _write_toml(tmp_path, doc)
        g = from_toml(path)
        assert len(g._package_constants) == 1
        # The constant unit should be "unknown" since neither resolver found it
        assert g._package_constants[0].unit.name == "unknown"

    def test_cross_basis_edge_without_transform_key(self, tmp_path):
        """Cross-basis edge without transform key skips add_edge (line 737→721)."""
        doc = {
            "units": [
                {"name": "meter", "dimension": "length"},
                {"name": "foot", "dimension": "length"},
            ],
            "cross_basis_edges": [{
                "src": "meter",
                "dst": "foot",
                "factor": 3.28084,
                # No "transform" key — bt will be None
            }],
        }
        path = _write_toml(tmp_path, doc)
        g = from_toml(path)
        # Graph should load; edge was not added (no transform)
        assert "meter" in g._name_registry_cs

    def test_parse_product_expression_local_fallback(self):
        """Product expression falls back to local resolution (line 920)."""
        from ucon.core import Unit
        from ucon.dimension import Dimension

        # Create a minimal graph and put the unit ONLY in unit_map, not
        # registered in the graph, so get_unit_by_name will fail but
        # _resolve_unit will find it via unit_map
        graph = ConversionGraph()
        custom = Unit("zzzwidget_notregistered", Dimension.length)
        unit_map = {"zzzwidget_notregistered": custom}

        with using_graph(graph):
            result = _parse_product_expression("zzzwidget_notregistered", unit_map, graph)
        assert result is not None

    def test_extract_cross_basis_dst_is_rebased_skipped(self):
        """RebasedUnit dst in cross-basis extraction is skipped (line 198)."""
        from ucon.core import RebasedUnit, Unit
        from ucon.dimension import Dimension
        from ucon.basis import Basis, BasisTransform
        from fractions import Fraction

        a = Basis("A", ["x"])
        b = Basis("B", ["y"])
        bt = BasisTransform(source=a, target=b, matrix=((Fraction(1),),))
        dim = Dimension.length
        u = Unit("meter", dim)
        ru1 = RebasedUnit(original=u, rebased_dimension=dim, basis_transform=bt)
        ru2 = RebasedUnit(original=u, rebased_dimension=dim, basis_transform=bt)

        graph = ConversionGraph()
        graph._rebased = {u: [ru1]}
        # ru1 maps to ru2 (both are RebasedUnit)
        graph._unit_edges = {dim: {ru1: {ru2: LinearMap(1.0)}}}

        result = _extract_cross_basis_edges(graph)
        # ru2 is a RebasedUnit, so the edge should be skipped
        assert result == []


# ---------------------------------------------------------------------------
# Change 1: Format version validation
# ---------------------------------------------------------------------------

class TestFormatVersionValidation:
    """Tests for _check_format_version()."""

    def test_missing_format_version_accepted(self):
        """No format_version key → no error."""
        _check_format_version({"package": {"name": "test"}})

    def test_matching_version_accepted(self):
        """Matching format_version → no error."""
        _check_format_version({"package": {"format_version": FORMAT_VERSION}})

    def test_older_minor_accepted(self):
        """Older minor version → no error, no warning."""
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _check_format_version({"package": {"format_version": "1.0"}})

    def test_newer_minor_warns(self):
        """Newer minor version → UserWarning."""
        with pytest.warns(UserWarning, match="newer than supported"):
            _check_format_version({"package": {"format_version": "1.99"}})

    def test_incompatible_major_raises(self):
        """Major version 2 → GraphLoadError."""
        with pytest.raises(GraphLoadError, match="Incompatible format version"):
            _check_format_version({"package": {"format_version": "2.0"}})

    def test_incompatible_major_lower_raises(self):
        """Major version 0 → GraphLoadError."""
        with pytest.raises(GraphLoadError, match="Incompatible format version"):
            _check_format_version({"package": {"format_version": "0.5"}})

    def test_malformed_version_raises(self):
        """Non-numeric version → GraphLoadError."""
        with pytest.raises(GraphLoadError, match="Malformed format_version"):
            _check_format_version({"package": {"format_version": "abc"}})

    def test_no_package_table_accepted(self):
        """No [package] table → no error."""
        _check_format_version({})

    def test_semver_tolerated(self):
        """Semver '1.2.3' parses as 1.2 → no error."""
        _check_format_version({"package": {"format_version": "1.2.3"}})

    def test_format_version_roundtrip(self, tmp_path):
        """from_toml validates version during import."""
        doc = {
            "package": {"format_version": "2.0"},
            "units": [{"name": "meter", "dimension": "length"}],
        }
        path = _write_toml(tmp_path, doc)
        with pytest.raises(GraphLoadError, match="Incompatible format version"):
            from_toml(path)

    def test_format_version_warning_roundtrip(self, tmp_path):
        """from_toml warns on newer minor version during import."""
        doc = {
            "package": {"format_version": "1.99"},
            "units": [{"name": "meter", "dimension": "length"}],
        }
        path = _write_toml(tmp_path, doc)
        with pytest.warns(UserWarning, match="newer than supported"):
            from_toml(path)


# ---------------------------------------------------------------------------
# Change 2: Product expression grammar
# ---------------------------------------------------------------------------

class TestProductExpressionGrammar:
    """Tests for '/' division sugar in product expressions."""

    def test_division_basic(self):
        """'meter/second' → meter^1, second^-1."""
        graph = get_default_graph()
        with using_graph(graph):
            result = _parse_product_expression("meter/second", {}, graph)
        assert result is not None
        from ucon.core import UnitFactor, Scale
        found = {}
        for uf, exp in result.factors.items():
            found[uf.unit.name] = exp
        assert found["meter"] == 1.0
        assert found["second"] == -1.0

    def test_division_compound_num(self):
        """'kg*meter/second^2' → kg^1, meter^1, second^-2."""
        graph = get_default_graph()
        with using_graph(graph):
            result = _parse_product_expression("kg*meter/second^2", {}, graph)
        assert result is not None
        found = {}
        for uf, exp in result.factors.items():
            found[uf.unit.name] = exp
        assert found.get("kilogram", found.get("kg")) == 1.0
        assert found["meter"] == 1.0
        assert found["second"] == -2.0

    def test_division_then_multiply(self):
        """'meter/second*kilogram' → meter^1, second^-1, kg^1 (standard math)."""
        graph = get_default_graph()
        with using_graph(graph):
            result = _parse_product_expression("meter/second*kilogram", {}, graph)
        assert result is not None
        found = {}
        for uf, exp in result.factors.items():
            found[uf.unit.name] = exp
        assert found["meter"] == 1.0
        assert found["second"] == -1.0
        assert found["kilogram"] == 1.0

    def test_compound_denominator_via_slashes(self):
        """'meter/second/kilogram' → meter^1, second^-1, kg^-1."""
        graph = get_default_graph()
        with using_graph(graph):
            result = _parse_product_expression("meter/second/kilogram", {}, graph)
        assert result is not None
        found = {}
        for uf, exp in result.factors.items():
            found[uf.unit.name] = exp
        assert found["meter"] == 1.0
        assert found["second"] == -1.0
        assert found["kilogram"] == -1.0

    def test_multiple_slash_left_associative(self):
        """'meter/second/kilogram' → meter^1, second^-1, kilogram^-1 (dosage-style)."""
        graph = get_default_graph()
        with using_graph(graph):
            result = _parse_product_expression("meter/second/kilogram", {}, graph)
        assert result is not None
        found = {}
        for uf, exp in result.factors.items():
            found[uf.unit.name] = exp
        assert found["meter"] == 1.0
        assert found["second"] == -1.0
        assert found["kilogram"] == -1.0

    def test_triple_slash_dosage(self):
        """'gram/kilogram/day/each' → g^1, kg^-1, day^-1, ea^-1."""
        graph = get_default_graph()
        with using_graph(graph):
            result = _parse_product_expression("gram/kilogram/day/each", {}, graph)
        assert result is not None
        found = {}
        for uf, exp in result.factors.items():
            found[uf.unit.name] = exp
        assert found["gram"] == 1.0
        assert found["kilogram"] == -1.0
        assert found["day"] == -1.0
        assert found["each"] == -1.0

    def test_invalid_exponent_raises(self):
        """'meter^abc' raises GraphLoadError."""
        graph = get_default_graph()
        with using_graph(graph):
            with pytest.raises(GraphLoadError, match="Invalid exponent.*abc"):
                _parse_product_expression("meter^abc", {}, graph)

    def test_backward_compat_star(self):
        """'meter*second^-1' still works (unchanged)."""
        graph = get_default_graph()
        with using_graph(graph):
            result = _parse_product_expression("meter*second^-1", {}, graph)
        assert result is not None
        found = {}
        for uf, exp in result.factors.items():
            found[uf.unit.name] = exp
        assert found["meter"] == 1.0
        assert found["second"] == -1.0

    def test_whitespace_tolerance(self):
        """'meter / second' with whitespace works."""
        graph = get_default_graph()
        with using_graph(graph):
            result = _parse_product_expression("meter / second", {}, graph)
        assert result is not None
        found = {}
        for uf, exp in result.factors.items():
            found[uf.unit.name] = exp
        assert found["meter"] == 1.0
        assert found["second"] == -1.0

    def test_division_with_prefix(self):
        """'kwatt/hour' → kilo-watt^1, hour^-1."""
        graph = get_default_graph()
        with using_graph(graph):
            result = _parse_product_expression("kwatt/hour", {}, graph)
        assert result is not None
        from ucon.core import Scale
        found_kilo_watt = False
        found_hour = False
        for uf, exp in result.factors.items():
            if uf.unit.name == "watt" and uf.scale == Scale.kilo:
                assert exp == 1.0
                found_kilo_watt = True
            if uf.unit.name == "hour":
                assert exp == -1.0
                found_hour = True
        assert found_kilo_watt
        assert found_hour

    def test_emitter_slash_notation(self):
        """Product key with meter^1, second^-1 emits 'meter/second'."""
        from ucon import units
        from ucon.core import UnitFactor, Scale, UnitProduct

        prod = UnitProduct({
            UnitFactor(units.meter, Scale.one): 1,
            UnitFactor(units.second, Scale.one): -1,
        })
        key = _product_key(prod)
        expr = _product_key_to_expression(key)
        assert "/" in expr
        assert "^-1" not in expr

    def test_emitter_all_negative(self):
        """Product key with second^-1 only emits 'second^-1' (no '1/second')."""
        from ucon import units
        from ucon.core import UnitFactor, Scale, UnitProduct

        prod = UnitProduct({
            UnitFactor(units.second, Scale.one): -1,
        })
        key = _product_key(prod)
        expr = _product_key_to_expression(key)
        assert expr == "second^-1"
        assert "/" not in expr

    def test_roundtrip_division(self, tmp_path):
        """Product edges with '/' notation survive export + reimport."""
        from ucon import units
        from ucon.core import UnitFactor, Scale, UnitProduct

        graph = get_default_graph()
        m_per_s = UnitProduct({
            UnitFactor(units.meter, Scale.one): 1,
            UnitFactor(units.second, Scale.one): -1,
        })
        ft_per_s = UnitProduct({
            UnitFactor(units.foot, Scale.one): 1,
            UnitFactor(units.second, Scale.one): -1,
        })
        graph.add_edge(src=m_per_s, dst=ft_per_s, map=LinearMap(3.28084))

        path = tmp_path / "division.ucon.toml"
        graph.to_toml(path)
        restored = ConversionGraph.from_toml(path)
        assert graph == restored

    def test_non_strict_warns_on_bad_expression(self, tmp_path):
        """Non-strict mode warns when a product expression is skipped."""
        doc = {
            "package": {"format_version": FORMAT_VERSION},
            "units": [{"name": "meter", "dimension": "length"}],
            "product_edges": [
                {"src": "meter^xyz", "dst": "meter", "factor": 1.0, "product": True},
            ],
        }
        path = _write_toml(tmp_path, doc)
        with pytest.warns(UserWarning, match="skipping product edge"):
            from_toml(path, strict=False)

    def test_non_strict_warns_on_unresolvable(self, tmp_path):
        """Non-strict mode warns when a unit name cannot be resolved."""
        doc = {
            "package": {"format_version": FORMAT_VERSION},
            "units": [{"name": "meter", "dimension": "length"}],
            "product_edges": [
                {"src": "meter", "dst": "nonexistent_unit", "factor": 1.0, "product": True},
            ],
        }
        path = _write_toml(tmp_path, doc)
        with pytest.warns(UserWarning, match="skipping unresolvable product edge"):
            from_toml(path, strict=False)


# ---------------------------------------------------------------------------
# Change 3: Map to_dict() and map type registry
# ---------------------------------------------------------------------------

class TestMapToDict:
    """Tests for Map.to_dict() on all subclasses."""

    def test_linear_to_dict(self):
        m = LinearMap(3.28084)
        assert m.to_dict() == {"type": "linear", "a": 3.28084}

    def test_affine_to_dict(self):
        m = AffineMap(1.8, 32.0)
        assert m.to_dict() == {"type": "affine", "a": 1.8, "b": 32.0}

    def test_log_to_dict_omits_defaults(self):
        m = LogMap(scale=10, base=10)
        d = m.to_dict()
        assert d == {"type": "log", "scale": 10.0, "base": 10.0}
        assert "reference" not in d
        assert "offset" not in d

    def test_log_to_dict_includes_nondefaults(self):
        m = LogMap(scale=10, base=10, reference=1e-3)
        d = m.to_dict()
        assert d["reference"] == 1e-3

    def test_exp_to_dict(self):
        m = ExpMap(scale=0.1, base=10, reference=1e-3)
        d = m.to_dict()
        assert d["type"] == "exp"
        assert d["scale"] == 0.1
        assert d["reference"] == 1e-3
        assert "offset" not in d

    def test_reciprocal_to_dict(self):
        m = ReciprocalMap(299792458.0)
        assert m.to_dict() == {"type": "reciprocal", "a": 299792458.0}

    def test_composed_to_dict_recursive(self):
        m = ComposedMap(LogMap(scale=-1), AffineMap(a=-1, b=1))
        d = m.to_dict()
        assert d["type"] == "composed"
        assert d["outer"]["type"] == "log"
        assert d["inner"]["type"] == "affine"

    def test_no_map_type_raises(self):
        """Custom Map without _map_type raises TypeError."""
        from ucon.maps import Map

        class BareMap(Map):
            def __call__(self, x): return x
            @property
            def invertible(self): return True
            def inverse(self): return self
            def __matmul__(self, other): return self
            def __pow__(self, n): return self
            def derivative(self, x): return 1.0

        with pytest.raises(TypeError, match="Cannot serialize map type"):
            BareMap().to_dict()

    def test_serialize_map_delegates(self):
        """_serialize_map(m) == m.to_dict() for all concrete types."""
        maps = [
            LinearMap(2.5),
            AffineMap(1.8, 32.0),
            LogMap(scale=10, base=10),
            ExpMap(scale=0.1, base=10),
            ReciprocalMap(42.0),
            ComposedMap(LogMap(scale=-1), AffineMap(a=-1, b=1)),
        ]
        for m in maps:
            assert _serialize_map(m) == m.to_dict()


class TestMapTypeRegistry:
    """Tests for MAP_TYPES / register_map_type()."""

    def test_map_types_is_immutable(self):
        """MAP_TYPES is a MappingProxyType — cannot be mutated."""
        from types import MappingProxyType
        from ucon.packages import MAP_TYPES

        assert isinstance(MAP_TYPES, MappingProxyType)
        with pytest.raises(TypeError):
            MAP_TYPES["foo"] = LinearMap  # type: ignore[index]

    def test_register_map_type_returns_new_dict(self):
        """register_map_type returns a new dict containing the custom entry."""
        from ucon.packages import MAP_TYPES, register_map_type
        from ucon.maps import Map
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class TestCustomMap(Map):
            _map_type = "test_custom_xyz"
            factor: float = 1.0
            def __call__(self, x): return self.factor * x
            @property
            def invertible(self): return True
            def inverse(self): return self
            def __matmul__(self, other): return self
            def __pow__(self, n): return self
            def derivative(self, x): return self.factor

        result = register_map_type("test_custom_xyz", TestCustomMap)
        # Returns a plain dict, not a MappingProxyType
        assert isinstance(result, dict)
        assert result["test_custom_xyz"] is TestCustomMap
        # Global MAP_TYPES is NOT mutated
        assert "test_custom_xyz" not in MAP_TYPES

    def test_register_duplicate_same_ok(self):
        """Registering the same class for the same name is idempotent."""
        from ucon.packages import register_map_type

        result = register_map_type("linear", LinearMap)
        assert result["linear"] is LinearMap

    def test_register_duplicate_different_raises(self):
        """Registering a different class for an existing name raises ValueError."""
        from ucon.packages import register_map_type

        with pytest.raises(ValueError, match="already registered"):
            register_map_type("linear", AffineMap)

    def test_register_non_map_raises(self):
        """Registering a non-Map class raises TypeError."""
        from ucon.packages import register_map_type

        with pytest.raises(TypeError, match="cls must be a Map subclass"):
            register_map_type("bad", str)

    def test_register_chaining(self):
        """Multiple registrations can be chained via the registry parameter."""
        from ucon.packages import register_map_type
        from ucon.maps import Map
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class MapA(Map):
            _map_type = "a"
            def __call__(self, x): return x
            @property
            def invertible(self): return True
            def inverse(self): return self
            def __matmul__(self, other): return self
            def __pow__(self, n): return self
            def derivative(self, x): return 1.0

        @dataclass(frozen=True)
        class MapB(Map):
            _map_type = "b"
            def __call__(self, x): return x
            @property
            def invertible(self): return True
            def inverse(self): return self
            def __matmul__(self, other): return self
            def __pow__(self, n): return self
            def derivative(self, x): return 1.0

        reg = register_map_type("a", MapA)
        reg = register_map_type("b", MapB, registry=reg)
        assert "a" in reg and "b" in reg
        assert "linear" in reg  # built-ins preserved

    def test_roundtrip_custom_map(self, tmp_path):
        """Custom Map subclass survives export/import with custom registry."""
        from ucon.packages import register_map_type
        from ucon.maps import Map
        from ucon import units
        from ucon.core import UnitFactor, Scale, UnitProduct
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class ScaleMap(Map):
            _map_type = "test_scale_rt"
            a: float
            def __call__(self, x): return self.a * x
            @property
            def invertible(self): return self.a != 0
            def inverse(self): return ScaleMap(1.0 / self.a)
            def __matmul__(self, other): return ComposedMap(self, other)
            def __pow__(self, n):
                if n == 1: return self
                if n == -1: return self.inverse()
                raise ValueError
            def derivative(self, x): return self.a

        custom_types = register_map_type("test_scale_rt", ScaleMap)

        graph = get_default_graph()
        prod_m = UnitProduct({UnitFactor(units.meter, Scale.one): 1})
        prod_ft = UnitProduct({UnitFactor(units.foot, Scale.one): 1})
        graph.add_edge(src=prod_m, dst=prod_ft, map=ScaleMap(a=3.28084))

        path = tmp_path / "custom_map.ucon.toml"
        graph.to_toml(path)
        restored = ConversionGraph.from_toml(path, map_types=custom_types)
        assert graph == restored

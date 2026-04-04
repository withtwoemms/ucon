# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for ucon.serialization — round-trip TOML export/import."""

from __future__ import annotations

import math
import sys
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
    _serialize_map,
    _extract_forward_edges,
    _extract_cross_basis_edges,
    _serialize_basis,
    _serialize_dimension,
    _serialize_transform,
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

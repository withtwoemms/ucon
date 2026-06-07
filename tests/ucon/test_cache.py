# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Tests for the marshal-based graph cache (``ucon._cache``).
"""
from __future__ import annotations

import os
import struct
import unittest
from pathlib import Path
from unittest import mock

from ucon._cache import (
    _CACHE_SCHEMA,
    _HEADER_FMT,
    _HEADER_SIZE,
    _MAGIC,
    _from_primitives,
    _to_primitives,
    load_cached_graph,
    write_cached_graph,
)
from ucon.conversion import Graph


TOML_PATH = Path(__file__).resolve().parent.parent.parent / "ucon" / "comprehensive.ucon.toml"


class TestRoundTrip(unittest.TestCase):
    """Cache write → read produces a structurally equivalent graph."""

    def test_roundtrip_unit_count(self):
        """Unit registries match after round-trip."""
        from ucon.serialization import from_toml

        original = from_toml(TOML_PATH)
        raw = _to_primitives(original)
        restored = _from_primitives(raw)

        self.assertEqual(
            len(original._name_registry_cs),
            len(restored._name_registry_cs),
        )

    def test_roundtrip_edge_count(self):
        """Edge counts match after round-trip."""
        from ucon.serialization import from_toml

        original = from_toml(TOML_PATH)
        raw = _to_primitives(original)
        restored = _from_primitives(raw)

        orig_edges = sum(
            1
            for dim, sd in original._unit_edges.items()
            for s, dd in sd.items()
            for d in dd
        )
        rest_edges = sum(
            1
            for dim, sd in restored._unit_edges.items()
            for s, dd in sd.items()
            for d in dd
        )
        self.assertEqual(orig_edges, rest_edges)

    def test_roundtrip_product_edge_count(self):
        """Product edge counts match."""
        from ucon.serialization import from_toml

        original = from_toml(TOML_PATH)
        raw = _to_primitives(original)
        restored = _from_primitives(raw)

        orig_pe = sum(len(d) for d in original._product_edges.values())
        rest_pe = sum(len(d) for d in restored._product_edges.values())
        self.assertEqual(orig_pe, rest_pe)

    def test_roundtrip_constants(self):
        """Constant count matches."""
        from ucon.serialization import from_toml

        original = from_toml(TOML_PATH)
        raw = _to_primitives(original)
        restored = _from_primitives(raw)

        self.assertEqual(
            len(original._package_constants),
            len(restored._package_constants),
        )

    def test_roundtrip_kinds(self):
        """Kind lattice count matches."""
        from ucon.serialization import from_toml

        original = from_toml(TOML_PATH)
        raw = _to_primitives(original)
        restored = _from_primitives(raw)

        self.assertEqual(
            len(original._kind_lattice),
            len(restored._kind_lattice),
        )

    def test_roundtrip_rebased(self):
        """Rebased unit count matches."""
        from ucon.serialization import from_toml

        original = from_toml(TOML_PATH)
        raw = _to_primitives(original)
        restored = _from_primitives(raw)

        orig_rb = sum(len(v) for v in original._rebased.values())
        rest_rb = sum(len(v) for v in restored._rebased.values())
        self.assertEqual(orig_rb, rest_rb)

    def test_conversion_after_roundtrip(self):
        """Conversions produce correct results from cached graph."""
        from ucon.serialization import from_toml

        original = from_toml(TOML_PATH)
        raw = _to_primitives(original)
        restored = _from_primitives(raw)

        # Find meter and foot in both graphs
        m_orig = original._name_registry_cs["meter"]
        ft_orig = original._name_registry_cs["foot"]
        m_rest = restored._name_registry_cs["meter"]
        ft_rest = restored._name_registry_cs["foot"]

        # Convert via original graph
        map_orig = original._convert_units(src=m_orig, dst=ft_orig)
        result_orig = map_orig(100.0)

        # Convert via restored graph
        map_rest = restored._convert_units(src=m_rest, dst=ft_rest)
        result_rest = map_rest(100.0)

        self.assertAlmostEqual(result_orig, result_rest, places=6)


class TestCacheIO(unittest.TestCase):
    """File-based cache read/write tests."""

    def test_write_and_load(self, tmp_path=None):
        """Write cache, then load it back."""
        import tempfile
        import shutil

        from ucon.serialization import from_toml

        tmpdir = Path(tempfile.mkdtemp())
        try:
            toml_copy = tmpdir / "test.ucon.toml"
            shutil.copy2(TOML_PATH, toml_copy)

            graph = from_toml(toml_copy)
            ok = write_cached_graph(graph, toml_copy)
            self.assertTrue(ok)

            cache_path = toml_copy.with_suffix(".cache")
            self.assertTrue(cache_path.exists())

            restored = load_cached_graph(toml_copy)
            self.assertIsNotNone(restored)
            self.assertEqual(
                len(graph._name_registry_cs),
                len(restored._name_registry_cs),
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_stale_cache_returns_none(self):
        """Stale cache (older than TOML) is rejected."""
        import tempfile
        import shutil
        import time

        from ucon.serialization import from_toml

        tmpdir = Path(tempfile.mkdtemp())
        try:
            toml_copy = tmpdir / "test.ucon.toml"
            shutil.copy2(TOML_PATH, toml_copy)

            graph = from_toml(toml_copy)
            ok = write_cached_graph(graph, toml_copy)
            self.assertTrue(ok)

            # Touch TOML to make it newer
            time.sleep(0.05)
            toml_copy.touch()

            restored = load_cached_graph(toml_copy)
            self.assertIsNone(restored)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_corrupt_cache_returns_none(self):
        """Corrupt cache data is silently rejected."""
        import tempfile
        import shutil

        tmpdir = Path(tempfile.mkdtemp())
        try:
            toml_copy = tmpdir / "test.ucon.toml"
            shutil.copy2(TOML_PATH, toml_copy)

            cache_path = toml_copy.with_suffix(".cache")
            cache_path.write_bytes(b"GARBAGE DATA HERE")

            restored = load_cached_graph(toml_copy)
            self.assertIsNone(restored)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_bad_magic_returns_none(self):
        """Wrong magic bytes are rejected."""
        import tempfile
        import shutil

        tmpdir = Path(tempfile.mkdtemp())
        try:
            toml_copy = tmpdir / "test.ucon.toml"
            shutil.copy2(TOML_PATH, toml_copy)

            cache_path = toml_copy.with_suffix(".cache")
            # Write header with wrong magic
            header = struct.pack(_HEADER_FMT, b"BAD!", 1, 3, 12, 1, b"\x00\x00\x00")
            cache_path.write_bytes(header + b"payload")

            restored = load_cached_graph(toml_copy)
            self.assertIsNone(restored)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestEnvDisable(unittest.TestCase):
    """UCON_NO_CACHE=1 disables cache."""

    def test_env_disables_load(self):
        """load_cached_graph returns None when disabled."""
        with mock.patch.dict(os.environ, {"UCON_NO_CACHE": "1"}):
            result = load_cached_graph(TOML_PATH)
            self.assertIsNone(result)

    def test_env_disables_write(self):
        """write_cached_graph returns False when disabled."""
        from ucon.serialization import from_toml

        graph = from_toml(TOML_PATH)
        with mock.patch.dict(os.environ, {"UCON_NO_CACHE": "1"}):
            result = write_cached_graph(graph, TOML_PATH)
            self.assertFalse(result)


class TestHeaderValidation(unittest.TestCase):
    """Header mismatch paths in load_cached_graph."""

    def _write_cache_with_header(self, tmpdir, **overrides):
        """Helper: write a cache file with custom header fields."""
        import shutil
        import sys as _sys

        from ucon.serialization import FORMAT_VERSION, from_toml

        toml_copy = tmpdir / "test.ucon.toml"
        shutil.copy2(TOML_PATH, toml_copy)

        graph = from_toml(toml_copy)
        raw = _to_primitives(graph)
        import marshal
        payload = marshal.dumps(raw)

        our_major, _our_minor = (int(x) for x in FORMAT_VERSION.split("."))
        fields = {
            "magic": _MAGIC,
            "fmt_ver": our_major,
            "py_major": _sys.version_info.major,
            "py_minor": _sys.version_info.minor,
            "cache_ver": _CACHE_SCHEMA,
        }
        fields.update(overrides)
        header = struct.pack(
            _HEADER_FMT,
            fields["magic"],
            fields["fmt_ver"],
            fields["py_major"],
            fields["py_minor"],
            fields["cache_ver"],
            b"\x00\x00\x00",
        )
        cache_path = toml_copy.with_suffix(".cache")
        cache_path.write_bytes(header + payload)
        return toml_copy

    def test_wrong_python_major_returns_none(self):
        import tempfile
        import shutil

        tmpdir = Path(tempfile.mkdtemp())
        try:
            toml_copy = self._write_cache_with_header(tmpdir, py_major=2)
            self.assertIsNone(load_cached_graph(toml_copy))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_wrong_python_minor_returns_none(self):
        import sys as _sys
        import tempfile
        import shutil

        tmpdir = Path(tempfile.mkdtemp())
        try:
            toml_copy = self._write_cache_with_header(
                tmpdir, py_minor=_sys.version_info.minor + 1
            )
            self.assertIsNone(load_cached_graph(toml_copy))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_wrong_cache_schema_returns_none(self):
        import tempfile
        import shutil

        tmpdir = Path(tempfile.mkdtemp())
        try:
            toml_copy = self._write_cache_with_header(
                tmpdir, cache_ver=_CACHE_SCHEMA + 99
            )
            self.assertIsNone(load_cached_graph(toml_copy))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_wrong_format_version_returns_none(self):
        import tempfile
        import shutil

        tmpdir = Path(tempfile.mkdtemp())
        try:
            toml_copy = self._write_cache_with_header(tmpdir, fmt_ver=999)
            self.assertIsNone(load_cached_graph(toml_copy))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_truncated_file_returns_none(self):
        """File shorter than header size is rejected."""
        import tempfile
        import shutil

        tmpdir = Path(tempfile.mkdtemp())
        try:
            toml_copy = tmpdir / "test.ucon.toml"
            shutil.copy2(TOML_PATH, toml_copy)
            cache_path = toml_copy.with_suffix(".cache")
            cache_path.write_bytes(b"\x00" * (_HEADER_SIZE - 1))
            self.assertIsNone(load_cached_graph(toml_copy))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestMissingCacheFile(unittest.TestCase):
    """load_cached_graph with no cache file."""

    def test_missing_cache_returns_none(self):
        import tempfile
        import shutil

        tmpdir = Path(tempfile.mkdtemp())
        try:
            toml_copy = tmpdir / "test.ucon.toml"
            shutil.copy2(TOML_PATH, toml_copy)
            # No cache file written
            self.assertIsNone(load_cached_graph(toml_copy))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestMapCodecCoverage(unittest.TestCase):
    """Codec coverage for all Map types."""

    def test_linear_map_roundtrip(self):
        from ucon._cache import _map_to_prim, _prim_to_map
        from ucon.maps import LinearMap

        m = LinearMap(a=2.54, rel_uncertainty=0.001)
        prim = _map_to_prim(m)
        restored = _prim_to_map(prim)
        self.assertAlmostEqual(restored.a, 2.54)
        self.assertAlmostEqual(restored.rel_uncertainty, 0.001)

    def test_affine_map_roundtrip(self):
        from ucon._cache import _map_to_prim, _prim_to_map
        from ucon.maps import AffineMap

        m = AffineMap(a=1.8, b=32.0, rel_uncertainty=0.0)
        prim = _map_to_prim(m)
        restored = _prim_to_map(prim)
        self.assertAlmostEqual(restored.a, 1.8)
        self.assertAlmostEqual(restored.b, 32.0)

    def test_log_map_roundtrip(self):
        from ucon._cache import _map_to_prim, _prim_to_map
        from ucon.maps import LogMap

        m = LogMap(scale=20.0, base=10.0, reference=1e-12, offset=0.0)
        prim = _map_to_prim(m)
        restored = _prim_to_map(prim)
        self.assertAlmostEqual(restored.scale, 20.0)
        self.assertAlmostEqual(restored.base, 10.0)
        self.assertAlmostEqual(restored.reference, 1e-12)

    def test_exp_map_roundtrip(self):
        from ucon._cache import _map_to_prim, _prim_to_map
        from ucon.maps import ExpMap

        m = ExpMap(scale=0.05, base=10.0, reference=1e-12, offset=0.0)
        prim = _map_to_prim(m)
        restored = _prim_to_map(prim)
        self.assertAlmostEqual(restored.scale, 0.05)
        self.assertAlmostEqual(restored.base, 10.0)

    def test_reciprocal_map_roundtrip(self):
        from ucon._cache import _map_to_prim, _prim_to_map
        from ucon.maps import ReciprocalMap

        m = ReciprocalMap(a=1000.0, rel_uncertainty=0.002)
        prim = _map_to_prim(m)
        restored = _prim_to_map(prim)
        self.assertAlmostEqual(restored.a, 1000.0)
        self.assertAlmostEqual(restored.rel_uncertainty, 0.002)

    def test_composed_map_roundtrip(self):
        from ucon._cache import _map_to_prim, _prim_to_map
        from ucon.maps import AffineMap, ComposedMap, LinearMap

        inner = LinearMap(a=2.0)
        outer = AffineMap(a=1.5, b=10.0)
        m = ComposedMap(outer=outer, inner=inner)
        prim = _map_to_prim(m)
        restored = _prim_to_map(prim)
        self.assertIsInstance(restored, ComposedMap)
        self.assertAlmostEqual(restored.inner.a, 2.0)
        self.assertAlmostEqual(restored.outer.a, 1.5)
        self.assertAlmostEqual(restored.outer.b, 10.0)

    def test_unknown_map_type_raises(self):
        from ucon._cache import _map_to_prim, _prim_to_map
        from ucon.maps import Map

        class FakeMap(Map):
            def __call__(self, x): return x
            def inverse(self): return self

        with self.assertRaises(TypeError):
            _map_to_prim(FakeMap())

    def test_unknown_prim_type_raises(self):
        from ucon._cache import _prim_to_map

        with self.assertRaises(ValueError):
            _prim_to_map({"_t": "UNKNOWN"})


class TestLazyNumpy(unittest.TestCase):
    """Lazy numpy accessor defers import."""

    def test_get_numpy_returns_module_when_available(self):
        from ucon.core._types import _get_numpy

        np = _get_numpy()
        # numpy is installed in the test env
        self.assertIsNotNone(np)
        self.assertEqual(np.__name__, "numpy")

    def test_get_numpy_caches_result(self):
        from ucon.core._types import _get_numpy

        first = _get_numpy()
        second = _get_numpy()
        self.assertIs(first, second)

    def test_maps_get_numpy_returns_module(self):
        from ucon.maps import _get_numpy

        np = _get_numpy()
        self.assertIsNotNone(np)
        self.assertEqual(np.__name__, "numpy")

    def test_is_array_with_ndarray(self):
        import numpy as np
        from ucon.maps import _is_array

        self.assertTrue(_is_array(np.array([1, 2, 3])))

    def test_is_array_with_list(self):
        from ucon.maps import _is_array

        self.assertFalse(_is_array([1, 2, 3]))

    def test_number_array_still_works(self):
        """NumberArray construction works with lazy numpy."""
        from ucon.core import NumberArray, Unit
        from ucon.dimension import LENGTH

        u = Unit(name="_test_lazy_np", dimension=LENGTH)
        arr = NumberArray(quantities=[1.0, 2.0, 3.0], unit=u)
        self.assertEqual(len(arr), 3)

    def test_unit_call_with_list_returns_number_array(self):
        """Unit.__call__ with list delegates to NumberArray via lazy numpy."""
        from ucon.core import Unit
        from ucon.dimension import LENGTH

        u = Unit(name="_test_lazy_np_call", dimension=LENGTH)
        result = u([1.0, 2.0])
        from ucon.core import NumberArray
        self.assertIsInstance(result, NumberArray)


class TestCacheFirstLoading(unittest.TestCase):
    """The units.py cache-first path."""

    def test_units_module_has_meter(self):
        """Basic sanity: units loaded (from cache or TOML)."""
        from ucon import units

        self.assertTrue(hasattr(units, "meter"))
        self.assertEqual(units.meter.name, "meter")

    def test_cache_file_exists_after_import(self):
        """After import, a cache file should exist alongside the TOML."""
        cache_path = TOML_PATH.with_suffix(".cache")
        # The cache is written on first import if missing.
        # In CI or fresh env, it may not exist yet — trigger write.
        from ucon.serialization import from_toml

        graph = from_toml(TOML_PATH)
        write_cached_graph(graph, TOML_PATH)
        self.assertTrue(cache_path.exists())


class TestProductKeySerialization(unittest.TestCase):
    """Coverage for _serialize_product_key / _deserialize_product_tuple_key."""

    def test_product_key_roundtrip(self):
        from ucon._cache import _deserialize_product_tuple_key, _serialize_product_key
        from ucon.core import Scale, Unit, UnitFactor
        from ucon.dimension import LENGTH, MASS

        meter = Unit(name="meter", dimension=LENGTH)
        kg = Unit(name="kilogram", dimension=MASS)
        unit_map = {"meter": meter, "kilogram": kg}

        # Construct a product key tuple (the format Graph._product_key() uses)
        key = (
            ("meter", LENGTH, Scale.one, 1),
            ("kilogram", MASS, Scale.kilo, -1),
        )
        ser = _serialize_product_key(key)
        restored = _deserialize_product_tuple_key(ser, unit_map)
        self.assertIsNotNone(restored)
        self.assertEqual(len(restored), 2)
        self.assertEqual(restored[0][0], "meter")
        self.assertEqual(restored[1][0], "kilogram")

    def test_product_key_missing_unit_returns_none(self):
        from ucon._cache import _deserialize_product_tuple_key

        ser = [("nonexistent", "LENGTH", "one", 1)]
        result = _deserialize_product_tuple_key(ser, {})
        self.assertIsNone(result)


class TestUnitRefCodec(unittest.TestCase):
    """Coverage for _unit_ref / _resolve_unit_ref with UnitProduct."""

    def test_unit_ref_plain_unit(self):
        from ucon._cache import _resolve_unit_ref, _unit_ref
        from ucon.core import Unit
        from ucon.dimension import LENGTH

        meter = Unit(name="meter", dimension=LENGTH)
        ref = _unit_ref(meter)
        self.assertEqual(ref["_t"], "UR")
        self.assertEqual(ref["n"], "meter")

        unit_map = {"meter": meter}
        restored = _resolve_unit_ref(ref, unit_map)
        self.assertIs(restored, meter)

    def test_unit_ref_unit_product(self):
        from ucon._cache import _resolve_unit_ref, _unit_ref
        from ucon.core import Scale, Unit, UnitFactor, UnitProduct
        from ucon.dimension import LENGTH, TIME

        meter = Unit(name="meter", dimension=LENGTH)
        second = Unit(name="second", dimension=TIME)
        # m/s
        prod = UnitProduct({UnitFactor(meter, Scale.one): 1, UnitFactor(second, Scale.one): -1})

        ref = _unit_ref(prod)
        self.assertEqual(ref["_t"], "UP")
        self.assertEqual(len(ref["fs"]), 2)

        unit_map = {"meter": meter, "second": second}
        restored = _resolve_unit_ref(ref, unit_map)
        self.assertIsInstance(restored, UnitProduct)
        self.assertEqual(len(restored.factors), 2)


class TestContextRoundTrip(unittest.TestCase):
    """Contexts survive round-trip when present in the graph."""

    def test_contexts_preserved(self):
        """If the graph has contexts, they survive cache round-trip."""
        from ucon.serialization import from_toml

        original = from_toml(TOML_PATH)
        if not original._contexts:
            self.skipTest("No contexts in comprehensive.ucon.toml")

        raw = _to_primitives(original)
        restored = _from_primitives(raw)

        self.assertEqual(
            set(original._contexts.keys()),
            set(restored._contexts.keys()),
        )
        for name, orig_ctx in original._contexts.items():
            rest_ctx = restored._contexts[name]
            self.assertEqual(len(orig_ctx.edges), len(rest_ctx.edges))


class TestWriteFailurePath(unittest.TestCase):
    """write_cached_graph handles write errors gracefully."""

    def test_write_to_readonly_dir_returns_false(self):
        """Write to a non-writable directory returns False."""
        import tempfile
        import shutil

        from ucon.serialization import from_toml

        tmpdir = Path(tempfile.mkdtemp())
        try:
            toml_copy = tmpdir / "test.ucon.toml"
            shutil.copy2(TOML_PATH, toml_copy)
            graph = from_toml(toml_copy)

            # Point to a path in a non-existent directory
            bad_path = tmpdir / "nonexistent_dir" / "test.ucon.toml"
            result = write_cached_graph(graph, bad_path)
            self.assertFalse(result)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestFractionCodec(unittest.TestCase):
    """Coverage for fraction serialization edge cases."""

    def test_fraction_roundtrip(self):
        from fractions import Fraction

        from ucon._cache import _fraction_to_prim, _prim_to_fraction

        # Standard fraction
        f = Fraction(3, 7)
        prim = _fraction_to_prim(f)
        restored = _prim_to_fraction(prim)
        self.assertEqual(f, restored)

    def test_integer_as_fraction(self):
        from fractions import Fraction

        from ucon._cache import _prim_to_fraction

        # Plain int (as stored for integer-valued vector components)
        restored = _prim_to_fraction(5)
        self.assertEqual(restored, Fraction(5))


if __name__ == "__main__":
    unittest.main()

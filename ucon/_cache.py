# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
ucon._cache
============

Marshal-based binary cache for the conversion graph.

Provides a ~15-25x speedup over TOML parsing by serializing/deserializing
the fully-constructed :class:`~ucon.conversion.Graph` as a dict of
primitives via :mod:`marshal`.

**Security model:** ``marshal.loads()`` produces only primitive Python
types (``dict``, ``list``, ``tuple``, ``str``, ``int``, ``float``,
``bytes``, ``None``, ``bool``, ``frozenset``, ``set``, ``complex``).
No code execution occurs during deserialization. A tampered cache file
produces garbage data, not arbitrary code execution. The reconstruction
pass type-checks ``_t`` discriminators at every step.

**Invalidation:** mtime comparison, magic header, format version, Python
version, and cache schema version must all match. Mismatches silently
fall through to TOML.

**Disable:** set ``UCON_NO_CACHE=1`` to bypass all cache reads and writes.
"""
from __future__ import annotations

import marshal
import os
import struct
import sys
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Cache format constants
# ---------------------------------------------------------------------------

_MAGIC = b"UCM\x01"
_CACHE_SCHEMA = 1  # Bump when _to_primitives/_from_primitives change shape

# Header layout: magic(4) + format_ver(2) + py_major(1) + py_minor(1) + cache_ver(1) + reserved(3) = 12
_HEADER_FMT = "!4sHBBB3s"
_HEADER_SIZE = struct.calcsize(_HEADER_FMT)


def _env_disabled() -> bool:
    return os.environ.get("UCON_NO_CACHE", "").strip() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_cached_graph(toml_path: Path) -> "Graph | None":
    """Load graph from binary cache if fresh and valid.

    Returns ``None`` on any miss (missing, stale, corrupt, env-disabled).
    Never raises.
    """
    if _env_disabled():
        return None

    cache_path = toml_path.with_suffix(".cache")
    try:
        if not cache_path.exists():
            return None

        # Stale check: cache must be at least as new as TOML
        if cache_path.stat().st_mtime < toml_path.stat().st_mtime:
            return None

        data = cache_path.read_bytes()
        if len(data) < _HEADER_SIZE:
            return None

        # Validate header
        from ucon.serialization import FORMAT_VERSION

        magic, fmt_ver, py_major, py_minor, cache_ver, _reserved = struct.unpack(
            _HEADER_FMT, data[:_HEADER_SIZE]
        )
        if magic != _MAGIC:
            return None

        our_major, our_minor = (int(x) for x in FORMAT_VERSION.split("."))
        if fmt_ver != our_major:
            return None
        if py_major != sys.version_info.major or py_minor != sys.version_info.minor:
            return None
        if cache_ver != _CACHE_SCHEMA:
            return None

        raw = marshal.loads(data[_HEADER_SIZE:])
        if not isinstance(raw, dict):
            return None

        return _from_primitives(raw)
    except Exception:
        return None


def write_cached_graph(graph: "Graph", toml_path: Path) -> bool:
    """Serialize graph to binary cache.

    Returns ``False`` on failure (silently swallowed). Writes atomically
    via ``tempfile`` + ``os.replace``.
    """
    if _env_disabled():
        return False

    try:
        from ucon.serialization import FORMAT_VERSION

        raw = _to_primitives(graph)
        payload = marshal.dumps(raw)

        our_major, _our_minor = (int(x) for x in FORMAT_VERSION.split("."))
        header = struct.pack(
            _HEADER_FMT,
            _MAGIC,
            our_major,
            sys.version_info.major,
            sys.version_info.minor,
            _CACHE_SCHEMA,
            b"\x00\x00\x00",
        )

        cache_path = toml_path.with_suffix(".cache")
        fd, tmp = tempfile.mkstemp(
            dir=str(cache_path.parent), suffix=".cache.tmp"
        )
        try:
            os.write(fd, header + payload)
            os.close(fd)
            os.replace(tmp, str(cache_path))
        except Exception:
            os.close(fd) if not os.get_inheritable(fd) else None  # noqa: E501
            try:
                os.unlink(tmp)
            except OSError:
                pass
            return False
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Codec: Graph -> primitives
# ---------------------------------------------------------------------------


def _fraction_to_prim(f: Fraction) -> list:
    """Fraction -> [numerator, denominator]."""
    return [f.numerator, f.denominator]


def _map_to_prim(m: "Map") -> dict:
    """Serialize a Map subclass to a primitive dict."""
    from ucon.maps import (
        AffineMap,
        ComposedMap,
        ExpMap,
        LinearMap,
        LogMap,
        ReciprocalMap,
    )

    if isinstance(m, LinearMap):
        d: dict[str, Any] = {"_t": "L", "a": m.a}
        if m.rel_uncertainty != 0.0:
            d["u"] = m.rel_uncertainty
        return d
    if isinstance(m, AffineMap):
        d = {"_t": "A", "a": m.a, "b": m.b}
        if m.rel_uncertainty != 0.0:
            d["u"] = m.rel_uncertainty
        return d
    if isinstance(m, LogMap):
        return {
            "_t": "LG",
            "sc": m.scale,
            "ba": m.base,
            "ref": m.reference,
            "off": m.offset,
        }
    if isinstance(m, ExpMap):
        return {
            "_t": "EX",
            "sc": m.scale,
            "ba": m.base,
            "ref": m.reference,
            "off": m.offset,
        }
    if isinstance(m, ReciprocalMap):
        d = {"_t": "R", "a": m.a}
        if m.rel_uncertainty != 0.0:
            d["u"] = m.rel_uncertainty
        return d
    if isinstance(m, ComposedMap):
        return {
            "_t": "CM",
            "outer": _map_to_prim(m.outer),
            "inner": _map_to_prim(m.inner),
        }
    raise TypeError(f"Unknown Map type: {type(m).__name__}")


def _unit_ref(u: "Unit | UnitProduct") -> dict:
    """Create a serializable reference to a Unit or UnitProduct."""
    from ucon.core import Unit, UnitFactor, UnitProduct

    if isinstance(u, UnitProduct):
        factors = []
        for f, exp in u.factors.items():
            if isinstance(f, UnitFactor):
                factors.append((f.unit.name, f.scale.name, exp))
            else:
                factors.append((f.name, "one", exp))
        return {"_t": "UP", "fs": factors, "cs": u.canonical_scale}
    # Plain Unit
    return {"_t": "UR", "n": u.name}


def _to_primitives(graph: "Graph") -> dict:
    """Reduce a Graph to a dict of marshal-safe primitives."""
    from ucon.basis import Basis
    from ucon.basis.transforms import ConstantBoundBasisTransform
    from ucon.core import RebasedUnit
    from ucon.dimension import Dimension

    out: dict[str, Any] = {}

    # --- Pass 1: Collect all bases ---
    bases: dict[str, Basis] = {}
    # Gather bases from dimensions in unit edges
    for dim in graph._unit_edges:
        b = dim.vector.basis
        bases[b.name] = b
    # Gather from basis graph
    if graph._basis_graph is not None:
        for src, targets in graph._basis_graph._edges.items():
            bases[src.name] = src
            for tgt in targets:
                bases[tgt.name] = tgt

    for name, basis in bases.items():
        out[f"b:{name}"] = {
            "_t": "B",
            "n": name,
            "c": [(c.name, c.symbol) for c in basis],
        }

    # --- Pass 2: Collect all dimensions ---
    dims: dict[str, Dimension] = {}
    for dim in graph._unit_edges:
        dims[dim.name or str(dim.vector)] = dim
    # Also collect dims from registered units
    for unit in graph._name_registry_cs.values():
        d = unit.dimension
        dims[d.name or str(d.vector)] = d
    # Also collect dims from kind lattice (some kinds reference dims not used by any unit)
    if graph._kind_lattice is not None:
        for kind in graph._kind_lattice:
            d = kind.dimension
            dims[d.name or str(d.vector)] = d

    for key, dim in dims.items():
        out[f"d:{key}"] = {
            "_t": "D",
            "n": dim.name,
            "b": dim.vector.basis.name,
            "v": tuple(int(c) if isinstance(c, (int, Fraction)) and (not isinstance(c, Fraction) or c.denominator == 1) else _fraction_to_prim(Fraction(c)) for c in dim.vector.components),
            "s": dim.symbol,
            "tag": dim.tag,
        }

    # --- Pass 3: Collect all transforms (basis graph edges) ---
    if graph._basis_graph is not None:
        t_idx = 0
        for src_basis, targets in graph._basis_graph._edges.items():
            for tgt_basis, transform in targets.items():
                is_cb = isinstance(transform, ConstantBoundBasisTransform)
                td: dict[str, Any] = {
                    "_t": "TC" if is_cb else "T",
                    "s": src_basis.name,
                    "t": tgt_basis.name,
                    "m": tuple(
                        tuple(_fraction_to_prim(Fraction(e)) for e in row)
                        for row in transform.matrix
                    ),
                }
                if is_cb:
                    bindings = []
                    for b in transform.bindings:
                        bindings.append({
                            "sc": b.source_component.name,
                            "te_b": b.target_expression.basis.name,
                            "te_c": tuple(
                                _fraction_to_prim(Fraction(c))
                                for c in b.target_expression.components
                            ),
                            "cs": b.constant_symbol,
                            "exp": _fraction_to_prim(b.exponent),
                        })
                    td["bindings"] = bindings
                out[f"t:{t_idx}"] = td
                t_idx += 1

    # --- Pass 4: Units ---
    units_done: set[str] = set()
    for name, unit in graph._name_registry_cs.items():
        if unit.name in units_done:
            continue
        units_done.add(unit.name)
        ud: dict[str, Any] = {
            "_t": "U",
            "n": unit.name,
            "d": unit.dimension.name or str(unit.dimension.vector),
            "a": unit.aliases,
            "sc": unit.scalable,
        }
        if unit.base_form is not None:
            ud["bf"] = {
                "pf": unit.base_form.prefactor,
                "fs": [(u.name, exp) for u, exp in unit.base_form.factors],
            }
        out[f"u:{unit.name}"] = ud

    # --- Pass 5: Kinds ---
    if graph._kind_lattice is not None:
        for kind in graph._kind_lattice:
            out[f"k:{kind.name}"] = {
                "_t": "K",
                "n": kind.name,
                "d": kind.dimension.name or str(kind.dimension.vector),
                "p": kind.parent.name if kind.parent else None,
                "jp": kind.join_policy.value,
                "a": kind.aliases,
            }

    # --- Pass 6: Constants ---
    for const in graph._package_constants:
        out[f"c:{const.symbol}"] = {
            "_t": "C",
            "sym": const.symbol,
            "n": const.name,
            "v": const.value,
            "u": _unit_ref(const.unit),
            "unc": const.uncertainty,
            "src": const.source,
            "cat": const.category,
            "a": const.aliases,
            "k": const.kind.name if const.kind else None,
        }

    # --- Pass 7: Unit edges (both directions for fast reconstruction) ---
    ue_idx = 0
    for dim, src_dict in graph._unit_edges.items():
        dim_key = dim.name or str(dim.vector)
        for src_node, dst_dict in src_dict.items():
            # Skip RebasedUnit nodes — handled in rebased pass
            if isinstance(src_node, RebasedUnit):
                continue
            for dst_node, edge_map in dst_dict.items():
                if isinstance(dst_node, RebasedUnit):
                    continue
                out[f"ue:{ue_idx}"] = {
                    "_t": "UE",
                    "dim": dim_key,
                    "src": src_node.name,
                    "dst": dst_node.name,
                    "map": _map_to_prim(edge_map),
                }
                ue_idx += 1

    # --- Pass 8: Product edges (both directions for fast reconstruction) ---
    pe_idx = 0
    for src_key, dst_dict in graph._product_edges.items():
        for dst_key, edge_map in dst_dict.items():
            src_ser = _serialize_product_key(src_key)
            dst_ser = _serialize_product_key(dst_key)
            out[f"pe:{pe_idx}"] = {
                "_t": "PE",
                "src_key": src_ser,
                "dst_key": dst_ser,
                "map": _map_to_prim(edge_map),
            }
            pe_idx += 1

    # --- Pass 9: Cross-basis edges (rebased units) ---
    # For each rebased unit, find the edges from it to regular units and
    # serialize the forward edge + transform reference.
    rb_idx = 0
    for orig_unit, rebased_set in graph._rebased.items():
        for rebased in rebased_set:
            bt = rebased.basis_transform
            dim = rebased.rebased_dimension
            # Find edges from this rebased node to regular units
            dst_edges = []
            if dim in graph._unit_edges and rebased in graph._unit_edges[dim]:
                for dst_node, edge_map in graph._unit_edges[dim][rebased].items():
                    if isinstance(dst_node, RebasedUnit):
                        continue
                    dst_edges.append({
                        "dst": dst_node.name,
                        "map": _map_to_prim(edge_map),
                    })
            out[f"rb:{rb_idx}"] = {
                "_t": "RB",
                "orig": orig_unit.name,
                "rd": dim.name or str(dim.vector),
                "bt_s": bt.source.name,
                "bt_t": bt.target.name,
                "edges": dst_edges,
            }
            rb_idx += 1

    # --- Pass 10: Contexts ---
    for ctx_name, ctx in graph._contexts.items():
        edges = []
        for edge in ctx.edges:
            edges.append({
                "src": _unit_ref(edge.src),
                "dst": _unit_ref(edge.dst),
                "map": _map_to_prim(edge.map),
            })
        out[f"cx:{ctx_name}"] = {
            "_t": "CX",
            "n": ctx.name,
            "desc": ctx.description,
            "edges": edges,
        }

    # --- Meta ---
    out["_meta"] = {
        "loaded_packages": tuple(graph._loaded_packages),
    }

    return out


def _serialize_product_key(key: tuple) -> list:
    """Serialize a product key tuple to marshal-safe form."""
    result = []
    for item in key:
        # Each item is (name, dimension, scale, exp)
        name, dim, scale, exp = item
        result.append((
            name,
            dim.name if hasattr(dim, "name") else str(dim),
            scale.name if hasattr(scale, "name") else str(scale),
            exp,
        ))
    return result


# ---------------------------------------------------------------------------
# Codec: primitives -> Graph
# ---------------------------------------------------------------------------


def _prim_to_fraction(p: Any) -> Fraction:
    """Deserialize a Fraction from [numerator, denominator] or plain int."""
    if isinstance(p, list):
        return Fraction(p[0], p[1])
    if isinstance(p, int):
        return Fraction(p)
    return Fraction(p)


def _prim_to_map(d: dict) -> "Map":
    """Reconstruct a Map from a primitive dict."""
    from ucon.maps import (
        AffineMap,
        ComposedMap,
        ExpMap,
        LinearMap,
        LogMap,
        ReciprocalMap,
    )

    t = d["_t"]
    if t == "L":
        return LinearMap(a=d["a"], rel_uncertainty=d.get("u", 0.0))
    if t == "A":
        return AffineMap(a=d["a"], b=d["b"], rel_uncertainty=d.get("u", 0.0))
    if t == "LG":
        return LogMap(
            scale=d["sc"], base=d["ba"], reference=d["ref"], offset=d["off"]
        )
    if t == "EX":
        return ExpMap(
            scale=d["sc"], base=d["ba"], reference=d["ref"], offset=d["off"]
        )
    if t == "R":
        return ReciprocalMap(a=d["a"], rel_uncertainty=d.get("u", 0.0))
    if t == "CM":
        return ComposedMap(
            outer=_prim_to_map(d["outer"]),
            inner=_prim_to_map(d["inner"]),
        )
    raise ValueError(f"Unknown map type: {t}")


def _resolve_unit_ref(
    ref: dict, unit_map: "dict[str, Unit]"
) -> "Unit | UnitProduct":
    """Resolve a serialized unit reference to a Unit or UnitProduct."""
    from ucon.core import Scale, UnitFactor, UnitProduct

    if ref["_t"] == "UR":
        return unit_map[ref["n"]]
    if ref["_t"] == "UP":
        factors: dict = {}
        for unit_name, scale_name, exp in ref["fs"]:
            u = unit_map[unit_name]
            s = Scale[scale_name]
            factors[UnitFactor(u, s)] = exp
        return UnitProduct(factors, canonical_scale=ref.get("cs", 1.0))
    raise ValueError(f"Unknown unit ref type: {ref['_t']}")


def _from_primitives(raw: dict) -> "Graph":
    """Reconstruct a Graph from a dict of primitives."""
    from ucon.basis import Basis, BasisComponent, BasisGraph, Vector
    from ucon.basis.transforms import (
        BasisTransform,
        ConstantBinding,
        ConstantBoundBasisTransform,
    )
    from ucon.constants import Constant
    from ucon.contexts import ContextEdge, ConversionContext
    from ucon.conversion import Graph
    from ucon.core import BaseForm, RebasedUnit, Unit
    from ucon.dimension import Dimension
    from ucon.kinds.lattice import KindLattice
    from ucon.kinds.types import Kind

    # --- Pass 1: Bases ---
    basis_map: dict[str, Basis] = {}
    for key, val in raw.items():
        if not key.startswith("b:"):
            continue
        if val.get("_t") != "B":
            continue
        components = [BasisComponent(name=c[0], symbol=c[1]) for c in val["c"]]
        basis_map[val["n"]] = Basis(val["n"], components)

    # --- Pass 2: Dimensions ---
    dim_map: dict[str, Dimension] = {}
    for key, val in raw.items():
        if not key.startswith("d:"):
            continue
        if val.get("_t") != "D":
            continue
        basis = basis_map[val["b"]]
        # Reconstruct vector components
        components = []
        for c in val["v"]:
            if isinstance(c, (list, tuple)):
                components.append(Fraction(c[0], c[1]))
            else:
                components.append(Fraction(c))
        vector = Vector(basis, tuple(components))
        dim = Dimension(
            vector=vector,
            name=val["n"],
            symbol=val["s"],
            tag=val["tag"],
        )
        dim_key = val["n"] or str(vector)
        dim_map[dim_key] = dim

    # --- Pass 3: Transforms ---
    transform_list: list = []
    transform_by_pair: dict[tuple[str, str], Any] = {}
    for key, val in raw.items():
        if not key.startswith("t:"):
            continue
        t = val.get("_t")
        if t not in ("T", "TC"):
            continue
        src_basis = basis_map[val["s"]]
        tgt_basis = basis_map[val["t"]]
        matrix = tuple(
            tuple(Fraction(e[0], e[1]) if isinstance(e, (list, tuple)) else Fraction(e) for e in row)
            for row in val["m"]
        )
        if t == "TC":
            bindings = []
            for bd in val["bindings"]:
                te_basis = basis_map[bd["te_b"]]
                te_components = tuple(
                    Fraction(c[0], c[1]) if isinstance(c, (list, tuple)) else Fraction(c)
                    for c in bd["te_c"]
                )
                bindings.append(ConstantBinding(
                    source_component=BasisComponent(bd["sc"], symbol=None),
                    target_expression=Vector(te_basis, te_components),
                    constant_symbol=bd["cs"],
                    exponent=Fraction(bd["exp"][0], bd["exp"][1]) if isinstance(bd["exp"], (list, tuple)) else Fraction(bd["exp"]),
                ))
            transform = ConstantBoundBasisTransform(
                source=src_basis,
                target=tgt_basis,
                matrix=matrix,
                bindings=tuple(bindings),
            )
        else:
            transform = BasisTransform(
                source=src_basis,
                target=tgt_basis,
                matrix=matrix,
            )
        transform_list.append(transform)
        transform_by_pair[(val["s"], val["t"])] = transform

    # --- Pass 4: BasisGraph ---
    basis_graph = BasisGraph()
    for transform in transform_list:
        basis_graph.add_transform(transform)

    # --- Pass 5: Create Graph ---
    meta = raw.get("_meta", {})
    graph = Graph(
        _basis_graph=basis_graph if transform_list else None,
        _loaded_packages=frozenset(meta.get("loaded_packages", ())),
    )

    # --- Pass 6a: Units (create and register, without base_form) ---
    unit_map: dict[str, Unit] = {}
    unit_base_form_deferred: dict[str, dict] = {}
    for key, val in raw.items():
        if not key.startswith("u:"):
            continue
        if val.get("_t") != "U":
            continue
        dim_key = val["d"]
        dim = dim_map.get(dim_key)
        if dim is None:
            continue
        unit = Unit(
            name=val["n"],
            dimension=dim,
            aliases=tuple(val["a"]) if val["a"] else (),
            scalable=val["sc"],
        )
        unit_map[val["n"]] = unit
        graph.register_unit(unit)
        if "bf" in val and val["bf"] is not None:
            unit_base_form_deferred[val["n"]] = val["bf"]

    # --- Pass 6b: Units (resolve base_form cross-references) ---
    for unit_name, bf_data in unit_base_form_deferred.items():
        unit = unit_map[unit_name]
        factors = []
        for factor_name, exp in bf_data["fs"]:
            factor_unit = unit_map.get(factor_name)
            if factor_unit is None:
                continue
            factors.append((factor_unit, exp))
        bf = BaseForm(factors=tuple(factors), prefactor=bf_data["pf"])
        try:
            unit._set_base_form(bf)
        except (ValueError, TypeError):
            pass  # Already set or type mismatch; skip silently

    # --- Pass 7: Kinds ---
    kind_list: list[Kind] = []
    kind_data_map: dict[str, dict] = {}
    for key, val in raw.items():
        if not key.startswith("k:"):
            continue
        if val.get("_t") != "K":
            continue
        kind_data_map[val["n"]] = val

    # Build kinds in dependency order (parents first)
    kind_obj_map: dict[str, Kind] = {}
    _build_kinds_recursive(kind_data_map, kind_obj_map, dim_map)

    if kind_obj_map:
        kind_lattice = KindLattice(kind_obj_map.values())
        graph._kind_lattice = kind_lattice

    # --- Pass 8: Constants ---
    constants = []
    for key, val in raw.items():
        if not key.startswith("c:"):
            continue
        if val.get("_t") != "C":
            continue
        unit = _resolve_unit_ref(val["u"], unit_map)
        kind = kind_obj_map.get(val["k"]) if val["k"] else None
        const = Constant(
            symbol=val["sym"],
            name=val["n"],
            value=val["v"],
            unit=unit,
            uncertainty=val["unc"],
            source=val["src"],
            category=val["cat"],
            aliases=tuple(val["a"]) if val["a"] else (),
            kind=kind,
        )
        constants.append(const)
    graph._package_constants = tuple(constants)

    # --- Pass 9: Unit edges (direct insertion, both directions pre-serialized) ---
    for key, val in raw.items():
        if not key.startswith("ue:"):
            continue
        if val.get("_t") != "UE":
            continue
        src_unit = unit_map.get(val["src"])
        dst_unit = unit_map.get(val["dst"])
        if src_unit is None or dst_unit is None:
            continue
        dim_key = val["dim"]
        dim = dim_map.get(dim_key)
        if dim is None:
            continue
        edge_map = _prim_to_map(val["map"])
        # Direct dict insertion — skip add_edge() overhead (inverse computation,
        # cyclic checks, cache clearing). Both directions are stored in cache.
        graph._ensure_dimension(dim)
        graph._unit_edges[dim].setdefault(src_unit, {})[dst_unit] = edge_map

    # --- Pass 10: Product edges (direct insertion) ---
    for key, val in raw.items():
        if not key.startswith("pe:"):
            continue
        if val.get("_t") != "PE":
            continue
        src_key = _deserialize_product_tuple_key(val["src_key"], unit_map)
        dst_key = _deserialize_product_tuple_key(val["dst_key"], unit_map)
        if src_key is None or dst_key is None:
            continue
        edge_map = _prim_to_map(val["map"])
        graph._product_edges.setdefault(src_key, {})[dst_key] = edge_map

    # --- Pass 11: Cross-basis edges (rebased units) ---
    for key, val in raw.items():
        if not key.startswith("rb:"):
            continue
        if val.get("_t") != "RB":
            continue
        orig = unit_map.get(val["orig"])
        if orig is None:
            continue
        rd = dim_map.get(val["rd"])
        if rd is None:
            continue
        bt = transform_by_pair.get((val["bt_s"], val["bt_t"]))
        if bt is None:
            continue
        rebased = RebasedUnit(
            original=orig,
            rebased_dimension=rd,
            basis_transform=bt,
        )
        graph._rebased.setdefault(orig, set()).add(rebased)
        # Reconstruct the cross-basis edges
        graph._ensure_dimension(rd)
        for edge_data in val.get("edges", []):
            dst_unit = unit_map.get(edge_data["dst"])
            if dst_unit is None:
                continue
            edge_map = _prim_to_map(edge_data["map"])
            # Directly insert into the edge dict (rebased → dst and dst → rebased)
            graph._unit_edges[rd].setdefault(rebased, {})[dst_unit] = edge_map
            graph._unit_edges[rd].setdefault(dst_unit, {})[rebased] = edge_map.inverse()

    # --- Pass 12: Contexts ---
    for key, val in raw.items():
        if not key.startswith("cx:"):
            continue
        if val.get("_t") != "CX":
            continue
        edges = []
        for edge_data in val["edges"]:
            src = _resolve_unit_ref(edge_data["src"], unit_map)
            dst = _resolve_unit_ref(edge_data["dst"], unit_map)
            edge_map = _prim_to_map(edge_data["map"])
            edges.append(ContextEdge(src=src, dst=dst, map=edge_map))
        ctx = ConversionContext(
            name=val["n"],
            edges=tuple(edges),
            description=val["desc"],
        )
        graph._contexts[val["n"]] = ctx

    return graph


def _build_kinds_recursive(
    data_map: dict[str, dict],
    obj_map: dict[str, "Kind"],
    dim_map: dict[str, "Dimension"],
) -> None:
    """Build Kind objects in parent-first order."""
    from ucon.kinds.types import JoinPolicy, Kind

    def _build(name: str) -> "Kind":
        if name in obj_map:
            return obj_map[name]
        val = data_map[name]
        parent = None
        if val["p"] is not None:
            parent = _build(val["p"])
        dim_key = val["d"]
        dim = dim_map.get(dim_key)
        kind = Kind(
            name=val["n"],
            dimension=dim,
            parent=parent,
            join_policy=JoinPolicy(val["jp"]),
            aliases=tuple(val["a"]) if val["a"] else (),
        )
        obj_map[name] = kind
        return kind

    for name in data_map:
        _build(name)


def _deserialize_product_key(
    ser: list, unit_map: "dict[str, Unit]"
) -> "UnitProduct | None":
    """Reconstruct a UnitProduct from a serialized product key."""
    from ucon.core import Scale, UnitFactor, UnitProduct

    factors: dict = {}
    for item in ser:
        name, _dim_name, scale_name, exp = item
        u = unit_map.get(name)
        if u is None:
            return None
        try:
            s = Scale[scale_name]
        except KeyError:
            s = Scale.one
        factors[UnitFactor(u, s)] = exp
    if not factors:
        return None
    return UnitProduct(factors)


def _deserialize_product_tuple_key(
    ser: list, unit_map: "dict[str, Unit]"
) -> "tuple | None":
    """Reconstruct a product key tuple from serialized form.

    The product key is a hashable tuple of (name, dimension, scale, exp)
    tuples — the same format used by ``Graph._product_key()``.
    """
    from ucon.core import Scale

    result = []
    for item in ser:
        name, dim_name, scale_name, exp = item
        u = unit_map.get(name)
        if u is None:
            return None
        try:
            s = Scale[scale_name]
        except KeyError:
            s = Scale.one
        result.append((name, u.dimension, s, exp))
    return tuple(result)

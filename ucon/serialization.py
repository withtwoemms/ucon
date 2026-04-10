# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
ucon.serialization
==================

Full round-trip serialization of ConversionGraph to/from TOML.

Exports ``to_toml()`` and ``from_toml()`` which handle:
- Bases, dimensions, and transforms (including ConstantBound)
- Unit edges (forward-only; inverses reconstructed on import)
- Product edges (composite unit conversions)
- Cross-basis edges (via RebasedUnit provenance)
- Physical constants
- Fraction preservation for exact round-trip of basis matrices

Format version: 1.2
"""
from __future__ import annotations

import re
import sys
import warnings
from fractions import Fraction
from pathlib import Path
from typing import Union

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from ucon.basis import (
    Basis,
    BasisComponent,
    BasisGraph,
    BasisTransform,
    Vector,
)
from ucon.basis.transforms import ConstantBoundBasisTransform, ConstantBinding
from ucon.constants import Constant
from ucon.core import BaseForm, RebasedUnit, Scale, Unit, UnitFactor, UnitProduct
from ucon.dimension import Dimension, resolve, _DIMENSION_ATTRS
from ucon.maps import (
    AffineMap,
    LinearMap,
    Map,
)

FORMAT_VERSION = "1.3"


class GraphLoadError(Exception):
    """Raised when a TOML graph file cannot be loaded or validated."""
    pass


def _require(spec: dict, key: str, section: str) -> object:
    """Retrieve a required key from a TOML dict, raising on absence."""
    try:
        return spec[key]
    except KeyError:
        raise GraphLoadError(
            f"Missing required key '{key}' in [{section}]"
        ) from None


def _check_format_version(doc: dict) -> None:
    """Validate the ``format_version`` field in a TOML document.

    Rules:
    - Missing ``format_version`` (or missing ``[package]``) → silently accepted
      for backward compatibility with old files.
    - Major version mismatch → :class:`GraphLoadError`.
    - File minor > our minor → :class:`UserWarning`.
    """
    raw = doc.get("package", {}).get("format_version")
    if raw is None:
        return  # backward compat with old files
    parts = str(raw).split(".")
    if len(parts) < 2:
        raise GraphLoadError(
            f"Malformed format_version: '{raw}' (expected 'major.minor')"
        )
    try:
        file_major, file_minor = int(parts[0]), int(parts[1])
    except ValueError:
        raise GraphLoadError(f"Malformed format_version: '{raw}'") from None
    our_major, our_minor = (int(x) for x in FORMAT_VERSION.split("."))
    if file_major != our_major:
        raise GraphLoadError(
            f"Incompatible format version: file is {raw}, "
            f"this library supports {FORMAT_VERSION}.x"
        )
    if file_minor > our_minor:
        warnings.warn(
            f"TOML file format version {raw} is newer than supported "
            f"{FORMAT_VERSION}. Some features may not be loaded.",
            stacklevel=3,
        )


# ---------------------------------------------------------------------------
# Map serialization
# ---------------------------------------------------------------------------

def _serialize_map(m: Map) -> dict:
    """Serialize a Map instance to a TOML-friendly dict.

    Delegates to ``Map.to_dict()``.
    """
    return m.to_dict()


# ---------------------------------------------------------------------------
# Edge extraction (forward-only)
# ---------------------------------------------------------------------------

def _unit_sort_key(unit: Unit) -> str:
    """Stable sort key for units."""
    return unit.name


def _extract_forward_edges(graph) -> list[dict]:
    """Extract forward-only unit edges from the graph.

    Skips RebasedUnit nodes (handled by cross-basis extraction).
    Deduplicates by only emitting edges where src.name < dst.name.
    """
    edges = []
    for dim, dim_edges in graph._unit_edges.items():
        for src, neighbors in dim_edges.items():
            if isinstance(src, RebasedUnit):
                continue
            for dst, m in neighbors.items():
                if isinstance(dst, RebasedUnit):
                    continue
                # Deduplicate: only emit forward direction
                if src.name >= dst.name:
                    continue
                edge = _edge_dict(src.name, dst.name, m)
                edges.append(edge)
    # Stable sort for deterministic output
    edges.sort(key=lambda e: (e["src"], e["dst"]))
    return edges


def _extract_product_edges(graph) -> list[dict]:
    """Extract forward-only product edges from the graph."""
    edges = []
    seen = set()
    for src_key, neighbors in graph._product_edges.items():
        for dst_key, m in neighbors.items():
            # Deduplicate: sort the pair
            pair = tuple(sorted([src_key, dst_key]))
            if pair in seen:
                continue
            seen.add(pair)

            # Reconstruct shorthand expressions from product keys
            src_expr = _product_key_to_expression(src_key)
            dst_expr = _product_key_to_expression(dst_key)
            edge = _edge_dict(src_expr, dst_expr, m)
            edge["product"] = True
            edges.append(edge)
    edges.sort(key=lambda e: (e["src"], e["dst"]))
    return edges


def _product_key_to_expression(key: tuple) -> str:
    """Convert a product key tuple back to a unit expression string.

    Each element is ``(name, dimension, scale, exponent)``.

    Uses ``/`` notation when there are both positive and negative exponents::

        meter^1, second^-1 → "meter/second"
        kg^1, m^1, s^-2   → "kg*m/s^2"

    All-negative exponents keep the ``^-n`` form (no ``"1/..."``).
    """
    num_parts: list[str] = []
    den_parts: list[str] = []

    for name, dim, scale, exp in key:
        scale_val = scale.value.evaluated if hasattr(scale, 'value') else 1.0
        prefix = ""
        if abs(scale_val - 1.0) > 1e-15:
            prefix = scale.shorthand if hasattr(scale, 'shorthand') else ""
        unit_str = prefix + name if prefix else name

        if exp > 0:
            if abs(exp - 1.0) < 1e-12:
                num_parts.append(unit_str)
            else:
                num_parts.append(f"{unit_str}^{exp}")
        else:
            abs_exp = abs(exp)
            if abs(abs_exp - 1.0) < 1e-12:
                den_parts.append(unit_str)
            else:
                den_parts.append(f"{unit_str}^{abs_exp}")

    if not num_parts and not den_parts:
        return "dimensionless"

    # All-negative: no numerator to anchor the `/` on → use ^-n form
    if not num_parts:
        neg_parts = []
        for name, dim, scale, exp in key:
            scale_val = scale.value.evaluated if hasattr(scale, 'value') else 1.0
            prefix = ""
            if abs(scale_val - 1.0) > 1e-15:
                prefix = scale.shorthand if hasattr(scale, 'shorthand') else ""
            unit_str = prefix + name if prefix else name
            if abs(exp - (-1.0)) < 1e-12:
                neg_parts.append(f"{unit_str}^-1")
            else:
                neg_parts.append(f"{unit_str}^{exp}")
        return "*".join(neg_parts)

    num_expr = "*".join(num_parts)
    if den_parts:
        den_expr = "/".join(den_parts)
        return f"{num_expr}/{den_expr}"
    return num_expr


def _extract_cross_basis_edges(graph) -> list[dict]:
    """Extract cross-basis edges from RebasedUnit provenance."""
    edges = []
    for original_unit, rebased_list in graph._rebased.items():
        for rebased in rebased_list:
            dim = rebased.dimension
            if dim not in graph._unit_edges:
                continue
            if rebased not in graph._unit_edges[dim]:
                continue
            for dst, m in graph._unit_edges[dim][rebased].items():
                if isinstance(dst, RebasedUnit):
                    continue
                # Determine the transform name
                bt = rebased.basis_transform
                transform_name = f"{bt.source.name}_TO_{bt.target.name}"
                edge = _edge_dict(original_unit.name, dst.name, m)
                edge["transform"] = transform_name
                edges.append(edge)
    edges.sort(key=lambda e: (e.get("transform", ""), e["src"], e["dst"]))
    return edges


def _edge_dict(src: str, dst: str, m: Map) -> dict:
    """Build an edge dict with shorthand for simple maps."""
    d: dict = {"src": src, "dst": dst}
    if isinstance(m, LinearMap):
        d["factor"] = m.a
        if m.rel_uncertainty > 0:
            d["rel_uncertainty"] = m.rel_uncertainty
    elif isinstance(m, AffineMap):
        d["factor"] = m.a
        d["offset"] = m.b
        if m.rel_uncertainty > 0:
            d["rel_uncertainty"] = m.rel_uncertainty
    else:
        d["map"] = _serialize_map(m)
    return d


# ---------------------------------------------------------------------------
# Basis / Dimension / Transform serialization
# ---------------------------------------------------------------------------

def _serialize_basis(basis: Basis) -> dict:
    """Serialize a Basis to TOML dict."""
    components = []
    for comp in basis:
        c: dict = {"name": comp.name}
        if comp.symbol is not None and comp.symbol != comp.name:
            c["symbol"] = comp.symbol
        components.append(c)
    return {"components": components}


def _serialize_dimension(dim: Dimension) -> dict:
    """Serialize a Dimension to TOML dict."""
    d: dict = {"basis": dim.vector.basis.name}
    # Serialize vector components as list (use strings for Fractions)
    components = []
    for c in dim.vector.components:
        if isinstance(c, Fraction) and c.denominator != 1:
            components.append(str(c))
        else:
            components.append(int(c))
    d["vector"] = components
    if dim.tag is not None:
        d["tag"] = dim.tag
    return d


def _serialize_transform(
    bt: Union[BasisTransform, ConstantBoundBasisTransform],
) -> dict:
    """Serialize a BasisTransform to TOML dict."""
    d: dict = {
        "source": bt.source.name,
        "target": bt.target.name,
    }
    # Serialize matrix with Fraction preservation
    matrix = []
    for row in bt.matrix:
        matrix_row = []
        for val in row:
            if isinstance(val, Fraction) and val.denominator != 1:
                matrix_row.append(str(val))
            else:
                matrix_row.append(int(val) if isinstance(val, Fraction) else val)
        matrix.append(matrix_row)
    d["matrix"] = matrix

    # Serialize bindings for ConstantBoundBasisTransform
    if isinstance(bt, ConstantBoundBasisTransform) and bt.bindings:
        bindings = []
        for binding in bt.bindings:
            b: dict = {
                "source_component": binding.source_component.name,
                "constant_symbol": binding.constant_symbol,
            }
            if binding.exponent != Fraction(1):
                b["exponent"] = str(binding.exponent)
            # Serialize target expression vector
            target_vec = []
            for c in binding.target_expression.components:
                if isinstance(c, Fraction) and c.denominator != 1:
                    target_vec.append(str(c))
                else:
                    target_vec.append(int(c))
            b["target_expression"] = target_vec
            bindings.append(b)
        d["bindings"] = bindings

    return d


def _serialize_unit(unit: Unit) -> dict:
    """Serialize a Unit to TOML dict."""
    d: dict = {"name": unit.name, "dimension": unit.dimension.name}
    if unit.aliases:
        d["aliases"] = list(unit.aliases)
    if unit.base_form is not None:
        d["base_form"] = {
            "prefactor": float(unit.base_form.prefactor),
            "factors": [[u.name, float(exp)] for u, exp in unit.base_form.factors],
        }
    return d


def _serialize_constant(const: Constant) -> dict:
    """Serialize a Constant to TOML dict."""
    d: dict = {
        "symbol": const.symbol,
        "name": const.name,
        "value": const.value,
        "unit": const.unit.shorthand if hasattr(const.unit, 'shorthand') else str(const.unit),
        "category": const.category,
    }
    if const.uncertainty is not None:
        d["uncertainty"] = const.uncertainty
    if const.source != "CODATA 2022":
        d["source"] = const.source
    return d


# ---------------------------------------------------------------------------
# Export: to_toml()
# ---------------------------------------------------------------------------

def to_toml(graph, path: Union[str, Path]) -> None:
    """Export a ConversionGraph to a TOML file.

    Parameters
    ----------
    graph : ConversionGraph
        The graph to export.
    path : str or Path
        Destination file path.
    """
    try:
        import tomli_w
    except ImportError:
        raise ImportError(
            "tomli_w is required for TOML export. "
            "Install with: pip install ucon[serialization]"
        )

    path = Path(path)
    doc: dict = {}

    # [package]
    doc["package"] = {
        "name": path.stem.replace(".ucon", ""),
        "format_version": FORMAT_VERSION,
    }
    if graph._loaded_packages:
        doc["package"]["loaded_packages"] = sorted(graph._loaded_packages)

    # Collect all bases and dimensions used in the graph
    bases: dict[str, Basis] = {}
    dimensions: dict[str, Dimension] = {}

    for dim in graph._unit_edges:
        if dim.vector.basis.name not in bases:
            bases[dim.vector.basis.name] = dim.vector.basis
        if dim.name and dim.name not in dimensions:
            dimensions[dim.name] = dim

    # Also collect bases from transforms (ensures bases like CGS_EMU that
    # are only referenced by transforms are included in the serialized output)
    _transforms_for_bases = _collect_transforms(graph)
    for _bt in _transforms_for_bases.values():
        if _bt.source.name not in bases:
            bases[_bt.source.name] = _bt.source
        if _bt.target.name not in bases:
            bases[_bt.target.name] = _bt.target

    # [bases.*]
    if bases:
        doc["bases"] = {
            name: _serialize_basis(b) for name, b in sorted(bases.items())
        }

    # [dimensions.*]
    if dimensions:
        doc["dimensions"] = {
            name: _serialize_dimension(d)
            for name, d in sorted(dimensions.items())
        }

    # [transforms.*]
    transforms = _collect_transforms(graph)
    if transforms:
        doc["transforms"] = {
            name: _serialize_transform(bt)
            for name, bt in sorted(transforms.items())
        }

    # [[units]]
    units_list = _collect_units(graph)
    if units_list:
        doc["units"] = units_list

    # [[edges]]
    edges = _extract_forward_edges(graph)
    if edges:
        doc["edges"] = edges

    # [[product_edges]]
    product_edges = _extract_product_edges(graph)
    if product_edges:
        doc["product_edges"] = product_edges

    # [[cross_basis_edges]]
    cross_basis_edges = _extract_cross_basis_edges(graph)
    if cross_basis_edges:
        doc["cross_basis_edges"] = cross_basis_edges

    # [[constants]]
    constants = _collect_constants(graph)
    if constants:
        doc["constants"] = constants

    # [contexts.*]
    contexts = _collect_contexts(graph)
    if contexts:
        doc["contexts"] = contexts

    with open(path, "wb") as f:
        tomli_w.dump(doc, f)


def _collect_transforms(graph) -> dict[str, Union[BasisTransform, ConstantBoundBasisTransform]]:
    """Collect all unique BasisTransforms from the graph."""
    transforms: dict[str, Union[BasisTransform, ConstantBoundBasisTransform]] = {}
    for rebased_list in graph._rebased.values():
        for rebased in rebased_list:
            bt = rebased.basis_transform
            name = f"{bt.source.name}_TO_{bt.target.name}"
            if name not in transforms:
                transforms[name] = bt
    # Also include basis_graph transforms if available
    if graph._basis_graph is not None:
        for src, targets in graph._basis_graph._edges.items():
            for tgt, bt in targets.items():
                name = f"{bt.source.name}_TO_{bt.target.name}"
                if name not in transforms:
                    transforms[name] = bt
    return transforms


def _collect_units(graph) -> list[dict]:
    """Collect all registered units from the graph."""
    seen = set()
    units_list = []
    for name, unit in sorted(graph._name_registry_cs.items()):
        if isinstance(unit, RebasedUnit):
            continue
        if unit.name in seen:
            continue
        seen.add(unit.name)
        units_list.append(_serialize_unit(unit))
    return units_list


def _collect_constants(graph) -> list[dict]:
    """Collect constants from the graph."""
    constants = []
    for const in graph._package_constants:
        constants.append(_serialize_constant(const))
    return constants


def _collect_contexts(graph) -> dict[str, dict]:
    """Collect registered ConversionContext objects from the graph."""
    contexts: dict[str, dict] = {}
    for name, ctx in sorted(graph._contexts.items()):
        ctx_dict: dict = {}
        if ctx.description:
            ctx_dict["description"] = ctx.description
        edges = []
        for ce in ctx.edges:
            # Determine src/dst name
            src_name = (
                _product_key_to_expression(_product_key(ce.src))
                if isinstance(ce.src, UnitProduct)
                else ce.src.name
            )
            dst_name = (
                _product_key_to_expression(_product_key(ce.dst))
                if isinstance(ce.dst, UnitProduct)
                else ce.dst.name
            )
            edges.append(_edge_dict(src_name, dst_name, ce.map))
        ctx_dict["edges"] = edges
        contexts[name] = ctx_dict
    return contexts


def _product_key(prod: UnitProduct) -> tuple:
    """Build the hashable product key for a UnitProduct (same as ConversionGraph)."""
    return tuple(sorted(
        (uf.unit.name, uf.unit.dimension, uf.scale, exp)
        for uf, exp in prod.factors.items()
    ))


# ---------------------------------------------------------------------------
# Import: from_toml()
# ---------------------------------------------------------------------------

def from_toml(path: Union[str, Path], *, strict: bool = True):
    """Import a ConversionGraph from a TOML file.

    Parameters
    ----------
    path : str or Path
        Source file path.
    strict : bool
        When ``True`` (default), raise :class:`GraphLoadError` if any edge
        references an unresolvable unit.  When ``False``, silently skip
        unresolvable edges (forward-compatible loading of partial files).

    Returns
    -------
    ConversionGraph
        The reconstructed graph.
    """
    from ucon.graph import ConversionGraph, using_graph
    from ucon.packages import _build_map

    path = Path(path)
    with open(path, "rb") as f:
        doc = tomllib.load(f)

    _check_format_version(doc)

    # 1. Build bases
    basis_map: dict[str, Basis] = {}
    for name, spec in doc.get("bases", {}).items():
        comp_list = _require(spec, "components", f"bases.{name}")
        if not isinstance(comp_list, list):
            raise GraphLoadError(
                f"[bases.{name}].components must be a list"
            )
        components = []
        for i, c in enumerate(comp_list):
            if isinstance(c, dict):
                comp_name = _require(c, "name", f"bases.{name}.components[{i}]")
                components.append(BasisComponent(comp_name, c.get("symbol")))
            elif isinstance(c, str):
                components.append(BasisComponent(c))
            else:
                raise GraphLoadError(
                    f"[bases.{name}].components[{i}]: expected string or table, "
                    f"got {type(c).__name__}"
                )
        basis_map[name] = Basis(name, components)

    # 2. Build dimensions
    dim_map: dict[str, Dimension] = {}
    # Pre-populate with standard dimensions
    for name, dim in _DIMENSION_ATTRS.items():
        dim_map[name] = dim

    for name, spec in doc.get("dimensions", {}).items():
        if name in dim_map:
            continue  # Use standard dimension if available
        basis_name = _require(spec, "basis", f"dimensions.{name}")
        basis = basis_map.get(basis_name)
        if basis is None:
            raise GraphLoadError(
                f"[dimensions.{name}]: references unknown basis '{basis_name}'"
            )
        raw_vector = _require(spec, "vector", f"dimensions.{name}")
        if not isinstance(raw_vector, list):
            raise GraphLoadError(
                f"[dimensions.{name}].vector must be a list"
            )
        vec_components = tuple(
            Fraction(c) if isinstance(c, str) else c
            for c in raw_vector
        )
        vector = Vector(basis, vec_components)
        tag = spec.get("tag")
        dim_map[name] = Dimension(vector=vector, name=name, tag=tag)

    # 3. Build transforms
    transform_map: dict[str, Union[BasisTransform, ConstantBoundBasisTransform]] = {}
    for name, spec in doc.get("transforms", {}).items():
        src_name = _require(spec, "source", f"transforms.{name}")
        tgt_name = _require(spec, "target", f"transforms.{name}")
        source = basis_map.get(src_name)
        target = basis_map.get(tgt_name)
        if source is None:
            raise GraphLoadError(
                f"[transforms.{name}]: references unknown source basis '{src_name}'"
            )
        if target is None:
            raise GraphLoadError(
                f"[transforms.{name}]: references unknown target basis '{tgt_name}'"
            )

        # Parse matrix
        raw_matrix = _require(spec, "matrix", f"transforms.{name}")
        if not isinstance(raw_matrix, list):
            raise GraphLoadError(
                f"[transforms.{name}].matrix must be a list of lists"
            )
        matrix = tuple(
            tuple(
                Fraction(c) if isinstance(c, str) else Fraction(c)
                for c in row
            )
            for row in raw_matrix
        )

        # Check for bindings (ConstantBoundBasisTransform)
        if "bindings" in spec:
            bindings = []
            for i, b in enumerate(spec["bindings"]):
                section = f"transforms.{name}.bindings[{i}]"
                src_comp_name = _require(b, "source_component", section)
                # Find the source component
                src_comp = None
                for comp in source:
                    if comp.name == src_comp_name:
                        src_comp = comp
                        break
                if src_comp is None:
                    raise GraphLoadError(
                        f"[{section}]: unknown source_component '{src_comp_name}' "
                        f"in basis '{source.name}'"
                    )

                raw_target_vec = _require(b, "target_expression", section)
                target_vec = tuple(
                    Fraction(c) if isinstance(c, str) else Fraction(c)
                    for c in raw_target_vec
                )
                const_sym = _require(b, "constant_symbol", section)
                exp = Fraction(b.get("exponent", "1"))
                bindings.append(ConstantBinding(
                    source_component=src_comp,
                    target_expression=Vector(target, target_vec),
                    constant_symbol=const_sym,
                    exponent=exp,
                ))
            transform_map[name] = ConstantBoundBasisTransform(
                source=source,
                target=target,
                matrix=matrix,
                bindings=tuple(bindings),
            )
        else:
            transform_map[name] = BasisTransform(
                source=source,
                target=target,
                matrix=matrix,
            )

    # 4. Build BasisGraph
    basis_graph = BasisGraph()
    for bt in transform_map.values():
        basis_graph.add_transform(bt if isinstance(bt, BasisTransform) else bt.as_basis_transform())

    # 5. Create empty graph
    graph = ConversionGraph()
    graph._basis_graph = basis_graph if transform_map else None

    # 6. Register units (two-pass: units first, then base_forms which
    #    reference other units by name).
    unit_map: dict[str, Unit] = {}
    pending_base_forms: list[tuple[Unit, dict, str]] = []
    for i, unit_spec in enumerate(doc.get("units", [])):
        section = f"units[{i}]"
        uname = _require(unit_spec, "name", section)
        dim_name = _require(unit_spec, "dimension", section)
        dim = dim_map.get(dim_name)
        if dim is None:
            # Try resolving from the standard dimension registry
            dim = _DIMENSION_ATTRS.get(dim_name)
            if dim is None:
                raise GraphLoadError(
                    f"[{section}]: unknown dimension '{dim_name}' "
                    f"for unit '{uname}'"
                )

        aliases = tuple(unit_spec.get("aliases", []))
        unit = Unit(
            name=uname,
            dimension=dim,
            aliases=aliases,
        )
        unit_map[unit.name] = unit
        graph.register_unit(unit)
        # Also register aliases for lookup
        for alias in aliases:
            unit_map[alias] = unit

        bf_spec = unit_spec.get("base_form")
        if bf_spec is not None:
            pending_base_forms.append((unit, bf_spec, section))

    # Pass 2: resolve base_form factor references now that all units exist.
    for unit, bf_spec, section in pending_base_forms:
        raw_factors = bf_spec.get("factors", [])
        resolved: list[tuple[Unit, float]] = []
        for entry in raw_factors:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                raise GraphLoadError(
                    f"[{section}]: invalid base_form factor {entry!r} "
                    f"for unit '{unit.name}'"
                )
            fname, fexp = entry
            fu = unit_map.get(fname)
            if fu is None:
                raise GraphLoadError(
                    f"[{section}]: unknown factor unit '{fname}' "
                    f"in base_form for unit '{unit.name}'"
                )
            resolved.append((fu, float(fexp)))
        prefactor = float(bf_spec.get("prefactor", 1.0))
        unit._set_base_form(
            BaseForm(factors=tuple(resolved), prefactor=prefactor),
        )

    # 7. Materialize edges
    with using_graph(graph):
        for i, edge_spec in enumerate(doc.get("edges", [])):
            section = f"edges[{i}]"
            src_name = _require(edge_spec, "src", section)
            dst_name = _require(edge_spec, "dst", section)
            src_unit = _resolve_unit(src_name, unit_map, graph)
            dst_unit = _resolve_unit(dst_name, unit_map, graph)
            if src_unit is None or dst_unit is None:
                if strict:
                    unresolvable = src_name if src_unit is None else dst_name
                    raise GraphLoadError(
                        f"[{section}]: cannot resolve unit '{unresolvable}'"
                    )
                continue
            m = _build_edge_map(edge_spec, _build_map)
            graph.add_edge(src=src_unit, dst=dst_unit, map=m)

    # 8. Materialize product edges
    with using_graph(graph):
        for i, edge_spec in enumerate(doc.get("product_edges", [])):
            section = f"product_edges[{i}]"
            src_expr = _require(edge_spec, "src", section)
            dst_expr = _require(edge_spec, "dst", section)
            m = _build_edge_map(edge_spec, _build_map)
            try:
                src_prod = _parse_product_expression(src_expr, unit_map, graph)
                dst_prod = _parse_product_expression(dst_expr, unit_map, graph)
            except GraphLoadError as exc:
                if strict:
                    raise
                warnings.warn(
                    f"[{section}]: skipping product edge — {exc}",
                    stacklevel=2,
                )
                continue
            if src_prod is None or dst_prod is None:
                if strict:
                    failed = src_expr if src_prod is None else dst_expr
                    raise GraphLoadError(
                        f"[{section}]: cannot resolve product expression '{failed}'"
                    )
                warnings.warn(
                    f"[{section}]: skipping unresolvable product edge "
                    f"'{src_expr}' -> '{dst_expr}'",
                    stacklevel=2,
                )
                continue
            graph.add_edge(src=src_prod, dst=dst_prod, map=m)

    # 9. Materialize cross-basis edges
    with using_graph(graph):
        for i, edge_spec in enumerate(doc.get("cross_basis_edges", [])):
            section = f"cross_basis_edges[{i}]"
            src_name = _require(edge_spec, "src", section)
            dst_name = _require(edge_spec, "dst", section)
            src_unit = _resolve_unit(src_name, unit_map, graph)
            dst_unit = _resolve_unit(dst_name, unit_map, graph)
            if src_unit is None or dst_unit is None:
                if strict:
                    unresolvable = src_name if src_unit is None else dst_name
                    raise GraphLoadError(
                        f"[{section}]: cannot resolve unit '{unresolvable}'"
                    )
                continue
            m = _build_edge_map(edge_spec, _build_map)
            transform_name = edge_spec.get("transform")
            bt = transform_map.get(transform_name) if transform_name else None
            if bt is not None:
                graph.add_edge(
                    src=src_unit, dst=dst_unit, map=m,
                    basis_transform=bt,
                )

    # 10. Materialize constants
    from ucon.resolver import get_unit_by_name

    constants = []
    with using_graph(graph):
        for i, const_spec in enumerate(doc.get("constants", [])):
            section = f"constants[{i}]"
            sym = _require(const_spec, "symbol", section)
            cname = _require(const_spec, "name", section)
            cvalue = _require(const_spec, "value", section)
            if not isinstance(cvalue, (int, float)):
                raise GraphLoadError(
                    f"[{section}]: 'value' must be numeric, "
                    f"got {type(cvalue).__name__}"
                )

            unit_str = const_spec.get("unit", "")
            try:
                unit_expr = get_unit_by_name(unit_str)
            except Exception:
                # Fall back to local resolution
                resolved = _resolve_unit(unit_str, unit_map, graph)
                unit_expr = resolved if resolved is not None else Unit(
                    name="unknown", dimension=dim_map.get("none", Dimension.none),
                )

            const = Constant(
                symbol=sym,
                name=cname,
                value=cvalue,
                unit=unit_expr,
                uncertainty=const_spec.get("uncertainty"),
                source=const_spec.get("source", "CODATA 2022"),
                category=const_spec.get("category", "measured"),
            )
            constants.append(const)

    # 11. Restore loaded packages
    loaded = doc.get("package", {}).get("loaded_packages", [])
    graph._loaded_packages = frozenset(loaded)

    graph._package_constants = tuple(constants)

    # 12. Materialize contexts
    from ucon.contexts import ConversionContext, ContextEdge

    with using_graph(graph):
        for ctx_name, ctx_spec in doc.get("contexts", {}).items():
            description = ctx_spec.get("description", "")
            ctx_edges = []
            for j, edge_spec in enumerate(ctx_spec.get("edges", [])):
                section = f"contexts.{ctx_name}.edges[{j}]"
                src_name = _require(edge_spec, "src", section)
                dst_name = _require(edge_spec, "dst", section)

                # Resolve src/dst — try full resolver first, then local
                src_unit = _resolve_context_unit(src_name, unit_map, graph)
                dst_unit = _resolve_context_unit(dst_name, unit_map, graph)
                if src_unit is None or dst_unit is None:
                    if strict:
                        unresolvable = src_name if src_unit is None else dst_name
                        raise GraphLoadError(
                            f"[{section}]: cannot resolve unit '{unresolvable}'"
                        )
                    continue

                m = _build_edge_map(edge_spec, _build_map)
                ctx_edges.append(ContextEdge(src=src_unit, dst=dst_unit, map=m))

            ctx = ConversionContext(
                name=ctx_name,
                edges=tuple(ctx_edges),
                description=description,
            )
            graph.register_context(ctx)

    return graph


# ---------------------------------------------------------------------------
# Import helpers
# ---------------------------------------------------------------------------

def _resolve_unit(name: str, unit_map: dict[str, Unit], graph) -> Union[Unit, None]:
    """Resolve a unit name from the local unit map or graph registry."""
    if name in unit_map:
        return unit_map[name]
    # Try graph's name registry
    result = graph.resolve_unit(name)
    if result is not None:
        return result[0]
    # Try case-insensitive
    if name.lower() in graph._name_registry:
        return graph._name_registry[name.lower()]
    return None


def _resolve_context_unit(
    name: str, unit_map: dict[str, Unit], graph,
) -> Union[Unit, UnitProduct, None]:
    """Resolve a unit name for context edges.

    Tries the full ``get_unit_by_name`` resolver first (which handles
    composite and scaled names), then falls back to local resolution.
    """
    from ucon.resolver import get_unit_by_name

    try:
        return get_unit_by_name(name)
    except Exception:
        pass
    resolved = _resolve_unit(name, unit_map, graph)
    return resolved


def _build_edge_map(edge_spec: dict, build_map_fn) -> Map:
    """Build a Map from an edge specification dict."""
    if "map" in edge_spec:
        return build_map_fn(edge_spec["map"])
    from ucon.packages import _parse_factor
    factor = _parse_factor(edge_spec.get("factor", 1.0))
    rel_unc = edge_spec.get("rel_uncertainty", 0.0)
    offset = edge_spec.get("offset")
    if offset is not None:
        return AffineMap(a=factor, b=_parse_factor(offset), rel_uncertainty=rel_unc)
    return LinearMap(a=factor, rel_uncertainty=rel_unc)


def _resolve_single_factor(
    unit_name: str,
    unit_map: dict[str, Unit],
    graph,
) -> Union[dict, None]:
    """Resolve a single unit name to a ``{UnitFactor: exponent}`` dict.

    Uses ``get_unit_by_name()`` first (handles scale prefixes like
    ``"kwatt"`` → ``UnitFactor(watt, kilo)``), then falls back to local
    resolution via *unit_map* / *graph*.

    Returns ``None`` if the unit cannot be resolved.
    """
    from ucon.resolver import get_unit_by_name

    unit_name = unit_name.strip()

    try:
        resolved = get_unit_by_name(unit_name)
        if isinstance(resolved, UnitProduct):
            return dict(resolved.factors)
        return {UnitFactor(resolved, Scale.one): 1.0}
    except Exception:
        pass

    unit = _resolve_unit(unit_name, unit_map, graph)
    if unit is None:
        return None
    return {UnitFactor(unit, Scale.one): 1.0}


def _parse_product_expression(
    expr: str,
    unit_map: dict[str, Unit],
    graph,
) -> Union[UnitProduct, None]:
    """Parse a product expression string into a UnitProduct.

    Grammar (left-to-right, standard arithmetic precedence)::

        expression := factor (('*' | '/') factor)*
        factor     := unit_name ('^' exponent)?

    ``*`` and ``/`` have equal precedence and are left-associative.
    Each ``*`` keeps the following factor in the numerator; each ``/``
    puts it in the denominator.  This matches standard mathematical
    convention::

        meter/second*kilogram   → m¹·s⁻¹·kg¹   (= m·kg/s)
        mg/kg/day               → mg¹·kg⁻¹·day⁻¹

    Uses ``get_unit_by_name()`` as the primary resolver so that
    scale-prefixed names (e.g. ``"kwatt"``) are decomposed correctly into
    a ``UnitFactor`` carrying the proper ``Scale``.

    Raises
    ------
    GraphLoadError
        If an exponent is not a valid number.
    """
    expr = expr.strip()
    if not expr:
        return None

    # Tokenize on * and / while keeping delimiters
    tokens = re.split(r'\s*([*/])\s*', expr)

    factors: dict = {}
    sign = 1.0  # first factor is always positive (numerator)

    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if token == '*':
            sign = 1.0
            continue
        if token == '/':
            sign = -1.0
            continue

        # Parse exponent
        if '^' in token:
            name_part, exp_str = token.rsplit('^', 1)
            try:
                base_exp = float(exp_str.strip())
            except ValueError:
                raise GraphLoadError(
                    f"Invalid exponent '{exp_str.strip()}' in "
                    f"product expression '{expr}'"
                )
        else:
            name_part = token
            base_exp = 1.0

        effective_exp = sign * base_exp

        resolved = _resolve_single_factor(name_part, unit_map, graph)
        if resolved is None:
            return None

        for uf, uf_exp in resolved.items():
            factors[uf] = factors.get(uf, 0.0) + effective_exp * uf_exp

    if not factors:
        return None
    return UnitProduct(factors)

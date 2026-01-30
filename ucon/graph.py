# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.graph
==========

Implements the **ConversionGraph** — the registry of unit conversion
morphisms that enables `Number.to()` conversions.

Classes
-------
- :class:`ConversionGraph` — Stores and composes conversion Maps between units.

Functions
---------
- :func:`get_default_graph` — Get the current default graph.
- :func:`set_default_graph` — Replace the default graph.
- :func:`reset_default_graph` — Reset to standard graph on next access.
- :func:`using_graph` — Context manager for scoped graph override.
"""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Union

from ucon.core import Dimension, Unit, UnitFactor, UnitProduct, Scale
from ucon.maps import Map, LinearMap, AffineMap


class DimensionMismatch(Exception):
    """Raised when attempting to convert between incompatible dimensions."""
    pass


class ConversionNotFound(Exception):
    """Raised when no conversion path exists between units."""
    pass


class CyclicInconsistency(Exception):
    """Raised when adding an edge creates an inconsistent cycle."""
    pass


@dataclass
class ConversionGraph:
    """Registry of conversion morphisms between units.

    Stores edges between Unit nodes (partitioned by Dimension) and between
    UnitProduct nodes (for composite unit conversions like joule → watt_hour).

    Supports:
    - Direct edge lookup
    - BFS path composition for multi-hop conversions
    - Factorwise decomposition for UnitProduct conversions
    """

    # Edges between Units, partitioned by Dimension
    _unit_edges: dict[Dimension, dict[Unit, dict[Unit, Map]]] = field(default_factory=dict)

    # Edges between UnitProducts (keyed by frozen factor representation)
    _product_edges: dict[tuple, dict[tuple, Map]] = field(default_factory=dict)

    # ------------- Edge Management -------------------------------------------

    def add_edge(
        self,
        *,
        src: Union[Unit, UnitProduct],
        dst: Union[Unit, UnitProduct],
        map: Map,
    ) -> None:
        """Register a conversion edge. Also registers the inverse.

        Parameters
        ----------
        src : Unit or UnitProduct
            Source unit expression.
        dst : Unit or UnitProduct
            Destination unit expression.
        map : Map
            The conversion morphism (src → dst).

        Raises
        ------
        DimensionMismatch
            If src and dst have different dimensions.
        CyclicInconsistency
            If the reverse edge exists and round-trip is not identity.
        """
        # Handle Unit vs UnitProduct dispatch
        if isinstance(src, Unit) and not isinstance(src, UnitProduct):
            if isinstance(dst, Unit) and not isinstance(dst, UnitProduct):
                self._add_unit_edge(src=src, dst=dst, map=map)
                return

        # At least one is a UnitProduct
        src_prod = src if isinstance(src, UnitProduct) else UnitProduct.from_unit(src)
        dst_prod = dst if isinstance(dst, UnitProduct) else UnitProduct.from_unit(dst)
        self._add_product_edge(src=src_prod, dst=dst_prod, map=map)

    def _add_unit_edge(self, *, src: Unit, dst: Unit, map: Map) -> None:
        """Add edge between plain Units."""
        if src.dimension != dst.dimension:
            raise DimensionMismatch(f"{src.dimension} != {dst.dimension}")

        dim = src.dimension
        self._ensure_dimension(dim)

        # Check cyclic consistency if reverse exists
        if self._has_direct_unit_edge(src=dst, dst=src):
            existing = self._get_direct_unit_edge(src=dst, dst=src)
            roundtrip = existing @ map
            if not roundtrip.is_identity():
                raise CyclicInconsistency(f"Inconsistent: {src}→{dst}→{src}")

        # Store forward and inverse
        self._unit_edges[dim].setdefault(src, {})[dst] = map
        self._unit_edges[dim].setdefault(dst, {})[src] = map.inverse()

    def _add_product_edge(self, *, src: UnitProduct, dst: UnitProduct, map: Map) -> None:
        """Add edge between UnitProducts."""
        if src.dimension != dst.dimension:
            raise DimensionMismatch(f"{src.dimension} != {dst.dimension}")

        src_key = self._product_key(src)
        dst_key = self._product_key(dst)

        # Check cyclic consistency
        if dst_key in self._product_edges and src_key in self._product_edges.get(dst_key, {}):
            existing = self._product_edges[dst_key][src_key]
            roundtrip = existing @ map
            if not roundtrip.is_identity():
                raise CyclicInconsistency(f"Inconsistent product edge cycle")

        # Store forward and inverse
        self._product_edges.setdefault(src_key, {})[dst_key] = map
        self._product_edges.setdefault(dst_key, {})[src_key] = map.inverse()

    def _ensure_dimension(self, dim: Dimension) -> None:
        if dim not in self._unit_edges:
            self._unit_edges[dim] = {}

    def _has_direct_unit_edge(self, *, src: Unit, dst: Unit) -> bool:
        dim = src.dimension
        return (
            dim in self._unit_edges
            and src in self._unit_edges[dim]
            and dst in self._unit_edges[dim][src]
        )

    def _get_direct_unit_edge(self, *, src: Unit, dst: Unit) -> Map:
        return self._unit_edges[src.dimension][src][dst]

    def _product_key(self, product: UnitProduct) -> tuple:
        """Create a hashable key for a UnitProduct."""
        # Sort by unit name for stable ordering
        items = sorted(
            ((f.unit.name, f.unit.dimension, f.scale, exp) for f, exp in product.factors.items()),
            key=lambda x: (x[0], str(x[1]))
        )
        return tuple(items)

    # ------------- Conversion ------------------------------------------------

    def convert(
        self,
        *,
        src: Union[Unit, UnitProduct],
        dst: Union[Unit, UnitProduct],
    ) -> Map:
        """Find or compose a conversion Map from src to dst.

        Parameters
        ----------
        src : Unit or UnitProduct
            Source unit expression.
        dst : Unit or UnitProduct
            Destination unit expression.

        Returns
        -------
        Map
            The conversion morphism.

        Raises
        ------
        DimensionMismatch
            If src and dst have different dimensions.
        ConversionNotFound
            If no conversion path exists.
        """
        # Both plain Units
        if isinstance(src, Unit) and not isinstance(src, UnitProduct):
            if isinstance(dst, Unit) and not isinstance(dst, UnitProduct):
                return self._convert_units(src=src, dst=dst)

        # At least one is a UnitProduct
        src_prod = src if isinstance(src, UnitProduct) else UnitProduct.from_unit(src)
        dst_prod = dst if isinstance(dst, UnitProduct) else UnitProduct.from_unit(dst)
        return self._convert_products(src=src_prod, dst=dst_prod)

    def _convert_units(self, *, src: Unit, dst: Unit) -> Map:
        """Convert between plain Units via BFS."""
        if src == dst:
            return LinearMap.identity()

        if src.dimension != dst.dimension:
            raise DimensionMismatch(f"{src.dimension} != {dst.dimension}")

        # Direct edge?
        if self._has_direct_unit_edge(src=src, dst=dst):
            return self._get_direct_unit_edge(src=src, dst=dst)

        # BFS
        dim = src.dimension
        if dim not in self._unit_edges:
            raise ConversionNotFound(f"No edges for dimension {dim}")

        visited: dict[Unit, Map] = {src: LinearMap.identity()}
        queue = deque([src])

        while queue:
            current = queue.popleft()
            current_map = visited[current]

            if current not in self._unit_edges[dim]:
                continue

            for neighbor, edge_map in self._unit_edges[dim][current].items():
                if neighbor in visited:
                    continue

                composed = edge_map @ current_map
                visited[neighbor] = composed

                if neighbor == dst:
                    return composed

                queue.append(neighbor)

        raise ConversionNotFound(f"No path from {src} to {dst}")

    def _convert_products(self, *, src: UnitProduct, dst: UnitProduct) -> Map:
        """Convert between UnitProducts.

        Tries in order:
        1. Direct product edge
        2. Factorwise decomposition
        """
        if src.dimension != dst.dimension:
            raise DimensionMismatch(f"{src.dimension} != {dst.dimension}")

        # Check for direct product edge first
        src_key = self._product_key(src)
        dst_key = self._product_key(dst)

        if src_key in self._product_edges and dst_key in self._product_edges.get(src_key, {}):
            return self._product_edges[src_key][dst_key]

        # Same product? Identity.
        if src_key == dst_key:
            return LinearMap.identity()

        # Try factorwise decomposition
        return self._convert_factorwise(src=src, dst=dst)

    def _convert_factorwise(self, *, src: UnitProduct, dst: UnitProduct) -> Map:
        """Factorwise conversion when factor structures align."""
        try:
            src_by_dim = src.factors_by_dimension()
            dst_by_dim = dst.factors_by_dimension()
        except ValueError as e:
            raise ConversionNotFound(f"Ambiguous decomposition: {e}")

        # Check that dimensions match exactly
        if set(src_by_dim.keys()) != set(dst_by_dim.keys()):
            raise ConversionNotFound(
                f"Factor structures don't align: {set(src_by_dim.keys())} vs {set(dst_by_dim.keys())}"
            )

        result = LinearMap.identity()

        for dim, (src_factor, src_exp) in src_by_dim.items():
            dst_factor, dst_exp = dst_by_dim[dim]

            if abs(src_exp - dst_exp) > 1e-12:
                raise ConversionNotFound(
                    f"Exponent mismatch for {dim}: {src_exp} vs {dst_exp}"
                )

            # Scale ratio
            src_scale_val = src_factor.scale.value.evaluated
            dst_scale_val = dst_factor.scale.value.evaluated
            scale_ratio = src_scale_val / dst_scale_val
            scale_map = LinearMap(scale_ratio)

            # Unit conversion (if different base units)
            if src_factor.unit == dst_factor.unit:
                unit_map = LinearMap.identity()
            else:
                unit_map = self._convert_units(
                    src=src_factor.unit,
                    dst=dst_factor.unit,
                )

            # Combine scale and unit conversion, apply exponent
            factor_map = (scale_map @ unit_map) ** src_exp
            result = result @ factor_map

        return result


# -----------------------------------------------------------------------------
# Default Graph Management
# -----------------------------------------------------------------------------

_default_graph: ConversionGraph | None = None
_graph_context: ContextVar[ConversionGraph | None] = ContextVar("graph", default=None)


def get_default_graph() -> ConversionGraph:
    """Get the current conversion graph.

    Priority:
    1. Context-local graph (from `using_graph`)
    2. Module-level default graph (lazily built)
    """
    # Check context first
    graph = _graph_context.get()
    if graph is not None:
        return graph

    # Fall back to module default
    global _default_graph
    if _default_graph is None:
        _default_graph = _build_standard_graph()
    return _default_graph


def set_default_graph(graph: ConversionGraph) -> None:
    """Replace the module-level default graph."""
    global _default_graph
    _default_graph = graph


def reset_default_graph() -> None:
    """Reset to standard graph on next access."""
    global _default_graph
    _default_graph = None


@contextmanager
def using_graph(graph: ConversionGraph):
    """Context manager for scoped graph override.

    Usage::

        with using_graph(custom_graph):
            result = value.to(target)  # uses custom_graph
    """
    token = _graph_context.set(graph)
    try:
        yield graph
    finally:
        _graph_context.reset(token)


def _build_standard_graph() -> ConversionGraph:
    """Build the default graph with common conversions."""
    from ucon import units

    graph = ConversionGraph()

    # --- Length ---
    graph.add_edge(src=units.meter, dst=units.foot, map=LinearMap(3.28084))
    graph.add_edge(src=units.foot, dst=units.inch, map=LinearMap(12))
    graph.add_edge(src=units.foot, dst=units.yard, map=LinearMap(1/3))
    graph.add_edge(src=units.mile, dst=units.foot, map=LinearMap(5280))

    # --- Mass ---
    graph.add_edge(src=units.kilogram, dst=units.gram, map=LinearMap(1000))
    graph.add_edge(src=units.kilogram, dst=units.pound, map=LinearMap(2.20462))
    graph.add_edge(src=units.pound, dst=units.ounce, map=LinearMap(16))

    # --- Time ---
    graph.add_edge(src=units.second, dst=units.minute, map=LinearMap(1/60))
    graph.add_edge(src=units.minute, dst=units.hour, map=LinearMap(1/60))
    graph.add_edge(src=units.hour, dst=units.day, map=LinearMap(1/24))

    # --- Temperature ---
    # C → K: K = C + 273.15
    graph.add_edge(src=units.celsius, dst=units.kelvin, map=AffineMap(1, 273.15))
    # F → C: C = (F - 32) * 5/9
    graph.add_edge(src=units.fahrenheit, dst=units.celsius, map=AffineMap(5/9, -32 * 5/9))

    # --- Volume ---
    graph.add_edge(src=units.liter, dst=units.gallon, map=LinearMap(0.264172))

    # --- Energy ---
    graph.add_edge(src=units.joule, dst=units.calorie, map=LinearMap(1/4.184))
    graph.add_edge(src=units.joule, dst=units.btu, map=LinearMap(1/1055.06))

    # --- Power ---
    graph.add_edge(src=units.watt, dst=units.horsepower, map=LinearMap(1/745.7))

    # --- Information ---
    graph.add_edge(src=units.byte, dst=units.bit, map=LinearMap(8))

    return graph

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
- :func:`get_parsing_graph` — Get the graph for name resolution during parsing.
"""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Union

from ucon.basis import BasisGraph, BasisTransform, NoTransformPath, Vector
from ucon.core import (
    Dimension,
    RebasedUnit,
    Unit,
    UnitFactor,
    UnitProduct,
    Scale,
)
from ucon.maps import Map, LinearMap, AffineMap, LogMap


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
    - Graph-local unit name resolution (v0.7.3+)
    - Optional BasisGraph for cross-basis validation (v0.8.3+)
    """

    # Edges between Units, partitioned by Dimension
    _unit_edges: dict[Dimension, dict[Unit, dict[Unit, Map]]] = field(default_factory=dict)

    # Edges between UnitProducts (keyed by frozen factor representation)
    _product_edges: dict[tuple, dict[tuple, Map]] = field(default_factory=dict)

    # Rebased units: original unit → RebasedUnit (for cross-basis edges)
    _rebased: dict[Unit, RebasedUnit] = field(default_factory=dict)

    # Graph-local name resolution (case-insensitive keys)
    _name_registry: dict[str, Unit] = field(default_factory=dict)

    # Graph-local name resolution (case-sensitive keys for shorthands like 'm', 'L')
    _name_registry_cs: dict[str, Unit] = field(default_factory=dict)

    # Optional BasisGraph for cross-basis dimensional validation
    _basis_graph: BasisGraph | None = field(default=None)

    # ------------- Edge Management -------------------------------------------

    def add_edge(
        self,
        *,
        src: Union[Unit, UnitProduct],
        dst: Union[Unit, UnitProduct],
        map: Map,
        basis_transform: BasisTransform | None = None,
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
        basis_transform : BasisTransform, optional
            If provided, creates a cross-basis edge. The src unit is rebased
            to the dst's dimension and the edge connects the rebased unit
            to dst.

        Raises
        ------
        DimensionMismatch
            If src and dst have different dimensions (and no basis_transform).
        CyclicInconsistency
            If the reverse edge exists and round-trip is not identity.
        NoTransformPath
            If basis_graph is set and no path exists between src/dst bases.
        """
        # If basis_graph is set, validate cross-basis compatibility
        if self._basis_graph is not None and basis_transform is None:
            src_basis = getattr(getattr(src, 'dimension', None), 'vector', None)
            dst_basis = getattr(getattr(dst, 'dimension', None), 'vector', None)
            if src_basis is not None and dst_basis is not None:
                src_basis = src_basis.basis
                dst_basis = dst_basis.basis
                if src_basis != dst_basis:
                    if not self._basis_graph.are_connected(src_basis, dst_basis):
                        raise NoTransformPath(src_basis, dst_basis)

        # Cross-basis edge with BasisTransform
        if basis_transform is not None:
            if isinstance(src, Unit) and not isinstance(src, UnitProduct):
                if isinstance(dst, Unit) and not isinstance(dst, UnitProduct):
                    self._add_cross_basis_edge(
                        src=src,
                        dst=dst,
                        map=map,
                        basis_transform=basis_transform,
                    )
                    return

        # Handle Unit vs UnitProduct dispatch (normal case)
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

    def _add_cross_basis_edge(
        self,
        *,
        src: Unit,
        dst: Unit,
        map: Map,
        basis_transform: BasisTransform,
    ) -> None:
        """Add cross-basis edge between Units via BasisTransform.

        Creates a RebasedUnit for src in the destination's dimension partition,
        then stores the edge from the rebased unit to dst.
        """
        # Validate that the transform maps src to dst's dimension
        src_vector = src.dimension.vector
        transformed = basis_transform(src_vector)
        if transformed != dst.dimension.vector:
            raise DimensionMismatch(
                f"Transform {basis_transform.source.name} -> {basis_transform.target.name} "
                f"does not map {src.name} to {dst.name}'s dimension"
            )

        # Create RebasedUnit in destination's dimension partition
        rebased = RebasedUnit(
            original=src,
            rebased_dimension=dst.dimension,
            basis_transform=basis_transform,
        )
        self._rebased[src] = rebased

        # Store edge from rebased to dst (same dimension now)
        dim = dst.dimension
        self._ensure_dimension(dim)
        self._unit_edges[dim].setdefault(rebased, {})[dst] = map
        self._unit_edges[dim].setdefault(dst, {})[rebased] = map.inverse()

    def connect_systems(
        self,
        *,
        basis_transform: BasisTransform,
        edges: dict[tuple[Unit, Unit], Map],
    ) -> None:
        """Bulk-add edges between systems.

        Parameters
        ----------
        basis_transform : BasisTransform
            The transform bridging the two systems.
        edges : dict
            Mapping from (src_unit, dst_unit) to Map.
        """
        for (src, dst), edge_map in edges.items():
            self.add_edge(
                src=src,
                dst=dst,
                map=edge_map,
                basis_transform=basis_transform,
            )

    def list_rebased_units(self) -> dict[Unit, RebasedUnit]:
        """Return all rebased units in the graph.

        Returns
        -------
        dict[Unit, RebasedUnit]
            Mapping from original unit to its RebasedUnit.
        """
        return dict(self._rebased)

    def list_transforms(self) -> list[BasisTransform]:
        """Return all BasisTransforms active in the graph.

        Returns
        -------
        list[BasisTransform]
            Unique transforms used by rebased units.
        """
        seen = set()
        result = []
        for rebased in self._rebased.values():
            bt = rebased.basis_transform
            if id(bt) not in seen:
                seen.add(id(bt))
                result.append(bt)
        return result

    def edges_for_transform(self, transform: BasisTransform) -> list[tuple[Unit, Unit]]:
        """Return all edges that use a specific BasisTransform.

        Parameters
        ----------
        transform : BasisTransform
            The transform to filter by.

        Returns
        -------
        list[tuple[Unit, Unit]]
            List of (original_unit, destination_unit) pairs.
        """
        result = []
        for original, rebased in self._rebased.items():
            if rebased.basis_transform == transform:
                # Find the destination unit (the one the rebased unit connects to)
                dim = rebased.dimension
                if dim in self._unit_edges and rebased in self._unit_edges[dim]:
                    for dst in self._unit_edges[dim][rebased]:
                        if not isinstance(dst, RebasedUnit):
                            result.append((original, dst))
        return result

    # ------------- Name Resolution --------------------------------------------

    def register_unit(self, unit: Unit) -> None:
        """Register a unit for name resolution within this graph.

        Populates both case-insensitive and case-sensitive registries
        with the unit's name, shorthand, and aliases.

        Parameters
        ----------
        unit : Unit
            The unit to register.
        """
        # Register canonical name (case-insensitive)
        self._name_registry[unit.name.lower()] = unit
        self._name_registry_cs[unit.name] = unit

        # Register shorthand (case-sensitive only — 'm' vs 'M' matters)
        if unit.shorthand:
            self._name_registry_cs[unit.shorthand] = unit

        # Register aliases
        for alias in (unit.aliases or ()):
            if alias:
                self._name_registry[alias.lower()] = unit
                self._name_registry_cs[alias] = unit

    def resolve_unit(self, name: str) -> tuple[Unit, Scale] | None:
        """Resolve a unit string in graph-local registry.

        Checks case-sensitive registry first (for shorthands like 'm', 'L'),
        then falls back to case-insensitive lookup.

        Parameters
        ----------
        name : str
            The unit name or alias to resolve.

        Returns
        -------
        tuple[Unit, Scale] | None
            (unit, Scale.one) if found, None otherwise.
            Caller should fall back to global registry if None.
        """
        # Case-sensitive first (preserves shorthand like 'm' vs 'M')
        if name in self._name_registry_cs:
            return self._name_registry_cs[name], Scale.one

        # Case-insensitive fallback
        if name.lower() in self._name_registry:
            return self._name_registry[name.lower()], Scale.one

        return None

    def copy(self) -> 'ConversionGraph':
        """Return a deep copy suitable for extension.

        Creates independent copies of edge dictionaries and name registries.
        The returned graph can be modified without affecting the original.

        Returns
        -------
        ConversionGraph
            A new graph with copied state.
        """
        import copy as copy_module

        new = ConversionGraph()
        new._unit_edges = copy_module.deepcopy(self._unit_edges)
        new._product_edges = copy_module.deepcopy(self._product_edges)
        new._rebased = dict(self._rebased)
        new._name_registry = dict(self._name_registry)
        new._name_registry_cs = dict(self._name_registry_cs)
        new._basis_graph = self._basis_graph  # BasisGraph is immutable, share reference
        return new

    def with_package(self, package: 'UnitPackage') -> 'ConversionGraph':
        """Return a new graph with this package's units and edges added.

        Creates a copy of this graph and applies the package contents.
        The original graph is not modified.

        Parameters
        ----------
        package : UnitPackage
            Package containing unit and edge definitions.

        Returns
        -------
        ConversionGraph
            New graph with package contents added.

        Example
        -------
        >>> from ucon.packages import load_package
        >>> aero = load_package("aerospace.ucon.toml")
        >>> graph = get_default_graph().with_package(aero)
        """
        from ucon.packages import UnitPackage

        new = self.copy()

        # Materialize and register units first
        for unit_def in package.units:
            unit = unit_def.materialize()
            new.register_unit(unit)

        # Materialize and add edges (resolved within new graph context)
        for edge_def in package.edges:
            edge_def.materialize(new)

        return new

    # ------------- Internal Helpers ------------------------------------------

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
        """Convert between plain Units via BFS.

        Handles cross-basis conversions via rebased units.
        """
        if src == dst:
            return LinearMap.identity()

        # Check if src has a rebased version that can reach dst
        if src in self._rebased:
            rebased = self._rebased[src]
            if rebased.dimension == dst.dimension:
                # Convert via the rebased unit
                return self._bfs_convert(start=rebased, target=dst, dim=dst.dimension)

        # Check if dst has a rebased version (inverse conversion)
        if dst in self._rebased:
            rebased_dst = self._rebased[dst]
            if rebased_dst.dimension == src.dimension:
                # Convert from src to the rebased dst
                return self._bfs_convert(start=src, target=rebased_dst, dim=src.dimension)

        # Check for dimension mismatch
        if src.dimension != dst.dimension:
            # If BasisGraph is available, check if cross-basis conversion is possible
            if self._basis_graph is not None:
                src_basis = src.dimension.vector.basis
                dst_basis = dst.dimension.vector.basis
                if src_basis != dst_basis and self._basis_graph.are_connected(src_basis, dst_basis):
                    # Bases are connected but no rebased path found above
                    raise ConversionNotFound(
                        f"No conversion path from {src} to {dst}. "
                        f"Bases {src_basis.name} and {dst_basis.name} are connected, "
                        f"but no rebased unit edge has been registered."
                    )
            raise DimensionMismatch(f"{src.dimension} != {dst.dimension}")

        # Direct edge?
        if self._has_direct_unit_edge(src=src, dst=dst):
            return self._get_direct_unit_edge(src=src, dst=dst)

        # BFS in same dimension
        return self._bfs_convert(start=src, target=dst, dim=src.dimension)

    def _bfs_convert(self, *, start, target, dim: Dimension) -> Map:
        """BFS to find conversion path within a dimension."""
        if dim not in self._unit_edges:
            raise ConversionNotFound(f"No edges for dimension {dim}")

        visited: dict = {start: LinearMap.identity()}
        queue = deque([start])

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

                if neighbor == target:
                    return composed

                queue.append(neighbor)

        raise ConversionNotFound(f"No path from {start} to {target}")

    def _bfs_product_path(self, *, src: UnitProduct, dst: UnitProduct) -> Map:
        """
        BFS to find conversion path through product AND unit edges.

        Used for cross-dimension conversions where vectors match but dimensions differ
        (e.g., gallon → liter → m³).

        Traverses both product edges and unit edges (for single-unit products).
        """
        src_key = self._product_key(src)
        dst_key = self._product_key(dst)

        # Direct edge?
        if src_key in self._product_edges and dst_key in self._product_edges.get(src_key, {}):
            return self._product_edges[src_key][dst_key]

        # BFS over product edges AND unit edges
        # Store: key → (Map, UnitProduct)
        visited: dict[tuple, tuple[Map, UnitProduct]] = {src_key: (LinearMap.identity(), src)}
        queue = deque([src_key])

        while queue:
            current_key = queue.popleft()
            current_map, current_product = visited[current_key]

            # Try product edges
            if current_key in self._product_edges:
                for neighbor_key, edge_map in self._product_edges[current_key].items():
                    if neighbor_key in visited:
                        continue

                    composed = edge_map @ current_map
                    # We don't have the UnitProduct for neighbor_key, but we can reconstruct later
                    visited[neighbor_key] = (composed, None)

                    if neighbor_key == dst_key:
                        return composed

                    queue.append(neighbor_key)

            # Try unit edges if current is a single-unit product
            if len(current_product.factors) == 1:
                factor, exp = next(iter(current_product.factors.items()))
                if abs(exp - 1.0) < 1e-12:  # exponent is 1
                    unit = factor.unit
                    dim = unit.dimension
                    if dim in self._unit_edges and unit in self._unit_edges[dim]:
                        for neighbor_unit, edge_map in self._unit_edges[dim][unit].items():
                            # Wrap neighbor as UnitProduct
                            neighbor_prod = UnitProduct.from_unit(neighbor_unit)
                            neighbor_key = self._product_key(neighbor_prod)

                            if neighbor_key in visited:
                                continue

                            # Apply scale factor from original factor
                            scale_factor = factor.scale.value.evaluated
                            neighbor_factor = UnitFactor(neighbor_unit, Scale.one)
                            scale_map = LinearMap(scale_factor)
                            composed = edge_map @ scale_map @ current_map

                            visited[neighbor_key] = (composed, neighbor_prod)

                            if neighbor_key == dst_key:
                                return composed

                            queue.append(neighbor_key)

        raise ConversionNotFound(f"No product path from {src} to {dst}")

    def _convert_products(self, *, src: UnitProduct, dst: UnitProduct) -> Map:
        """Convert between UnitProducts.

        Tries in order:
        1. Direct product edge
        2. Product edge to base-scale version of dst (then apply scale)
        3. Factorwise decomposition
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

        # Try product edge to base-scale version of dst
        # This handles cases like BTU/h → kW where edge exists to watt but not kW
        dst_base_factors = {
            UnitFactor(f.unit, Scale.one): exp
            for f, exp in dst.factors.items()
        }
        dst_base = UnitProduct(dst_base_factors)
        dst_base_key = self._product_key(dst_base)
        if dst_base_key != dst_key and src_key in self._product_edges:
            if dst_base_key in self._product_edges.get(src_key, {}):
                # Found edge to base-scale version, compose with scale factor
                base_map = self._product_edges[src_key][dst_base_key]
                scale_ratio = dst_base.fold_scale() / dst.fold_scale()
                return LinearMap(scale_ratio) @ base_map

        # Try factorwise decomposition
        return self._convert_factorwise(src=src, dst=dst)

    def _convert_factorwise(self, *, src: UnitProduct, dst: UnitProduct) -> Map:
        """
        Factorwise conversion when factor structures align.

        Uses vector-based grouping instead of Dimension enum identity,
        so that named dimensions (volume) match their base expansions (length³).
        """
        try:
            src_by_dim = src.factors_by_dimension()
            dst_by_dim = dst.factors_by_dimension()
        except ValueError as e:
            raise ConversionNotFound(f"Ambiguous decomposition: {e}")

        # Group by EFFECTIVE dimensional vector (dimension × exponent).
        # This allows volume¹ (vec = L³) to match length³ (vec = L¹ × 3 = L³).
        src_by_vector: dict[Vector, tuple[UnitFactor, float, Dimension]] = {}
        dst_by_vector: dict[Vector, tuple[UnitFactor, float, Dimension]] = {}

        for dim, (factor, exp) in src_by_dim.items():
            # Effective vector = dimension's vector raised to exponent
            effective_vec = dim.vector ** exp
            if effective_vec in src_by_vector:
                raise ConversionNotFound(
                    f"Multiple source factors with same effective dimensional vector: {effective_vec}"
                )
            src_by_vector[effective_vec] = (factor, exp, dim)

        for dim, (factor, exp) in dst_by_dim.items():
            # Effective vector = dimension's vector raised to exponent
            effective_vec = dim.vector ** exp
            if effective_vec in dst_by_vector:
                raise ConversionNotFound(
                    f"Multiple destination factors with same effective dimensional vector: {effective_vec}"
                )
            dst_by_vector[effective_vec] = (factor, exp, dim)

        # Check that effective vectors match
        if set(src_by_vector.keys()) != set(dst_by_vector.keys()):
            raise ConversionNotFound(
                f"Factor structures don't align: {set(src_by_dim.keys())} vs {set(dst_by_dim.keys())}"
            )

        result = LinearMap.identity()

        for vec, (src_factor, src_exp, src_dim) in src_by_vector.items():
            dst_factor, dst_exp, dst_dim = dst_by_vector[vec]

            # Pseudo-dimensions (angle, solid_angle, ratio) are semantically isolated.
            # They share zero vectors but must NOT convert between each other.
            src_is_pseudo = getattr(src_dim, 'is_pseudo', False)
            dst_is_pseudo = getattr(dst_dim, 'is_pseudo', False)
            if src_is_pseudo or dst_is_pseudo:
                if src_dim != dst_dim:
                    raise ConversionNotFound(
                        f"Cannot convert between pseudo-dimensions: {src_dim.name} and {dst_dim.name}"
                    )

            # Same dimension case: exponents must match, convert units directly
            if src_dim == dst_dim or (src_dim.vector == dst_dim.vector and abs(src_exp - dst_exp) < 1e-12):
                if abs(src_exp - dst_exp) > 1e-12:
                    raise ConversionNotFound(
                        f"Exponent mismatch for {src_dim}: {src_exp} vs {dst_exp}"
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

            else:
                # Cross-dimension case: e.g., volume¹ ↔ length³
                # Need to find a path through product edges (e.g., gallon → liter → m³)
                src_product = UnitProduct({src_factor: src_exp})
                dst_product = UnitProduct({dst_factor: dst_exp})

                # Try BFS over product edges to find a path
                try:
                    factor_map = self._bfs_product_path(src=src_product, dst=dst_product)
                except ConversionNotFound:
                    raise ConversionNotFound(
                        f"No conversion path from {src_product} ({src_dim}) to {dst_product} ({dst_dim})"
                    )

                result = result @ factor_map

        return result


# -----------------------------------------------------------------------------
# Default Graph Management
# -----------------------------------------------------------------------------

_default_graph: ConversionGraph | None = None
_graph_context: ContextVar[ConversionGraph | None] = ContextVar("graph", default=None)
_parsing_graph: ContextVar[ConversionGraph | None] = ContextVar("parsing_graph", default=None)


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


def get_parsing_graph() -> ConversionGraph | None:
    """Get the graph to use for name resolution during parsing.

    Returns the context-local parsing graph if set, otherwise None.
    Used by _lookup_factor() to check graph-local registry first.

    Returns
    -------
    ConversionGraph | None
        The parsing graph, or None if not in a using_graph() context.
    """
    return _parsing_graph.get()


@contextmanager
def using_graph(graph: ConversionGraph):
    """Context manager for scoped graph override.

    Sets both the conversion graph and parsing graph contexts,
    so that name resolution and conversions both use the same graph.

    Usage::

        with using_graph(custom_graph):
            result = value.to(target)  # uses custom_graph
            unit = get_unit_by_name("custom_unit")  # resolves in custom_graph

    Parameters
    ----------
    graph : ConversionGraph
        The graph to use within this context.

    Yields
    ------
    ConversionGraph
        The same graph passed in.
    """
    token_graph = _graph_context.set(graph)
    token_parsing = _parsing_graph.set(graph)
    try:
        yield graph
    finally:
        _graph_context.reset(token_graph)
        _parsing_graph.reset(token_parsing)


def _build_standard_graph() -> ConversionGraph:
    """Build the default graph with common conversions."""
    from ucon import units

    graph = ConversionGraph()

    # Register all standard units for graph-local name resolution
    for name in dir(units):
        obj = getattr(units, name)
        if isinstance(obj, Unit) and not isinstance(obj, RebasedUnit):
            graph.register_unit(obj)

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
    # K → °R: °R = K × 9/5 (both absolute scales, same zero point)
    graph.add_edge(src=units.kelvin, dst=units.rankine, map=LinearMap(9/5))

    # --- Pressure ---
    # 1 Pa = 0.00001 bar, so 1 bar = 100000 Pa
    graph.add_edge(src=units.pascal, dst=units.bar, map=LinearMap(1/100000))
    # 1 Pa = 0.000145038 psi
    graph.add_edge(src=units.pascal, dst=units.psi, map=LinearMap(0.000145038))
    # 1 atm = 101325 Pa
    graph.add_edge(src=units.atmosphere, dst=units.pascal, map=LinearMap(101325))
    # 1 torr = 133.322368 Pa
    graph.add_edge(src=units.torr, dst=units.pascal, map=LinearMap(133.322368))
    # 1 mmHg ≈ 1 torr (by definition, at 0°C)
    graph.add_edge(src=units.millimeter_mercury, dst=units.torr, map=LinearMap(1.0))
    # 1 inHg = 3386.389 Pa
    graph.add_edge(src=units.inch_mercury, dst=units.pascal, map=LinearMap(3386.389))

    # --- Force ---
    # 1 lbf = 4.4482216152605 N (exact, from lb_m × g_n)
    graph.add_edge(src=units.pound_force, dst=units.newton, map=LinearMap(4.4482216152605))
    # 1 kgf = 9.80665 N (exact, by definition)
    graph.add_edge(src=units.kilogram_force, dst=units.newton, map=LinearMap(9.80665))
    # 1 dyne = 1e-5 N (CGS unit)
    graph.add_edge(src=units.dyne, dst=units.newton, map=LinearMap(1e-5))

    # --- Dynamic Viscosity ---
    # 1 poise = 0.1 Pa·s (CGS unit)
    graph.add_edge(src=units.poise, dst=units.pascal * units.second, map=LinearMap(0.1))

    # --- Kinematic Viscosity ---
    # 1 stokes = 1e-4 m²/s (CGS unit)
    graph.add_edge(src=units.stokes, dst=units.meter ** 2 / units.second, map=LinearMap(1e-4))

    # --- Volume ---
    graph.add_edge(src=units.liter, dst=units.gallon, map=LinearMap(0.264172))
    # Cross-dimension: volume → length³ (enables gal/min → m³/h)
    # 1 L = 0.001 m³
    graph.add_edge(src=units.liter, dst=units.meter ** 3, map=LinearMap(0.001))

    # --- Energy ---
    graph.add_edge(src=units.joule, dst=units.calorie, map=LinearMap(1/4.184))
    graph.add_edge(src=units.joule, dst=units.btu, map=LinearMap(1/1055.06))
    graph.add_edge(src=units.joule, dst=units.watt_hour, map=LinearMap(1/3600))  # 1 Wh = 3600 J
    # Cross-structure: energy/time → power (enables BTU/h → kW)
    # 1 BTU/h = 1055.06 J/h = 1055.06/3600 W = 0.29307 W
    graph.add_edge(src=units.btu / units.hour, dst=units.watt, map=LinearMap(1055.06 / 3600))

    # --- Power ---
    graph.add_edge(src=units.watt, dst=units.horsepower, map=LinearMap(1/745.7))

    # --- Information ---
    graph.add_edge(src=units.byte, dst=units.bit, map=LinearMap(8))

    # --- Angle ---
    import math
    graph.add_edge(src=units.radian, dst=units.degree, map=LinearMap(180 / math.pi))
    graph.add_edge(src=units.degree, dst=units.arcminute, map=LinearMap(60))
    graph.add_edge(src=units.arcminute, dst=units.arcsecond, map=LinearMap(60))
    graph.add_edge(src=units.turn, dst=units.radian, map=LinearMap(2 * math.pi))
    graph.add_edge(src=units.turn, dst=units.gradian, map=LinearMap(400))

    # --- Solid Angle ---
    graph.add_edge(src=units.steradian, dst=units.square_degree, map=LinearMap((180 / math.pi) ** 2))

    # --- Ratio ---
    graph.add_edge(src=units.fraction, dst=units.percent, map=LinearMap(100))
    graph.add_edge(src=units.fraction, dst=units.permille, map=LinearMap(1000))
    graph.add_edge(src=units.fraction, dst=units.ppm, map=LinearMap(1e6))
    graph.add_edge(src=units.fraction, dst=units.ppb, map=LinearMap(1e9))
    graph.add_edge(src=units.fraction, dst=units.basis_point, map=LinearMap(10000))
    # nines: -log₁₀(1 - availability) for SRE uptime (0.99999 → 5 nines)
    graph.add_edge(src=units.fraction, dst=units.nines, map=LogMap(scale=-1) @ AffineMap(a=-1, b=1))

    return graph

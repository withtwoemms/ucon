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
- :func:`ucon.core._get_parsing_graph` — Get the graph for name resolution during parsing.
"""
from __future__ import annotations

import copy
import math
from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Union

from ucon.basis import BasisGraph, BasisTransform, NoTransformPath, Vector
from ucon.basis.graph import _build_standard_basis_graph
from ucon.basis.transforms import (
    ConstantBoundBasisTransform,
    CGS_TO_SI,
    SI_TO_CGS_ESU,
    SI_TO_CGS_EMU,
    CGS_ESU_TO_CGS_EMU,
    SI_TO_NATURAL,
    SI_TO_PLANCK,
    SI_TO_ATOMIC,
    NATURAL_TO_PLANCK,
    NATURAL_TO_ATOMIC,
    PLANCK_TO_ATOMIC,
)
from ucon.core import (
    Dimension,
    RebasedUnit,
    Unit,
    UnitFactor,
    UnitProduct,
    Scale,
    UnknownUnitError,
    _get_parsing_graph,
    _parsing_graph,
)
from ucon.maps import Map, LinearMap, AffineMap, LogMap

__all__ = [
    'ConversionGraph',
    'DimensionMismatch',
    'ConversionNotFound',
    'CyclicInconsistency',
    'get_default_graph',
    'set_default_graph',
    'reset_default_graph',
    'using_graph',
]


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

    # Rebased units: original unit → set of RebasedUnits (one per target basis)
    _rebased: dict[Unit, set[RebasedUnit]] = field(default_factory=dict)

    # Graph-local name resolution (case-insensitive keys)
    _name_registry: dict[str, Unit] = field(default_factory=dict)

    # Graph-local name resolution (case-sensitive keys for shorthands like 'm', 'L')
    _name_registry_cs: dict[str, Unit] = field(default_factory=dict)

    # Optional BasisGraph for cross-basis dimensional validation
    _basis_graph: BasisGraph | None = field(default=None)

    # Names of loaded packages (for dependency validation)
    _loaded_packages: frozenset[str] = field(default_factory=frozenset)

    # Constants materialized from loaded packages
    _package_constants: tuple = field(default_factory=tuple)

    # Named ConversionContext definitions (for serialization round-trip)
    _contexts: dict[str, 'ConversionContext'] = field(default_factory=dict)

    # Conversion path cache: (src_key, dst_key) -> Map
    # Cleared when edges are added
    _conversion_cache: dict[tuple, Map] = field(default_factory=dict)

    # ------------- Edge Management -------------------------------------------

    def add_edge(
        self,
        *,
        src: Union[Unit, UnitProduct],
        dst: Union[Unit, UnitProduct],
        map: Map,
        basis_transform: BasisTransform | ConstantBoundBasisTransform | None = None,
    ) -> None:
        """Register a conversion edge (and its inverse) on this graph.

        ``add_edge`` is the primary mechanism for extending a
        :class:`ConversionGraph` with domain-specific units. Call it on
        either the default package graph (``ucon.graph.default_graph``) or
        your own ``ConversionGraph`` instance to wire new units into the
        conversion system.

        For every forward edge ``src → dst`` registered with :class:`Map`
        ``m``, the inverse ``dst → src`` is automatically registered using
        ``m.inverse()``. Adding an inconsistent inverse (one whose
        round-trip is not the identity) raises
        :exc:`CyclicInconsistency`. Adding an edge between units of
        different dimensions without a ``basis_transform`` raises
        :exc:`DimensionMismatch`.

        Parameters
        ----------
        src : Unit or UnitProduct
            Source unit expression. Both plain :class:`Unit` instances and
            composite :class:`UnitProduct` expressions are accepted; the
            graph dispatches to the appropriate edge-type internally.
        dst : Unit or UnitProduct
            Destination unit expression.
        map : Map
            The conversion morphism ``src → dst``. Typically
            :class:`LinearMap` for pure scalings, :class:`AffineMap` for
            offset conversions (e.g., °C ↔ K), or :class:`LogMap` for
            logarithmic units (dB, nepers).
        basis_transform : BasisTransform or ConstantBoundBasisTransform, optional
            For cross-basis edges (e.g., CGS ↔ SI when dimensional
            exponents differ, as for electromagnetic units). The ``src``
            unit is rebased to the dst's dimension and the edge connects
            the rebased unit to ``dst``. Most edges do not need this.

        Raises
        ------
        DimensionMismatch
            ``src`` and ``dst`` have different dimensions and no
            ``basis_transform`` was supplied.
        CyclicInconsistency
            A reverse edge exists already and composing it with the new
            ``map`` does not yield the identity. This protects against
            silently registering incompatible conversions.
        NoTransformPath
            The graph has a :class:`BasisGraph` attached and no path
            exists between the source and destination bases.

        Examples
        --------
        Register a simple linear conversion on the default graph::

            from ucon import units, LinearMap
            from ucon.graph import default_graph

            default_graph.add_edge(
                src=units.mile,
                dst=units.kilometer,
                map=LinearMap(1.609344),
            )

        Register an affine temperature conversion::

            from ucon import units, AffineMap
            from ucon.graph import default_graph

            default_graph.add_edge(
                src=units.celsius,
                dst=units.kelvin,
                map=AffineMap(a=1.0, b=273.15),
            )

        Register a composite-unit edge (``joule`` ↔ ``kWh``)::

            from ucon import units, LinearMap
            from ucon.graph import default_graph

            kwh = units.kilo * units.watt * units.hour
            default_graph.add_edge(
                src=units.joule,
                dst=kwh,
                map=LinearMap(1 / 3.6e6),
            )

        See Also
        --------
        ConversionGraph.convert : Path-find between registered units.
        ConversionGraph.connect_systems : Bulk-add cross-basis edges.
        Number.to : User-facing conversion that delegates to this graph.

        Notes
        -----
        **Stability:** ``add_edge`` is part of the public API of
        :mod:`ucon` as of v1.3.0. Its keyword-only signature
        (``src``, ``dst``, ``map``, ``basis_transform``) is considered
        stable and will not change in a backwards-incompatible way
        without a major-version bump.
        """
        # Clear conversion cache (new edge may create shorter paths)
        self._conversion_cache.clear()

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
        basis_transform: BasisTransform | ConstantBoundBasisTransform,
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
        self._rebased.setdefault(src, set()).add(rebased)

        # Store edge from rebased to dst (same dimension now)
        dim = dst.dimension
        self._ensure_dimension(dim)
        self._unit_edges[dim].setdefault(rebased, {})[dst] = map
        self._unit_edges[dim].setdefault(dst, {})[rebased] = map.inverse()

    def connect_systems(
        self,
        *,
        basis_transform: BasisTransform | ConstantBoundBasisTransform,
        edges: dict[tuple[Unit, Unit], Map],
    ) -> None:
        """Bulk-add edges between systems.

        Parameters
        ----------
        basis_transform : BasisTransform or ConstantBoundBasisTransform
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

    @property
    def package_constants(self) -> tuple:
        """Constants materialized from loaded packages.

        Returns
        -------
        tuple[Constant, ...]
            All constants from loaded packages, in load order.
        """
        return self._package_constants

    def list_rebased_units(self) -> dict[Unit, list[RebasedUnit]]:
        """Return all rebased units in the graph.

        Returns
        -------
        dict[Unit, list[RebasedUnit]]
            Mapping from original unit to its RebasedUnit(s).
        """
        return {k: list(v) for k, v in self._rebased.items()}

    def list_transforms(self) -> list[BasisTransform]:
        """Return all BasisTransforms active in the graph.

        Returns
        -------
        list[BasisTransform]
            Unique transforms used by rebased units.
        """
        seen = set()
        result = []
        for rebased_list in self._rebased.values():
            for rebased in rebased_list:
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
        for original, rebased_list in self._rebased.items():
            for rebased in rebased_list:
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

        Only performs case-sensitive matching. Case-insensitive resolution
        is handled by the global ``_lookup_factor()`` which applies the
        correct priority chain (priority aliases → scale-prefix decomposition
        → case-sensitive → case-insensitive).

        Returning a case-insensitive match here would short-circuit
        scale-prefix decomposition, causing e.g. ``GB`` (giga-byte) to
        resolve as ``Gb`` (gilbert) or ``nm`` (nano-meter) as nautical mile
        (alias ``NM``).

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
        # Case-sensitive only (preserves shorthand like 'm' vs 'M',
        # 'Gb' vs 'GB', and avoids shadowing scale-prefix parsing)
        if name in self._name_registry_cs:
            return self._name_registry_cs[name], Scale.one

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
        new = ConversionGraph()
        new._unit_edges = copy.deepcopy(self._unit_edges)
        new._product_edges = copy.deepcopy(self._product_edges)
        new._rebased = {k: set(v) for k, v in self._rebased.items()}
        new._name_registry = dict(self._name_registry)
        new._name_registry_cs = dict(self._name_registry_cs)
        new._basis_graph = self._basis_graph  # BasisGraph is immutable, share reference
        new._loaded_packages = self._loaded_packages  # frozenset is immutable, share reference
        new._package_constants = self._package_constants  # tuple is immutable, share reference
        new._contexts = dict(self._contexts)  # ConversionContext is frozen, share refs
        return new

    def register_context(self, ctx: 'ConversionContext') -> None:
        """Register a named conversion context for serialization.

        Parameters
        ----------
        ctx : ConversionContext
            A frozen context to store by name.
        """
        self._contexts[ctx.name] = ctx

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
        from ucon.packages import PackageLoadError

        # Validate requires
        missing = [r for r in package.requires if r not in self._loaded_packages]
        if missing:
            raise PackageLoadError(
                f"Package '{package.name}' requires packages not yet loaded: "
                f"{', '.join(missing)}"
            )

        new = self.copy()

        # Materialize and register units first
        for unit_def in package.units:
            unit = unit_def.materialize()
            new.register_unit(unit)

        # Materialize and add edges (resolved within new graph context).
        # Skip edges whose endpoints are already convertible in the graph
        # (e.g., a package defines knot→m/s but the built-in graph already has it).
        for edge_def in package.edges:
            if self._package_edge_already_covered(edge_def, new):
                continue
            edge_def.materialize(new)

        # Materialize constants (resolved within new graph context)
        materialized_constants = tuple(
            const_def.materialize(new) for const_def in package.constants
        )
        new._package_constants = getattr(self, '_package_constants', ()) + materialized_constants

        # Track loaded package name
        new._loaded_packages = self._loaded_packages | {package.name}

        return new

    @staticmethod
    def _package_edge_already_covered(
        edge_def: 'EdgeDef',
        graph: 'ConversionGraph',
    ) -> bool:
        """Check if a package edge is redundant because the graph can already convert between its endpoints."""
        from ucon.resolver import get_unit_by_name
        with using_graph(graph):
            try:
                src_unit = get_unit_by_name(edge_def.src)
                dst_unit = get_unit_by_name(edge_def.dst)
            except UnknownUnitError:
                return False  # Can't resolve — let materialize handle the error

        try:
            graph.convert(src=src_unit, dst=dst_unit)
            return True  # Path already exists
        except (ConversionNotFound, DimensionMismatch):
            return False

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
        # Check cache first (units are hashable)
        cache_key = (src, dst)
        if cache_key in self._conversion_cache:
            return self._conversion_cache[cache_key]

        # Both plain Units
        if isinstance(src, Unit) and not isinstance(src, UnitProduct):
            if isinstance(dst, Unit) and not isinstance(dst, UnitProduct):
                result = self._convert_units(src=src, dst=dst)
                self._conversion_cache[cache_key] = result
                return result

        # At least one is a UnitProduct
        src_prod = src if isinstance(src, UnitProduct) else UnitProduct.from_unit(src)
        dst_prod = dst if isinstance(dst, UnitProduct) else UnitProduct.from_unit(dst)
        result = self._convert_products(src=src_prod, dst=dst_prod)
        self._conversion_cache[cache_key] = result
        return result

    def _convert_units(self, *, src: Unit, dst: Unit) -> Map:
        """Convert between plain Units via BFS.

        Handles cross-basis conversions via rebased units.
        """
        if src == dst:
            return LinearMap.identity()

        # Check if src has a rebased version that can reach dst
        if src in self._rebased:
            for rebased in self._rebased[src]:
                if rebased.dimension == dst.dimension:
                    # Convert via the rebased unit
                    return self._bfs_convert(start=rebased, target=dst, dim=dst.dimension)

        # Check if dst has a rebased version (inverse conversion)
        if dst in self._rebased:
            for rebased_dst in self._rebased[dst]:
                if rebased_dst.dimension == src.dimension:
                    # Convert from src to the rebased dst
                    return self._bfs_convert(start=src, target=rebased_dst, dim=src.dimension)

        # Check for dimension mismatch
        if src.dimension != dst.dimension:
            # Try cross-dimensional BFS (context edges span dimensions)
            try:
                return self._bfs_convert_cross_dimensional(start=src, target=dst)
            except ConversionNotFound:
                pass

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

    def _bfs_convert_cross_dimensional(self, *, start, target) -> Map:
        """BFS across ALL dimension partitions.

        Used for context edges that span dimensions (e.g., meter -> hertz
        in a spectroscopy context). Searches every dimension partition
        for edges from the current node.
        """
        visited: dict = {start: LinearMap.identity()}
        queue = deque([start])

        while queue:
            current = queue.popleft()
            current_map = visited[current]

            for dim, dim_edges in self._unit_edges.items():
                if current not in dim_edges:
                    continue
                for neighbor, edge_map in dim_edges[current].items():
                    if neighbor in visited:
                        continue

                    composed = edge_map @ current_map
                    visited[neighbor] = composed

                    if neighbor == target:
                        return composed

                    queue.append(neighbor)

        raise ConversionNotFound(
            f"No cross-dimensional path from {start} to {target}"
        )

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
        4. (On dimension mismatch) Unit-level cross-basis conversion if both
           products are trivial single-unit wrappers
        """
        if src.dimension != dst.dimension:
            # Before raising, check if both products can be resolved to atomic
            # units with a cross-basis conversion path (e.g., poise → Pa·s
            # where cgs_dynamic_viscosity ≠ dynamic_viscosity but a rebased
            # edge exists at the Unit level).
            #
            # Resolution strategy (for each product):
            # 1. as_unit() — trivial single-factor wrapper
            # 2. resolve_unit(shorthand) — graph-registered alias for a
            #    composite string like "Pa·s" → pascal_second
            src_unit = src.as_unit()
            if src_unit is None:
                resolved = self.resolve_unit(src.shorthand)
                if resolved is not None:
                    src_unit = resolved[0]
            dst_unit = dst.as_unit()
            if dst_unit is None:
                resolved = self.resolve_unit(dst.shorthand)
                if resolved is not None:
                    dst_unit = resolved[0]
            if src_unit is not None and dst_unit is not None:
                return self._convert_units(src=src_unit, dst=dst_unit)
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

        # Before factorwise decomposition, try resolving products to atomic
        # units via the graph's name registry.  Composite strings like "Pa·s"
        # parse into multi-factor products but may correspond to registered
        # atomic units (pascal_second) that have direct conversion edges.
        src_unit = src.as_unit()
        if src_unit is None:
            resolved = self.resolve_unit(src.shorthand)
            if resolved is not None:
                src_unit = resolved[0]
        dst_unit = dst.as_unit()
        if dst_unit is None:
            resolved = self.resolve_unit(dst.shorthand)
            if resolved is not None:
                dst_unit = resolved[0]
        if src_unit is not None and dst_unit is not None:
            try:
                return self._convert_units(src=src_unit, dst=dst_unit)
            except (ConversionNotFound, DimensionMismatch):
                pass  # Fall through to factorwise

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

    # ------------- Serialization ----------------------------------------------

    def to_toml(self, path: Union[str, 'Path']) -> None:
        """Export this graph to a TOML file.

        Parameters
        ----------
        path : str or Path
            Destination file path.

        Raises
        ------
        ImportError
            If ``tomli_w`` is not installed.
        """
        from ucon.serialization import to_toml
        to_toml(self, path)

    @classmethod
    def from_toml(cls, path: Union[str, 'Path'], *, strict: bool = True) -> 'ConversionGraph':
        """Import a graph from a TOML file.

        Parameters
        ----------
        path : str or Path
            Source file path.
        strict : bool
            When ``True`` (default), raise ``GraphLoadError`` if any edge
            references an unresolvable unit.  When ``False``, silently skip
            unresolvable edges.

        Returns
        -------
        ConversionGraph
            The reconstructed graph.
        """
        from ucon.serialization import from_toml
        return from_toml(path, strict=strict)

    # ------------- Equality ---------------------------------------------------

    @staticmethod
    def _maps_equal(m: Map, other_m: Map) -> bool:
        """Compare two maps by evaluating at test points.

        Tries (1.0, 0.0) first; falls back to (1.0, 2.0) if 0.0
        raises; falls back to (0.5, 2.0) if 1.0 also raises.
        Returns True when no evaluable test points can distinguish
        the maps (conservative: assumes equal).
        """
        try:
            if abs(m(1.0) - other_m(1.0)) > 1e-9:
                return False
            if abs(m(0.0) - other_m(0.0)) > 1e-9:
                return False
            return True
        except (ValueError, ZeroDivisionError):
            pass

        # Fallback: 0.0 (or 1.0) raised — try alternative points
        try:
            if abs(m(1.0) - other_m(1.0)) > 1e-9:
                return False
            if abs(m(2.0) - other_m(2.0)) > 1e-9:
                return False
            return True
        except (ValueError, ZeroDivisionError):
            pass

        # Last resort: both common points fail (e.g. nines inverse at 1.0)
        try:
            if abs(m(0.5) - other_m(0.5)) > 1e-9:
                return False
            if abs(m(2.0) - other_m(2.0)) > 1e-9:
                return False
            return True
        except (ValueError, ZeroDivisionError):
            # No evaluable test points — structurally compare types
            return type(m) is type(other_m)

    @staticmethod
    def _non_rebased_edges(dim_edges: dict) -> dict[Unit, dict[Unit, Map]]:
        """Filter a dimension's edge dict to exclude RebasedUnit nodes."""
        return {
            src: {
                dst: m
                for dst, m in neighbors.items()
                if not isinstance(dst, RebasedUnit)
            }
            for src, neighbors in dim_edges.items()
            if not isinstance(src, RebasedUnit)
        }

    def _cross_basis_edge_signature(
        self, rebased_list: list[RebasedUnit],
    ) -> dict[tuple[str, str, str], Map]:
        """Build a signature dict for cross-basis edges from a rebased list.

        Returns {(original_name, dst_name, transform_key): map} for each
        non-rebased destination reachable from the rebased units.
        """
        sig: dict[tuple[str, str, str], Map] = {}
        for rebased in rebased_list:
            dim = rebased.dimension
            if dim not in self._unit_edges:
                continue
            if rebased not in self._unit_edges[dim]:
                continue
            bt = rebased.basis_transform
            transform_key = f"{bt.source.name}_TO_{bt.target.name}"
            for dst, m in self._unit_edges[dim][rebased].items():
                if isinstance(dst, RebasedUnit):
                    continue
                key = (rebased.original.name, dst.name, transform_key)
                sig[key] = m
        return sig

    def __eq__(self, other: object) -> bool:
        """Compare graphs for structural equality.

        Two graphs are equal if they have the same registered unit names,
        the same edge conversions (within tolerance), the same loaded
        packages, the same constants, and the same contexts.
        """
        if not isinstance(other, ConversionGraph):
            return NotImplemented

        # Compare registered unit names
        if set(self._name_registry_cs.keys()) != set(other._name_registry_cs.keys()):
            return False

        # Compare loaded packages
        if self._loaded_packages != other._loaded_packages:
            return False

        # Compare package constants (all serialized fields)
        if len(self._package_constants) != len(other._package_constants):
            return False
        for c_self, c_other in zip(self._package_constants, other._package_constants):
            if (c_self.symbol, c_self.name, c_self.value,
                c_self.uncertainty, c_self.source, c_self.category) != \
               (c_other.symbol, c_other.name, c_other.value,
                c_other.uncertainty, c_other.source, c_other.category):
                return False
            # Compare unit by dimension (unit object form may differ across round-trip)
            if c_self.unit.dimension != c_other.unit.dimension:
                return False

        # Compare basis graph structure
        if (self._basis_graph is None) != (other._basis_graph is None):
            return False
        if self._basis_graph is not None and other._basis_graph is not None:
            self_edges = {
                (src.name, tgt.name)
                for src, targets in self._basis_graph._edges.items()
                for tgt in targets
            }
            other_edges = {
                (src.name, tgt.name)
                for src, targets in other._basis_graph._edges.items()
                for tgt in targets
            }
            if self_edges != other_edges:
                return False

        # Compare unit edges (symmetric: check both directions)
        self_dims = set(self._unit_edges.keys())
        other_dims = set(other._unit_edges.keys())
        if self_dims != other_dims:
            return False

        for dim in self_dims:
            self_filtered = self._non_rebased_edges(self._unit_edges[dim])
            other_filtered = self._non_rebased_edges(other._unit_edges[dim])

            # Symmetric src-node check
            if set(self_filtered.keys()) != set(other_filtered.keys()):
                return False

            for src, neighbors in self_filtered.items():
                other_neighbors = other_filtered.get(src, {})
                # Symmetric dst-node check
                if set(neighbors.keys()) != set(other_neighbors.keys()):
                    return False
                for dst, m in neighbors.items():
                    other_m = other_neighbors[dst]
                    if not self._maps_equal(m, other_m):
                        return False

        # Compare product edges (already symmetric)
        if set(self._product_edges.keys()) != set(other._product_edges.keys()):
            return False
        for src_key, neighbors in self._product_edges.items():
            other_neighbors = other._product_edges.get(src_key, {})
            if set(neighbors.keys()) != set(other_neighbors.keys()):
                return False
            for dst_key, m in neighbors.items():
                other_m = other_neighbors[dst_key]
                if not self._maps_equal(m, other_m):
                    return False

        # Compare cross-basis rebased units and their edge maps
        if set(self._rebased.keys()) != set(other._rebased.keys()):
            return False
        for original, rebased_list in self._rebased.items():
            other_rebased_list = other._rebased.get(original, [])
            # Build {(original_name, dst_name, transform_name): map} for each side
            self_xb = self._cross_basis_edge_signature(rebased_list)
            other_xb = other._cross_basis_edge_signature(other_rebased_list)
            if set(self_xb.keys()) != set(other_xb.keys()):
                return False
            for key, m in self_xb.items():
                other_m = other_xb[key]
                if not self._maps_equal(m, other_m):
                    return False

        # Compare registered contexts
        if set(self._contexts.keys()) != set(other._contexts.keys()):
            return False
        for name, ctx in self._contexts.items():
            other_ctx = other._contexts[name]
            if ctx.description != other_ctx.description:
                return False
            if len(ctx.edges) != len(other_ctx.edges):
                return False
            for edge, other_edge in zip(ctx.edges, other_ctx.edges):
                if edge.src.name != other_edge.src.name:
                    return False
                if edge.dst.name != other_edge.dst.name:
                    return False
                if not self._maps_equal(edge.map, other_edge.map):
                    return False

        return True


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
    """Replace the module-level default graph.

    Parameters
    ----------
    graph : ConversionGraph
        The new default conversion graph.
    """
    global _default_graph
    _default_graph = graph


def reset_default_graph() -> None:
    """Reset to the standard graph on next access.

    The standard graph (with all built-in unit conversions) is lazily
    rebuilt when :func:`get_default_graph` is next called.
    """
    global _default_graph
    _default_graph = None


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
    graph = ConversionGraph()
    _build_standard_edges(graph)
    return graph


def _build_standard_edges(graph: ConversionGraph) -> None:
    """Populate standard conversion edges. Called from __init__.py hook wiring."""
    # Import units module — safe because this function is only called after
    # all modules are fully loaded via the hook wiring in ucon.__init__.
    from ucon import units

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
    # 1 nautical mile = 1852 m (exact, by international definition)
    graph.add_edge(src=units.nautical_mile, dst=units.meter, map=LinearMap(1852))
    # 1 fathom = 6 feet (exact, by definition)
    graph.add_edge(src=units.fathom, dst=units.foot, map=LinearMap(6))
    # 1 angstrom = 1e-10 m (exact)
    graph.add_edge(src=units.angstrom, dst=units.meter, map=LinearMap(1e-10))
    # 1 light year = 9.4607304725808e15 m (IAU definition)
    graph.add_edge(src=units.light_year, dst=units.meter, map=LinearMap(9.4607304725808e15))
    # 1 parsec = 3.0856775814913673e16 m (IAU 2015 definition)
    graph.add_edge(src=units.parsec, dst=units.meter, map=LinearMap(3.0856775814913673e16))
    # 1 AU = 1.495978707e11 m (exact, IAU 2012 definition)
    graph.add_edge(src=units.astronomical_unit, dst=units.meter, map=LinearMap(1.495978707e11))
    # 1 furlong = 201.168 m (exact, 660 feet)
    graph.add_edge(src=units.furlong, dst=units.meter, map=LinearMap(201.168))
    # 1 chain = 20.1168 m (exact, 66 feet, Gunter's chain)
    graph.add_edge(src=units.chain, dst=units.meter, map=LinearMap(20.1168))
    # 1 rod = 5.0292 m (exact, 16.5 feet, aka perch/pole)
    graph.add_edge(src=units.rod, dst=units.meter, map=LinearMap(5.0292))
    # 1 mil = 1/1000 inch = 2.54e-5 m (exact)
    graph.add_edge(src=units.mil, dst=units.inch, map=LinearMap(1/1000))
    # 1 hand = 4 inches = 0.1016 m (exact, equestrian)
    graph.add_edge(src=units.hand, dst=units.inch, map=LinearMap(4))
    # 1 league = 3 miles (statute league)
    graph.add_edge(src=units.league, dst=units.mile, map=LinearMap(3))
    # 1 cable = 1/10 nautical mile = 185.2 m
    graph.add_edge(src=units.cable, dst=units.nautical_mile, map=LinearMap(1/10))
    # 1 typographic point = 1/72 inch (PostScript/DTP point, exact)
    graph.add_edge(src=units.point_typo, dst=units.inch, map=LinearMap(1/72))
    # 1 pica = 12 points
    graph.add_edge(src=units.pica, dst=units.point_typo, map=LinearMap(12))

    # --- Mass ---
    graph.add_edge(src=units.kilogram, dst=units.gram, map=LinearMap(1000))
    graph.add_edge(src=units.kilogram, dst=units.pound, map=LinearMap(2.20462))
    graph.add_edge(src=units.pound, dst=units.ounce, map=LinearMap(16))
    # 1 metric ton = 1000 kg
    graph.add_edge(src=units.metric_ton, dst=units.kilogram, map=LinearMap(1000))
    # 1 dalton = 1.66053906660e-27 kg (CODATA 2018, exact by 2019 SI)
    graph.add_edge(src=units.dalton, dst=units.kilogram, map=LinearMap(1.66053906660e-27))
    # 1 stone = 14 lb (exact, Imperial definition)
    graph.add_edge(src=units.stone, dst=units.pound, map=LinearMap(14))
    # 1 grain = 1/7000 lb (exact, avoirdupois definition)
    graph.add_edge(src=units.grain, dst=units.pound, map=LinearMap(1/7000))
    # 1 slug = 14.5939 kg (derived from lbf = slug × ft/s²)
    graph.add_edge(src=units.slug, dst=units.kilogram, map=LinearMap(14.5939))
    # 1 carat = 0.2 g (exact, metric carat definition)
    graph.add_edge(src=units.carat, dst=units.gram, map=LinearMap(0.2))
    # 1 troy ounce = 31.1035 g (exact: 480 grains)
    graph.add_edge(src=units.troy_ounce, dst=units.gram, map=LinearMap(31.1035))
    # 1 long ton = 2240 lb (Imperial ton)
    graph.add_edge(src=units.long_ton, dst=units.pound, map=LinearMap(2240))
    # 1 short ton = 2000 lb (US ton)
    graph.add_edge(src=units.short_ton, dst=units.pound, map=LinearMap(2000))
    # 1 dram = 1/16 ounce = 1/256 pound (avoirdupois)
    graph.add_edge(src=units.dram, dst=units.ounce, map=LinearMap(1/16))
    # 1 pennyweight = 24 grains = 1.55517384 g (Troy)
    graph.add_edge(src=units.pennyweight, dst=units.grain, map=LinearMap(24))

    # --- Time ---
    graph.add_edge(src=units.second, dst=units.minute, map=LinearMap(1/60))
    graph.add_edge(src=units.minute, dst=units.hour, map=LinearMap(1/60))
    graph.add_edge(src=units.hour, dst=units.day, map=LinearMap(1/24))
    # 1 week = 7 days
    graph.add_edge(src=units.week, dst=units.day, map=LinearMap(7))
    # 1 year = 365.25 days (Julian year, standard in astronomy and SI)
    graph.add_edge(src=units.year, dst=units.day, map=LinearMap(365.25))
    # 1 month = 1/12 year (mean calendar month)
    graph.add_edge(src=units.year, dst=units.month, map=LinearMap(12))
    # 1 fortnight = 14 days (exact)
    graph.add_edge(src=units.fortnight, dst=units.day, map=LinearMap(14))
    # 1 shake = 1e-8 s (nuclear physics time unit)
    graph.add_edge(src=units.shake, dst=units.second, map=LinearMap(1e-8))

    # --- Temperature ---
    # C → K: K = C + 273.15
    graph.add_edge(src=units.celsius, dst=units.kelvin, map=AffineMap(1, 273.15))
    # F → C: C = (F - 32) * 5/9
    graph.add_edge(src=units.fahrenheit, dst=units.celsius, map=AffineMap(5/9, -32 * 5/9))
    # K → °R: °R = K × 9/5 (both absolute scales, same zero point)
    graph.add_edge(src=units.kelvin, dst=units.rankine, map=LinearMap(9/5))
    # Ré → °C: °C = °Ré × 5/4 (same zero point: water freezing = 0)
    graph.add_edge(src=units.reaumur, dst=units.celsius, map=LinearMap(5/4))

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
    # 1 cmH₂O = 98.0665 Pa (conventional, at 4°C)
    graph.add_edge(src=units.centimeter_water, dst=units.pascal, map=LinearMap(98.0665))
    # 1 cmHg = 1333.22 Pa (conventional)
    graph.add_edge(src=units.centimeter_mercury, dst=units.pascal, map=LinearMap(1333.22))
    # 1 ksi = 1000 psi = 6.894757e6 Pa
    graph.add_edge(src=units.ksi, dst=units.psi, map=LinearMap(1000))
    # 1 technical atmosphere (at) = 98066.5 Pa (exact, 1 kgf/cm²)
    graph.add_edge(src=units.technical_atmosphere, dst=units.pascal, map=LinearMap(98066.5))
    # 1 mmH₂O = 9.80665 Pa (conventional, at 4°C)
    graph.add_edge(src=units.millimeter_water, dst=units.pascal, map=LinearMap(9.80665))
    # 1 inH₂O = 249.08891 Pa (conventional, at 4°C, 25.4 mm × 9.80665)
    graph.add_edge(src=units.inch_water, dst=units.pascal, map=LinearMap(249.08891))

    # --- Force ---
    # 1 lbf = 4.4482216152605 N (exact, from lb_m × g_n)
    graph.add_edge(src=units.pound_force, dst=units.newton, map=LinearMap(4.4482216152605))
    # 1 kgf = 9.80665 N (exact, by definition)
    graph.add_edge(src=units.kilogram_force, dst=units.newton, map=LinearMap(9.80665))
    # 1 kip = 1000 lbf (kilo-pound force)
    graph.add_edge(src=units.kip, dst=units.pound_force, map=LinearMap(1000))
    # 1 poundal = 0.138255 N (ft·lb/s², British absolute unit of force)
    graph.add_edge(src=units.poundal, dst=units.newton, map=LinearMap(0.138255))
    # 1 gram-force = 9.80665e-3 N (exact, by definition of standard gravity)
    graph.add_edge(src=units.gram_force, dst=units.newton, map=LinearMap(9.80665e-3))
    # 1 ounce-force = 0.27801385095378125 N (exact, 1/16 lbf)
    graph.add_edge(src=units.ounce_force, dst=units.newton, map=LinearMap(0.27801385095378125))
    # 1 short ton-force = 8896.443230521 N (exact, 2000 lbf)
    graph.add_edge(src=units.ton_force, dst=units.newton, map=LinearMap(8896.443230521))
    # 1 metric ton-force = 9806.65 N (exact, 1000 kgf)
    graph.add_edge(src=units.metric_ton_force, dst=units.newton, map=LinearMap(9806.65))

    # --- Dynamic Viscosity ---
    # SI equivalence: pascal_second ↔ Pa·s (identity)
    graph.add_edge(src=units.pascal_second, dst=units.pascal * units.second, map=LinearMap(1))

    # --- Kinematic Viscosity ---
    # SI equivalence: square_meter_per_second ↔ m²/s (identity)
    graph.add_edge(src=units.square_meter_per_second, dst=units.meter ** 2 / units.second, map=LinearMap(1))

    # --- Volume ---
    graph.add_edge(src=units.liter, dst=units.gallon, map=LinearMap(0.264172))
    # Cross-dimension: volume → length³ (enables gal/min → m³/h)
    # 1 L = 0.001 m³
    graph.add_edge(src=units.liter, dst=units.meter ** 3, map=LinearMap(0.001))
    # US Customary volume chain: gallon → quart → pint → cup → floz → tbsp → tsp
    graph.add_edge(src=units.gallon, dst=units.quart, map=LinearMap(4))
    graph.add_edge(src=units.quart, dst=units.pint_volume, map=LinearMap(2))
    graph.add_edge(src=units.pint_volume, dst=units.cup, map=LinearMap(2))
    graph.add_edge(src=units.cup, dst=units.fluid_ounce, map=LinearMap(8))
    graph.add_edge(src=units.fluid_ounce, dst=units.tablespoon, map=LinearMap(2))
    graph.add_edge(src=units.tablespoon, dst=units.teaspoon, map=LinearMap(3))
    # 1 oil barrel = 42 US gallons (petroleum industry standard)
    graph.add_edge(src=units.barrel, dst=units.gallon, map=LinearMap(42))
    # 1 imperial gallon = 4.54609 L (exact, by definition)
    graph.add_edge(src=units.imperial_gallon, dst=units.liter, map=LinearMap(4.54609))
    # 1 imperial gallon = 8 imperial pints
    graph.add_edge(src=units.imperial_gallon, dst=units.imperial_pint, map=LinearMap(8))
    # 1 US bushel = 35.23907016688 L (exact, dry measure)
    graph.add_edge(src=units.bushel, dst=units.liter, map=LinearMap(35.23907016688))
    # 1 peck = 1/4 bushel
    graph.add_edge(src=units.bushel, dst=units.peck, map=LinearMap(4))
    # 1 gill = 1/4 US pint = 0.118294 L (US gill)
    graph.add_edge(src=units.pint_volume, dst=units.gill, map=LinearMap(4))
    # 1 minim = 1/480 US fluid ounce = 6.161152e-5 L
    graph.add_edge(src=units.fluid_ounce, dst=units.minim, map=LinearMap(480))
    # 1 cubic foot = 28.316846592 L (exact)
    graph.add_edge(src=units.cubic_foot, dst=units.liter, map=LinearMap(28.316846592))
    # 1 cubic inch = 16.387064 mL = 0.016387064 L (exact)
    graph.add_edge(src=units.cubic_inch, dst=units.liter, map=LinearMap(0.016387064))
    # 1 cubic yard = 764.554857984 L (exact, 27 ft³)
    graph.add_edge(src=units.cubic_yard, dst=units.liter, map=LinearMap(764.554857984))
    # 1 acre-foot = 1233481.83754752 L (exact, 43560 ft³)
    graph.add_edge(src=units.acre_foot, dst=units.liter, map=LinearMap(1233481.83754752))
    # 1 stere = 1 m³ = 1000 L (exact, by definition)
    graph.add_edge(src=units.stere, dst=units.liter, map=LinearMap(1000))
    # 1 imperial quart = 1.1365225 L (exact, 1/4 imperial gallon)
    graph.add_edge(src=units.imperial_quart, dst=units.liter, map=LinearMap(1.1365225))
    # 1 imperial fluid ounce = 28.4130625 mL (exact, 1/20 imperial pint)
    graph.add_edge(src=units.imperial_fluid_ounce, dst=units.liter, map=LinearMap(0.0284130625))
    # 1 imperial gill = 142.0653125 mL (exact, 1/4 imperial pint)
    graph.add_edge(src=units.imperial_gill, dst=units.liter, map=LinearMap(0.1420653125))
    # 1 imperial cup = 284.130625 mL (exact, 1/2 imperial pint)
    graph.add_edge(src=units.imperial_cup, dst=units.liter, map=LinearMap(0.284130625))

    # --- Energy ---
    graph.add_edge(src=units.joule, dst=units.calorie, map=LinearMap(1/4.184))
    graph.add_edge(src=units.joule, dst=units.btu, map=LinearMap(1/1055.06))
    graph.add_edge(src=units.joule, dst=units.watt_hour, map=LinearMap(1/3600))  # 1 Wh = 3600 J
    # 1 therm = 1.05506e8 J (US therm, ≈ 100,000 BTU)
    graph.add_edge(src=units.therm, dst=units.joule, map=LinearMap(1.05506e8))
    # 1 foot-pound = 1.3558179483314 J (exact, lbf × ft)
    graph.add_edge(src=units.foot_pound, dst=units.joule, map=LinearMap(1.3558179483314))
    # 1 thermochemical calorie = 4.184 J (exact, by definition)
    graph.add_edge(src=units.thermochemical_calorie, dst=units.joule, map=LinearMap(4.184))
    # 1 ton of TNT = 4.184e9 J (exact, by convention)
    graph.add_edge(src=units.ton_tnt, dst=units.joule, map=LinearMap(4.184e9))
    # 1 tonne of oil equivalent = 4.1868e10 J (IEA/ISO definition)
    graph.add_edge(src=units.tonne_oil_equivalent, dst=units.joule, map=LinearMap(4.1868e10))
    # Cross-structure: energy/time → power (enables BTU/h → kW)
    # 1 BTU/h = 1055.06 J/h = 1055.06/3600 W = 0.29307 W
    graph.add_edge(src=units.btu / units.hour, dst=units.watt, map=LinearMap(1055.06 / 3600))

    # --- Power ---
    graph.add_edge(src=units.watt, dst=units.horsepower, map=LinearMap(1/745.7))
    # 1 volt-ampere = 1 watt (apparent power equals real power for resistive loads)
    graph.add_edge(src=units.volt_ampere, dst=units.watt, map=LinearMap(1))
    # 1 metric horsepower (PS) = 735.49875 W (exact, by DIN definition)
    graph.add_edge(src=units.metric_horsepower, dst=units.watt, map=LinearMap(735.49875))
    # 1 electrical horsepower = 746 W (exact, by definition)
    graph.add_edge(src=units.electrical_horsepower, dst=units.watt, map=LinearMap(746))
    # 1 boiler horsepower = 9809.5 W (ASME definition)
    graph.add_edge(src=units.boiler_horsepower, dst=units.watt, map=LinearMap(9809.5))
    # 1 refrigeration ton = 3516.8525 W (12000 BTU/h, exact)
    graph.add_edge(src=units.refrigeration_ton, dst=units.watt, map=LinearMap(3516.8525))

    # --- Area ---
    # 1 acre = 43560 ft² = 4046.8564224 m² (exact)
    graph.add_edge(src=units.acre, dst=units.meter ** 2, map=LinearMap(4046.8564224))
    # 1 hectare = 10000 m²
    graph.add_edge(src=units.hectare, dst=units.meter ** 2, map=LinearMap(10000))
    # 1 barn = 1e-28 m² (nuclear/particle physics cross-section unit)
    graph.add_edge(src=units.barn, dst=units.meter ** 2, map=LinearMap(1e-28))

    # --- Velocity ---
    # 1 knot = 1 nmi/h = 1852/3600 m/s
    graph.add_edge(src=units.knot, dst=units.meter / units.second, map=LinearMap(1852 / 3600))
    # 1 mph = 1609.344/3600 m/s
    graph.add_edge(src=units.mile_per_hour, dst=units.meter / units.second, map=LinearMap(1609.344 / 3600))

    # --- Charge ---
    # 1 Ah = 3600 C
    graph.add_edge(src=units.ampere_hour, dst=units.coulomb, map=LinearMap(3600))

    # --- Radiation ---
    # 1 curie = 3.7e10 Bq (exact, by definition)
    graph.add_edge(src=units.curie, dst=units.becquerel, map=LinearMap(3.7e10))
    # 1 rem = 0.01 Sv (exact, by definition)
    graph.add_edge(src=units.rem, dst=units.sievert, map=LinearMap(0.01))
    # 1 rad (absorbed dose) = 0.01 Gy (exact, by definition)
    graph.add_edge(src=units.rad_dose, dst=units.gray, map=LinearMap(0.01))
    # Radiation exposure: 1 R = 2.58e-4 C/kg (exact, ICRU definition)
    graph.add_edge(src=units.coulomb_per_kilogram, dst=units.coulomb / units.kilogram, map=LinearMap(1))
    graph.add_edge(src=units.roentgen, dst=units.coulomb_per_kilogram, map=LinearMap(2.58e-4))

    # --- Historical Electrical ---
    # Pre-1948 "international" electrical units (based on physical standards)
    # 1 international ampere = 1.000022 A (silver voltameter definition)
    graph.add_edge(src=units.international_ampere, dst=units.ampere, map=LinearMap(1.000022))
    # 1 international volt = 1.00034 V (Weston cell definition)
    graph.add_edge(src=units.international_volt, dst=units.volt, map=LinearMap(1.00034))
    # 1 international ohm = 1.00049 Ω (mercury column definition)
    graph.add_edge(src=units.international_ohm, dst=units.ohm, map=LinearMap(1.00049))

    # --- Catalytic Activity ---
    # 1 enzyme unit (U) = 1/60 µkat = 1.6667e-8 kat
    graph.add_edge(src=units.enzyme_unit, dst=units.katal, map=LinearMap(1/60e6))

    # --- Textile (linear density) ---
    # 1 tex = 1 g/1000m = 1e-6 kg/m
    graph.add_edge(src=units.tex, dst=units.gram / units.meter, map=LinearMap(1/1000))
    # 1 denier = 1 g/9000m = 1/9 tex
    graph.add_edge(src=units.denier, dst=units.tex, map=LinearMap(1/9))

    # --- Photometry ---
    # 1 foot-candle = 1 lm/ft² = 10.763910417 lux
    graph.add_edge(src=units.foot_candle, dst=units.lux, map=LinearMap(10.763910417))
    # 1 phot = 1 lm/cm² = 10000 lux (exact)
    graph.add_edge(src=units.phot, dst=units.lux, map=LinearMap(10000))
    # 1 nit = 1 cd/m² (identity with lux when sr = 1)
    graph.add_edge(src=units.nit, dst=units.lux, map=LinearMap(1))
    # 1 stilb = 1 cd/cm² = 10000 cd/m² = 10000 nit (exact)
    graph.add_edge(src=units.stilb, dst=units.nit, map=LinearMap(10000))
    # 1 lambert = (1/π) cd/cm² = 10000/π nit
    graph.add_edge(src=units.lambert, dst=units.nit, map=LinearMap(10000 / math.pi))
    # 1 apostilb = (1/π) cd/m² = 1/π nit
    graph.add_edge(src=units.apostilb, dst=units.nit, map=LinearMap(1 / math.pi))

    # --- Viscosity ---
    # 1 reyn = 1 lbf·s/in² = 6894.757 Pa·s (exact, from psi definition)
    graph.add_edge(src=units.reyn, dst=units.pascal_second, map=LinearMap(6894.757))

    # --- Spectroscopy / Radiation ---
    # SI bridge: joule_per_square_meter ↔ J/m² (identity)
    graph.add_edge(src=units.joule_per_square_meter, dst=units.joule / units.meter ** 2, map=LinearMap(1))
    # 1 jansky = 1e-26 W/(m²·Hz) = 1e-26 J/m² (exact, by IAU definition)
    graph.add_edge(src=units.jansky, dst=units.joule_per_square_meter, map=LinearMap(1e-26))

    # --- Electric Dipole Moment ---
    # SI bridge: coulomb_meter ↔ C·m (identity)
    graph.add_edge(src=units.coulomb_meter, dst=units.coulomb * units.meter, map=LinearMap(1))

    # --- Acceleration ---
    # SI bridge: meter_per_second_squared ↔ m/s² (identity)
    graph.add_edge(src=units.meter_per_second_squared, dst=units.meter / units.second ** 2, map=LinearMap(1))
    # 1 standard gravity (g₀) = 9.80665 m/s² (exact, by definition)
    graph.add_edge(src=units.standard_gravity, dst=units.meter_per_second_squared, map=LinearMap(9.80665))

    # --- Wavenumber ---
    # SI bridge: reciprocal_meter ↔ m⁻¹ (identity)
    graph.add_edge(src=units.reciprocal_meter, dst=units.meter ** -1, map=LinearMap(1))

    # --- Concentration ---
    # 1 molar (M) = 1 mol/L (exact, by definition)
    graph.add_edge(src=units.molar, dst=units.mole / units.liter, map=LinearMap(1))

    # --- Information ---
    graph.add_edge(src=units.byte, dst=units.bit, map=LinearMap(8))

    # --- Angle ---
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

    # --- Logarithmic (v0.9.1) ---
    # Pure ratio → logarithmic unit conversions
    graph.add_edge(src=units.fraction, dst=units.bel, map=LogMap(scale=1, base=10))        # ratio → bel
    graph.add_edge(src=units.fraction, dst=units.decibel, map=LogMap(scale=10, base=10))   # ratio → dB
    graph.add_edge(src=units.fraction, dst=units.neper, map=LogMap(scale=1, base=math.e))  # ratio → Np
    graph.add_edge(src=units.bel, dst=units.decibel, map=LinearMap(10))                    # 1 B = 10 dB

    # Reference-level conversions (linear unit → dB variant)
    # dBm: 10·log₁₀(P / 1 mW), reference = 1e-3 W
    graph.add_edge(src=units.watt, dst=units.decibel_milliwatt, map=LogMap(scale=10, base=10, reference=1e-3))
    # dBW: 10·log₁₀(P / 1 W), reference = 1 W
    graph.add_edge(src=units.watt, dst=units.decibel_watt, map=LogMap(scale=10, base=10, reference=1.0))
    # dBV: 20·log₁₀(V / 1 V), reference = 1 V (amplitude uses scale=20)
    graph.add_edge(src=units.volt, dst=units.decibel_volt, map=LogMap(scale=20, base=10, reference=1.0))
    # dBSPL: 20·log₁₀(P / 20 µPa), reference = 20e-6 Pa (amplitude-like for pressure)
    graph.add_edge(src=units.pascal, dst=units.decibel_spl, map=LogMap(scale=20, base=10, reference=20e-6))

    # pH: -log₁₀([H⁺] / 1 mol/L)
    # pH has concentration dimension (same as mol/L), enabling direct conversion.
    graph.add_edge(
        src=units.mole / units.liter,
        dst=units.pH,
        map=LogMap(scale=-1, base=10, reference=1.0),
    )

    # -------------------------------------------------------------------------
    # Cross-Basis Edges (CGS/CGS-ESU ↔ SI)
    # -------------------------------------------------------------------------
    graph._basis_graph = _build_standard_basis_graph()

    # CGS mechanical → SI (CGS_TO_SI: src=CGS unit, dst=SI unit)
    graph.connect_systems(
        basis_transform=CGS_TO_SI,
        edges={
            (units.dyne, units.newton): LinearMap(1e-5),
            (units.erg, units.joule): LinearMap(1e-7),
            (units.barye, units.pascal): LinearMap(0.1),
            (units.poise, units.pascal_second): LinearMap(0.1),
            (units.stokes, units.square_meter_per_second): LinearMap(1e-4),
            (units.galileo, units.meter_per_second_squared): LinearMap(0.01),
            (units.kayser, units.reciprocal_meter): LinearMap(100),
            (units.langley, units.joule_per_square_meter): LinearMap(41840),
        },
    )

    # CGS-ESU electromagnetic ↔ SI (SI_TO_CGS_ESU: src=SI unit, dst=CGS-ESU unit)
    graph.connect_systems(
        basis_transform=SI_TO_CGS_ESU,
        edges={
            (units.ampere, units.statampere): LinearMap(2.99792458e9),
            (units.coulomb, units.statcoulomb): LinearMap(2.99792458e9),
            (units.volt, units.statvolt): LinearMap(1 / 2.99792458e2),
            (units.ohm, units.statohm): LinearMap(1 / 8.9875517873681764e11),
            (units.farad, units.statfarad): LinearMap(8.9875517873681764e11),
            (units.tesla, units.gauss): LinearMap(1e4),
            (units.weber, units.maxwell): LinearMap(1e8),
            (units.ampere_per_meter, units.oersted): LinearMap(4 * math.pi * 1e-3),
            (units.coulomb_meter, units.debye): LinearMap(1 / 3.33564095198152e-30),
        },
    )

    # CGS-EMU electromagnetic ↔ SI (SI_TO_CGS_EMU: src=SI unit, dst=CGS-EMU unit)
    graph.connect_systems(
        basis_transform=SI_TO_CGS_EMU,
        edges={
            (units.ampere, units.biot): LinearMap(0.1),          # 1 A = 0.1 Bi
            (units.coulomb, units.abcoulomb): LinearMap(0.1),    # 1 C = 0.1 abC
            (units.volt, units.abvolt): LinearMap(1e8),          # 1 V = 1e8 abV
            (units.ohm, units.abohm): LinearMap(1e9),            # 1 Ω = 1e9 abΩ
            (units.farad, units.abfarad): LinearMap(1e-9),       # 1 F = 1e-9 abF
            (units.henry, units.abhenry): LinearMap(1e9),        # 1 H = 1e9 abH
        },
    )
    # Gilbert: 1 Gb = 1/(4π) biot (magnetomotive force)
    graph.add_edge(src=units.gilbert, dst=units.biot, map=LinearMap(1 / (4 * math.pi)))

    # CGS-ESU ↔ CGS-EMU (ESU↔EMU bridge via speed of light c)
    # c_cgs = 29979245800 cm/s (exact)
    c_cgs = 29979245800
    graph.connect_systems(
        basis_transform=CGS_ESU_TO_CGS_EMU,
        edges={
            (units.statampere, units.biot): LinearMap(1 / c_cgs),
            (units.statcoulomb, units.abcoulomb): LinearMap(1 / c_cgs),
            (units.statvolt, units.abvolt): LinearMap(c_cgs),
            (units.statohm, units.abohm): LinearMap(c_cgs ** 2),
            (units.statfarad, units.abfarad): LinearMap(1 / c_cgs ** 2),
        },
    )

    # ---- Physical constants (defined once, derived factors computed below) ----
    # Exact (2019 SI redefinition)
    _eV_J = 1.602176634e-19             # electronvolt in joules (exact)
    # CODATA 2018 recommended values
    _Eh_J = 4.3597447222071e-18         # hartree energy in joules
    _Ry_J = 2.1798723611035e-18         # rydberg energy in joules (= 0.5 Eh)
    _a0_m = 5.29177210903e-11           # Bohr radius in metres
    _tau_s = 2.4188843265857e-17        # atomic time unit in seconds (ℏ/Eh)
    _me_kg = 9.1093837015e-31           # electron mass in kilograms
    _EP_J = 1.9560813e9                 # Planck energy in joules (m_P c², CODATA 2018)
    _mP_kg = 2.176434e-8               # Planck mass in kilograms
    _lP_m = 1.616255e-35               # Planck length in metres
    _tP_s = 5.391247e-44               # Planck time in seconds
    _TP_K = 1.416784e32                # Planck temperature in kelvin

    # Natural units ↔ SI (SI_TO_NATURAL: src=SI unit, dst=natural unit)
    graph.connect_systems(
        basis_transform=SI_TO_NATURAL,
        edges={
            (units.joule, units.electron_volt): LinearMap(1 / _eV_J),
        },
    )

    # Atomic units ↔ SI (SI_TO_ATOMIC: src=SI unit, dst=atomic unit)
    graph.connect_systems(
        basis_transform=SI_TO_ATOMIC,
        edges={
            (units.joule, units.hartree): LinearMap(1 / _Eh_J),
            (units.joule, units.rydberg): LinearMap(1 / _Ry_J),
            (units.meter, units.bohr_radius): LinearMap(1 / _a0_m),
            (units.second, units.atomic_time): LinearMap(1 / _tau_s),
            (units.kilogram, units.electron_mass): LinearMap(1 / _me_kg),
        },
    )

    # Atomic intra-basis edges (factors derived from SI bridge constants)
    # electron_mass ↔ hartree: mₑc²/Eₕ = 1/α² ≈ 18778.9
    _c = 299792458  # speed of light (exact)
    graph.add_edge(src=units.electron_mass, dst=units.hartree, map=LinearMap(_me_kg * _c ** 2 / _Eh_J))
    # bohr_radius ↔ atomic_time: a₀/τ = αc ≈ 2.188e6 m/s... but both in E⁻¹,
    # so factor = (1/a₀ in SI) / (1/τ in SI) = τ/a₀  →  a₀ → τ: multiply by a₀/τ...
    # Actually: 1 bohr_radius = a₀ metres, 1 atomic_time = τ seconds.
    # Both map to E⁻¹. Converting bohr_radius → atomic_time means:
    # a₀ m → ? atomic_time. Via SI: a₀ m × (1/τ atomic_time/s) = a₀/τ atomic_time.
    graph.add_edge(src=units.bohr_radius, dst=units.atomic_time, map=LinearMap(_a0_m / _tau_s))

    # Planck units ↔ SI (SI_TO_PLANCK: src=SI unit, dst=Planck unit)
    graph.connect_systems(
        basis_transform=SI_TO_PLANCK,
        edges={
            (units.joule, units.planck_energy): LinearMap(1 / _EP_J),
            (units.kilogram, units.planck_mass): LinearMap(1 / _mP_kg),
            (units.meter, units.planck_length): LinearMap(1 / _lP_m),
            (units.second, units.planck_time): LinearMap(1 / _tP_s),
            (units.kelvin, units.planck_temperature): LinearMap(1 / _TP_K),
        },
    )

    # Planck intra-basis edges (c = ℏ = k_B = 1 ⇒ mass ≡ energy, length ≡ time)
    graph.add_edge(src=units.planck_mass, dst=units.planck_energy, map=LinearMap(1))
    graph.add_edge(src=units.planck_temperature, dst=units.planck_energy, map=LinearMap(1))
    graph.add_edge(src=units.planck_length, dst=units.planck_time, map=LinearMap(1))

    # Inter-basis isomorphisms
    # Factors are computed from the SI bridge constants above so that
    # round-trips like J → E_P → eV → Eh → J cancel algebraically,
    # independent of the absolute precision of any single constant.

    # Natural ↔ Planck (mediated by G)
    graph.connect_systems(
        basis_transform=NATURAL_TO_PLANCK,
        edges={
            (units.electron_volt, units.planck_energy): LinearMap(_eV_J / _EP_J),
        },
    )

    # Natural ↔ Atomic (mediated by e, mₑ, 4πε₀)
    graph.connect_systems(
        basis_transform=NATURAL_TO_ATOMIC,
        edges={
            (units.electron_volt, units.hartree): LinearMap(_eV_J / _Eh_J),
        },
    )

    # Planck ↔ Atomic (mediated by G, e, mₑ, 4πε₀)
    graph.connect_systems(
        basis_transform=PLANCK_TO_ATOMIC,
        edges={
            (units.planck_energy, units.hartree): LinearMap(_EP_J / _Eh_J),
        },
    )



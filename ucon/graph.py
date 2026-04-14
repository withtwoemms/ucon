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
            if current_product is not None and len(current_product.factors) == 1:
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

        # Try BFS product path on base-scale versions.
        # This handles cases like kN/cm² → Pa where no direct edge exists
        # but a multi-hop path through base-scale intermediates does:
        # kN/cm² → (scale) → N/m² → (product edge) → Pa
        src_base_factors = {
            UnitFactor(f.unit, Scale.one): exp
            for f, exp in src.factors.items()
        }
        src_base = UnitProduct(src_base_factors)
        src_base_key = self._product_key(src_base)
        # Reuse dst_base/dst_base_key from above
        try:
            base_map = self._bfs_product_path(src=src_base, dst=dst_base)
            # Compose: src → src_base (fold scale) → dst_base (BFS) → dst (fold scale)
            src_scale = src.fold_scale() / src_base.fold_scale()
            dst_scale = dst_base.fold_scale() / dst.fold_scale()
            return LinearMap(dst_scale) @ base_map @ LinearMap(src_scale)
        except ConversionNotFound:
            pass

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
    """Load the default conversion graph from comprehensive.ucon.toml."""
    from ucon._loader import get_graph
    return get_graph()


def _build_standard_edges(graph: ConversionGraph) -> None:  # pragma: no cover
    """Legacy stub — edges are now loaded from TOML via _build_standard_graph().

    Retained as a no-op for any external code that references it.
    """
    return

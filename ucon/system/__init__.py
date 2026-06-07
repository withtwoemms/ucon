# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.system
===========

System-level value types for ucon.

This subpackage hosts the abstractions that record which units, dimensions,
conversions, and basis transforms a coherent unit system uses.

Public surface (v1.8):

- :class:`BaseUnits` -- a small named ``Mapping[Dimension, Unit]`` that
  records the canonical base unit per dimension. The renamed predecessor
  of the v1.7 top-level ``UnitSystem`` class.
- :class:`UnitSystem` -- the new value type that owns a ``BaseUnits`` plus
  the registries (units, dimensions, conversions, basis_graph, contexts,
  constants) and a per-instance :class:`AlgebraCache`.
- :class:`AlgebraCache` -- per-instance cache for ``Dimension`` algebra
  (mul/div/pow).
- :func:`use` -- contextmanager that sets the active ``UnitSystem``.
- :func:`active` -- returns the active ``UnitSystem`` (snapshotting from
  globals if none has been set).

The PEP-562 alias ``from ucon import UnitSystem`` continues to resolve to
:class:`BaseUnits` in v1.8 with a ``PendingDeprecationWarning``. The new
value type is reachable only via ``from ucon.system import UnitSystem``.
"""

from __future__ import annotations

import warnings
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Tuple,
    Union,
)

from ucon._active import _active
from ucon.core import Number, Unit, UnitFactor, UnitProduct
from ucon.core._parsing_graph import _parsing_graph
from ucon.core.exceptions import DimensionNotCovered, UnknownUnitError
from ucon.formulas import FormulaRegistry
from ucon.kinds import KindLattice
from ucon.resolver import parse_unit as _parse_unit
from ucon._algebra_cache import AlgebraCache, _get_active_cache

if TYPE_CHECKING:
    from ucon.basis import Vector
    from ucon.basis.graph import BasisGraph
    from ucon.basis.transforms import BasisTransform, ConstantBoundBasisTransform
    from ucon.basis.types import Basis
    from ucon.dimension import Dimension
    from ucon.constants import Constant
    from ucon.contexts import ContextEdge, ConversionContext
    from ucon.conversion import Graph as ConversionGraph
    from ucon.maps import Map


# -----------------------------------------------------------------------------
# Algebra-level types
# -----------------------------------------------------------------------------


class ConflictPolicy(Enum):
    """Policy for resolving name collisions when combining two
    :class:`UnitSystem` values.

    - :attr:`RAISE` (default): raise :class:`ExtendConflict` on any
      collision.
    - :attr:`PREFER_SELF`: keep the LHS definition; ignore the RHS.
    - :attr:`PREFER_OTHER`: replace the LHS definition with the RHS.
    """

    RAISE = "raise"
    PREFER_SELF = "prefer-self"
    PREFER_OTHER = "prefer-other"


class ExtendConflict(ValueError):
    """Raised when :meth:`UnitSystem.extend` finds a name collision under
    :attr:`ConflictPolicy.RAISE` policy.

    The ``registry`` attribute names the registry in which the conflict
    occurred (``"units"``, ``"dimensions"``, ``"base_units"``,
    ``"conversions"``, ``"contexts"``, or ``"constants"``); ``key`` is the
    colliding name.
    """

    def __init__(self, registry: str, key: str, message: str = "") -> None:
        super().__init__(message or f"conflict in {registry!r} on key {key!r}")
        self.registry = registry
        self.key = key


class InvalidRename(ValueError):
    """Raised when :class:`Bridge` is constructed with a rename pair that
    is not synonym-equivalent.

    A pair ``(src_name, dst_name)`` is synonym-equivalent only when
    ``src.units[src_name]`` and ``dst.units[dst_name]`` represent the
    same physical unit -- same dimension (under ``basis_transform`` when
    one is supplied) and identical base form. Definitional differences
    must be expressed via ``basis_transform`` or a custom conversion
    edge, not via rename.

    Attributes
    ----------
    src_name : str
        The source-side rename key.
    dst_name : str
        The destination-side rename value.
    reason : str
        Why the pair is not synonym-equivalent.
    """

    def __init__(self, src_name: str, dst_name: str, reason: str = "") -> None:
        super().__init__(
            f"invalid rename {src_name!r} -> {dst_name!r}"
            + (f": {reason}" if reason else "")
        )
        self.src_name = src_name
        self.dst_name = dst_name
        self.reason = reason


@dataclass(frozen=True)
class RegistryDiff:
    """Per-registry diff payload for :class:`SystemDiff`.

    Attributes
    ----------
    added : frozenset[str]
        Keys present in ``other`` but not in ``self``.
    removed : frozenset[str]
        Keys present in ``self`` but not in ``other``.
    redefined : frozenset[str]
        Keys present in both with non-equal values.
    """

    added: FrozenSet[str] = field(default_factory=frozenset)
    removed: FrozenSet[str] = field(default_factory=frozenset)
    redefined: FrozenSet[str] = field(default_factory=frozenset)

    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.redefined)


@dataclass(frozen=True)
class SystemDiff:
    """Structured difference between two :class:`UnitSystem` values.

    Returned by :meth:`UnitSystem.diff`. Each field is a
    :class:`RegistryDiff` describing additions, removals, and
    redefinitions in that registry as ``self -> other``.
    """

    units: RegistryDiff = field(default_factory=RegistryDiff)
    dimensions: RegistryDiff = field(default_factory=RegistryDiff)
    base_units: RegistryDiff = field(default_factory=RegistryDiff)
    conversions: RegistryDiff = field(default_factory=RegistryDiff)
    contexts: RegistryDiff = field(default_factory=RegistryDiff)
    constants: RegistryDiff = field(default_factory=RegistryDiff)

    def is_empty(self) -> bool:
        return all(
            getattr(self, name).is_empty()
            for name in (
                "units", "dimensions", "base_units",
                "conversions", "contexts", "constants",
            )
        )


@dataclass(frozen=True)
class BaseUnits:
    """
    A named mapping from dimensions to base units.

    Represents a coherent unit system like SI or Imperial, where each
    covered dimension has exactly one base unit. Partial systems are
    allowed (Imperial doesn't need mole).

    Parameters
    ----------
    name : str
        The name of the unit system (e.g., "SI", "Imperial").
    bases : dict[Dimension, Unit]
        Mapping from dimensions to their base units.

    Raises
    ------
    ValueError
        If name is empty, bases is empty, or a unit's dimension doesn't
        match its declared dimension key.

    Examples
    --------
    >>> si = BaseUnits(
    ...     name="SI",
    ...     bases={
    ...         LENGTH: meter,
    ...         MASS: kilogram,
    ...         TIME: second,
    ...     }
    ... )
    >>> si.base_for(LENGTH)
    <Unit m>
    """
    name: str
    bases: Dict[Dimension, 'Unit']

    def __post_init__(self):
        if not self.name:
            raise ValueError("BaseUnits must have a name")
        if not self.bases:
            raise ValueError("BaseUnits must have at least one base unit")

        for dim, unit in self.bases.items():
            if unit.dimension != dim:
                raise ValueError(
                    f"Base unit {unit.name} has dimension {unit.dimension.name}, "
                    f"but was declared as base for {dim.name}"
                )

    def base_for(self, dim: Dimension) -> 'Unit':
        """Return the base unit for a dimension.

        Raises
        ------
        DimensionNotCovered
            If this system has no base unit for the dimension.
        """
        if dim not in self.bases:
            raise DimensionNotCovered(
                f"{self.name} has no base unit for {dim.name}"
            )
        return self.bases[dim]

    def covers(self, dim: Dimension) -> bool:
        """Return True if this system has a base unit for the dimension."""
        return dim in self.bases

    @property
    def dimensions(self) -> set:
        """Return the set of dimensions covered by this system."""
        return set(self.bases.keys())

    def __hash__(self):
        # Frozen dataclass with dict field needs custom hash
        return hash((self.name, tuple(sorted(self.bases.items(), key=lambda x: x[0].name))))


# AlgebraCache and _get_active_cache are imported from
# ucon._algebra_cache (Layer 0/1) and re-exported here for
# backward compatibility with ``from ucon.system import AlgebraCache``.


# -----------------------------------------------------------------------------
# UnitSystem value type
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class UnitSystem:
    """A complete unit system as a value type.

    Owns the basis, the registries (units, dimensions, conversion_graph,
    basis_graph, contexts, constants), the canonical ``base_units``
    mapping, and a per-instance :class:`AlgebraCache`.

    Parameters
    ----------
    basis : Basis
        Dimensional coordinate system.
    units : Mapping[str, Unit]
        Name registry of units.
    dimensions : Mapping[str, Dimension]
        Name registry of dimensions.
    base_units : BaseUnits
        Canonical base unit per covered dimension.
    conversion_graph : ConversionGraph
        Graph of unit conversion morphisms.
    basis_graph : BasisGraph
        Graph of basis transforms.
    contexts : Mapping[str, ConversionContext]
        Named cross-dimensional context bundles. Defaults to empty.
    constants : Mapping[str, Constant]
        Physical constants registry. Defaults to empty.
    _algebra_cache : AlgebraCache
        Per-instance dimension-algebra cache. Constructed empty by default.

    Notes
    -----
    The frozen dataclass holds references to mutable registries (dicts and
    graph objects). "Frozen" applies to the field bindings, not the
    contents of the registries -- mirroring how :class:`BaseUnits` already
    treats its ``bases`` dict. Equality and hash use identity for the
    mutable mappings/graphs and value equality for ``basis`` and
    ``base_units``; the per-instance ``_algebra_cache`` is excluded from
    both.
    """

    basis: 'Basis'
    units: Mapping[str, 'Unit']
    dimensions: Mapping[str, 'Dimension']
    base_units: BaseUnits
    conversion_graph: 'ConversionGraph'
    basis_graph: 'BasisGraph'
    contexts: Mapping[str, 'ConversionContext'] = field(default_factory=dict)
    constants: Mapping[str, 'Constant'] = field(default_factory=dict)
    _algebra_cache: AlgebraCache = field(
        default_factory=AlgebraCache, compare=False, repr=False
    )
    dimensions_by_vector: Optional[Mapping['Vector', 'Dimension']] = field(
        default=None, compare=False, repr=False
    )

    def __post_init__(self) -> None:
        # ``dimensions_by_vector`` powers ``resolve(vector)``. It is
        # derived from ``dimensions`` (excluding pseudo-dimensions, which
        # share the zero vector and are tag-isolated) when not supplied
        # explicitly. The bootstrap path passes the precomputed standard
        # registry; ``from_toml`` and other call sites get the derivation
        # for free.
        if self.dimensions_by_vector is None:
            derived = {
                d.vector: d
                for d in self.dimensions.values()
                if not d.is_pseudo
            }
            object.__setattr__(self, 'dimensions_by_vector', derived)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UnitSystem):
            return NotImplemented
        return (
            self.basis == other.basis
            and self.base_units == other.base_units
            and self.units is other.units
            and self.dimensions is other.dimensions
            and self.conversion_graph is other.conversion_graph
            and self.basis_graph is other.basis_graph
            and self.contexts is other.contexts
            and self.constants is other.constants
        )

    def __hash__(self) -> int:
        return hash((
            self.basis,
            self.base_units,
            id(self.units),
            id(self.dimensions),
            id(self.conversion_graph),
            id(self.basis_graph),
            id(self.contexts),
            id(self.constants),
        ))

    def resolve_unit(self, name: str):
        """Resolve a unit name/alias/expression string to a ``Unit`` or ``UnitProduct``.

        Delegates to :func:`~ucon.resolver.parse_unit` with ``system=self``
        so the resolver draws from this system's unit registry.

        Parameters
        ----------
        name : str
            Unit name, alias, scale-prefixed name, or composite expression
            (e.g., ``"ft"``, ``"km"``, ``"kg*m/s^2"``).

        Returns
        -------
        Unit or UnitProduct
            The resolved unit.

        Raises
        ------
        UnknownUnitError
            If the string cannot be resolved.
        """
        return _parse_unit(name, system=self)

    # -------------------------------------------------------------------
    # Algebra — pure functions returning new ``UnitSystem`` values.
    # -------------------------------------------------------------------

    def extend(
        self,
        other: 'UnitSystem',
        *,
        on_conflict: ConflictPolicy = ConflictPolicy.RAISE,
    ) -> 'UnitSystem':
        """Return a new system combining ``self`` and ``other``.

        Unions each registry (units, dimensions, base_units, conversion
        edges, contexts, constants). Name collisions are resolved by
        ``on_conflict`` (a :class:`ConflictPolicy` member):

        - :attr:`ConflictPolicy.RAISE` (default): raise
          :class:`ExtendConflict` if any registry has two non-equal
          definitions for the same name. Identical values do not trigger
          the error.
        - :attr:`ConflictPolicy.PREFER_SELF`: keep the LHS value on
          conflict; the RHS value is silently discarded.
        - :attr:`ConflictPolicy.PREFER_OTHER`: replace the LHS value with
          the RHS value.

        ``self.basis`` and ``self.basis_graph`` are preserved unchanged.
        Use :meth:`with_basis` / :meth:`with_basis_graph` to change them
        explicitly.
        """
        _validate_conflict_policy(on_conflict)

        merged_units = _merge_mapping(
            self.units, other.units, "units", on_conflict
        )
        merged_dimensions = _merge_mapping(
            self.dimensions, other.dimensions, "dimensions", on_conflict
        )
        merged_base_units = _merge_base_units(
            self.base_units, other.base_units, on_conflict
        )
        merged_contexts = _merge_mapping(
            self.contexts, other.contexts, "contexts", on_conflict
        )
        merged_constants = _merge_mapping(
            self.constants, other.constants, "constants", on_conflict
        )
        merged_graph = _merge_conversion_graphs(
            self.conversion_graph,
            other.conversion_graph,
            merged_units,
            on_conflict,
        )

        return UnitSystem(
            basis=self.basis,
            units=merged_units,
            dimensions=merged_dimensions,
            base_units=merged_base_units,
            conversion_graph=merged_graph,
            basis_graph=self.basis_graph,
            contexts=merged_contexts,
            constants=merged_constants,
        )

    def extend_many(
        self,
        *others: 'UnitSystem',
        on_conflict: ConflictPolicy = ConflictPolicy.RAISE,
    ) -> 'UnitSystem':
        """Return a new system combining ``self`` with all ``others``.

        Semantically equivalent to chaining ``.extend()`` calls but
        performs a single conversion-graph copy regardless of how many
        systems are merged. This avoids the O(N * graph_size) cost of
        sequential ``extend()`` when composing many packages.

        Parameters
        ----------
        *others : UnitSystem
            One or more systems to merge into ``self``.
        on_conflict : ConflictPolicy
            Collision resolution strategy (same semantics as
            :meth:`extend`).
        """
        if not others:
            return self

        _validate_conflict_policy(on_conflict)

        merged_units: Mapping[str, Unit] = dict(self.units)
        merged_dimensions: Mapping[str, 'Dimension'] = dict(self.dimensions)
        merged_base_units = self.base_units
        merged_contexts: Mapping[str, 'ConversionContext'] = dict(self.contexts)
        merged_constants: Mapping[str, 'Constant'] = dict(self.constants)

        for other in others:
            merged_units = _merge_mapping(
                merged_units, other.units, "units", on_conflict
            )
            merged_dimensions = _merge_mapping(
                merged_dimensions, other.dimensions, "dimensions", on_conflict
            )
            merged_base_units = _merge_base_units(
                merged_base_units, other.base_units, on_conflict
            )
            merged_contexts = _merge_mapping(
                merged_contexts, other.contexts, "contexts", on_conflict
            )
            merged_constants = _merge_mapping(
                merged_constants, other.constants, "constants", on_conflict
            )

        merged_graph = _merge_conversion_graphs_bulk(
            self.conversion_graph,
            [o.conversion_graph for o in others],
            merged_units,
            on_conflict,
        )

        return UnitSystem(
            basis=self.basis,
            units=merged_units,
            dimensions=merged_dimensions,
            base_units=merged_base_units,
            conversion_graph=merged_graph,
            basis_graph=self.basis_graph,
            contexts=merged_contexts,
            constants=merged_constants,
        )

    def restrict(
        self,
        *,
        dimensions: Optional[Iterable['Dimension']] = None,
        units: Optional[Iterable[str]] = None,
    ) -> 'UnitSystem':
        """Return a new system retaining only the named dimensions and units.

        Either filter may be ``None`` to leave that registry unrestricted.
        Filters compose: a unit survives only if both filters admit it.

        The conversion graph is filtered to edges whose endpoints survive.
        ``base_units`` is filtered to entries whose dimension and unit
        survive. ``basis``, ``basis_graph``, ``contexts``, and
        ``constants`` are preserved unchanged.
        """
        # Resolve dimensions filter to a frozenset of dimension objects.
        if dimensions is None:
            kept_dims: Optional[FrozenSet['Dimension']] = None
        else:
            kept_dims = frozenset(dimensions)

        kept_unit_names: Optional[FrozenSet[str]] = (
            frozenset(units) if units is not None else None
        )

        def _keep_unit(name: str, unit_obj: 'Unit') -> bool:
            if kept_unit_names is not None and name not in kept_unit_names:
                return False
            if kept_dims is not None and unit_obj.dimension not in kept_dims:
                return False
            return True

        new_units: Dict[str, 'Unit'] = {
            name: u for name, u in self.units.items() if _keep_unit(name, u)
        }
        kept_unit_name_set = frozenset(new_units.keys())

        if kept_dims is None:
            new_dimensions: Mapping[str, 'Dimension'] = dict(self.dimensions)
        else:
            new_dimensions = {
                name: d for name, d in self.dimensions.items() if d in kept_dims
            }

        new_base_units = _restrict_base_units(
            self.base_units, kept_dims, kept_unit_name_set
        )

        new_graph = _restrict_conversion_graph(
            self.conversion_graph, kept_unit_name_set
        )

        return UnitSystem(
            basis=self.basis,
            units=new_units,
            dimensions=new_dimensions,
            base_units=new_base_units,
            conversion_graph=new_graph,
            basis_graph=self.basis_graph,
            contexts=dict(self.contexts),
            constants=dict(self.constants),
        )

    def merge(
        self,
        other: 'UnitSystem',
        resolver: Callable[['Unit', 'Unit'], 'Unit'],
    ) -> 'UnitSystem':
        """Return a new system combining ``self`` and ``other`` with a
        callable resolver for unit-name conflicts.

        For every unit name shared between ``self.units`` and
        ``other.units`` whose values are non-equal, the resolver is invoked
        as ``resolver(self_unit, other_unit)`` and must return one of the
        two units (or a structurally-equal alternative). All other
        registries (dimensions, base_units, conversion edges, contexts,
        constants) use :attr:`ConflictPolicy.PREFER_SELF` semantics on
        conflict.

        The resolver is *not* called for keys present in only one side or
        for keys whose values are already equal.
        """
        merged_units: Dict[str, 'Unit'] = dict(self.units)
        for name, unit in other.units.items():
            if name not in merged_units:
                merged_units[name] = unit
                continue
            existing = merged_units[name]
            if existing == unit:
                continue
            merged_units[name] = resolver(existing, unit)

        merged_dimensions = _merge_mapping(
            self.dimensions, other.dimensions, "dimensions",
            ConflictPolicy.PREFER_SELF,
        )
        merged_base_units = _merge_base_units(
            self.base_units, other.base_units, ConflictPolicy.PREFER_SELF
        )
        merged_contexts = _merge_mapping(
            self.contexts, other.contexts, "contexts",
            ConflictPolicy.PREFER_SELF,
        )
        merged_constants = _merge_mapping(
            self.constants, other.constants, "constants",
            ConflictPolicy.PREFER_SELF,
        )
        merged_graph = _merge_conversion_graphs(
            self.conversion_graph,
            other.conversion_graph,
            merged_units,
            ConflictPolicy.PREFER_SELF,
        )

        return UnitSystem(
            basis=self.basis,
            units=merged_units,
            dimensions=merged_dimensions,
            base_units=merged_base_units,
            conversion_graph=merged_graph,
            basis_graph=self.basis_graph,
            contexts=merged_contexts,
            constants=merged_constants,
        )

    # -------------------------------------------------------------------
    # Incremental construction
    # -------------------------------------------------------------------

    def with_unit(self, unit: 'Unit') -> 'UnitSystem':
        """Return a new system with ``unit`` added to the units registry.

        If a unit with the same name already exists and is structurally
        equal, returns ``self`` unchanged. Otherwise raises
        :class:`ExtendConflict` on a non-equal collision.
        """
        existing = self.units.get(unit.name)
        if existing is not None:
            if existing == unit:
                return self
            raise ExtendConflict(
                "units",
                unit.name,
                f"with_unit: name {unit.name!r} already registered with a "
                f"different definition",
            )

        new_units: Dict[str, 'Unit'] = dict(self.units)
        new_units[unit.name] = unit

        new_graph = self.conversion_graph.copy()
        new_graph.register_unit(unit)

        return UnitSystem(
            basis=self.basis,
            units=new_units,
            dimensions=dict(self.dimensions),
            base_units=self.base_units,
            conversion_graph=new_graph,
            basis_graph=self.basis_graph,
            contexts=dict(self.contexts),
            constants=dict(self.constants),
        )

    def with_conversion(self, edge: 'ContextEdge') -> 'UnitSystem':
        """Return a new system with ``edge`` added to the conversion graph.

        Accepts the existing :class:`ucon.contexts.ContextEdge` value type
        (``src``, ``dst``, ``map``). Edges are bidirectional; the inverse is
        registered automatically by :meth:`Graph.add_edge`. Re-adding an
        identical edge is a no-op.
        """
        new_graph = self.conversion_graph.copy()
        new_graph.add_edge(
            src=edge.src,
            dst=edge.dst,
            map=edge.map,
        )
        return UnitSystem(
            basis=self.basis,
            units=dict(self.units),
            dimensions=dict(self.dimensions),
            base_units=self.base_units,
            conversion_graph=new_graph,
            basis_graph=self.basis_graph,
            contexts=dict(self.contexts),
            constants=dict(self.constants),
        )

    def with_basis(self, basis: 'Basis') -> 'UnitSystem':
        """Return a new system whose ``basis`` is replaced.

        ``basis_graph`` is preserved as-is; callers are responsible for
        ensuring it contains the new basis (otherwise cross-basis
        operations from this system will fail at use time, not at
        construction).
        """
        if basis == self.basis:
            return self
        return UnitSystem(
            basis=basis,
            units=dict(self.units),
            dimensions=dict(self.dimensions),
            base_units=self.base_units,
            conversion_graph=self.conversion_graph,
            basis_graph=self.basis_graph,
            contexts=dict(self.contexts),
            constants=dict(self.constants),
        )

    def with_basis_graph(self, graph: 'BasisGraph') -> 'UnitSystem':
        """Return a new system whose ``basis_graph`` is replaced."""
        if graph is self.basis_graph:
            return self
        return UnitSystem(
            basis=self.basis,
            units=dict(self.units),
            dimensions=dict(self.dimensions),
            base_units=self.base_units,
            conversion_graph=self.conversion_graph,
            basis_graph=graph,
            contexts=dict(self.contexts),
            constants=dict(self.constants),
        )

    # -------------------------------------------------------------------
    # Relations — pure queries.
    # -------------------------------------------------------------------

    def subsystem_of(self, other: 'UnitSystem') -> bool:
        """Return True iff every unit, dimension, base-unit mapping, and
        conversion edge in ``self`` exists with the same definition in
        ``other``.

        ``basis`` and ``basis_graph`` are not compared; subsystem is a
        registry-content relation.
        """
        for name, unit in self.units.items():
            if other.units.get(name) != unit:
                return False
        for name, dim in self.dimensions.items():
            if other.dimensions.get(name) != dim:
                return False
        for dim, unit in self.base_units.bases.items():
            if other.base_units.bases.get(dim) != unit:
                return False
        # Conversion edges
        self_edges = _enumerate_unit_edges(self.conversion_graph)
        other_edges = _enumerate_unit_edges(other.conversion_graph)
        for key, map_obj in self_edges.items():
            if other_edges.get(key) != map_obj:
                return False
        return True

    def compatible_with(self, other: 'UnitSystem') -> bool:
        """Return True iff ``self`` and ``other`` agree wherever they
        overlap.

        Every shared unit name maps to equal :class:`Unit` definitions;
        every shared dimension name maps to equal :class:`Dimension`
        definitions; every shared base-unit dimension maps to equal
        :class:`Unit`; every shared conversion edge (by endpoint-name)
        maps to the same :class:`Map`. Non-overlapping registry entries
        are ignored.
        """
        for name in self.units.keys() & other.units.keys():
            if self.units[name] != other.units[name]:
                return False
        for name in self.dimensions.keys() & other.dimensions.keys():
            if self.dimensions[name] != other.dimensions[name]:
                return False
        for dim in self.base_units.bases.keys() & other.base_units.bases.keys():
            if self.base_units.bases[dim] != other.base_units.bases[dim]:
                return False
        self_edges = _enumerate_unit_edges(self.conversion_graph)
        other_edges = _enumerate_unit_edges(other.conversion_graph)
        for key in self_edges.keys() & other_edges.keys():
            if self_edges[key] != other_edges[key]:
                return False
        return True

    def diff(self, other: 'UnitSystem') -> SystemDiff:
        """Return a :class:`SystemDiff` describing ``self -> other``.

        Each registry contributes a :class:`RegistryDiff` with ``added``
        (in ``other`` but not ``self``), ``removed`` (in ``self`` but not
        ``other``), and ``redefined`` (in both with non-equal values).
        """
        return SystemDiff(
            units=_mapping_diff(self.units, other.units),
            dimensions=_mapping_diff(self.dimensions, other.dimensions),
            base_units=_base_units_diff(self.base_units, other.base_units),
            conversions=_conversion_diff(
                self.conversion_graph, other.conversion_graph
            ),
            contexts=_mapping_diff(self.contexts, other.contexts),
            constants=_mapping_diff(self.constants, other.constants),
        )

    def shared_units(self, other: 'UnitSystem') -> FrozenSet[str]:
        """Return the set of unit names defined in both systems."""
        return frozenset(self.units.keys() & other.units.keys())

    def shared_dimensions(self, other: 'UnitSystem') -> FrozenSet[str]:
        """Return the set of dimension names defined in both systems."""
        return frozenset(self.dimensions.keys() & other.dimensions.keys())

    # -------------------------------------------------------------------
    # Cross-system value movement.
    # -------------------------------------------------------------------

    def adopt(self, n: 'Number') -> 'Number':
        """Rebind ``n`` to use this system's :class:`Unit` objects.

        Walks ``n.unit`` (a :class:`Unit` or :class:`UnitProduct`) and
        checks that every component-unit name resolves in
        ``self.units``. Returns a new :class:`Number` whose unit
        references point at the objects owned by this system; the
        numeric quantity and uncertainty are unchanged.

        ``adopt`` performs **no conversion**. It is the trivial value-
        movement primitive for the case where unit names already match
        between systems. When names diverge or numeric correction is
        needed, use :class:`Bridge`.

        Parameters
        ----------
        n : Number
            The value to re-bind.

        Returns
        -------
        Number
            A :class:`Number` whose ``unit`` references this system's
            :class:`Unit` objects.

        Raises
        ------
        UnknownUnitError
            If any component unit name is not defined in ``self.units``.
        """
        unit = n.unit
        if isinstance(unit, UnitFactor):
            if unit.unit.name not in self.units:
                raise UnknownUnitError(unit.unit.name)
            rebound = UnitFactor(self.units[unit.unit.name], unit.scale)
            return Number(
                quantity=n.quantity, unit=rebound, uncertainty=n.uncertainty
            )
        if isinstance(unit, Unit):
            if unit.name not in self.units:
                raise UnknownUnitError(unit.name)
            return Number(
                quantity=n.quantity,
                unit=self.units[unit.name],
                uncertainty=n.uncertainty,
            )
        if isinstance(unit, UnitProduct):
            rebound_factors: Dict['UnitFactor', float] = {}
            for factor, exponent in unit.factors.items():
                if factor.unit.name not in self.units:
                    raise UnknownUnitError(factor.unit.name)
                rebound_factor = UnitFactor(
                    self.units[factor.unit.name], factor.scale
                )
                rebound_factors[rebound_factor] = exponent
            return Number(
                quantity=n.quantity,
                unit=UnitProduct(rebound_factors),
                uncertainty=n.uncertainty,
            )
        # Number with no unit — return as-is.
        return Number(
            quantity=n.quantity, unit=unit, uncertainty=n.uncertainty
        )



# _active is imported from ucon._active (Layer 0) and re-exported
# here for backward compatibility.


@dataclass(frozen=True)
class ActiveContext:
    """The ambient state bundle consulted by ucon's runtime.

    A single :class:`~contextvars.ContextVar` (``ucon._active``) carries
    one :class:`ActiveContext` at a time. The payload bundles the
    :class:`UnitSystem` (units, dimensions, graphs) with the
    :class:`~ucon.formulas.FormulaRegistry` (kind-aware arithmetic
    dispatch table), the :class:`~ucon.kinds.KindLattice` (kind taxonomy
    consulted by ``Number.bound_to`` etc.), and ``strict`` (source-unit
    resolution mode for :meth:`Number.to` and arithmetic).

    Keeping ``formulas`` and ``kinds`` off :class:`UnitSystem` is
    deliberate: a system does not own its formulas, and an
    :class:`ActiveContext` lets the caller swap the dispatch table
    without rebuilding the system.

    Attributes
    ----------
    system : UnitSystem
        The active unit system.
    formulas : FormulaRegistry
        Kind-aware arithmetic dispatch table.
    kinds : KindLattice
        Kind taxonomy.
    strict : bool
        Whether source-unit resolution is identity-based (``True``,
        v2.0 default) or falls back to name-based lookup (``False``,
        v1.x ergonomics).
    """

    system: 'UnitSystem'
    formulas: FormulaRegistry
    kinds: KindLattice
    strict: bool = True


def active() -> ActiveContext:
    """Return the currently active :class:`ActiveContext`.

    After ``import ucon``, the active context is always set via eager
    initialization.

    .. versionchanged:: 2.0
       Returns :class:`ActiveContext` instead of :class:`UnitSystem`.
       Use :func:`active_system` for the prior semantics.

    Raises
    ------
    RuntimeError
        If called before ``import ucon`` has completed (i.e. the eager
        init block in ``ucon/__init__.py`` has not yet run).
    """
    ctx = _active.get()
    if ctx is None:
        raise RuntimeError(
            "No active UnitSystem. This usually means ucon.system.active() "
            "was called before 'import ucon' completed. Import the top-level "
            "ucon package first."
        )
    return ctx


def active_system() -> 'UnitSystem':
    """Return the active :class:`UnitSystem`.

    Convenience accessor equivalent to ``active().system``. Replaces the
    pre-v2.0 ``active()`` semantics.
    """
    return active().system


def active_formulas() -> FormulaRegistry:
    """Return the active :class:`~ucon.formulas.FormulaRegistry`.

    Convenience accessor equivalent to ``active().formulas``.
    """
    return active().formulas


def active_kinds() -> KindLattice:
    """Return the active :class:`~ucon.kinds.KindLattice`.

    Convenience accessor equivalent to ``active().kinds``.
    """
    return active().kinds


def active_strict() -> bool:
    """Return the active source-unit resolution mode.

    Convenience accessor equivalent to ``active().strict``.
    """
    return active().strict


@contextmanager
def use(
    system: 'UnitSystem',
    *,
    formulas: Optional[FormulaRegistry] = None,
    kinds: Optional[KindLattice] = None,
    strict: Optional[bool] = None,
) -> Iterator[ActiveContext]:
    """Set the active :class:`ActiveContext` for the with-block.

    Constructs an :class:`ActiveContext` with the given ``system`` and
    inherits ``formulas``, ``kinds``, and ``strict`` from the enclosing
    context when those kwargs are not supplied. On exit the prior
    context is restored.

    Parameters
    ----------
    system : UnitSystem
        The system to activate for the duration of the with-block.
    formulas : FormulaRegistry, optional
        Override the formulas registry. Inherits from the enclosing
        context when ``None``.
    kinds : KindLattice, optional
        Override the kind lattice. Inherits from the enclosing context
        when ``None``.
    strict : bool, optional
        Override source-unit resolution mode. Inherits from the
        enclosing context when ``None``.

    Examples
    --------
    >>> sys = active_system()
    >>> with use(sys) as ctx:
    ...     assert ctx.system is sys
    """
    current = _active.get()
    if current is None:
        # No enclosing context — fall back to empty defaults for the
        # kind-side fields. The eager init in ``ucon/__init__.py``
        # normally ensures ``current`` is set before any ``use()`` call.
        ctx = ActiveContext(
            system=system,
            formulas=formulas if formulas is not None else FormulaRegistry(),
            kinds=kinds if kinds is not None else KindLattice(),
            strict=strict if strict is not None else True,
        )
    else:
        ctx = ActiveContext(
            system=system,
            formulas=formulas if formulas is not None else current.formulas,
            kinds=kinds if kinds is not None else current.kinds,
            strict=strict if strict is not None else current.strict,
        )
    token = _active.set(ctx)
    token_parsing = _parsing_graph.set(system.conversion_graph)
    try:
        yield ctx
    finally:
        _parsing_graph.reset(token_parsing)
        _active.reset(token)


# -----------------------------------------------------------------------------
# Cross-system value movement -- Bridge.
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Bridge:
    """Sanctioned cross-system value movement.

    A ``Bridge`` carries a :class:`~ucon.core.Number` from ``src`` to
    ``dst``, applying optional unit-name renames (synonym-equivalent
    pairs only) and an optional :class:`~ucon.basis.BasisTransform` for
    cross-basis rebasing.

    Rename is **synonym-only**: each ``(a, b)`` in ``rename`` must
    satisfy ``src.units[a]`` and ``dst.units[b]`` representing the same
    physical unit. Definitional remapping (two systems naming distinct
    units identically) must be expressed via ``basis_transform`` or a
    custom conversion edge; it is rejected at construction with
    :class:`InvalidRename`.

    Apply order is rename → ``basis_transform`` → identity-bind to dst
    :class:`Unit`. Under the synonym constraint the two layers commute;
    the order is pinned for trace-readability.

    Attributes
    ----------
    src : UnitSystem
        The source system.
    dst : UnitSystem
        The destination system.
    rename : Mapping[str, str]
        Synonym-equivalent unit-name pairs.
    basis_transform : BasisTransform, optional
        Optional coordinate change for cross-basis values.
    """

    src: UnitSystem
    dst: UnitSystem
    rename: Mapping[str, str] = field(default_factory=dict)
    basis_transform: Optional['BasisTransform'] = None

    def __post_init__(self) -> None:
        for a, b in self.rename.items():
            if a not in self.src.units:
                raise InvalidRename(a, b, f"{a!r} not in src.units")
            if b not in self.dst.units:
                raise InvalidRename(a, b, f"{b!r} not in dst.units")
            self._validate_synonym(a, b, self.src.units[a], self.dst.units[b])

    def _validate_synonym(
        self, a: str, b: str, src_unit: 'Unit', dst_unit: 'Unit'
    ) -> None:
        """Verify ``src_unit`` and ``dst_unit`` are the same physical unit.

        Trivial case (``basis_transform is None``): dimensions must be
        equal, and base forms must agree. Cross-basis case: the
        transform maps ``src_unit.dimension.vector`` to
        ``dst_unit.dimension.vector``, and base forms must agree.
        """
        if self.basis_transform is None:
            if src_unit.dimension != dst_unit.dimension:
                raise InvalidRename(
                    a, b,
                    f"dimensions differ ({src_unit.dimension!r} vs "
                    f"{dst_unit.dimension!r}); supply basis_transform if "
                    f"systems live in different bases",
                )
        else:
            src_vec = src_unit.dimension.vector
            dst_vec = dst_unit.dimension.vector
            if src_vec.basis != self.basis_transform.source:
                raise InvalidRename(
                    a, b,
                    f"src_unit basis does not match basis_transform.source",
                )
            if dst_vec.basis != self.basis_transform.target:
                raise InvalidRename(
                    a, b,
                    f"dst_unit basis does not match basis_transform.target",
                )
            if self.basis_transform(src_vec) != dst_vec:
                raise InvalidRename(
                    a, b,
                    f"transformed src dimension does not equal dst dimension",
                )
        if src_unit.base_form != dst_unit.base_form:
            raise InvalidRename(
                a, b,
                f"base forms differ ({src_unit.base_form!r} vs "
                f"{dst_unit.base_form!r}); rename is for synonyms, not "
                f"definitional differences",
            )

    def apply(self, n: 'Number') -> 'Number':
        """Move ``n`` from :attr:`src` to :attr:`dst`.

        Order: rename (name layer) → ``basis_transform`` (numeric
        layer; no-op under the synonym constraint) → identity-bind to
        :attr:`dst`'s :class:`Unit` objects. The result is a new
        :class:`Number` whose units reference :attr:`dst`'s registry.

        Raises
        ------
        UnknownUnitError
            If a component-unit name (after rename) is not in
            ``self.dst.units``.
        """
        def _rebind_name(name: str) -> str:
            return self.rename.get(name, name)

        unit = n.unit
        if isinstance(unit, UnitFactor):
            target_name = _rebind_name(unit.unit.name)
            if target_name not in self.dst.units:
                raise UnknownUnitError(target_name)
            rebound = UnitFactor(self.dst.units[target_name], unit.scale)
            return Number(
                quantity=n.quantity, unit=rebound, uncertainty=n.uncertainty
            )
        if isinstance(unit, Unit):
            target_name = _rebind_name(unit.name)
            if target_name not in self.dst.units:
                raise UnknownUnitError(target_name)
            return Number(
                quantity=n.quantity,
                unit=self.dst.units[target_name],
                uncertainty=n.uncertainty,
            )
        if isinstance(unit, UnitProduct):
            rebound_factors: Dict['UnitFactor', float] = {}
            for factor, exponent in unit.factors.items():
                target_name = _rebind_name(factor.unit.name)
                if target_name not in self.dst.units:
                    raise UnknownUnitError(target_name)
                rebound_factor = UnitFactor(
                    self.dst.units[target_name], factor.scale
                )
                rebound_factors[rebound_factor] = exponent
            return Number(
                quantity=n.quantity,
                unit=UnitProduct(rebound_factors),
                uncertainty=n.uncertainty,
            )
        return Number(
            quantity=n.quantity, unit=unit, uncertainty=n.uncertainty
        )

    def inverse(self) -> 'Bridge':
        """Return the reverse bridge ``dst → src``.

        Renames are reversed; ``basis_transform`` is inverted; the
        result is re-validated by :meth:`__post_init__`.
        """
        return Bridge(
            src=self.dst,
            dst=self.src,
            rename={b: a for a, b in self.rename.items()},
            basis_transform=(
                self.basis_transform.inverse()
                if self.basis_transform is not None
                else None
            ),
        )

    def __matmul__(self, other: 'Bridge') -> 'Bridge':
        """Compose ``self @ other``: apply ``other`` first, then ``self``.

        Requires ``other.dst is self.src`` (registry identity). The
        composed rename chains source names through ``other`` to
        ``self``; the composed ``basis_transform`` is
        ``self.basis_transform @ other.basis_transform`` when both are
        present.

        The resulting :class:`Bridge` is re-validated by
        :meth:`__post_init__` so that pairs valid individually but not
        jointly are caught.
        """
        if other.dst is not self.src:
            raise ValueError(
                "Bridge composition requires other.dst is self.src"
            )
        composed_rename: Dict[str, str] = {}
        # Names renamed by other: forward through self.
        for a, b in other.rename.items():
            c = self.rename.get(b, b)
            if c != a:
                composed_rename[a] = c
        # Names identity-passed through other and renamed by self: only
        # meaningful if the name also exists in other.src.
        other_targets = set(other.rename.values())
        for b, c in self.rename.items():
            if b in other_targets:
                continue
            if b in other.src.units and b != c:
                composed_rename[b] = c

        if self.basis_transform is None and other.basis_transform is None:
            composed_transform = None
        elif self.basis_transform is None:
            composed_transform = other.basis_transform
        elif other.basis_transform is None:
            composed_transform = self.basis_transform
        else:
            composed_transform = self.basis_transform @ other.basis_transform

        return Bridge(
            src=other.src,
            dst=self.dst,
            rename=composed_rename,
            basis_transform=composed_transform,
        )


# -----------------------------------------------------------------------------
# Algebra & relation helpers — module-private. Keep at bottom so they sit
# under the public surface and only run when a method calls them.
# -----------------------------------------------------------------------------


def _validate_conflict_policy(policy: ConflictPolicy) -> None:
    if not isinstance(policy, ConflictPolicy):
        raise TypeError(
            f"on_conflict must be a ConflictPolicy member, got {policy!r}"
        )


def _merge_mapping(
    a: Mapping[str, Any],
    b: Mapping[str, Any],
    registry: str,
    on_conflict: ConflictPolicy,
) -> Dict[str, Any]:
    """Combine two name→value mappings under the given conflict policy.

    Used for ``units``, ``dimensions``, ``contexts``, and ``constants``.
    """
    merged: Dict[str, Any] = dict(a)
    for name, value in b.items():
        if name not in merged:
            merged[name] = value
            continue
        existing = merged[name]
        if existing == value:
            continue
        if on_conflict is ConflictPolicy.RAISE:
            raise ExtendConflict(
                registry,
                name,
                f"extend: {registry}[{name!r}] has incompatible definitions",
            )
        if on_conflict is ConflictPolicy.PREFER_OTHER:
            merged[name] = value
        # PREFER_SELF: leave existing in place
    return merged


def _merge_base_units(
    a: BaseUnits, b: BaseUnits, on_conflict: ConflictPolicy
) -> BaseUnits:
    merged: Dict['Dimension', 'Unit'] = dict(a.bases)
    for dim, unit in b.bases.items():
        if dim not in merged:
            merged[dim] = unit
            continue
        existing = merged[dim]
        if existing == unit:
            continue
        if on_conflict is ConflictPolicy.RAISE:
            raise ExtendConflict(
                "base_units",
                dim.name,
                f"extend: base_units[{dim.name!r}] differs between systems",
            )
        if on_conflict is ConflictPolicy.PREFER_OTHER:
            merged[dim] = unit
        # PREFER_SELF: leave existing in place
    # Preserve self.name; the result is a strict superset (modulo policy).
    return BaseUnits(name=a.name, bases=merged)


def _enumerate_unit_edges(
    graph: 'ConversionGraph',
) -> Dict[Tuple[str, str], 'Map']:
    """Flatten a graph's ``_unit_edges`` into a ``(src.name, dst.name) -> Map``
    dict, suitable for set-style comparison.
    """
    edges: Dict[Tuple[str, str], 'Map'] = {}
    for _dim, srcs in graph._unit_edges.items():
        for src, dsts in srcs.items():
            for dst, m in dsts.items():
                edges[(src.name, dst.name)] = m
    return edges


def _merge_conversion_graphs(
    a: 'ConversionGraph',
    b: 'ConversionGraph',
    units: Mapping[str, 'Unit'],
    on_conflict: ConflictPolicy,
) -> 'ConversionGraph':
    """Return a new graph holding the union of edges from ``a`` and ``b``.

    Conflicts on the same ``(src.name, dst.name)`` pair are resolved by
    ``on_conflict``. Units already registered on ``a`` are preserved; any
    unit in ``units`` that isn't yet registered on the copied graph is
    registered via :meth:`Graph.register_unit`.
    """
    new = a.copy()
    a_edges = _enumerate_unit_edges(a)

    for _dim, srcs in b._unit_edges.items():
        for src, dsts in srcs.items():
            for dst, m in dsts.items():
                key = (src.name, dst.name)
                if key in a_edges:
                    if a_edges[key] == m:
                        continue
                    if on_conflict is ConflictPolicy.RAISE:
                        raise ExtendConflict(
                            "conversions",
                            f"{src.name}->{dst.name}",
                            "extend: conversion edges differ between systems",
                        )
                    if on_conflict is ConflictPolicy.PREFER_SELF:
                        continue
                    # PREFER_OTHER: overwrite LHS edge with RHS edge.
                    new.add_edge(src=src, dst=dst, map=m, overwrite=True)
                    continue
                new.add_edge(src=src, dst=dst, map=m)

    # Ensure every chosen unit is registered for name lookup. ``copy``
    # already carried over ``a``'s name registry; pick up b-only units.
    for name, unit_obj in units.items():
        if name not in new._name_registry_cs:
            new.register_unit(unit_obj)

    return new


def _merge_conversion_graphs_bulk(
    base: 'ConversionGraph',
    others: 'list[ConversionGraph]',
    units: Mapping[str, 'Unit'],
    on_conflict: ConflictPolicy,
) -> 'ConversionGraph':
    """Single-copy bulk merge of multiple graphs into ``base``.

    Like :func:`_merge_conversion_graphs` but merges an arbitrary number
    of ``others`` into a single copy of ``base``, avoiding repeated
    deep-copy overhead.
    """
    new = base.copy()  # ONE copy for all merges
    known_edges = _enumerate_unit_edges(base)

    for other in others:
        for _dim, srcs in other._unit_edges.items():
            for src, dsts in srcs.items():
                for dst, m in dsts.items():
                    key = (src.name, dst.name)
                    if key in known_edges:
                        if known_edges[key] == m:
                            continue
                        if on_conflict is ConflictPolicy.RAISE:
                            raise ExtendConflict(
                                "conversions",
                                f"{src.name}->{dst.name}",
                                "extend_many: conversion edges differ between systems",
                            )
                        if on_conflict is ConflictPolicy.PREFER_SELF:
                            continue
                        new.add_edge(src=src, dst=dst, map=m, overwrite=True)
                        known_edges[key] = m
                        continue
                    new.add_edge(src=src, dst=dst, map=m)
                    known_edges[key] = m

    for name, unit_obj in units.items():
        if name not in new._name_registry_cs:
            new.register_unit(unit_obj)

    return new


def _restrict_base_units(
    base_units: BaseUnits,
    kept_dims: Optional[FrozenSet['Dimension']],
    kept_unit_names: FrozenSet[str],
) -> BaseUnits:
    """Return a copy of ``base_units`` with entries pruned to those whose
    dimension survives ``kept_dims`` (if not None) and whose unit name
    survives ``kept_unit_names``.

    If pruning would empty the mapping, a sentinel ``bases`` of size one
    cannot be constructed under the v1.x ``BaseUnits`` invariant; in that
    case the caller has restricted away the whole system. We retain the
    intersection if any survives; otherwise we raise ``ValueError`` via
    ``BaseUnits``'s own constructor.
    """
    pruned: Dict['Dimension', 'Unit'] = {}
    for dim, unit in base_units.bases.items():
        if kept_dims is not None and dim not in kept_dims:
            continue
        if unit.name not in kept_unit_names:
            continue
        pruned[dim] = unit
    if not pruned:
        # Preserve at least one base unit when possible by relaxing the
        # unit-name filter; otherwise let BaseUnits raise.
        for dim, unit in base_units.bases.items():
            if kept_dims is None or dim in kept_dims:
                pruned[dim] = unit
                break
    return BaseUnits(name=base_units.name, bases=pruned)


def _restrict_conversion_graph(
    graph: 'ConversionGraph',
    kept_unit_names: FrozenSet[str],
) -> 'ConversionGraph':
    """Return a copy of ``graph`` pruned to edges whose endpoints are both
    in ``kept_unit_names``. Product edges and rebased entries are dropped
    conservatively when they reference any pruned unit.
    """
    new = graph.copy()

    for dim in list(new._unit_edges.keys()):
        srcs = new._unit_edges[dim]
        for src in list(srcs.keys()):
            if src.name not in kept_unit_names:
                del srcs[src]
                continue
            dsts = srcs[src]
            for dst in list(dsts.keys()):
                if dst.name not in kept_unit_names:
                    del dsts[dst]
            if not dsts:
                del srcs[src]
        if not srcs:
            del new._unit_edges[dim]

    # Product edges: drop pessimistically. Product edges represent
    # composite conversions that are reconstructed by the path-finder on
    # demand; dropping them is correct but may force recomputation.
    new._product_edges.clear()

    # Rebased: keep entries whose base unit survives.
    for base in list(new._rebased.keys()):
        if base.name not in kept_unit_names:
            del new._rebased[base]

    # Name registries.
    new._name_registry = {
        k: v for k, v in new._name_registry.items()
        if v.name in kept_unit_names
    }
    new._name_registry_cs = {
        k: v for k, v in new._name_registry_cs.items()
        if v.name in kept_unit_names
    }

    new._conversion_cache.clear()
    return new


def _mapping_diff(
    a: Mapping[str, Any], b: Mapping[str, Any]
) -> RegistryDiff:
    """``self -> other`` diff for a string-keyed mapping."""
    a_keys = set(a.keys())
    b_keys = set(b.keys())
    return RegistryDiff(
        added=frozenset(b_keys - a_keys),
        removed=frozenset(a_keys - b_keys),
        redefined=frozenset(
            k for k in (a_keys & b_keys) if a[k] != b[k]
        ),
    )


def _base_units_diff(a: BaseUnits, b: BaseUnits) -> RegistryDiff:
    """Diff two :class:`BaseUnits` mappings by dimension name."""
    a_pairs = {dim.name: unit for dim, unit in a.bases.items()}
    b_pairs = {dim.name: unit for dim, unit in b.bases.items()}
    return _mapping_diff(a_pairs, b_pairs)


def _conversion_diff(
    a: 'ConversionGraph', b: 'ConversionGraph'
) -> RegistryDiff:
    """Diff two conversion graphs by ``"src->dst"`` edge labels."""
    a_edges = {f"{s}->{d}": m for (s, d), m in _enumerate_unit_edges(a).items()}
    b_edges = {f"{s}->{d}": m for (s, d), m in _enumerate_unit_edges(b).items()}
    return _mapping_diff(a_edges, b_edges)


__all__ = [
    'ActiveContext',
    'AlgebraCache',
    'BaseUnits',
    'Bridge',
    'ConflictPolicy',
    'ExtendConflict',
    'InvalidRename',
    'RegistryDiff',
    'SystemDiff',
    'UnitSystem',
    'active',
    'active_formulas',
    'active_kinds',
    'active_strict',
    'active_system',
    'use',
]

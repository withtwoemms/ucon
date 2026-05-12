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
  constants) and a per-instance :class:`AlgebraCache`. Phase 2 introduces
  the type and its construction surface; later phases route call sites
  through it.
- :class:`AlgebraCache` -- per-instance cache for ``Dimension`` algebra
  (mul/div/pow). Replaces the module-level caches in ``ucon.dimension`` in
  later phases.
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
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Iterator, Mapping

from ucon.core import DimensionNotCovered, Unit
from ucon.dimension import Dimension

if TYPE_CHECKING:
    from ucon.basis.graph import BasisGraph
    from ucon.basis.types import Basis
    from ucon.constants import Constant
    from ucon.contexts import ConversionContext
    from ucon.graph import ConversionGraph


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


# -----------------------------------------------------------------------------
# Per-instance Dimension algebra cache
# -----------------------------------------------------------------------------


@dataclass
class AlgebraCache:
    """Per-instance cache for ``Dimension`` algebraic operations.

    Holds three sub-caches keyed by argument tuples:

    - ``mul``: ``(Dimension, Dimension) -> Dimension``
    - ``div``: ``(Dimension, Dimension) -> Dimension``
    - ``pow``: ``(Dimension, exponent) -> Dimension``

    In v1.8 Phase 2 this type exists as a per-``UnitSystem`` field. Later
    phases will route ``Dimension.__mul__`` / ``__truediv__`` / ``__pow__``
    through the active system's cache, retiring the module-level caches in
    ``ucon.dimension``.
    """

    mul: dict = field(default_factory=dict)
    div: dict = field(default_factory=dict)
    pow: dict = field(default_factory=dict)

    def clear(self) -> None:
        """Empty all three sub-caches."""
        self.mul.clear()
        self.div.clear()
        self.pow.clear()


#: Module-level fallback used by ``_get_active_cache`` when no
#: ``UnitSystem`` has been activated via :func:`use`. This is the v1.8
#: replacement for the module-level ``_DIM_MUL_CACHE`` / ``_DIM_DIV_CACHE``
#: / ``_DIM_POW_CACHE`` dicts that previously lived in ``ucon.dimension``.
_DEFAULT_ALGEBRA_CACHE: 'AlgebraCache' = AlgebraCache()


def _get_active_cache() -> 'AlgebraCache':
    """Return the algebra cache that ``Dimension`` algebra should use now.

    Routes through the active :class:`UnitSystem`'s per-instance cache when
    one has been set via :func:`use`. Falls back to
    :data:`_DEFAULT_ALGEBRA_CACHE` otherwise.

    The fallback is intentionally a stable module-level object rather than
    a fresh ``UnitSystem.from_globals()`` snapshot: that snapshot would
    construct a new :class:`AlgebraCache` on every call and defeat
    memoization in the default (no ``use(...)``) state.
    """
    system = _active.get()
    if system is None:
        return _DEFAULT_ALGEBRA_CACHE
    return system._algebra_cache


# -----------------------------------------------------------------------------
# UnitSystem value type
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class UnitSystem:
    """A complete unit system as a value type.

    Owns the basis, the registries (units, dimensions, conversion_graph,
    basis_graph, contexts, constants), the canonical ``base_units``
    mapping, and a per-instance :class:`AlgebraCache`.

    In v1.8 Phase 2 the type exists with a construction surface but no
    callers. Later phases route the user-facing entry points
    (``compute``, ``convert``, ``declare_computation``, ...) through it.

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

    @property
    def conversions(self) -> 'ConversionGraph':
        """Deprecated alias for :attr:`conversion_graph`.

        Returns ``self.conversion_graph`` and emits
        ``PendingDeprecationWarning``. The field was renamed in v1.8.1 for
        symmetry with ``basis_graph``; the alias is scheduled for removal
        in v2.0.
        """
        warnings.warn(
            "UnitSystem.conversions is a deprecated alias for "
            "UnitSystem.conversion_graph; it will be removed in ucon v2.0.",
            PendingDeprecationWarning,
            stacklevel=2,
        )
        return self.conversion_graph

    @classmethod
    def from_globals(cls, *, base_units: BaseUnits | None = None) -> 'UnitSystem':
        """Snapshot the current global state into a ``UnitSystem``.

        Reads the live registries from ``ucon._loader``, ``ucon.dimension``,
        ``ucon.basis.graph``, and ``ucon.graph``. The registries are passed
        through *by reference* (not copied) so two snapshots compare equal
        and share state with the legacy global path.

        Parameters
        ----------
        base_units : BaseUnits, optional
            Override for the ``base_units`` field. Defaults to
            ``ucon.units.si``.
        """
        # Deferred imports to avoid a load-time cycle:
        # ucon.system is imported very early via ucon/__init__.py, before
        # ucon.graph / ucon._loader / ucon.units have been initialised.
        from ucon._loader import get_constants, get_units
        from ucon.basis.graph import get_basis_graph, get_default_basis
        from ucon.dimension import _DIMENSION_ATTRS
        from ucon.graph import get_default_graph
        from ucon import units as _units_module

        if base_units is None:
            base_units = _units_module.si

        graph = get_default_graph()
        return cls(
            basis=get_default_basis(),
            units=get_units(),
            dimensions=_DIMENSION_ATTRS,
            base_units=base_units,
            conversion_graph=graph,
            basis_graph=get_basis_graph(),
            contexts=getattr(graph, '_contexts', {}),
            constants=get_constants(),
        )


# -----------------------------------------------------------------------------
# Deprecated kwarg alias: conversions= -> conversion_graph=
#
# The field was named ``conversions`` in v1.8.0 and renamed to
# ``conversion_graph`` in v1.8.1 for symmetry with ``basis_graph``. The
# alias accepts the old kwarg with a ``PendingDeprecationWarning`` and is
# scheduled for removal in v2.0 alongside the matching property shim.
# -----------------------------------------------------------------------------


_unitsystem_dataclass_init = UnitSystem.__init__


def _unitsystem_init_with_conversions_alias(self, *args, **kwargs):
    if 'conversions' in kwargs:
        if 'conversion_graph' in kwargs:
            raise TypeError(
                "UnitSystem() got both 'conversion_graph' and the deprecated "
                "alias 'conversions'; pass only 'conversion_graph'"
            )
        warnings.warn(
            "UnitSystem(conversions=...) is a deprecated alias for "
            "UnitSystem(conversion_graph=...); it will be removed in ucon v2.0.",
            PendingDeprecationWarning,
            stacklevel=2,
        )
        kwargs['conversion_graph'] = kwargs.pop('conversions')
    _unitsystem_dataclass_init(self, *args, **kwargs)


_unitsystem_init_with_conversions_alias.__doc__ = _unitsystem_dataclass_init.__doc__
UnitSystem.__init__ = _unitsystem_init_with_conversions_alias


# -----------------------------------------------------------------------------
# Active-system context variable
# -----------------------------------------------------------------------------


_active: ContextVar['UnitSystem | None'] = ContextVar('ucon_active_system', default=None)


def active() -> UnitSystem:
    """Return the currently active :class:`UnitSystem`.

    If no system has been activated via :func:`use`, snapshots the current
    global state via :meth:`UnitSystem.from_globals` and returns that.
    """
    system = _active.get()
    if system is None:
        return UnitSystem.from_globals()
    return system


@contextmanager
def use(system: UnitSystem) -> Iterator[UnitSystem]:
    """Set ``system`` as the active :class:`UnitSystem` for the with-block.

    On exit the previous active system (or ``None``) is restored.

    Examples
    --------
    >>> sys = UnitSystem.from_globals()
    >>> with use(sys):
    ...     assert active() is sys
    """
    token = _active.set(system)
    try:
        yield system
    finally:
        _active.reset(token)


__all__ = [
    'BaseUnits',
    'UnitSystem',
    'AlgebraCache',
    'use',
    'active'
]

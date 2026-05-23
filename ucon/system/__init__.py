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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Iterator, Mapping

from ucon.system._active import _active
from ucon.system._active import active as _raw_active
from ucon.system.algebra_cache import AlgebraCache, _get_active_cache, _DEFAULT_ALGEBRA_CACHE
from ucon.core.exceptions import DimensionNotCovered

if TYPE_CHECKING:
    from ucon.basis.graph import BasisGraph
    from ucon.basis.types import Basis
    from ucon.core import Unit
    from ucon.dimension import Dimension
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


# AlgebraCache, _get_active_cache, and _DEFAULT_ALGEBRA_CACHE are
# imported from ucon.system.algebra_cache (Layer 1) and re-exported
# here for backward compatibility.


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
            DeprecationWarning,
            stacklevel=2,
        )
        return self.conversion_graph

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
        from ucon.resolver import parse_unit as _parse_unit
        return _parse_unit(name, system=self)

    @classmethod
    def from_globals(cls, *, base_units: BaseUnits | None = None, _internal: bool = False) -> 'UnitSystem':
        """Snapshot the current global state into a ``UnitSystem``.

        .. deprecated:: 1.11
           ``from_globals()`` snapshots module-level registries into a
           ``UnitSystem``. With eager system initialization, the active
           system is always available via :func:`active`. Use
           ``active()`` to obtain the current system. Scheduled for
           removal in ucon 2.0.

        Parameters
        ----------
        base_units : BaseUnits, optional
            Override for the ``base_units`` field. When provided, returns
            a copy of the active system with the given base units.
        """
        if not _internal:
            warnings.warn(
                "UnitSystem.from_globals() is deprecated; use active() to "
                "obtain the current system. Scheduled for removal in ucon v2.0.",
                DeprecationWarning,
                stacklevel=2,
            )
        system = active()
        if base_units is not None:
            # Return a copy with overridden base_units (frozen dataclass)
            from dataclasses import replace as _replace
            return _replace(system, base_units=base_units)
        return system


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
            DeprecationWarning,
            stacklevel=2,
        )
        kwargs['conversion_graph'] = kwargs.pop('conversions')
    _unitsystem_dataclass_init(self, *args, **kwargs)


_unitsystem_init_with_conversions_alias.__doc__ = _unitsystem_dataclass_init.__doc__
UnitSystem.__init__ = _unitsystem_init_with_conversions_alias


# _active is imported from ucon.system._active (Layer 1) and re-exported
# here for backward compatibility.


def active() -> UnitSystem:
    """Return the currently active :class:`UnitSystem`.

    After ``import ucon``, the active system is always set via eager
    initialization. The fallback branch below handles the edge case
    where ``ucon.system`` is imported directly without ``ucon``.
    """
    system = _active.get()
    if system is not None:
        return system
    # Fallback: construct from global registries (deferred imports to
    # avoid a load-time cycle — ucon.system is imported before the
    # high-level modules are initialised).
    from ucon.basis.graph import get_basis_graph, get_default_basis
    from ucon.dimension import _DIMENSION_ATTRS
    from ucon.graph import get_default_graph
    from ucon import units as _units_module

    graph = get_default_graph()
    # Build constants dict from the graph's package_constants
    _constants: dict = {}
    for _const in graph._package_constants:
        _constants[_const.symbol] = _const
        _safe = _const.name.replace(" ", "_").replace("-", "_").lower()
        _constants[_safe] = _const
        for _alias in getattr(_const, 'aliases', ()):
            _constants[_alias] = _const

    system = UnitSystem(
        basis=get_default_basis(),
        units=_units_module._units,
        dimensions=_DIMENSION_ATTRS,
        base_units=_units_module.si,
        conversion_graph=graph,
        basis_graph=get_basis_graph(),
        contexts=getattr(graph, '_contexts', {}),
        constants=_constants,
    )
    _active.set(system)
    return system


@contextmanager
def use(system: UnitSystem) -> Iterator[UnitSystem]:
    """Set ``system`` as the active :class:`UnitSystem` for the with-block.

    On exit the previous active system (or ``None``) is restored.

    Examples
    --------
    >>> sys = active()
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

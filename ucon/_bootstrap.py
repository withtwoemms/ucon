# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon._bootstrap
===============

Construct the default :class:`~ucon.system.UnitSystem` and seed the
active :class:`~ucon.system.ActiveContext`.

This is the v2.0 mega-bootstrap site: a single place that wires together
the standard catalog from the imported modules, then sets the active
context via :data:`ucon._active._active`. The top-level
``ucon/__init__.py`` calls :func:`install_default_active_context` exactly
once, during top-level import, after every module that defines a leaf of
the standard catalog has been loaded.

The bootstrap reads only immutable builder outputs:

* :data:`ucon.dimension._STANDARD_ATTRS` -- name -> Dimension map for
  every standard dimension (powers ``Dimension.length`` style attribute
  access via :class:`ucon.dimension._DimensionMeta`).
* :data:`ucon.dimension._STANDARD_REGISTRY` -- Vector -> Dimension map
  for resolution by exponent vector (powers :func:`ucon.dimension.resolve`).

These two dicts replace the v1.x mutable module-level globals
``_DIMENSION_ATTRS`` and ``_REGISTRY``.
"""

from __future__ import annotations

from ucon import constants, units
from ucon._active import _active as _active_var
from ucon.basis.builtin import SI
from ucon.basis.graph import _build_standard_basis_graph
from ucon.dimension import _STANDARD_ATTRS, _STANDARD_REGISTRY
from ucon.formulas import FormulaRegistry
from ucon.kinds import KindLattice
from ucon.system import ActiveContext, UnitSystem


def build_default_system() -> UnitSystem:
    """Build the default :class:`UnitSystem` for ucon's standard catalog.

    Returns
    -------
    UnitSystem
        Frozen value type owning the standard SI catalog: units,
        dimensions, conversion graph, basis graph, contexts, and the
        package-registered constants. The active context is *not* set
        here; use :func:`install_default_active_context` to do that
        atomically together with the formulas / kinds bundles.
    """
    graph = units._graph
    standard_constants = constants._build_symbol_lookup(graph._package_constants)
    return UnitSystem(
        basis=SI,
        units=units._units,
        dimensions=_STANDARD_ATTRS,
        dimensions_by_vector=_STANDARD_REGISTRY,
        base_units=units.si,
        conversion_graph=graph,
        basis_graph=_build_standard_basis_graph(),
        contexts=getattr(graph, '_contexts', {}),
        constants=standard_constants,
    )


def install_default_active_context() -> None:
    """Build the default system and install it as the active context.

    Called once from :mod:`ucon`'s top-level import after every standard
    catalog module has been loaded. Also re-populates the
    :mod:`ucon.constants` lookup cache so module-level attribute access
    on ``ucon.constants`` continues to work.
    """
    system = build_default_system()
    graph = system.conversion_graph
    kinds = getattr(graph, '_kind_lattice', None) or KindLattice()
    _active_var.set(ActiveContext(
        system=system,
        formulas=FormulaRegistry(),
        kinds=kinds,
        strict=True,
    ))
    constants._populate_cache(graph._package_constants)

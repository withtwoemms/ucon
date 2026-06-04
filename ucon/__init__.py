# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

# Enable namespace package support for ucon-tools coexistence
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)

"""
ucon
====

*ucon* (Unit Conversion & Dimensional Analysis) is a lightweight,
introspective library for reasoning about physical quantities.

Unlike conventional unit libraries that focus purely on arithmetic convenience,
*ucon* models the **semantics** of measurement-—exposing the algebra of
dimensions and the structure of compound units.

Overview
--------
*ucon* is organized into a small set of composable modules:

- :mod:`ucon.dimension` — defines the algebra of physical dimensions using
  exponent vectors. Provides the foundation for all dimensional reasoning.
- :mod:`ucon.unit` — defines the :class:`Unit` abstraction, representing a
  measurable quantity with an associated dimension, factor, and offset.
- :mod:`ucon.core` — implements numeric handling via :class:`Number`,
  :class:`Scale`, and :class:`Ratio`, along with unified conversion logic.
- :mod:`ucon.units` — declares canonical SI base and derived units for immediate use.

Design Philosophy
-----------------
*ucon* treats unit conversion not as a lookup problem but as an **algebra**:

- **Dimensional Algebra** — all physical quantities are represented as
  exponent vectors over the seven SI bases, ensuring strict composability.
- **Explicit Semantics** — units, dimensions, and scales are first-class
  objects, not strings or tokens.
- **Unified Conversion Model** — all conversions are expressed through one
  data-driven framework that is generalizable to arbitrary unit systems.
"""
from ucon import constants, units
from ucon.constants import Constant
from ucon.core import Exponent
from ucon.basis import (
    Basis,
    BasisComponent,
    BasisGraph,
    BasisTransform,
    ConstantBoundBasisTransform,
    ConstantBinding,
    LossyProjection,
    NoTransformPath,
    Vector as BasisVector,
    get_default_basis,
    get_basis_graph,
    using_basis,
    using_basis_graph,
)
from ucon.basis.builtin import (
    CGS,
    CGS_ESU,
    NATURAL,
    SI,
)
from ucon.basis.transforms import (
    CGS_TO_SI,
    NATURAL_TO_SI,
    SI_TO_CGS,
    SI_TO_CGS_ESU,
    SI_TO_NATURAL,
)
from ucon.core import (
    BaseForm,
    DimensionConstraint,
    DimensionNotCovered,
    KindConstraint,
    KindDimensionMismatch,
    KindMismatch,
    NonScalableError,
    Number,
    Ratio,
    RebasedUnit,
    Scale,
    Unit,
    UnitDefinitionMismatch,
    UnitFactor,
    UnitProduct,
    UnknownUnitError,
)
from ucon.system import (
    ActiveContext,
    BaseUnits,
    Bridge,
    ConflictPolicy,
    ExtendConflict,
    InvalidRename,
    RegistryDiff,
    SystemDiff,
    UnitSystem,
    active,
    active_formulas,
    active_kinds,
    active_strict,
    active_system,
    use,
)
from ucon.formulas import FormulaRegistry
from ucon.kinds import Kind, KindLattice
from ucon.dimension import (
    Dimension,
    all_dimensions,
    resolve as resolve_dimension,
)
from ucon.checking import enforce_dimensions
from ucon.conversion import (
    Graph,
    ConversionGraph,
    ConversionNotFound,
    CyclicInconsistency,
    DimensionMismatch,
    get_default_graph,
    using_conversion_graph,
)
from ucon.contexts import (
    ContextEdge,
    ConversionContext,
    boltzmann,
    spectroscopy,
    using_context,
)
from ucon.packages import ConstantDef, EdgeDef, PackageLoadError, UnitDef, UnitPackage, load_package
from ucon.resolver import parse_unit, register_unit
from ucon.parsing import ParseError, parse, parse_dimension


# ---------------------------------------------------------------------------
# Eager system initialization
# ---------------------------------------------------------------------------
# Set the active UnitSystem at import time so the active-system tier in
# get_default_graph() is always hit.  This makes _default_graph dead code
# and routes all conversions through the UnitSystem authority.
#
# All required modules are already imported above, so we construct the
# UnitSystem directly — no need for from_globals() or deferred imports.
from ucon.dimension import _DIMENSION_ATTRS
from ucon._active import _active as _sys_active_var
_init_graph = units._graph  # Direct reference; get_default_graph() isn't usable yet

# Symbol/name/alias lookup used by ``UnitSystem.constants``; descriptive
# lookup feeds ``ucon.constants`` module-level attribute access. Both
# builders live in ``ucon.constants`` so no cross-module attribute
# assignment is required here.
_init_constants = constants._build_symbol_lookup(_init_graph._package_constants)

_init_system = UnitSystem(
    basis=get_default_basis(),
    units=units._units,
    dimensions=_DIMENSION_ATTRS,
    base_units=units.si,
    conversion_graph=_init_graph,
    basis_graph=get_basis_graph(),
    contexts=getattr(_init_graph, '_contexts', {}),
    constants=_init_constants,
)
_init_kinds = getattr(_init_graph, '_kind_lattice', None) or KindLattice()
_sys_active_var.set(ActiveContext(
    system=_init_system,
    formulas=FormulaRegistry(),
    kinds=_init_kinds,
    strict=True,
))
constants._populate_cache(_init_graph._package_constants)

del _sys_active_var, _init_graph, _init_constants, _init_system, _init_kinds

__all__ = [
    # Basis abstractions
    'Basis',
    'BasisComponent',
    'BasisGraph',
    'BasisTransform',
    'BasisVector',
    'ConstantBoundBasisTransform',
    'ConstantBinding',
    'LossyProjection',
    'NoTransformPath',
    # Basis context scoping
    'get_default_basis',
    'get_basis_graph',
    'using_basis',
    'using_basis_graph',
    # Standard bases
    'CGS',
    'CGS_ESU',
    'NATURAL',
    'SI',
    # Standard transforms
    'CGS_TO_SI',
    'NATURAL_TO_SI',
    'SI_TO_CGS',
    'SI_TO_CGS_ESU',
    'SI_TO_NATURAL',
    # Contexts
    'ContextEdge',
    'ConversionContext',
    'boltzmann',
    'spectroscopy',
    'using_context',
    # Core types
    'ActiveContext',
    'BaseForm',
    'BaseUnits',
    'Bridge',
    'ConflictPolicy',
    'ExtendConflict',
    'FormulaRegistry',
    'InvalidRename',
    'Kind',
    'KindLattice',
    'RegistryDiff',
    'SystemDiff',
    'UnitSystem',
    'Constant',
    'ConstantDef',
    'ConversionGraph',
    'Graph',
    'ConversionNotFound',
    'CyclicInconsistency',
    'DimensionConstraint',
    'Dimension',
    'DimensionMismatch',
    'DimensionNotCovered',
    'EdgeDef',
    'Exponent',
    'KindConstraint',
    'KindDimensionMismatch',
    'KindMismatch',
    'NonScalableError',
    'Number',
    'PackageLoadError',
    'ParseError',
    'Ratio',
    'RebasedUnit',
    'Scale',
    'Unit',
    'UnitDef',
    'UnitDefinitionMismatch',
    'UnitFactor',
    'UnitPackage',
    'UnitProduct',
    'UnknownUnitError',
    # System
    'active',
    'active_formulas',
    'active_kinds',
    'active_strict',
    'active_system',
    'use',
    # Functions
    'all_dimensions',
    'enforce_dimensions',
    'get_default_graph',
    'register_unit',
    'load_package',
    'parse',
    'parse_dimension',
    'parse_unit',
    'resolve_dimension',
    'using_conversion_graph',
    # Submodules
    'constants',
    'units',
]


# ---------------------------------------------------------------------------
# Note on UnitSystem naming
# ---------------------------------------------------------------------------
#
# Prior to v2.0 ``ucon.UnitSystem`` was a deprecated alias for the simpler
# ``BaseUnits`` mapping. In v2.0 ``UnitSystem`` is the real system type
# imported directly from ``ucon.system``. The ``BaseUnits`` class remains
# available under its own name for the dimension→unit mapping role.

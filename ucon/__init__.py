# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

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
from ucon import units
from ucon.core import Exponent
from ucon.basis import (
    Basis,
    BasisComponent,
    BasisGraph,
    BasisTransform,
    LossyProjection,
    NoTransformPath,
    Vector as BasisVector,
    get_default_basis,
    get_basis_graph,
    set_default_basis_graph,
    reset_default_basis_graph,
    using_basis,
    using_basis_graph,
)
from ucon.bases import (
    CGS,
    CGS_ESU,
    CGS_TO_SI,
    SI,
    SI_TO_CGS,
    SI_TO_CGS_ESU,
)
from ucon.core import (
    DimConstraint,
    DimensionNotCovered,
    RebasedUnit,
    Scale,
    Unit,
    UnitFactor,
    UnitProduct,
    UnitSystem,
    Number,
    Ratio,
)
from ucon.dimension import (
    Dimension,
    all_dimensions,
    resolve as resolve_dimension,
)
from ucon.checking import enforce_dimensions
from ucon.graph import get_default_graph, get_parsing_graph, set_default_graph, using_graph
from ucon.packages import EdgeDef, PackageLoadError, UnitDef, UnitPackage, load_package
from ucon.units import UnknownUnitError, get_unit_by_name


__all__ = [
    # Basis abstractions
    'Basis',
    'BasisComponent',
    'BasisGraph',
    'BasisTransform',
    'BasisVector',
    'LossyProjection',
    'NoTransformPath',
    # Basis context scoping
    'get_default_basis',
    'get_basis_graph',
    'set_default_basis_graph',
    'reset_default_basis_graph',
    'using_basis',
    'using_basis_graph',
    # Standard bases
    'CGS',
    'CGS_ESU',
    'SI',
    # Standard transforms
    'CGS_TO_SI',
    'SI_TO_CGS',
    'SI_TO_CGS_ESU',
    # Core types
    'DimConstraint',
    'Dimension',
    'DimensionNotCovered',
    'EdgeDef',
    'Exponent',
    'Number',
    'PackageLoadError',
    'Ratio',
    'RebasedUnit',
    'Scale',
    'Unit',
    'UnitDef',
    'UnitFactor',
    'UnitPackage',
    'UnitProduct',
    'UnitSystem',
    'UnknownUnitError',
    # Functions
    'all_dimensions',
    'enforce_dimensions',
    'get_default_graph',
    'get_parsing_graph',
    'get_unit_by_name',
    'load_package',
    'resolve_dimension',
    'set_default_graph',
    'using_graph',
    # Submodules
    'units',
]

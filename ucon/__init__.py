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
from ucon.algebra import Exponent
from ucon.basis import (
    Basis,
    BasisComponent,
    BasisGraph,
    BasisTransform as NewBasisTransform,
    LossyProjection,
    NoTransformPath,
    Vector as BasisVector,
)
from ucon.bases import (
    CGS,
    CGS_ESU,
    CGS_TO_SI,
    SI,
    SI_TO_CGS,
    SI_TO_CGS_ESU,
)
# Note: ucon.basis.BasisTransform not exported here to avoid collision with
# ucon.core.BasisTransform. Import from ucon.basis directly for new API.
# This will be resolved in v0.9.0 when the old BasisTransform is removed.
from ucon.core import (
    BasisTransform,
    DimConstraint,
    Dimension,
    DimensionNotCovered,
    NonInvertibleTransform,
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
    all_dimensions,
    resolve as resolve_dimension,
    # Base dimensions
    NONE,
    TIME,
    LENGTH,
    MASS,
    CURRENT,
    TEMPERATURE,
    LUMINOUS_INTENSITY,
    AMOUNT_OF_SUBSTANCE,
    INFORMATION,
    # Pseudo-dimensions
    ANGLE,
    SOLID_ANGLE,
    RATIO,
    COUNT,
    # Common derived dimensions
    VELOCITY,
    ACCELERATION,
    FORCE,
    ENERGY,
    POWER,
    AREA,
    VOLUME,
    DENSITY,
    PRESSURE,
    FREQUENCY,
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
    'NewBasisTransform',
    'NoTransformPath',
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
    'NonInvertibleTransform',
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
    # Dimension constants
    'NONE',
    'TIME',
    'LENGTH',
    'MASS',
    'CURRENT',
    'TEMPERATURE',
    'LUMINOUS_INTENSITY',
    'AMOUNT_OF_SUBSTANCE',
    'INFORMATION',
    'ANGLE',
    'SOLID_ANGLE',
    'RATIO',
    'COUNT',
    'VELOCITY',
    'ACCELERATION',
    'FORCE',
    'ENERGY',
    'POWER',
    'AREA',
    'VOLUME',
    'DENSITY',
    'PRESSURE',
    'FREQUENCY',
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

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
    set_default_basis_graph,
    reset_default_basis_graph,
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
    DimensionNotCovered,
    RebasedUnit,
    Scale,
    Unit,
    UnitFactor,
    UnitProduct,
    UnitSystem,
    UnknownUnitError,
)
from ucon.quantity import (
    DimensionConstraint,
    Number,
    Ratio,
)
from ucon.dimension import (
    Dimension,
    all_dimensions,
    resolve as resolve_dimension,
)
from ucon.checking import enforce_dimensions
from ucon.graph import (
    ConversionGraph,
    ConversionNotFound,
    DimensionMismatch,
    get_default_graph,
    reset_default_graph,
    set_default_graph,
    using_graph,
)
from ucon.contexts import (
    ContextEdge,
    ConversionContext,
    using_context,
)
from ucon.packages import EdgeDef, PackageLoadError, UnitDef, UnitPackage, load_package
from ucon.units import get_unit_by_name
from ucon.parsing import ParseError, parse


# =============================================================================
# Wire dependency-injection hooks (eliminates all circular imports)
# =============================================================================

import ucon.core as _core
import ucon.quantity as _quantity
import ucon.graph as _graph
import ucon.parsing as _parsing
import ucon.packages as _packages
import ucon.constants as _constants

# core: Unit/UnitProduct.__call__ → Number and NumberArray
_core._number_factory = lambda q, u, unc: Number(quantity=q, unit=u, uncertainty=unc)
try:
    from ucon.integrations.numpy import NumberArray as _NumberArray
    _core._array_factory = lambda q, u, unc: _NumberArray(quantities=q, unit=u, uncertainty=unc)
except ImportError:
    pass

# quantity: Number.to() string resolution
_quantity._get_unit_by_name = get_unit_by_name

# graph: standard graph builder + unit name resolution
_graph._build_standard_units = _graph._build_standard_edges
_graph._resolve_unit_by_name = get_unit_by_name

# parsing: unit name resolution
_parsing._resolve_unit = get_unit_by_name

# packages: unit name resolution + graph context manager
_packages._resolve_unit_by_name = get_unit_by_name
_packages._using_graph = using_graph

# constants: units module access
_constants._get_units_module = lambda: units


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
    'set_default_basis_graph',
    'reset_default_basis_graph',
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
    'using_context',
    # Core types
    'Constant',
    'ConversionGraph',
    'ConversionNotFound',
    'DimensionConstraint',
    'Dimension',
    'DimensionMismatch',
    'DimensionNotCovered',
    'EdgeDef',
    'Exponent',
    'Number',
    'PackageLoadError',
    'ParseError',
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
    'get_unit_by_name',
    'load_package',
    'parse',
    'reset_default_graph',
    'resolve_dimension',
    'set_default_graph',
    'using_graph',
    # Submodules
    'constants',
    'units',
]

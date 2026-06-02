# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.core
=========

Core types for the ucon unit system.

This package re-exports all public symbols from its submodules for
backward compatibility. ``from ucon.core import Unit`` continues to work.
"""
from ucon.core._parsing_graph import _get_parsing_graph, _parsing_graph
from ucon.core.exceptions import (
    DimensionNotCovered,
    KindDimensionMismatch,
    KindMismatch,
    NonScalableError,
    UnitDefinitionMismatch,
    UnknownUnitError,
)
from ucon.core._types import (
    BaseForm,
    DimensionConstraint,
    Exponent,
    KindConstraint,
    Number,
    NumberArray,
    Ratio,
    RebasedUnit,
    Scale,
    Unit,
    UnitFactor,
    UnitProduct,
    _Quantifiable,
    _ScaleDescriptor,
)

# Re-export Dimension for backward compatibility — several modules do
# ``from ucon.core import Dimension``.
from ucon.dimension import Dimension, NONE  # noqa: F401

__all__ = [
    'BaseForm',
    'Dimension',
    'DimensionConstraint',
    'DimensionNotCovered',
    'Exponent',
    'KindConstraint',
    'KindDimensionMismatch',
    'KindMismatch',
    'NonScalableError',
    'Number',
    'NumberArray',
    'Ratio',
    'RebasedUnit',
    'Scale',
    'Unit',
    'UnitDefinitionMismatch',
    'UnitFactor',
    'UnitProduct',
    'UnknownUnitError',
    '_ScaleDescriptor',
    '_get_parsing_graph',
    '_parsing_graph',
    '_Quantifiable',
]

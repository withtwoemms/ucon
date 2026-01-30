# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.conversion
===============

Unit conversion engine for *ucon*.

Classes
-------
- :class:`Map` — Abstract base for conversion morphisms.
- :class:`LinearMap` — Linear conversion: y = a * x
- :class:`AffineMap` — Affine conversion: y = a * x + b
- :class:`ComposedMap` — Generic composition fallback.
- :class:`ConversionGraph` — Registry and composer of conversion Maps.

Exceptions
----------
- :class:`DimensionMismatch` — Incompatible dimensions.
- :class:`ConversionNotFound` — No conversion path exists.
- :class:`CyclicInconsistency` — Inconsistent cycle detected.
"""
from ucon.conversion.map import Map, LinearMap, AffineMap, ComposedMap
from ucon.conversion.graph import (
    ConversionGraph,
    DimensionMismatch,
    ConversionNotFound,
    CyclicInconsistency,
)

__all__ = [
    'Map',
    'LinearMap',
    'AffineMap',
    'ComposedMap',
    'ConversionGraph',
    'DimensionMismatch',
    'ConversionNotFound',
    'CyclicInconsistency',
]

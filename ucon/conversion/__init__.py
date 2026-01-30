# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.conversion
===============

Unit conversion engine for *ucon*.

This module re-exports from :mod:`ucon.maps` and :mod:`ucon.graph`
for backward compatibility.

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

Functions
---------
- :func:`get_default_graph` — Get the current default graph.
- :func:`set_default_graph` — Replace the default graph.
- :func:`reset_default_graph` — Reset to standard graph on next access.
- :func:`using_graph` — Context manager for scoped graph override.
"""
from ucon.maps import Map, LinearMap, AffineMap, ComposedMap
from ucon.graph import (
    ConversionGraph,
    DimensionMismatch,
    ConversionNotFound,
    CyclicInconsistency,
    get_default_graph,
    set_default_graph,
    reset_default_graph,
    using_graph,
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
    'get_default_graph',
    'set_default_graph',
    'reset_default_graph',
    'using_graph',
]

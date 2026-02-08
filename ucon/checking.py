# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.checking
=============

Runtime dimensional validation for functions accepting Number arguments.

Provides the @enforce_dimensions decorator, which validates Number arguments
against their Number[Dimension.X] annotations at call time.
"""
from __future__ import annotations

import functools
import inspect
import sys
from typing import get_type_hints, get_args, get_origin

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

from ucon.core import Dimension, Number, Unit, UnitProduct, DimConstraint


def _get_dimension(n: Number) -> Dimension:
    """Extract the Dimension from a Number's unit."""
    unit = n.unit
    if isinstance(unit, (UnitProduct, Unit)):
        return unit.dimension
    raise TypeError(f"Cannot extract dimension from {type(unit).__name__}")


def enforce_dimensions(fn):
    """Validate Number arguments against their Number[Dimension] annotations.

    Only parameters annotated as Number[Dimension.X] are checked.
    Plain Number parameters and non-Number parameters are ignored.

    Checks are precomputed at decoration time. Per-call overhead is
    one dict lookup and one dimension comparison per constrained parameter.

    Parameters
    ----------
    fn : callable
        The function to wrap.

    Returns
    -------
    callable
        Wrapped function with dimensional validation on entry.

    Raises
    ------
    TypeError
        If a constrained argument is not a Number instance.
    ValueError
        If a Number's dimension does not match the annotated constraint.

    Example
    -------
    >>> @enforce_dimensions
    ... def speed(distance: Number[Dimension.length], time: Number[Dimension.time]) -> Number:
    ...     return distance / time
    """
    hints = get_type_hints(fn, include_extras=True)
    sig = inspect.signature(fn)

    # Precompute: which params have DimConstraint annotations?
    checks: dict[str, DimConstraint] = {}
    for name, hint in hints.items():
        if name == "return":
            continue
        if get_origin(hint) is not Annotated:
            continue
        for metadata in get_args(hint)[1:]:
            if isinstance(metadata, DimConstraint):
                checks[name] = metadata
                break

    # Fast path: no constrained params → return unwrapped
    if not checks:
        return fn

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()

        for name, constraint in checks.items():
            value = bound.arguments.get(name)
            if value is None:
                continue
            if not isinstance(value, Number):
                raise TypeError(
                    f"{name}: expected Number, got {type(value).__name__}"
                )
            actual = _get_dimension(value)
            if actual != constraint.dimension:
                raise ValueError(
                    f"{name}: expected dimension '{constraint.dimension.name}', "
                    f"got '{actual.name}'"
                )

        return fn(*args, **kwargs)

    return wrapper


__all__ = ['enforce_dimensions']

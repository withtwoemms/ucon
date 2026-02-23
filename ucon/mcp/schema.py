# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Schema introspection utilities for MCP tools.

Extracts dimension constraints from @enforce_dimensions decorated functions
to expose in MCP tool schemas.
"""

from typing import Callable, get_type_hints, get_origin, get_args, Annotated

from ucon.core import DimConstraint


def extract_dimension_constraints(fn: Callable) -> dict[str, str | None]:
    """Extract dimension constraints from a function's type annotations.

    Inspects parameters annotated with Number[Dimension.X] syntax and returns
    a mapping of parameter name to dimension name.

    Parameters
    ----------
    fn : Callable
        A function, typically decorated with @enforce_dimensions.

    Returns
    -------
    dict[str, str | None]
        Mapping of parameter name to dimension name (or None if unconstrained).

    Examples
    --------
    >>> from ucon import Number, Dimension, enforce_dimensions
    >>> @enforce_dimensions
    ... def speed(distance: Number[Dimension.length], time: Number[Dimension.time]) -> Number:
    ...     return distance / time
    >>> extract_dimension_constraints(speed)
    {'distance': 'length', 'time': 'time'}
    """
    # Handle wrapped functions (from @enforce_dimensions or @functools.wraps)
    target = getattr(fn, '__wrapped__', fn)

    try:
        hints = get_type_hints(target, include_extras=True)
    except Exception:
        # If we can't get hints (e.g., forward refs), return empty
        return {}

    constraints: dict[str, str | None] = {}

    for name, hint in hints.items():
        if name == "return":
            continue

        # Check if this is an Annotated type with DimConstraint
        if get_origin(hint) is Annotated:
            args = get_args(hint)
            for metadata in args[1:]:
                if isinstance(metadata, DimConstraint):
                    constraints[name] = metadata.dimension.name
                    break
            else:
                # Annotated but no DimConstraint found
                constraints[name] = None
        else:
            # Not annotated with dimension constraint
            constraints[name] = None

    return constraints


__all__ = ['extract_dimension_constraints']

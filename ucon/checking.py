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

if sys.version_info >= (3, 9):
    from typing import Annotated, get_type_hints, get_args, get_origin
else:
    # Python 3.7 and 3.8: use typing_extensions for all Annotated-related utilities
    # to ensure get_origin() correctly identifies typing_extensions.Annotated
    from typing_extensions import Annotated, get_type_hints, get_args, get_origin

from ucon.basis import NoTransformPath
from ucon.basis.builtin import SI
from ucon.basis.graph import get_basis_graph
from ucon.core import Dimension, Unit, UnitProduct
from ucon.core import Number, DimensionConstraint


def _get_dimension(n: Number) -> Dimension:
    """Extract the Dimension from a Number's unit."""
    unit = n.unit
    if isinstance(unit, (UnitProduct, Unit)):
        return unit.dimension
    raise TypeError(f"Cannot extract dimension from {type(unit).__name__}")


def _dimensions_compatible(actual: Dimension, expected: Dimension) -> bool:
    """Check dimensional compatibility across bases.

    Two dimensions are compatible if they resolve to the same SI vector.
    This allows e.g. CGS ``cgs_dynamic_viscosity`` to satisfy an
    ``enforce_dimensions`` constraint expecting SI ``dynamic_viscosity``.
    """
    if actual == expected:
        return True

    # Different bases — normalize both to SI and compare
    if actual.vector.basis == expected.vector.basis:
        return False  # same basis, already failed __eq__

    bg = get_basis_graph()
    try:
        if actual.vector.basis != SI:
            actual = actual.in_basis(bg.get_transform(actual.vector.basis, SI))
        if expected.vector.basis != SI:
            expected = expected.in_basis(bg.get_transform(expected.vector.basis, SI))
    except (ValueError, KeyError, NoTransformPath):
        return False  # no transform path → not compatible

    return actual == expected


def _coerce_to_si(value: Number) -> Number:
    """Rewrite a cross-basis Number into SI base units.

    Strategy:
    1. If the unit has a ``base_form`` with SI factors, decompose algebraically
       (no graph required).
    2. Otherwise, fall back to ``Number.to()`` via the default conversion graph
       to find an SI equivalent.

    Returns *value* unchanged when coercion is not possible.
    """
    unit = value.unit

    # --- algebraic path (base_form available) ---
    if isinstance(unit, UnitProduct):
        result = _coerce_product_to_si(value)
        if result is not value:
            return result
    elif isinstance(unit, Unit) and unit.base_form is not None:
        bf = unit.base_form
        # Verify factors are SI-basis before using them
        if all(u.dimension.vector.basis == SI for u, _ in bf.factors):
            si_unit = UnitProduct({u: e for u, e in bf.factors})
            si_qty = value.quantity * bf.prefactor
            si_unc = value.uncertainty * bf.prefactor if value.uncertainty else None
            return Number(si_qty, si_unit, uncertainty=si_unc)

    # --- graph path (CGS units without SI base_form) ---
    return _coerce_via_graph(value)


def _coerce_product_to_si(value: Number) -> Number:
    """Coerce a cross-basis UnitProduct to SI base units algebraically."""
    combined_prefactor = 1.0
    si_factors: dict[Unit, float] = {}
    for uf, exp in value.unit.factors.items():
        unit = uf.unit
        bf = unit.base_form
        if bf is None:
            return value  # can't coerce algebraically
        if not all(u.dimension.vector.basis == SI for u, _ in bf.factors):
            return value  # factors aren't SI
        combined_prefactor *= bf.prefactor ** exp
        for base_unit, base_exp in bf.factors:
            si_factors[base_unit] = si_factors.get(base_unit, 0.0) + base_exp * exp
    si_unit = UnitProduct(si_factors)
    si_qty = value.quantity * combined_prefactor
    si_unc = value.uncertainty * abs(combined_prefactor) if value.uncertainty else None
    return Number(si_qty, si_unit, uncertainty=si_unc)


def _coerce_via_graph(value: Number) -> Number:
    """Coerce a cross-basis Number to SI using the conversion graph.

    Finds an SI-basis unit with the matching dimension and converts to it.
    Returns *value* unchanged if no SI target is found.
    """
    from ucon.graph import get_default_graph, ConversionNotFound

    graph = get_default_graph()
    unit = value.unit

    # Determine the SI dimension by transforming through the basis graph
    actual_dim = unit.dimension if isinstance(unit, Unit) else unit.dimension
    bg = get_basis_graph()
    try:
        if actual_dim.vector.basis != SI:
            si_dim = actual_dim.in_basis(bg.get_transform(actual_dim.vector.basis, SI))
        else:
            return value  # already SI
    except (ValueError, KeyError, NoTransformPath):
        return value

    # Find the coherent SI unit for this dimension (prefactor == 1.0)
    from ucon.core import RebasedUnit
    dim_edges = graph._unit_edges.get(si_dim, {})
    target = None
    for candidate in dim_edges:
        if (isinstance(candidate, Unit)
                and not isinstance(candidate, RebasedUnit)
                and candidate.dimension == si_dim):
            bf = candidate.base_form
            if bf is not None and bf.prefactor == 1.0:
                target = candidate
                break
    # Fallback: any non-rebased SI unit with matching dimension
    if target is None:
        for candidate in dim_edges:
            if (isinstance(candidate, Unit)
                    and not isinstance(candidate, RebasedUnit)
                    and candidate.dimension == si_dim):
                target = candidate
                break

    if target is None:
        return value

    try:
        conversion = graph.convert(src=unit, dst=target)
    except (ConversionNotFound, Exception):
        return value

    si_qty = conversion(value.quantity)
    si_unc = None
    if value.uncertainty is not None:
        si_unc = abs(value.uncertainty * conversion.a) if hasattr(conversion, 'a') else None
    return Number(si_qty, target, uncertainty=si_unc)


def enforce_dimensions(fn):
    """Validate and coerce Number arguments against their Number[Dimension] annotations.

    Only parameters annotated as Number[Dimension.X] are checked.
    Plain Number parameters and non-Number parameters are ignored.

    Cross-basis inputs (e.g. CGS dyne for an SI force constraint) are
    automatically coerced to their SI equivalents so that arithmetic
    inside the function body does not raise on mixed bases.

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

    # Precompute: which params have DimensionConstraint annotations?
    checks: dict[str, DimensionConstraint] = {}
    for name, hint in hints.items():
        if name == "return":
            continue
        if get_origin(hint) is not Annotated:
            continue
        for metadata in get_args(hint)[1:]:
            if isinstance(metadata, DimensionConstraint):
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
            if not _dimensions_compatible(actual, constraint.dimension):
                raise ValueError(
                    f"{name}: expected dimension '{constraint.dimension.name}', "
                    f"got '{actual.name}'"
                )

        # Coerce cross-basis arguments to SI base units so that
        # arithmetic inside the function body does not raise.
        needs_coercion = False
        for name, constraint in checks.items():
            value = bound.arguments.get(name)
            if value is None or not isinstance(value, Number):
                continue
            actual_basis = _get_dimension(value).vector.basis
            if actual_basis != constraint.dimension.vector.basis:
                bound.arguments[name] = _coerce_to_si(value)
                needs_coercion = True

        if needs_coercion:
            return fn(*bound.args, **bound.kwargs)
        return fn(*args, **kwargs)

    return wrapper


__all__ = ['enforce_dimensions']

# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.mcp.suggestions
====================

Suggestion logic for MCP error responses, optimized for AI agent self-correction.

This module provides helper functions for building structured error responses
with high-confidence fixes (likely_fix) and lower-confidence hints. The split
enables agents to distinguish mechanical corrections from exploratory suggestions.
"""
from __future__ import annotations

from difflib import SequenceMatcher, get_close_matches
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from ucon.core import Dimension, Unit, UnitProduct


class ConversionError(BaseModel):
    """Structured error response optimized for agent self-correction.

    Attributes
    ----------
    error : str
        Human-readable description of what went wrong.
    error_type : str
        One of: "unknown_unit", "dimension_mismatch", "no_conversion_path".
    parameter : str | None
        Which input caused the error (e.g., "from_unit", "to_unit", "unit_a").
    got : str | None
        What the agent provided (dimension or unit name).
    expected : str | None
        What was expected (dimension name).
    likely_fix : str | None
        High-confidence mechanical fix. When present, the agent should apply
        it without additional reasoning.
    hints : list[str]
        Lower-confidence exploratory suggestions. The agent should reason
        about these or escalate to the user.
    """

    error: str
    error_type: str
    parameter: str | None = None
    got: str | None = None
    expected: str | None = None
    likely_fix: str | None = None
    hints: list[str] = []


# -----------------------------------------------------------------------------
# Fuzzy Matching
# -----------------------------------------------------------------------------


def _get_fuzzy_corpus() -> list[str]:
    """All registry keys suitable for fuzzy matching.

    Returns the case-insensitive keys from _UNIT_REGISTRY.
    Excludes generated scaled variants (km, MHz, etc.) to prevent dilution.
    """
    from ucon.units import _UNIT_REGISTRY

    return list(_UNIT_REGISTRY.keys())


def _similarity(a: str, b: str) -> float:
    """SequenceMatcher ratio between two strings."""
    return SequenceMatcher(None, a, b).ratio()


def _suggest_units(bad_name: str) -> tuple[str | None, list[str]]:
    """Fuzzy match a bad unit name against the registry.

    Parameters
    ----------
    bad_name : str
        The unrecognized unit string.

    Returns
    -------
    tuple[str | None, list[str]]
        (likely_fix, similar_names) where likely_fix is set when
        the top match scores >= 0.7 and is significantly better than
        alternatives. Ambiguous matches go to hints only.
    """
    from ucon.units import _UNIT_REGISTRY

    corpus = _get_fuzzy_corpus()
    matches = get_close_matches(bad_name.lower(), corpus, n=3, cutoff=0.6)

    if not matches:
        return None, []

    # Check top match score
    top_score = _similarity(bad_name.lower(), matches[0])

    # High-confidence top match (>= 0.7) with clear gap to second match → likely_fix
    if top_score >= 0.7:
        # If there's a second match, check if top is clearly better
        if len(matches) >= 2:
            second_score = _similarity(bad_name.lower(), matches[1])
            # Gap of 0.1 means top match is clearly the intended unit
            if top_score - second_score >= 0.1:
                unit = _UNIT_REGISTRY[matches[0]]
                # Include other matches as hints
                other_formatted = [
                    _format_unit_with_aliases(_UNIT_REGISTRY[m])
                    for m in matches[1:]
                ]
                return _format_unit_with_aliases(unit), other_formatted
        else:
            # Single match at >= 0.7 → definitely likely_fix
            unit = _UNIT_REGISTRY[matches[0]]
            return _format_unit_with_aliases(unit), []

    # Multiple matches with similar scores or lower confidence → hints only
    formatted = [_format_unit_with_aliases(_UNIT_REGISTRY[m]) for m in matches]
    return None, formatted


def _format_unit_with_aliases(unit: 'Unit') -> str:
    """Format a unit with its shorthand for display: 'meter (m)'."""
    if unit.shorthand and unit.shorthand != unit.name:
        return f"{unit.name} ({unit.shorthand})"
    return unit.name


# -----------------------------------------------------------------------------
# Compatible Units
# -----------------------------------------------------------------------------


def _get_compatible_units(dimension: 'Dimension', limit: int = 5) -> list[str]:
    """Find units with conversion paths for a given dimension.

    Walks ConversionGraph._unit_edges rather than filtering by dimension alone,
    so only units with actual conversion paths are returned.

    Parameters
    ----------
    dimension : Dimension
        The dimension to find compatible units for.
    limit : int
        Maximum number of units to return.

    Returns
    -------
    list[str]
        Unit shorthands or names with conversion paths.
    """
    from ucon.graph import get_default_graph

    graph = get_default_graph()
    if dimension not in graph._unit_edges:
        return []

    units = []
    for unit in graph._unit_edges[dimension]:
        # Skip RebasedUnit instances
        if hasattr(unit, 'original'):
            continue
        label = unit.shorthand or unit.name
        if label and label not in units:
            units.append(label)
        if len(units) >= limit:
            break
    return units


def _get_dimension_name(unit) -> str:
    """Get readable dimension name from a Unit or UnitProduct.

    Named dimensions return their name (e.g., 'velocity').
    Unnamed derived dimensions return 'derived(length^3/time)'.
    Never returns 'Vector(...)'.

    Parameters
    ----------
    unit : Unit or UnitProduct
        The unit to get the dimension name for.

    Returns
    -------
    str
        Human-readable dimension name.
    """
    dim = unit.dimension
    return dim.name


# -----------------------------------------------------------------------------
# Error Builders
# -----------------------------------------------------------------------------


def build_unknown_unit_error(bad_name: str, parameter: str) -> ConversionError:
    """Build a ConversionError for an unknown unit.

    Parameters
    ----------
    bad_name : str
        The unrecognized unit string.
    parameter : str
        Which parameter was bad (e.g., "from_unit", "to_unit").

    Returns
    -------
    ConversionError
        Structured error with fuzzy match suggestions.
    """
    likely_fix, similar = _suggest_units(bad_name)

    hints = []
    if similar:
        hints.append(f"Similar units: {', '.join(similar)}")
    elif not likely_fix:
        hints.append("No similar units found")
        hints.append("Use list_units() to see all available units")

    # Generic hints always included
    hints.append("For scaled variants, combine with a prefix: km, mm, µm (see list_scales)")
    hints.append("For composite units: m/s, kg*m/s^2")

    # Limit to 3 hints
    hints = hints[:3]

    return ConversionError(
        error=f"Unknown unit: '{bad_name}'",
        error_type="unknown_unit",
        parameter=parameter,
        likely_fix=likely_fix,
        hints=hints,
    )


def build_dimension_mismatch_error(
    from_unit_str: str,
    to_unit_str: str,
    src_unit,
    dst_unit,
) -> ConversionError:
    """Build a ConversionError for a dimension mismatch.

    Parameters
    ----------
    from_unit_str : str
        The source unit string as provided by the user.
    to_unit_str : str
        The target unit string as provided by the user.
    src_unit : Unit or UnitProduct
        The parsed source unit.
    dst_unit : Unit or UnitProduct
        The parsed target unit.

    Returns
    -------
    ConversionError
        Structured error with dimension info and compatible units.
    """
    src_dim_name = _get_dimension_name(src_unit)
    dst_dim_name = _get_dimension_name(dst_unit)

    # Build hints
    hints = [f"{from_unit_str} is {src_dim_name}; {to_unit_str} is {dst_dim_name}"]

    # Get compatible units for source dimension
    compatible = _get_compatible_units(src_unit.dimension)
    if compatible:
        hints.append(f"Compatible {src_dim_name} units: {', '.join(compatible)}")
    else:
        hints.append("These are fundamentally different physical quantities")

    hints.append("Use check_dimensions() to verify compatibility before converting")

    # Limit to 3 hints
    hints = hints[:3]

    return ConversionError(
        error=f"Cannot convert '{from_unit_str}' to '{to_unit_str}': "
              f"{src_dim_name} is not compatible with {dst_dim_name}",
        error_type="dimension_mismatch",
        parameter="to_unit",
        got=src_dim_name,
        expected=src_dim_name,  # Expected same dimension as source
        hints=hints,
    )


def build_no_path_error(
    from_unit_str: str,
    to_unit_str: str,
    src_unit,
    dst_unit,
    exception: Exception,
) -> ConversionError:
    """Build a ConversionError for a missing conversion path.

    Parameters
    ----------
    from_unit_str : str
        The source unit string as provided by the user.
    to_unit_str : str
        The target unit string as provided by the user.
    src_unit : Unit or UnitProduct
        The parsed source unit.
    dst_unit : Unit or UnitProduct
        The parsed target unit.
    exception : Exception
        The ConversionNotFound exception.

    Returns
    -------
    ConversionError
        Structured error explaining why conversion is impossible.
    """
    src_dim = src_unit.dimension
    dst_dim = dst_unit.dimension
    src_dim_name = _get_dimension_name(src_unit)
    dst_dim_name = _get_dimension_name(dst_unit)

    hints = [f"{from_unit_str} is {src_dim_name}; {to_unit_str} is {dst_dim_name}"]

    # Check if this is pseudo-dimension isolation
    exc_msg = str(exception)
    is_pseudo_isolation = "pseudo-dimension" in exc_msg.lower()

    if is_pseudo_isolation or (src_dim != dst_dim and src_dim.vector == dst_dim.vector):
        # Pseudo-dimension isolation (angle, ratio, solid_angle share zero vector)
        hints.append(
            f"{src_dim_name} and {dst_dim_name} are isolated pseudo-dimensions — "
            "they cannot interconvert"
        )

        # Provide workaround hints based on the specific pseudo-dimensions
        if src_dim_name == "angle":
            hints.append("To express an angle as a fraction, compute angle/(2π) explicitly")
            other_units = _get_compatible_units(src_dim)
            if other_units:
                hints.append(f"Other angle units: {', '.join(other_units)}")
        elif src_dim_name == "ratio":
            other_units = _get_compatible_units(src_dim)
            if other_units:
                hints.append(f"Other ratio units: {', '.join(other_units)}")
        elif src_dim_name == "solid_angle":
            other_units = _get_compatible_units(src_dim)
            if other_units:
                hints.append(f"Other solid angle units: {', '.join(other_units)}")

    elif src_dim == dst_dim:
        # Same dimension but missing edge — suggest intermediate
        hints.append(
            "Both units are in the same dimension, but no direct conversion edge exists"
        )
        hints.append("Convert via an intermediate: try converting to a base unit first")
        compatible = _get_compatible_units(src_dim)
        if compatible:
            hints.append(f"Other {src_dim_name} units with paths: {', '.join(compatible)}")

    else:
        # Different dimensions — shouldn't normally reach here (would be DimensionMismatch)
        hints.append("These units have different dimensions")
        hints.append("Use check_dimensions() to verify compatibility before converting")

    # Limit to 3 hints
    hints = hints[:3]

    return ConversionError(
        error=f"No conversion path from '{from_unit_str}' to '{to_unit_str}'",
        error_type="no_conversion_path",
        parameter=None,
        got=src_dim_name,
        expected=dst_dim_name,
        hints=hints,
    )


def build_unknown_dimension_error(bad_dimension: str) -> ConversionError:
    """Build a ConversionError for an unknown dimension filter.

    Parameters
    ----------
    bad_dimension : str
        The unrecognized dimension string.

    Returns
    -------
    ConversionError
        Structured error with similar dimension suggestions.
    """
    from ucon import Dimension

    known = [d.name for d in Dimension]
    matches = get_close_matches(bad_dimension.lower(), [k.lower() for k in known], n=3, cutoff=0.6)

    # Map back to proper case
    matches_proper = []
    for m in matches:
        for k in known:
            if k.lower() == m:
                matches_proper.append(k)
                break

    likely_fix = matches_proper[0] if len(matches_proper) == 1 else None
    hints = []

    if matches_proper and not likely_fix:
        hints.append(f"Similar dimensions: {', '.join(matches_proper)}")
    elif not matches_proper:
        hints.append("Use list_dimensions() to see all available dimensions")

    return ConversionError(
        error=f"Unknown dimension: '{bad_dimension}'",
        error_type="unknown_unit",
        parameter="dimension",
        likely_fix=likely_fix,
        hints=hints,
    )


__all__ = [
    "ConversionError",
    "build_unknown_unit_error",
    "build_dimension_mismatch_error",
    "build_no_path_error",
    "build_unknown_dimension_error",
]

# ucon MCP Server
#
# Provides unit conversion and dimensional analysis tools for AI agents.
#
# Usage:
#   ucon-mcp              # Run via entry point
#   python -m ucon.mcp    # Run as module

import hashlib
import json
from contextvars import ContextVar
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ucon import Dimension, get_default_graph
from ucon.core import Number, Scale, Unit, UnitProduct
from ucon.graph import ConversionGraph, DimensionMismatch, ConversionNotFound, using_graph
from ucon.maps import LinearMap
from ucon.mcp.suggestions import (
    ConversionError,
    resolve_unit,
    build_dimension_mismatch_error,
    build_no_path_error,
    build_unknown_dimension_error,
)
from ucon.packages import EdgeDef, PackageLoadError, UnitDef


mcp = FastMCP("ucon")


# -----------------------------------------------------------------------------
# Session Graph Management
# -----------------------------------------------------------------------------

# Session-scoped graph for persistent custom definitions
_session_graph: ContextVar[ConversionGraph | None] = ContextVar(
    '_session_graph', default=None
)

# Cache for inline graph compilation (keyed by hash of definitions)
_inline_graph_cache: dict[str, ConversionGraph] = {}


def _get_session_graph() -> ConversionGraph:
    """Get or create the session graph.

    Returns a copy of the default graph on first access, then reuses
    the session graph for subsequent calls within the same session.
    """
    graph = _session_graph.get()
    if graph is None:
        graph = get_default_graph().copy()
        _session_graph.set(graph)
    return graph


def _reset_session_graph() -> None:
    """Reset the session graph to a fresh copy of the default graph."""
    graph = get_default_graph().copy()
    _session_graph.set(graph)


def _hash_definitions(
    custom_units: list[dict] | None,
    custom_edges: list[dict] | None,
) -> str:
    """Compute a stable hash for inline definitions."""
    data = {
        'units': sorted([json.dumps(u, sort_keys=True) for u in (custom_units or [])]),
        'edges': sorted([json.dumps(e, sort_keys=True) for e in (custom_edges or [])]),
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]


def _build_inline_graph(
    custom_units: list[dict] | None,
    custom_edges: list[dict] | None,
) -> tuple[ConversionGraph | None, ConversionError | None]:
    """Build an ephemeral graph with inline definitions.

    Returns (graph, None) on success, (None, error) on failure.
    Uses caching to avoid redundant compilation.
    """
    if not custom_units and not custom_edges:
        return None, None

    # Check cache
    cache_key = _hash_definitions(custom_units, custom_edges)
    if cache_key in _inline_graph_cache:
        return _inline_graph_cache[cache_key], None

    # Build new graph from session (or default)
    base_graph = _session_graph.get()
    if base_graph is None:
        base_graph = get_default_graph()
    graph = base_graph.copy()

    # Register custom units first
    for i, unit_dict in enumerate(custom_units or []):
        try:
            unit_def = UnitDef(
                name=unit_dict.get('name', ''),
                dimension=unit_dict.get('dimension', ''),
                aliases=tuple(unit_dict.get('aliases', ())),
            )
            unit = unit_def.materialize()
            graph.register_unit(unit)
        except PackageLoadError as e:
            return None, ConversionError(
                error=str(e),
                error_type="invalid_input",
                parameter=f"custom_units[{i}]",
                hints=["Check dimension name is valid (use list_dimensions())"],
            )
        except Exception as e:
            return None, ConversionError(
                error=f"Invalid unit definition: {e}",
                error_type="invalid_input",
                parameter=f"custom_units[{i}]",
                hints=["Unit needs 'name' and 'dimension' fields"],
            )

    # Add custom edges
    for i, edge_dict in enumerate(custom_edges or []):
        try:
            edge_def = EdgeDef(
                src=edge_dict.get('src', ''),
                dst=edge_dict.get('dst', ''),
                factor=float(edge_dict.get('factor', 1.0)),
            )
            edge_def.materialize(graph)
        except PackageLoadError as e:
            return None, ConversionError(
                error=str(e),
                error_type="invalid_input",
                parameter=f"custom_edges[{i}]",
                hints=["Check that src and dst units are defined"],
            )
        except Exception as e:
            return None, ConversionError(
                error=f"Invalid edge definition: {e}",
                error_type="invalid_input",
                parameter=f"custom_edges[{i}]",
                hints=["Edge needs 'src', 'dst', and 'factor' fields"],
            )

    # Cache the compiled graph
    _inline_graph_cache[cache_key] = graph
    return graph, None


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------


class ConversionResult(BaseModel):
    """Result of a unit conversion."""

    quantity: float
    unit: str | None
    dimension: str
    uncertainty: float | None = None


class UnitInfo(BaseModel):
    """Information about an available unit."""

    name: str
    shorthand: str
    aliases: list[str]
    dimension: str
    scalable: bool


class ScaleInfo(BaseModel):
    """Information about a scale prefix."""

    name: str
    prefix: str
    factor: float


class DimensionCheck(BaseModel):
    """Result of a dimensional compatibility check."""

    compatible: bool
    dimension_a: str
    dimension_b: str


class ComputeStep(BaseModel):
    """A single step in a compute chain."""

    factor: str
    dimension: str
    unit: str


class ComputeResult(BaseModel):
    """Result of a multi-step factor-label computation."""

    quantity: float
    unit: str
    dimension: str
    steps: list[ComputeStep]


class SessionResult(BaseModel):
    """Result of a session management operation."""

    success: bool
    message: str


class UnitDefinitionResult(BaseModel):
    """Result of defining a custom unit."""

    success: bool
    name: str
    dimension: str
    aliases: list[str]
    message: str


class ConversionDefinitionResult(BaseModel):
    """Result of defining a custom conversion."""

    success: bool
    src: str
    dst: str
    factor: float
    message: str


# -----------------------------------------------------------------------------
# Tools
# -----------------------------------------------------------------------------


@mcp.tool()
def convert(value: float, from_unit: str, to_unit: str) -> ConversionResult | ConversionError:
    """
    Convert a numeric value from one unit to another.

    Units can be specified as:
    - Base units: "meter", "m", "second", "s", "gram", "g"
    - Scaled units: "km", "mL", "kg", "MHz" (use list_scales for prefixes)
    - Composite units: "m/s", "kg*m/s^2", "N*m"
    - Exponents: "m^2", "s^-1" (ASCII) or "m²", "s⁻¹" (Unicode)

    Args:
        value: The numeric quantity to convert.
        from_unit: Source unit string.
        to_unit: Target unit string.

    Returns:
        ConversionResult with converted quantity, unit, and dimension.
        ConversionError if the conversion fails, with suggestions for correction.
    """
    # 1. Parse source unit
    src, err = resolve_unit(from_unit, parameter="from_unit")
    if err:
        return err

    # 2. Parse target unit
    dst, err = resolve_unit(to_unit, parameter="to_unit")
    if err:
        return err

    # 3. Perform conversion
    try:
        num = Number(quantity=value, unit=src)
        result = num.to(dst)
    except DimensionMismatch:
        return build_dimension_mismatch_error(from_unit, to_unit, src, dst)
    except ConversionNotFound as e:
        return build_no_path_error(from_unit, to_unit, src, dst, e)

    # Use the target unit string as output (what the user asked for).
    # This handles cases like mg/kg → µg/kg where internal representation
    # may lose unit info due to dimension cancellation.
    unit_str = to_unit
    dim_name = dst.dimension.name if hasattr(dst, 'dimension') else "none"

    return ConversionResult(
        quantity=result.quantity,
        unit=unit_str,
        dimension=dim_name,
        uncertainty=result.uncertainty,
    )


@mcp.tool()
def list_units(dimension: str | None = None) -> list[UnitInfo] | ConversionError:
    """
    List available units, optionally filtered by dimension.

    Returns base units only. Use scale prefixes (from list_scales) to form
    scaled variants. For example, "meter" with prefix "k" becomes "km".

    Args:
        dimension: Optional filter by dimension name (e.g., "length", "mass", "time").
                   Use list_dimensions() to see available dimensions.

    Returns:
        List of UnitInfo objects describing available units.
        ConversionError if the dimension filter is invalid.
    """
    import ucon.units as units_module

    # Validate dimension filter if provided
    if dimension:
        known_dimensions = [d.name for d in Dimension]
        if dimension not in known_dimensions:
            return build_unknown_dimension_error(dimension)

    # Units that accept SI scale prefixes
    SCALABLE_UNITS = {
        "meter", "gram", "second", "ampere", "kelvin", "mole", "candela",
        "hertz", "newton", "pascal", "joule", "watt", "coulomb", "volt",
        "farad", "ohm", "siemens", "weber", "tesla", "henry", "lumen",
        "lux", "becquerel", "gray", "sievert", "katal",
        "liter", "byte",
    }

    result = []
    seen_names = set()

    for name in dir(units_module):
        obj = getattr(units_module, name)
        if isinstance(obj, Unit) and obj.name and obj.name not in seen_names:
            seen_names.add(obj.name)

            if dimension and obj.dimension.name != dimension:
                continue

            result.append(
                UnitInfo(
                    name=obj.name,
                    shorthand=obj.shorthand,
                    aliases=list(obj.aliases) if obj.aliases else [],
                    dimension=obj.dimension.name,
                    scalable=obj.name in SCALABLE_UNITS,
                )
            )

    return sorted(result, key=lambda u: (u.dimension, u.name))


@mcp.tool()
def list_scales() -> list[ScaleInfo]:
    """
    List available scale prefixes for units.

    These prefixes can be combined with scalable units (see list_units).
    For example, prefix "k" (kilo) with unit "m" (meter) forms "km".

    Includes both SI decimal prefixes (kilo, mega, milli, micro, etc.)
    and binary prefixes (kibi, mebi, gibi) for information units.

    Note on bytes:
    - SI prefixes: kB = 1000 B, MB = 1,000,000 B (decimal)
    - Binary prefixes: KiB = 1024 B, MiB = 1,048,576 B (powers of 2)

    Returns:
        List of ScaleInfo objects with name, prefix symbol, and numeric factor.
    """
    result = []
    for scale in Scale:
        if scale == Scale.one:
            continue  # Skip the identity scale
        result.append(
            ScaleInfo(
                name=scale.name,
                prefix=scale.shorthand,
                factor=scale.descriptor.evaluated,
            )
        )
    return sorted(result, key=lambda s: -s.factor)


@mcp.tool()
def check_dimensions(unit_a: str, unit_b: str) -> DimensionCheck | ConversionError:
    """
    Check if two units have compatible dimensions.

    Units with the same dimension can be converted between each other.
    Units with different dimensions cannot be added or directly compared.

    Args:
        unit_a: First unit string.
        unit_b: Second unit string.

    Returns:
        DimensionCheck indicating compatibility and the dimension of each unit.
        ConversionError if a unit string cannot be parsed.
    """
    a, err = resolve_unit(unit_a, parameter="unit_a")
    if err:
        return err

    b, err = resolve_unit(unit_b, parameter="unit_b")
    if err:
        return err

    dim_a = a.dimension if isinstance(a, Unit) else a.dimension
    dim_b = b.dimension if isinstance(b, Unit) else b.dimension

    return DimensionCheck(
        compatible=(dim_a == dim_b),
        dimension_a=dim_a.name,
        dimension_b=dim_b.name,
    )


@mcp.tool()
def compute(
    initial_value: float,
    initial_unit: str,
    factors: list[dict],
) -> ComputeResult | ConversionError:
    """
    Perform multi-step factor-label calculations with dimensional tracking.

    This tool processes a chain of conversion factors, validating dimensional
    consistency at each step. It's designed for dosage calculations, stoichiometry,
    and other multi-step unit conversions.

    Each factor is applied as: result = result × (value × numerator / denominator)

    Args:
        initial_value: Starting numeric quantity.
        initial_unit: Starting unit string.
        factors: List of conversion factors. Each factor is a dict with:
            - value: Numeric coefficient (multiplied into numerator)
            - numerator: Numerator unit string (e.g., "kg", "mg")
            - denominator: Denominator unit string, optionally with numeric prefix
                          (e.g., "lb", "2.205 lb", "kg*day")

    Returns:
        ComputeResult with final quantity, unit, dimension, and step-by-step trace.
        ConversionError with step localization if any factor fails.

    Example:
        # Convert 154 lb to mg/dose for a drug with 15 mg/kg/day dosing, 3 doses/day
        compute(
            initial_value=154,
            initial_unit="lb",
            factors=[
                {"value": 1, "numerator": "kg", "denominator": "2.205 lb"},
                {"value": 15, "numerator": "mg", "denominator": "kg*day"},
                {"value": 1, "numerator": "day", "denominator": "3 dose"},
            ]
        )
    """
    import re

    # Parse initial unit
    initial_parsed, err = resolve_unit(initial_unit, parameter="initial_unit")
    if err:
        return err

    # Track numeric value separately from unit accumulator
    # The flat accumulator keys by (unit.name, dimension, scale) so that
    # mg and kg remain separate entries (different scales, shouldn't cancel)
    running_value = float(initial_value)
    accum: dict[tuple, tuple] = {}
    _accumulate_factors(accum, initial_parsed, +1.0)

    steps: list[ComputeStep] = []

    # Record initial state
    running_unit = _build_product_from_accum(accum)
    initial_dim = initial_parsed.dimension.name
    initial_unit_str = _format_unit_output(running_unit)
    steps.append(ComputeStep(
        factor=f"{initial_value} {initial_unit}",
        dimension=initial_dim,
        unit=initial_unit_str,
    ))

    # Process each factor
    for i, factor in enumerate(factors):
        step_num = i + 1  # 1-indexed for user-facing errors

        # Validate factor structure
        if not isinstance(factor, dict):
            return ConversionError(
                error=f"Factor at step {step_num} must be a dict",
                error_type="invalid_input",
                parameter=f"factors[{i}]",
                step=i,
                hints=["Each factor should be: {\"value\": float, \"numerator\": str, \"denominator\": str}"],
            )

        value = factor.get("value", 1.0)
        numerator = factor.get("numerator")
        denominator = factor.get("denominator")

        if numerator is None:
            return ConversionError(
                error=f"Factor at step {step_num} missing 'numerator' field",
                error_type="invalid_input",
                parameter=f"factors[{i}].numerator",
                step=i,
                hints=["Each factor needs a numerator unit string"],
            )

        if denominator is None:
            return ConversionError(
                error=f"Factor at step {step_num} missing 'denominator' field",
                error_type="invalid_input",
                parameter=f"factors[{i}].denominator",
                step=i,
                hints=["Each factor needs a denominator unit string"],
            )

        # Parse numerator unit
        num_unit, err = resolve_unit(numerator, parameter=f"factors[{i}].numerator", step=i)
        if err:
            return err

        # Parse denominator - may have numeric prefix (e.g., "2.205 lb")
        denom_value = 1.0
        denom_unit_str = denominator.strip()

        # Try to extract leading number from denominator
        match = re.match(r'^([0-9]*\.?[0-9]+)\s*(.+)$', denom_unit_str)
        if match:
            denom_value = float(match.group(1))
            denom_unit_str = match.group(2).strip()

        denom_unit, err = resolve_unit(denom_unit_str, parameter=f"factors[{i}].denominator", step=i)
        if err:
            return err

        # Apply factor: multiply by (value * num_unit) / (denom_value * denom_unit)
        try:
            # Compute numeric factor: value / denom_value
            numeric_factor = value / denom_value
            running_value *= numeric_factor

            # Accumulate numerator factors at +1, denominator factors at -1
            _accumulate_factors(accum, num_unit, +1.0)
            _accumulate_factors(accum, denom_unit, -1.0)

            # Build current unit product for step recording
            running_unit = _build_product_from_accum(accum)

        except Exception as e:
            return ConversionError(
                error=f"Error applying factor at step {step_num}: {str(e)}",
                error_type="computation_error",
                parameter=f"factors[{i}]",
                step=i,
                hints=["Check that units are compatible for this operation"],
            )

        # Record step
        result_dim = running_unit.dimension.name if running_unit else "none"
        result_unit_str = _format_unit_output(running_unit)

        # Format factor description
        if denom_value != 1.0:
            factor_desc = f"× ({value} {numerator} / {denom_value} {denom_unit_str})"
        else:
            factor_desc = f"× ({value} {numerator} / {denom_unit_str})"

        steps.append(ComputeStep(
            factor=factor_desc,
            dimension=result_dim,
            unit=result_unit_str,
        ))

    # Build final result
    running_unit = _build_product_from_accum(accum)
    final_dim = running_unit.dimension.name if running_unit else "none"
    final_unit_str = _format_unit_output(running_unit)

    return ComputeResult(
        quantity=running_value,
        unit=final_unit_str,
        dimension=final_dim,
        steps=steps,
    )


def _format_unit_output(unit) -> str:
    """Format a unit or unit product for output display."""
    if unit is None:
        return "1"
    elif isinstance(unit, Unit):
        return unit.shorthand or unit.name
    elif isinstance(unit, UnitProduct):
        return unit.shorthand or "1"
    else:
        return str(unit)


def _accumulate_factors(
    accum: dict[tuple, tuple],
    product: Unit | UnitProduct,
    sign: float,
) -> None:
    """Add all UnitFactors from a parsed unit into the accumulator.

    The accumulator is keyed by (unit.name, dimension, scale) so that
    same-unit-different-scale entries (mg vs kg) don't cancel.

    Args:
        accum: The accumulator dict mapping key → (UnitFactor, exponent).
        product: A Unit or UnitProduct to accumulate.
        sign: +1.0 for numerator factors, -1.0 for denominator factors.
    """
    from ucon.core import UnitFactor

    if isinstance(product, Unit):
        product = UnitProduct.from_unit(product)

    for uf, exp in product.factors.items():
        key = (uf.unit.name, uf.unit.dimension, uf.scale)
        if key in accum:
            existing_uf, existing_exp = accum[key]
            accum[key] = (existing_uf, existing_exp + exp * sign)
        else:
            accum[key] = (uf, exp * sign)


def _build_product_from_accum(
    accum: dict[tuple, tuple],
) -> UnitProduct:
    """Build a UnitProduct from surviving non-zero accumulator entries."""
    surviving = {}
    for key, (uf, exp) in accum.items():
        if abs(exp) > 1e-12:
            surviving[uf] = exp
    if not surviving:
        return UnitProduct({})
    return UnitProduct(surviving)


@mcp.tool()
def list_dimensions() -> list[str]:
    """
    List available physical dimensions.

    Dimensions represent fundamental physical quantities (length, mass, time, etc.)
    and derived quantities (velocity, force, energy, etc.).

    Use these dimension names to filter list_units().

    Returns:
        List of dimension names.
    """
    return sorted([d.name for d in Dimension])


# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------


def main():
    """Run the ucon MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()

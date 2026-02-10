# ucon MCP Server
#
# Provides unit conversion and dimensional analysis tools for AI agents.
#
# Usage:
#   ucon-mcp              # Run via entry point
#   python -m ucon.mcp    # Run as module

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ucon import Dimension
from ucon.core import Number, Scale, Unit, UnitProduct
from ucon.graph import DimensionMismatch, ConversionNotFound
from ucon.mcp.suggestions import (
    ConversionError,
    resolve_unit,
    build_dimension_mismatch_error,
    build_no_path_error,
    build_unknown_dimension_error,
)


mcp = FastMCP("ucon")


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

    # Build running result
    result = Number(quantity=initial_value, unit=initial_parsed)
    steps: list[ComputeStep] = []

    # Record initial state
    initial_dim = initial_parsed.dimension.name
    initial_unit_str = initial_parsed.shorthand or initial_parsed.name if isinstance(initial_parsed, Unit) else str(initial_parsed)
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

        # Create the factor as a Number ratio
        try:
            # factor_number = (value * numerator) / (denom_value * denominator)
            numerator_num = Number(quantity=value, unit=num_unit)
            denominator_num = Number(quantity=denom_value, unit=denom_unit)
            factor_ratio = numerator_num / denominator_num

            # Multiply running result by factor
            result = result * factor_ratio

        except Exception as e:
            return ConversionError(
                error=f"Error applying factor at step {step_num}: {str(e)}",
                error_type="computation_error",
                parameter=f"factors[{i}]",
                step=i,
                hints=["Check that units are compatible for this operation"],
            )

        # Record step
        result_unit = result.unit
        if result_unit is None:
            result_dim = "none"
            result_unit_str = "1"
        elif isinstance(result_unit, Unit):
            result_dim = result_unit.dimension.name
            result_unit_str = result_unit.shorthand or result_unit.name
        else:
            result_dim = result_unit.dimension.name
            result_unit_str = str(result_unit)

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
    final_unit = result.unit
    if final_unit is None:
        final_dim = "none"
        final_unit_str = "1"
    elif isinstance(final_unit, Unit):
        final_dim = final_unit.dimension.name
        final_unit_str = final_unit.shorthand or final_unit.name
    else:
        final_dim = final_unit.dimension.name
        final_unit_str = str(final_unit)

    return ComputeResult(
        quantity=result.quantity,
        unit=final_unit_str,
        dimension=final_dim,
        steps=steps,
    )


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

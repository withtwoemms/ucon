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

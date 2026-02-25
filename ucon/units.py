# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.units
===========

Defines and registers the canonical **unit set** for the *ucon* library.

This module exports the standard SI base and derived units, along with a few
common non-SI units. Each unit is a pre-constructed :class:`ucon.unit.Unit`
object associated with a :class:`ucon.dimension.Dimension`.

Example
-------
>>> from ucon import units
>>> units.meter.dimension
<LENGTH>
>>> units.newton.dimension
<FORCE>

Includes convenience utilities such as :func:`have(name)` for unit membership
checks.

Notes
-----
The design allows for future extensibility: users can register their own units,
systems, or aliases dynamically, without modifying the core definitions.
"""
import re
from typing import Dict, Tuple, Union

from ucon.core import Dimension, Scale, Unit, UnitFactor, UnitProduct, UnitSystem
from ucon.dimension import (
    NONE, TIME, LENGTH, MASS, CURRENT, TEMPERATURE,
    LUMINOUS_INTENSITY, AMOUNT_OF_SUBSTANCE, INFORMATION,
    ANGLE, SOLID_ANGLE, RATIO, COUNT,
    VELOCITY, ACCELERATION, FORCE, ENERGY, POWER,
    MOMENTUM, ANGULAR_MOMENTUM, AREA, VOLUME, DENSITY, PRESSURE, FREQUENCY,
    DYNAMIC_VISCOSITY, KINEMATIC_VISCOSITY, GRAVITATION,
    CHARGE, VOLTAGE, RESISTANCE, RESISTIVITY, CONDUCTANCE, CONDUCTIVITY,
    CAPACITANCE, INDUCTANCE, MAGNETIC_FLUX, MAGNETIC_FLUX_DENSITY,
    MAGNETIC_PERMEABILITY, PERMITTIVITY, ELECTRIC_FIELD_STRENGTH,
    ENTROPY, SPECIFIC_HEAT_CAPACITY, THERMAL_CONDUCTIVITY,
    ILLUMINANCE, CATALYTIC_ACTIVITY, MOLAR_MASS, MOLAR_VOLUME,
)
from ucon.graph import get_parsing_graph
from ucon.parsing import parse_unit_expression, ParseError


class UnknownUnitError(Exception):
    """Raised when a unit string cannot be resolved to a known unit."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Unknown unit: {name!r}")


none = Unit()


# -- International System of Units (SI) --------------------------------
ampere = Unit(name='ampere', dimension=CURRENT, aliases=('A', 'I', 'amp'))
becquerel = Unit(name='becquerel', dimension=FREQUENCY, aliases=('Bq',))
celsius = Unit(name='celsius', dimension=TEMPERATURE, aliases=('°C', 'degC'))
coulomb = Unit(name='coulomb', dimension=CHARGE, aliases=('C',))
farad = Unit(name='farad', dimension=CAPACITANCE, aliases=('F',))
gram = Unit(name='gram', dimension=MASS, aliases=('g',))
gray = Unit(name='gray', dimension=ENERGY, aliases=('Gy',))
henry = Unit(name='henry', dimension=INDUCTANCE, aliases=('H',))
hertz = Unit(name='hertz', dimension=FREQUENCY, aliases=('Hz',))
joule = Unit(name='joule', dimension=ENERGY, aliases=('J',))
joule_per_kelvin = Unit(name='joule_per_kelvin', dimension=ENTROPY, aliases=('J/K',))
katal = Unit(name='katal', dimension=CATALYTIC_ACTIVITY, aliases=('kat',))
kelvin = Unit(name='kelvin', dimension=TEMPERATURE, aliases=('K',))
kilogram = Unit(name='kilogram', dimension=MASS, aliases=('kg',))
liter = Unit(name='liter', dimension=VOLUME, aliases=('L', 'l'))
candela = Unit(name='candela', dimension=LUMINOUS_INTENSITY, aliases=('cd',))
lumen = Unit(name='lumen', dimension=LUMINOUS_INTENSITY, aliases=('lm',))
lux = Unit(name='lux', dimension=ILLUMINANCE, aliases=('lx',))
meter = Unit(name='meter', dimension=LENGTH, aliases=('m',))
mole = Unit(name='mole', dimension=AMOUNT_OF_SUBSTANCE, aliases=('mol', 'n'))
newton = Unit(name='newton', dimension=FORCE, aliases=('N',))
ohm = Unit(name='ohm', dimension=RESISTANCE, aliases=('Ω',))
pascal = Unit(name='pascal', dimension=PRESSURE, aliases=('Pa',))
radian = Unit(name='radian', dimension=ANGLE, aliases=('rad',))
siemens = Unit(name='siemens', dimension=CONDUCTANCE, aliases=('S',))
sievert = Unit(name='sievert', dimension=ENERGY, aliases=('Sv',))
steradian = Unit(name='steradian', dimension=SOLID_ANGLE, aliases=('sr',))
tesla = Unit(name='tesla', dimension=MAGNETIC_FLUX_DENSITY, aliases=('T',))
volt = Unit(name='volt', dimension=VOLTAGE, aliases=('V',))
watt = Unit(name='watt', dimension=POWER, aliases=('W',))
weber = Unit(name='weber', dimension=MAGNETIC_FLUX, aliases=('Wb',))
webers_per_meter = Unit(name='webers_per_meter', dimension=MAGNETIC_PERMEABILITY, aliases=('Wb/m',))
# ----------------------------------------------------------------------


# -- Viscosity Units ---------------------------------------------------
poise = Unit(name='poise', dimension=DYNAMIC_VISCOSITY, aliases=('P',))
stokes = Unit(name='stokes', dimension=KINEMATIC_VISCOSITY, aliases=('St',))
# ----------------------------------------------------------------------


# -- Time Units --------------------------------------------------------
second = Unit(name='second', dimension=TIME, aliases=('s', 'sec'))
minute = Unit(name='minute', dimension=TIME, aliases=('min',))
hour = Unit(name='hour', dimension=TIME, aliases=('h', 'hr'))
day = Unit(name='day', dimension=TIME, aliases=('d',))
# ----------------------------------------------------------------------


# -- Imperial / US Customary Units -------------------------------------
# Length
foot = Unit(name='foot', dimension=LENGTH, aliases=('ft', 'feet'))
inch = Unit(name='inch', dimension=LENGTH, aliases=('in', 'inches'))
yard = Unit(name='yard', dimension=LENGTH, aliases=('yd', 'yards'))
mile = Unit(name='mile', dimension=LENGTH, aliases=('mi', 'miles'))

# Mass
pound = Unit(name='pound', dimension=MASS, aliases=('lb', 'lbs'))
ounce = Unit(name='ounce', dimension=MASS, aliases=('oz', 'ounces'))

# Temperature
fahrenheit = Unit(name='fahrenheit', dimension=TEMPERATURE, aliases=('°F', 'degF'))
rankine = Unit(name='rankine', dimension=TEMPERATURE, aliases=('°R', 'degR', 'R'))

# Volume
gallon = Unit(name='gallon', dimension=VOLUME, aliases=('gal', 'gallons'))

# Energy
calorie = Unit(name='calorie', dimension=ENERGY, aliases=('cal', 'calories'))
btu = Unit(name='btu', dimension=ENERGY, aliases=('BTU',))
watt_hour = Unit(name='watt_hour', dimension=ENERGY, aliases=('Wh',))

# Power
horsepower = Unit(name='horsepower', dimension=POWER, aliases=('hp',))

# Pressure
bar = Unit(name='bar', dimension=PRESSURE, aliases=('bar',))
psi = Unit(name='psi', dimension=PRESSURE, aliases=('psi', 'lbf/in²'))
atmosphere = Unit(name='atmosphere', dimension=PRESSURE, aliases=('atm',))
torr = Unit(name='torr', dimension=PRESSURE, aliases=('Torr',))
millimeter_mercury = Unit(name='millimeter_mercury', dimension=PRESSURE, aliases=('mmHg',))
inch_mercury = Unit(name='inch_mercury', dimension=PRESSURE, aliases=('inHg',))

# Force
pound_force = Unit(name='pound_force', dimension=FORCE, aliases=('lbf',))
kilogram_force = Unit(name='kilogram_force', dimension=FORCE, aliases=('kgf',))
dyne = Unit(name='dyne', dimension=FORCE, aliases=('dyn',))
# ----------------------------------------------------------------------


# -- Information Units -------------------------------------------------
bit = Unit(name='bit', dimension=INFORMATION, aliases=('b', 'bits'))
byte = Unit(name='byte', dimension=INFORMATION, aliases=('B', 'bytes'))
# ----------------------------------------------------------------------


# -- Angle Units -------------------------------------------------------
degree = Unit(name='degree', dimension=ANGLE, aliases=('deg', '°'))
gradian = Unit(name='gradian', dimension=ANGLE, aliases=('grad', 'gon'))
arcminute = Unit(name='arcminute', dimension=ANGLE, aliases=('arcmin', "'"))
arcsecond = Unit(name='arcsecond', dimension=ANGLE, aliases=('arcsec', '"'))
turn = Unit(name='turn', dimension=ANGLE, aliases=('rev', 'revolution'))
# ----------------------------------------------------------------------


# -- Solid Angle Units -------------------------------------------------
square_degree = Unit(name='square_degree', dimension=SOLID_ANGLE, aliases=('deg²', 'sq_deg'))
# ----------------------------------------------------------------------


# -- Ratio Units -------------------------------------------------------
fraction = Unit(name='fraction', dimension=RATIO, aliases=('frac', '1'))
percent = Unit(name='percent', dimension=RATIO, aliases=('%',))
permille = Unit(name='permille', dimension=RATIO, aliases=('‰',))
ppm = Unit(name='ppm', dimension=RATIO, aliases=())
ppb = Unit(name='ppb', dimension=RATIO, aliases=())
basis_point = Unit(name='basis_point', dimension=RATIO, aliases=('bp', 'bps'))
nines = Unit(name='nines', dimension=RATIO, aliases=('9s',))
# ----------------------------------------------------------------------


# -- Count Units -------------------------------------------------------
each = Unit(name='each', dimension=COUNT, aliases=('ea', 'item', 'ct'))
# ----------------------------------------------------------------------


# Backward compatibility alias
webers = weber


# -- Predefined Unit Systems -----------------------------------------------
si = UnitSystem(
    name="SI",
    bases={
        LENGTH: meter,
        MASS: kilogram,
        TIME: second,
        TEMPERATURE: kelvin,
        CURRENT: ampere,
        AMOUNT_OF_SUBSTANCE: mole,
        LUMINOUS_INTENSITY: candela,
    }
)

imperial = UnitSystem(
    name="Imperial",
    bases={
        LENGTH: foot,
        MASS: pound,
        TIME: second,
        TEMPERATURE: fahrenheit,
    }
)
# --------------------------------------------------------------------------


def have(name: str) -> bool:
    assert name, "Must provide a unit name to check"
    assert isinstance(name, str), "Unit name must be a string"
    target = name.lower()
    for attr, val in globals().items():
        if isinstance(val, Unit):
            # match the variable name (e.g., "none", "meter")
            if attr.lower() == target:
                return True
            # match the declared unit name
            if val.name and val.name.lower() == target:
                return True
            # match any alias
            if any((alias or "").lower() == target for alias in getattr(val, "aliases", ())):
                return True
    return False


# -- Unit String Parsing Infrastructure ------------------------------------

# Module-level registries (populated by _build_registry at module load)
_UNIT_REGISTRY: Dict[str, Unit] = {}
_UNIT_REGISTRY_CASE_SENSITIVE: Dict[str, Unit] = {}

# -----------------------------------------------------------------------------
# Priority Alias Invariant (for contributors)
# -----------------------------------------------------------------------------
#
# When a unit alias could be misinterpreted as a scale prefix + unit symbol,
# add it to _PRIORITY_ALIASES or _PRIORITY_SCALED_ALIASES to prevent ambiguity.
#
# Examples:
#   - "min" could parse as milli-inch (m + in), but should be minute
#   - "mcg" could fail (no "mc" prefix), but should be microgram
#   - "cc" could fail, but should be cubic centimeter (cm³)
#
# Rule: If a unit string starts with a valid scale prefix AND the remainder
# is a valid unit symbol, check whether the whole string should be treated
# as a single unit. If so, add it to:
#
#   _PRIORITY_ALIASES - for unscaled units (e.g., "min" -> minute)
#   _PRIORITY_SCALED_ALIASES - for scaled units (e.g., "mcg" -> microgram)
#
# The parser checks these sets BEFORE attempting prefix decomposition.
# -----------------------------------------------------------------------------

# Priority aliases that must match exactly before prefix decomposition.
# Prevents ambiguous parses like "min" -> milli-inch instead of minute.
_PRIORITY_ALIASES: set = {'min'}

# Priority scaled aliases that map to a specific (unit, scale) tuple.
# Used for medical conventions like "mcg" -> (gram, Scale.micro).
# Populated by _build_registry() after units are defined.
_PRIORITY_SCALED_ALIASES: Dict[str, Tuple[Unit, Scale]] = {}

# Scale prefix mapping (shorthand -> Scale)
# Derived from Scale enum's ScaleDescriptor.shorthand, plus input-only aliases
_SCALE_PREFIXES: Dict[str, Scale] = {
    s.shorthand: s for s in Scale if s.shorthand
}

# Additional input aliases not in canonical ScaleDescriptor.shorthand
_SCALE_PREFIXES.update({
    'u': Scale.micro,  # ASCII alternative for µ
    'μ': Scale.micro,  # Unicode MICRO SIGN (U+00B5)
    # Note: Scale.micro.shorthand is 'µ' (GREEK SMALL LETTER MU, U+03BC)
})

# Sorted by length descending for greedy prefix matching
_SCALE_PREFIXES_SORTED = sorted(_SCALE_PREFIXES.keys(), key=len, reverse=True)

# Unicode superscript translation table
_SUPERSCRIPT_TO_DIGIT = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻', '0123456789-')


def _build_registry() -> None:
    """
    Populate the unit registry from module globals.

    Called once at module load time. Builds both case-insensitive and
    case-sensitive lookup tables.
    """
    for obj in globals().values():
        if isinstance(obj, Unit) and obj.name:
            # Case-insensitive registry (for lookups by name)
            _UNIT_REGISTRY[obj.name.lower()] = obj
            # Case-sensitive registry (for alias lookups like 'L' for liter)
            _UNIT_REGISTRY_CASE_SENSITIVE[obj.name] = obj
            for alias in obj.aliases:
                if alias:
                    _UNIT_REGISTRY[alias.lower()] = obj
                    _UNIT_REGISTRY_CASE_SENSITIVE[alias] = obj

    # Register priority scaled aliases (medical conventions)
    _PRIORITY_SCALED_ALIASES['mcg'] = (gram, Scale.micro)  # microgram
    _PRIORITY_SCALED_ALIASES['cc'] = (liter, Scale.milli)  # cubic centimeter = 1 mL


def _parse_exponent(s: str) -> Tuple[str, float]:
    """
    Extract exponent from unit factor string.

    Handles both formats:
    - Unicode: 'm²' -> ('m', 2.0), 's⁻¹' -> ('s', -1.0)
    - ASCII:  'm^2' -> ('m', 2.0), 's^-1' -> ('s', -1.0)

    Returns:
        Tuple of (base_unit_str, exponent) where exponent defaults to 1.0.
    """
    # Try ASCII caret notation first: "m^2", "s^-1"
    if '^' in s:
        base, exp_str = s.rsplit('^', 1)
        try:
            return base.strip(), float(exp_str)
        except ValueError:
            raise UnknownUnitError(s)

    # Try Unicode superscripts: "m²", "s⁻¹"
    match = re.search(r'[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+$', s)
    if match:
        base = s[:match.start()]
        exp_str = match.group().translate(_SUPERSCRIPT_TO_DIGIT)
        try:
            return base, float(exp_str)
        except ValueError:
            raise UnknownUnitError(s)

    # No exponent found
    return s, 1.0


def _lookup_factor(s: str) -> Tuple[Unit, Scale]:
    """
    Look up a single unit factor, handling scale prefixes.

    Checks graph-local registry first (if within a using_graph() context),
    then falls back to the global registry.

    Prioritizes prefix+unit interpretation over direct unit lookup,
    except for priority aliases (like 'min', 'mcg') which are checked first
    to avoid ambiguous parses or to handle domain-specific conventions.

    This means "kg" returns (gram, Scale.kilo) rather than (kilogram, Scale.one).

    Examples:
    - 'meter' -> (meter, Scale.one)
    - 'm' -> (meter, Scale.one)
    - 'km' -> (meter, Scale.kilo)
    - 'kg' -> (gram, Scale.kilo)
    - 'mL' -> (liter, Scale.milli)
    - 'min' -> (minute, Scale.one)  # priority alias, not milli-inch
    - 'mcg' -> (gram, Scale.micro)  # medical convention for microgram

    Returns:
        Tuple of (unit, scale).

    Raises:
        UnknownUnitError: If the unit cannot be resolved.
    """
    # Check graph-local registry first (if in using_graph() context)
    graph = get_parsing_graph()
    if graph is not None:
        result = graph.resolve_unit(s)
        if result is not None:
            return result

    # Check priority scaled aliases first (e.g., "mcg" -> microgram)
    if s in _PRIORITY_SCALED_ALIASES:
        return _PRIORITY_SCALED_ALIASES[s]

    # Check priority aliases (prevents "min" -> milli-inch)
    if s in _PRIORITY_ALIASES:
        if s in _UNIT_REGISTRY_CASE_SENSITIVE:
            return _UNIT_REGISTRY_CASE_SENSITIVE[s], Scale.one
        s_lower = s.lower()
        if s_lower in _UNIT_REGISTRY:
            return _UNIT_REGISTRY[s_lower], Scale.one

    # Try scale prefix + unit (prioritize decomposition)
    # Only case-sensitive matching for remainder (e.g., "fT" = femto-tesla, "ft" = foot)
    for prefix in _SCALE_PREFIXES_SORTED:
        if s.startswith(prefix) and len(s) > len(prefix):
            remainder = s[len(prefix):]
            if remainder in _UNIT_REGISTRY_CASE_SENSITIVE:
                return _UNIT_REGISTRY_CASE_SENSITIVE[remainder], _SCALE_PREFIXES[prefix]

    # Fall back to exact case-sensitive match (for aliases like 'L', 'B', 'm')
    if s in _UNIT_REGISTRY_CASE_SENSITIVE:
        return _UNIT_REGISTRY_CASE_SENSITIVE[s], Scale.one

    # Fall back to case-insensitive match
    s_lower = s.lower()
    if s_lower in _UNIT_REGISTRY:
        return _UNIT_REGISTRY[s_lower], Scale.one

    raise UnknownUnitError(s)


def _parse_composite(s: str) -> UnitProduct:
    """
    Parse composite unit string into UnitProduct using recursive descent.

    Accepts both Unicode and ASCII notation:
    - Unicode: 'm/s²', 'kg·m/s²', 'N·m', 'W/(m²*K)'
    - ASCII:  'm/s^2', 'kg*m/s^2', 'N*m', 'W/(m^2*K)'

    Supports:
    - Parentheses: `W/(m²*K)`, `(kg*m)/(s^2)`
    - Chained division: `mg/kg/d`
    - Unicode superscripts: `⁰¹²³⁴⁵⁶⁷⁸⁹⁻`
    - ASCII exponents: `^2`, `^-1`

    Returns:
        UnitProduct representing the parsed composite unit.

    Raises:
        ParseError: If the expression is malformed (e.g., unbalanced parens).
        UnknownUnitError: If a unit name cannot be resolved.
    """
    return parse_unit_expression(s, _lookup_factor, UnitFactor, UnitProduct)


def get_unit_by_name(name: str) -> Union[Unit, UnitProduct]:
    """
    Look up a unit by name, alias, or shorthand.

    Handles:
    - Plain units: "meter", "m", "second", "s"
    - Scaled units: "km", "mL", "kg"
    - Composite units: "m/s", "kg*m/s^2", "N·m"
    - Exponents: "m²", "m^2", "s⁻¹", "s^-1"

    Args:
        name: Unit string to parse.

    Returns:
        Unit for simple unscaled units, UnitProduct for scaled or composite.

    Raises:
        UnknownUnitError: If the unit cannot be resolved.

    Examples:
        >>> get_unit_by_name("meter")
        <Unit m>
        >>> get_unit_by_name("km")
        <UnitProduct km>
        >>> get_unit_by_name("m/s^2")
        <UnitProduct m/s²>
    """
    if not name or not name.strip():
        raise UnknownUnitError(name if name else "")

    name = name.strip()

    # Check for composite (has operators or parentheses)
    # Note: · (U+00B7 middle dot) and ⋅ (U+22C5 dot operator) are both multiplication
    if '/' in name or '·' in name or '⋅' in name or '*' in name or '(' in name:
        return _parse_composite(name)

    # Check for exponent
    base_str, exp = _parse_exponent(name)
    if exp != 1.0:
        unit, scale = _lookup_factor(base_str)
        return UnitProduct({UnitFactor(unit, scale): exp})

    # Simple unit or scaled unit
    unit, scale = _lookup_factor(name)
    if scale == Scale.one:
        return unit
    else:
        return UnitProduct({UnitFactor(unit, scale): 1})


# Build the registry at module load time
_build_registry()

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
<Dimension.length>
>>> units.newton.dimension
<Dimension.force>

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


class UnknownUnitError(Exception):
    """Raised when a unit string cannot be resolved to a known unit."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Unknown unit: {name!r}")


none = Unit()


# -- International System of Units (SI) --------------------------------
ampere = Unit(name='ampere', dimension=Dimension.current, aliases=('I', 'amp'))
becquerel = Unit(name='becquerel', dimension=Dimension.frequency, aliases=('Bq',))
celsius = Unit(name='celsius', dimension=Dimension.temperature, aliases=('°C', 'degC'))
coulomb = Unit(name='coulomb', dimension=Dimension.charge, aliases=('C',))
farad = Unit(name='farad', dimension=Dimension.capacitance, aliases=('F',))
gram = Unit(name='gram', dimension=Dimension.mass, aliases=('g',))
gray = Unit(name='gray', dimension=Dimension.energy, aliases=('Gy',))
henry = Unit(name='henry', dimension=Dimension.inductance, aliases=('H',))
hertz = Unit(name='hertz', dimension=Dimension.frequency, aliases=('Hz',))
joule = Unit(name='joule', dimension=Dimension.energy, aliases=('J',))
joule_per_kelvin = Unit(name='joule_per_kelvin', dimension=Dimension.entropy, aliases=('J/K',))
kelvin = Unit(name='kelvin', dimension=Dimension.temperature, aliases=('K',))
kilogram = Unit(name='kilogram', dimension=Dimension.mass, aliases=('kg',))
liter = Unit(name='liter', dimension=Dimension.volume, aliases=('L', 'l'))
candela = Unit(name='candela', dimension=Dimension.luminous_intensity, aliases=('cd',))
lumen = Unit(name='lumen', dimension=Dimension.luminous_intensity, aliases=('lm',))
lux = Unit(name='lux', dimension=Dimension.illuminance, aliases=('lx',))
meter = Unit(name='meter', dimension=Dimension.length, aliases=('m',))
mole = Unit(name='mole', dimension=Dimension.amount_of_substance, aliases=('mol', 'n'))
newton = Unit(name='newton', dimension=Dimension.force, aliases=('N',))
ohm = Unit(name='ohm', dimension=Dimension.resistance, aliases=('Ω',))
pascal = Unit(name='pascal', dimension=Dimension.pressure, aliases=('Pa',))
radian = Unit(name='radian', dimension=Dimension.angle, aliases=('rad',))
siemens = Unit(name='siemens', dimension=Dimension.conductance, aliases=('S',))
sievert = Unit(name='sievert', dimension=Dimension.energy, aliases=('Sv',))
steradian = Unit(name='steradian', dimension=Dimension.solid_angle, aliases=('sr',))
tesla = Unit(name='tesla', dimension=Dimension.magnetic_flux_density, aliases=('T',))
volt = Unit(name='volt', dimension=Dimension.voltage, aliases=('V',))
watt = Unit(name='watt', dimension=Dimension.power, aliases=('W',))
weber = Unit(name='weber', dimension=Dimension.magnetic_flux, aliases=('Wb',))
webers_per_meter = Unit(name='webers_per_meter', dimension=Dimension.magnetic_permeability, aliases=('Wb/m',))
# ----------------------------------------------------------------------


# -- Time Units --------------------------------------------------------
second = Unit(name='second', dimension=Dimension.time, aliases=('s', 'sec'))
minute = Unit(name='minute', dimension=Dimension.time, aliases=('min',))
hour = Unit(name='hour', dimension=Dimension.time, aliases=('h', 'hr'))
day = Unit(name='day', dimension=Dimension.time, aliases=('d',))
# ----------------------------------------------------------------------


# -- Imperial / US Customary Units -------------------------------------
# Length
foot = Unit(name='foot', dimension=Dimension.length, aliases=('ft', 'feet'))
inch = Unit(name='inch', dimension=Dimension.length, aliases=('in', 'inches'))
yard = Unit(name='yard', dimension=Dimension.length, aliases=('yd', 'yards'))
mile = Unit(name='mile', dimension=Dimension.length, aliases=('mi', 'miles'))

# Mass
pound = Unit(name='pound', dimension=Dimension.mass, aliases=('lb', 'lbs'))
ounce = Unit(name='ounce', dimension=Dimension.mass, aliases=('oz', 'ounces'))

# Temperature
fahrenheit = Unit(name='fahrenheit', dimension=Dimension.temperature, aliases=('°F', 'degF'))

# Volume
gallon = Unit(name='gallon', dimension=Dimension.volume, aliases=('gal', 'gallons'))

# Energy
calorie = Unit(name='calorie', dimension=Dimension.energy, aliases=('cal', 'calories'))
btu = Unit(name='btu', dimension=Dimension.energy, aliases=('BTU',))

# Power
horsepower = Unit(name='horsepower', dimension=Dimension.power, aliases=('hp',))

# Pressure
bar = Unit(name='bar', dimension=Dimension.pressure, aliases=('bar',))
psi = Unit(name='psi', dimension=Dimension.pressure, aliases=('psi', 'lbf/in²'))
atmosphere = Unit(name='atmosphere', dimension=Dimension.pressure, aliases=('atm',))
# ----------------------------------------------------------------------


# -- Information Units -------------------------------------------------
bit = Unit(name='bit', dimension=Dimension.information, aliases=('b', 'bits'))
byte = Unit(name='byte', dimension=Dimension.information, aliases=('B', 'bytes'))
# ----------------------------------------------------------------------


# -- Angle Units -------------------------------------------------------
degree = Unit(name='degree', dimension=Dimension.angle, aliases=('deg', '°'))
gradian = Unit(name='gradian', dimension=Dimension.angle, aliases=('grad', 'gon'))
arcminute = Unit(name='arcminute', dimension=Dimension.angle, aliases=('arcmin', "'"))
arcsecond = Unit(name='arcsecond', dimension=Dimension.angle, aliases=('arcsec', '"'))
turn = Unit(name='turn', dimension=Dimension.angle, aliases=('rev', 'revolution'))
# ----------------------------------------------------------------------


# -- Solid Angle Units -------------------------------------------------
square_degree = Unit(name='square_degree', dimension=Dimension.solid_angle, aliases=('deg²', 'sq_deg'))
# ----------------------------------------------------------------------


# -- Ratio Units -------------------------------------------------------
ratio_one = Unit(name='one', dimension=Dimension.ratio, aliases=('1',))
percent = Unit(name='percent', dimension=Dimension.ratio, aliases=('%',))
permille = Unit(name='permille', dimension=Dimension.ratio, aliases=('‰',))
ppm = Unit(name='ppm', dimension=Dimension.ratio, aliases=())
ppb = Unit(name='ppb', dimension=Dimension.ratio, aliases=())
basis_point = Unit(name='basis_point', dimension=Dimension.ratio, aliases=('bp', 'bps'))
nines = Unit(name='nines', dimension=Dimension.ratio, aliases=('9s',))
# ----------------------------------------------------------------------


# Backward compatibility alias
webers = weber


# -- Predefined Unit Systems -----------------------------------------------
si = UnitSystem(
    name="SI",
    bases={
        Dimension.length: meter,
        Dimension.mass: kilogram,
        Dimension.time: second,
        Dimension.temperature: kelvin,
        Dimension.current: ampere,
        Dimension.amount_of_substance: mole,
        Dimension.luminous_intensity: candela,
    }
)

imperial = UnitSystem(
    name="Imperial",
    bases={
        Dimension.length: foot,
        Dimension.mass: pound,
        Dimension.time: second,
        Dimension.temperature: fahrenheit,
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

# Scale prefix mapping (shorthand -> Scale)
# Sorted by length descending for greedy matching
_SCALE_PREFIXES: Dict[str, Scale] = {
    # Binary (IEC) - must come before single-char metric
    'Gi': Scale.gibi,
    'Mi': Scale.mebi,
    'Ki': Scale.kibi,
    # Metric (decimal) - multi-char first
    'da': Scale.deca,
    # Single-char metric
    'P': Scale.peta,
    'T': Scale.tera,
    'G': Scale.giga,
    'M': Scale.mega,
    'k': Scale.kilo,
    'h': Scale.hecto,
    'd': Scale.deci,
    'c': Scale.centi,
    'm': Scale.milli,
    'u': Scale.micro,  # ASCII alternative
    'μ': Scale.micro,  # Unicode micro sign
    'µ': Scale.micro,  # Unicode mu (common substitute)
    'n': Scale.nano,
    'p': Scale.pico,
    'f': Scale.femto,
}

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

    Prioritizes prefix+unit interpretation over direct unit lookup.
    This means "kg" returns (gram, Scale.kilo) rather than (kilogram, Scale.one).

    Examples:
    - 'meter' -> (meter, Scale.one)
    - 'm' -> (meter, Scale.one)
    - 'km' -> (meter, Scale.kilo)
    - 'kg' -> (gram, Scale.kilo)
    - 'mL' -> (liter, Scale.milli)

    Returns:
        Tuple of (unit, scale).

    Raises:
        UnknownUnitError: If the unit cannot be resolved.
    """
    # Try scale prefix + unit first (prioritize decomposition)
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
    Parse composite unit string into UnitProduct.

    Accepts both Unicode and ASCII notation:
    - Unicode: 'm/s²', 'kg·m/s²', 'N·m'
    - ASCII:  'm/s^2', 'kg*m/s^2', 'N*m'

    Delimiters:
    - Division: '/'
    - Multiplication: '·' (Unicode) or '*' (ASCII)

    Returns:
        UnitProduct representing the parsed composite unit.
    """
    # Normalize multiplication operator
    s = s.replace('*', '·')

    # Split numerator and denominator
    if '/' in s:
        num_part, den_part = s.split('/', 1)
    else:
        num_part, den_part = s, ''

    factors: Dict[UnitFactor, float] = {}

    # Parse numerator factors
    if num_part:
        for factor_str in num_part.split('·'):
            factor_str = factor_str.strip()
            if not factor_str:
                continue
            base_str, exp = _parse_exponent(factor_str)
            unit, scale = _lookup_factor(base_str)
            uf = UnitFactor(unit, scale)
            factors[uf] = factors.get(uf, 0) + exp

    # Parse denominator factors (negative exponents)
    if den_part:
        for factor_str in den_part.split('·'):
            factor_str = factor_str.strip()
            if not factor_str:
                continue
            base_str, exp = _parse_exponent(factor_str)
            unit, scale = _lookup_factor(base_str)
            uf = UnitFactor(unit, scale)
            factors[uf] = factors.get(uf, 0) - exp

    return UnitProduct(factors)


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

    # Check for composite (has operators)
    if '/' in name or '·' in name or '*' in name:
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

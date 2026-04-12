# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
ucon.units
===========

Unit objects loaded from ``comprehensive.ucon.toml`` at import time.

Every ``Unit`` defined in the TOML file becomes a module-level global.
For IDE autocomplete, see the companion ``units.pyi`` stub.

Example
-------
>>> from ucon import units
>>> units.meter.dimension
<LENGTH>
>>> units.newton.dimension
<FORCE>

Notes
-----
The design allows for future extensibility: users can register their own units,
systems, or aliases dynamically, without modifying the core definitions.
"""
from ucon.core import BaseForm, Dimension, Scale, Unit, UnitSystem, UnknownUnitError  # noqa: F401
from ucon.dimension import (
    NONE, TIME, LENGTH, MASS, CURRENT, TEMPERATURE,
    LUMINOUS_INTENSITY, AMOUNT_OF_SUBSTANCE, INFORMATION,
    ANGLE, SOLID_ANGLE, RATIO, COUNT,
    VELOCITY, ACCELERATION, FORCE, ENERGY, POWER,
    MOMENTUM, ANGULAR_MOMENTUM, AREA, VOLUME, DENSITY, PRESSURE, FREQUENCY,
    DYNAMIC_VISCOSITY, KINEMATIC_VISCOSITY, LINEAR_DENSITY, GRAVITATION,
    CHARGE, VOLTAGE, RESISTANCE, RESISTIVITY, CONDUCTANCE, CONDUCTIVITY,
    CAPACITANCE, INDUCTANCE, MAGNETIC_FLUX, MAGNETIC_FLUX_DENSITY,
    MAGNETIC_PERMEABILITY, PERMITTIVITY, ELECTRIC_FIELD_STRENGTH,
    MAGNETIC_FIELD_STRENGTH,
    ENTROPY, SPECIFIC_HEAT_CAPACITY, THERMAL_CONDUCTIVITY,
    ILLUMINANCE, CATALYTIC_ACTIVITY, MOLAR_MASS, MOLAR_VOLUME, CONCENTRATION,
    WAVENUMBER, RADIANT_EXPOSURE, EXPOSURE, ELECTRIC_DIPOLE_MOMENT,
    # CGS dimensions
    CGS_FORCE, CGS_ENERGY, CGS_PRESSURE,
    CGS_DYNAMIC_VISCOSITY, CGS_KINEMATIC_VISCOSITY,
    CGS_ACCELERATION, CGS_WAVENUMBER, CGS_RADIANT_EXPOSURE,
    # CGS-ESU dimensions
    CGS_ESU_CHARGE, CGS_ESU_CURRENT, CGS_ESU_VOLTAGE,
    CGS_ESU_RESISTANCE, CGS_ESU_CAPACITANCE,
    CGS_ESU_MAGNETIC_FLUX_DENSITY, CGS_ESU_MAGNETIC_FLUX,
    CGS_ESU_MAGNETIC_FIELD_STRENGTH, CGS_ESU_ELECTRIC_DIPOLE_MOMENT,
    # CGS-EMU dimensions
    CGS_EMU_CURRENT, CGS_EMU_CHARGE, CGS_EMU_VOLTAGE,
    CGS_EMU_RESISTANCE, CGS_EMU_CAPACITANCE, CGS_EMU_INDUCTANCE,
    # Natural-unit dimensions
    NATURAL_ENERGY,
    # Planck-unit dimensions
    PLANCK_ENERGY, PLANCK_LENGTH,
    # Atomic-unit dimensions
    ATOMIC_ENERGY, ATOMIC_LENGTH,
)
from ucon.resolver import register_unit, register_priority_scaled_alias, get_unit_by_name


# ---------------------------------------------------------------------------
# Load all units from the canonical TOML file
# ---------------------------------------------------------------------------

from ucon._loader import get_units as _get_units

_units = _get_units()
globals().update(_units)

# Sentinel unit (no name, no dimension) — not in TOML
none = Unit()

# Variable-name aliases for units whose Python variable name differs from
# the Unit.name (backward compatibility with pre-TOML code).
pint_volume = _units.get('pint')     # variable was 'pint_volume', Unit.name='pint'
point_typo = _units.get('point')     # variable was 'point_typo', Unit.name='point'

# Register all units with the global resolver
for _u in _units.values():
    register_unit(_u)


# ---------------------------------------------------------------------------
# Predefined Unit Systems
# ---------------------------------------------------------------------------

si = UnitSystem(
    name="SI",
    bases={
        LENGTH: _units['meter'],
        MASS: _units['kilogram'],
        TIME: _units['second'],
        TEMPERATURE: _units['kelvin'],
        CURRENT: _units['ampere'],
        AMOUNT_OF_SUBSTANCE: _units['mole'],
        LUMINOUS_INTENSITY: _units['candela'],
    }
)

imperial = UnitSystem(
    name="Imperial",
    bases={
        LENGTH: _units['foot'],
        MASS: _units['pound'],
        TIME: _units['second'],
        TEMPERATURE: _units['fahrenheit'],
    }
)


# ---------------------------------------------------------------------------
# Priority scaled aliases (usage conventions, not unit definitions)
# ---------------------------------------------------------------------------

def _register_aliases() -> None:
    """Register scaled aliases that encode usage conventions."""
    gram = _units['gram']
    meter = _units['meter']
    second = _units['second']
    hertz = _units['hertz']
    liter = _units['liter']
    watt = _units['watt']
    joule = _units['joule']
    pascal = _units['pascal']
    volt = _units['volt']
    ampere = _units['ampere']
    byte = _units['byte']
    bit = _units['bit']

    # Medical conventions
    register_priority_scaled_alias('mcg', gram, Scale.micro)   # microgram
    register_priority_scaled_alias('cc', liter, Scale.milli)   # cubic centimeter = 1 mL

    # -- Spelled-out scale aliases -----------------------------------------
    # Length
    register_priority_scaled_alias('kilometer', meter, Scale.kilo)
    register_priority_scaled_alias('centimeter', meter, Scale.centi)
    register_priority_scaled_alias('millimeter', meter, Scale.milli)
    register_priority_scaled_alias('micrometer', meter, Scale.micro)
    register_priority_scaled_alias('nanometer', meter, Scale.nano)
    register_priority_scaled_alias('picometer', meter, Scale.pico)

    # Mass
    register_priority_scaled_alias('milligram', gram, Scale.milli)
    register_priority_scaled_alias('microgram', gram, Scale.micro)

    # Time
    register_priority_scaled_alias('millisecond', second, Scale.milli)
    register_priority_scaled_alias('microsecond', second, Scale.micro)
    register_priority_scaled_alias('nanosecond', second, Scale.nano)
    register_priority_scaled_alias('picosecond', second, Scale.pico)

    # Frequency
    register_priority_scaled_alias('kilohertz', hertz, Scale.kilo)
    register_priority_scaled_alias('megahertz', hertz, Scale.mega)
    register_priority_scaled_alias('gigahertz', hertz, Scale.giga)

    # Volume
    register_priority_scaled_alias('milliliter', liter, Scale.milli)
    register_priority_scaled_alias('microliter', liter, Scale.micro)

    # Power
    register_priority_scaled_alias('kilowatt', watt, Scale.kilo)
    register_priority_scaled_alias('megawatt', watt, Scale.mega)
    register_priority_scaled_alias('gigawatt', watt, Scale.giga)
    register_priority_scaled_alias('milliwatt', watt, Scale.milli)

    # Energy
    register_priority_scaled_alias('kilojoule', joule, Scale.kilo)
    register_priority_scaled_alias('megajoule', joule, Scale.mega)

    # Pressure
    register_priority_scaled_alias('kilopascal', pascal, Scale.kilo)
    register_priority_scaled_alias('megapascal', pascal, Scale.mega)
    register_priority_scaled_alias('hectopascal', pascal, Scale.hecto)

    # Voltage
    register_priority_scaled_alias('millivolt', volt, Scale.milli)
    register_priority_scaled_alias('kilovolt', volt, Scale.kilo)

    # Current
    register_priority_scaled_alias('milliampere', ampere, Scale.milli)
    register_priority_scaled_alias('microampere', ampere, Scale.micro)

    # Information (decimal)
    register_priority_scaled_alias('kilobyte', byte, Scale.kilo)
    register_priority_scaled_alias('megabyte', byte, Scale.mega)
    register_priority_scaled_alias('gigabyte', byte, Scale.giga)
    register_priority_scaled_alias('terabyte', byte, Scale.tera)
    register_priority_scaled_alias('petabyte', byte, Scale.peta)
    register_priority_scaled_alias('kilobit', bit, Scale.kilo)
    register_priority_scaled_alias('megabit', bit, Scale.mega)
    register_priority_scaled_alias('gigabit', bit, Scale.giga)

    # Information (binary)
    register_priority_scaled_alias('kibibyte', byte, Scale.kibi)
    register_priority_scaled_alias('mebibyte', byte, Scale.mebi)
    register_priority_scaled_alias('gibibyte', byte, Scale.gibi)
    register_priority_scaled_alias('tebibyte', byte, Scale.tebi)
    register_priority_scaled_alias('pebibyte', byte, Scale.pebi)
    register_priority_scaled_alias('exbibyte', byte, Scale.exbi)


_register_aliases()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def have(name: str) -> bool:
    """Check if a unit name is defined."""
    assert name, "Must provide a unit name to check"
    assert isinstance(name, str), "Unit name must be a string"
    target = name.lower()
    for attr, val in globals().items():
        if isinstance(val, Unit):
            if attr.lower() == target:
                return True
            if val.name and val.name.lower() == target:
                return True
            if any((alias or "").lower() == target for alias in getattr(val, "aliases", ())):
                return True
    return False

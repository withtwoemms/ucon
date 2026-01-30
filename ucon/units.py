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
from ucon.core import Dimension, Unit


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
lumen = Unit(name='lumen', dimension=Dimension.luminous_intensity, aliases=('lm',))
lux = Unit(name='lux', dimension=Dimension.illuminance, aliases=('lx',))
meter = Unit(name='meter', dimension=Dimension.length, aliases=('m',))
mole = Unit(name='mole', dimension=Dimension.amount_of_substance, aliases=('mol', 'n'))
newton = Unit(name='newton', dimension=Dimension.force, aliases=('N',))
ohm = Unit(name='ohm', dimension=Dimension.resistance, aliases=('Ω',))
pascal = Unit(name='pascal', dimension=Dimension.pressure, aliases=('Pa',))
radian = Unit(name='radian', dimension=Dimension.none, aliases=('rad',))
siemens = Unit(name='siemens', dimension=Dimension.conductance, aliases=('S',))
sievert = Unit(name='sievert', dimension=Dimension.energy, aliases=('Sv',))
steradian = Unit(name='steradian', dimension=Dimension.none, aliases=('sr',))
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
foot = Unit(name='foot', dimension=Dimension.length, aliases=('ft',))
inch = Unit(name='inch', dimension=Dimension.length, aliases=('in',))
yard = Unit(name='yard', dimension=Dimension.length, aliases=('yd',))
mile = Unit(name='mile', dimension=Dimension.length, aliases=('mi',))

# Mass
pound = Unit(name='pound', dimension=Dimension.mass, aliases=('lb', 'lbs'))
ounce = Unit(name='ounce', dimension=Dimension.mass, aliases=('oz',))

# Temperature
fahrenheit = Unit(name='fahrenheit', dimension=Dimension.temperature, aliases=('°F', 'degF'))

# Volume
gallon = Unit(name='gallon', dimension=Dimension.volume, aliases=('gal',))

# Energy
calorie = Unit(name='calorie', dimension=Dimension.energy, aliases=('cal',))
btu = Unit(name='btu', dimension=Dimension.energy, aliases=('BTU',))

# Power
horsepower = Unit(name='horsepower', dimension=Dimension.power, aliases=('hp',))
# ----------------------------------------------------------------------


# -- Information Units -------------------------------------------------
bit = Unit(name='bit', dimension=Dimension.information, aliases=('b',))
byte = Unit(name='byte', dimension=Dimension.information, aliases=('B',))
# ----------------------------------------------------------------------


# Backward compatibility alias
webers = weber


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

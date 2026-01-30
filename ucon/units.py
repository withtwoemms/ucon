# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.units
===========

Defines and registers the canonical **unit set** for the *ucon* library.

This module exports the standard SI base and derived units, along with a few
common non-SI units. Each unit is a pre-constructed :class:`ucon.quantity.Quantity`
object associated with a :class:`ucon.dimension.Dimension`.

Example
-------
>>> from ucon import units
>>> units.meter.dimension
<Dimension.length>
>>> units.meter(5)
<5 m>

Includes convenience utilities such as :func:`have(name)` for unit membership
checks.

Notes
-----
The design allows for future extensibility: users can register their own units,
systems, or aliases dynamically, without modifying the core definitions.
"""
from ucon.core import Dimension, Unit
from ucon.quantity import Quantity


none = Unit()


# -- International System of Units (SI) --------------------------------
ampere = Quantity(name='ampere', dimension=Dimension.current, aliases=('I', 'amp'))
becquerel = Quantity(name='becquerel', dimension=Dimension.frequency, aliases=('Bq',))
celsius = Quantity(name='celsius', dimension=Dimension.temperature, aliases=('°C', 'degC'))
coulomb = Quantity(name='coulomb', dimension=Dimension.charge, aliases=('C',))
farad = Quantity(name='farad', dimension=Dimension.capacitance, aliases=('F',))
gram = Quantity(name='gram', dimension=Dimension.mass, aliases=('g',))
gray = Quantity(name='gray', dimension=Dimension.energy, aliases=('Gy',))
henry = Quantity(name='henry', dimension=Dimension.inductance, aliases=('H',))
hertz = Quantity(name='hertz', dimension=Dimension.frequency, aliases=('Hz',))
joule = Quantity(name='joule', dimension=Dimension.energy, aliases=('J',))
joule_per_kelvin = Quantity(name='joule_per_kelvin', dimension=Dimension.entropy, aliases=('J/K',))
kelvin = Quantity(name='kelvin', dimension=Dimension.temperature, aliases=('K',))
kilogram = Quantity(name='kilogram', dimension=Dimension.mass, aliases=('kg',))
liter = Quantity(name='liter', dimension=Dimension.volume, aliases=('L', 'l'))
lumen = Quantity(name='lumen', dimension=Dimension.luminous_intensity, aliases=('lm',))
lux = Quantity(name='lux', dimension=Dimension.illuminance, aliases=('lx',))
meter = Quantity(name='meter', dimension=Dimension.length, aliases=('m',))
mole = Quantity(name='mole', dimension=Dimension.amount_of_substance, aliases=('mol', 'n'))
newton = Quantity(name='newton', dimension=Dimension.force, aliases=('N',))
ohm = Quantity(name='ohm', dimension=Dimension.resistance, aliases=('Ω',))
pascal = Quantity(name='pascal', dimension=Dimension.pressure, aliases=('Pa',))
radian = Quantity(name='radian', dimension=Dimension.none, aliases=('rad',))
siemens = Quantity(name='siemens', dimension=Dimension.conductance, aliases=('S',))
sievert = Quantity(name='sievert', dimension=Dimension.energy, aliases=('Sv',))
steradian = Quantity(name='steradian', dimension=Dimension.none, aliases=('sr',))
tesla = Quantity(name='tesla', dimension=Dimension.magnetic_flux_density, aliases=('T',))
volt = Quantity(name='volt', dimension=Dimension.voltage, aliases=('V',))
watt = Quantity(name='watt', dimension=Dimension.power, aliases=('W',))
weber = Quantity(name='weber', dimension=Dimension.magnetic_flux, aliases=('Wb',))
webers_per_meter = Quantity(name='webers_per_meter', dimension=Dimension.magnetic_permeability, aliases=('Wb/m',))
# ----------------------------------------------------------------------


# -- Time Units --------------------------------------------------------
second = Quantity(name='second', dimension=Dimension.time, aliases=('s', 'sec'))
minute = Quantity(name='minute', dimension=Dimension.time, aliases=('min',))
hour = Quantity(name='hour', dimension=Dimension.time, aliases=('h', 'hr'))
day = Quantity(name='day', dimension=Dimension.time, aliases=('d',))
# ----------------------------------------------------------------------


# -- Imperial / US Customary Units -------------------------------------
# Length
foot = Quantity(name='foot', dimension=Dimension.length, aliases=('ft',))
inch = Quantity(name='inch', dimension=Dimension.length, aliases=('in',))
yard = Quantity(name='yard', dimension=Dimension.length, aliases=('yd',))
mile = Quantity(name='mile', dimension=Dimension.length, aliases=('mi',))

# Mass
pound = Quantity(name='pound', dimension=Dimension.mass, aliases=('lb', 'lbs'))
ounce = Quantity(name='ounce', dimension=Dimension.mass, aliases=('oz',))

# Temperature
fahrenheit = Quantity(name='fahrenheit', dimension=Dimension.temperature, aliases=('°F', 'degF'))

# Volume
gallon = Quantity(name='gallon', dimension=Dimension.volume, aliases=('gal',))

# Energy
calorie = Quantity(name='calorie', dimension=Dimension.energy, aliases=('cal',))
btu = Quantity(name='btu', dimension=Dimension.energy, aliases=('BTU',))

# Power
horsepower = Quantity(name='horsepower', dimension=Dimension.power, aliases=('hp',))
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

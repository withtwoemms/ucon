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
from ucon.dimension import Dimension
from ucon.unit import Unit


none = Unit()


# -- International System of Units (SI) --------------------------------
ampere = Unit('I', 'amp', name='ampere', dimension=Dimension.current)
becquerel = Unit('Bq', name='becquerel', dimension=Dimension.frequency)
celsius = Unit('°C', name='celsius', dimension=Dimension.temperature)
coulomb = Unit('C', name='coulomb', dimension=Dimension.charge)
farad = Unit('F', name='farad', dimension=Dimension.capacitance)
gram = Unit('g', 'G', name='gram', dimension=Dimension.mass)
gray = Unit('Gy', name='gray', dimension=Dimension.energy)
henry = Unit('H', name='henry', dimension=Dimension.inductance)
hertz = Unit('Hz', name='hertz', dimension=Dimension.frequency)
hour = Unit('h', 'H', name='hour', dimension=Dimension.time)
joule = Unit('J', name='joule', dimension=Dimension.energy)
joule_per_kelvin = Unit('J/K', name='joule_per_kelvin', dimension=Dimension.entropy)
kelvin = Unit('K', name='kelvin', dimension=Dimension.temperature)
liter = Unit('L', 'l', name='liter', dimension=Dimension.volume)
lumen = Unit('lm', name='lumen', dimension=Dimension.luminous_intensity)
lux = Unit('lx', name='lux', dimension=Dimension.illuminance)
meter = Unit('m', 'M', name='meter', dimension=Dimension.length)
mole = Unit('mol', 'n', name='mole', dimension=Dimension.amount_of_substance)
newton = Unit('N', name='newton', dimension=Dimension.force)
ohm = Unit('Ω', name='ohm', dimension=Dimension.resistance)
pascal = Unit('Pa', name='pascal', dimension=Dimension.pressure)
radian = Unit('rad', name='radian', dimension=Dimension.none)
second = Unit('s', 'sec', name='second', dimension=Dimension.time)
sievert = Unit('Sv', name='sievert', dimension=Dimension.energy)
siemens = Unit('S', name='siemens', dimension=Dimension.conductance)
steradian = Unit('sr', name='steradian', dimension=Dimension.none)
tesla = Unit('T', name='tesla', dimension=Dimension.magnetic_flux_density)
volt = Unit('V', name='volt', dimension=Dimension.voltage)
watt = Unit('W', name='watt', dimension=Dimension.power)
webers = Unit('Wb', name='weber', dimension=Dimension.magnetic_flux)
webers_per_meter = Unit('Wb/m', name='webers_per_meter', dimension=Dimension.magnetic_permeability)
# ----------------------------------------------------------------------


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

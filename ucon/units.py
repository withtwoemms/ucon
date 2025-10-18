from ucon.dimension import Dimension
from ucon.unit import Unit


none = Unit()


# -- International System of Units (SI) --------------------------------
gram = Unit('g', 'G', name='gram', dimension=Dimension.mass)
meter = Unit('m', 'M', name='meter', dimension=Dimension.length)
second = Unit('s', 'sec', name='second', dimension=Dimension.time)
hour = Unit('h', 'H', name='hour', dimension=Dimension.time)
liter = Unit('L', 'l', name='liter', dimension=Dimension.volume)
volt = Unit('V', name='volt', dimension=Dimension.voltage)
kelvin = Unit('K', name='kelvin', dimension=Dimension.temperature)
mole = Unit('mol', 'n', name='mole', dimension=Dimension.amount_of_substance)
coulomb = Unit('C', name='coulomb', dimension=Dimension.charge)
ampere = Unit('I', 'amp', name='ampere', dimension=Dimension.current)
ohm = Unit('Ω', name='ohm', dimension=Dimension.resistance)
joule = Unit('J', name='joule', dimension=Dimension.energy)
watt = Unit('W', name='watt', dimension=Dimension.power)
newton = Unit('N', name='newton', dimension=Dimension.force)
hertz = Unit('Hz', name='hertz', dimension=Dimension.frequency)
pascal = Unit('Pa', name='pascal', dimension=Dimension.pressure)
farad = Unit('F', name='farad', dimension=Dimension.capacitance)
henry = Unit('H', name='henry', dimension=Dimension.inductance)
siemens = Unit('S', name='siemens', dimension=Dimension.conductance)
webers = Unit('Wb', name='weber', dimension=Dimension.magnetic_flux)
tesla = Unit('T', name='tesla', dimension=Dimension.magnetic_flux_density)
celsius = Unit('°C', name='celsius', dimension=Dimension.temperature)
lux = Unit('lx', name='lux', dimension=Dimension.illuminance)
becquerel = Unit('Bq', name='becquerel', dimension=Dimension.frequency)
joule_per_kelvin = Unit('J/K', name='joule_per_kelvin', dimension=Dimension.entropy)
gray = Unit('Gy', name='gray', dimension=Dimension.energy)
sievert = Unit('Sv', name='sievert', dimension=Dimension.energy)
webers_per_meter = Unit('Wb/m', name='webers_per_meter', dimension=Dimension.magnetic_permeability)
lumen = Unit('lm', name='lumen', dimension=Dimension.luminous_intensity)
radian = Unit('rad', name='radian', dimension=Dimension.none)
steradian = Unit('sr', name='steradian', dimension=Dimension.none)
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

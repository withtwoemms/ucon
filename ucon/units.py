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
)
from ucon.resolver import register_unit, register_priority_scaled_alias, get_unit_by_name


# ----- bootstrap helper for self-referential base units --------------------
def _self_base(unit: Unit) -> BaseForm:
    """For coherent base units of a basis: 1 U = 1.0 × U^1."""
    return BaseForm(factors=((unit, 1.0),), prefactor=1.0)
# ---------------------------------------------------------------------------

none = Unit()

# -- SI canonical base units (definitional bootstrap) -------------------
# These 8 units anchor the SI basis. Their `base_form` is self-referential
# (1 kg ≡ 1 × kg, etc.), which cannot be expressed as a constructor literal
# because the Unit being constructed is itself the factor. We work around
# the fixed-point by calling ``Unit._set_base_form`` once per base unit;
# that method encapsulates the sanctioned post-construction mutation.
#
# Every other unit in this module receives `base_form=...` via the Unit
# constructor (definitional, never mutated).
kilogram = Unit(name='kilogram', dimension=MASS, aliases=('kg',))
meter = Unit(name='meter', dimension=LENGTH, aliases=('m',))
second = Unit(name='second', dimension=TIME, aliases=('s', 'sec'))
ampere = Unit(name='ampere', dimension=CURRENT, aliases=('A', 'I', 'amp'))
kelvin = Unit(name='kelvin', dimension=TEMPERATURE, aliases=('K',))
candela = Unit(name='candela', dimension=LUMINOUS_INTENSITY, aliases=('cd',))
mole = Unit(name='mole', dimension=AMOUNT_OF_SUBSTANCE, aliases=('mol', 'n'))
bit = Unit(name='bit', dimension=INFORMATION, aliases=('b', 'bits'))
kilogram._set_base_form(_self_base(kilogram))
meter._set_base_form(_self_base(meter))
second._set_base_form(_self_base(second))
ampere._set_base_form(_self_base(ampere))
kelvin._set_base_form(_self_base(kelvin))
candela._set_base_form(_self_base(candela))
mole._set_base_form(_self_base(mole))
bit._set_base_form(_self_base(bit))
# -----------------------------------------------------------------------



# -- International System of Units (SI) --------------------------------
becquerel = Unit(name='becquerel', dimension=FREQUENCY, aliases=('Bq',))
celsius = Unit(name='celsius', dimension=TEMPERATURE, aliases=('°C', 'degC'))
coulomb = Unit(name='coulomb', dimension=CHARGE, aliases=('C',), base_form=BaseForm(factors=((ampere, 1.0), (second, 1.0)), prefactor=1.0))
farad = Unit(name='farad', dimension=CAPACITANCE, aliases=('F',))
gram = Unit(name='gram', dimension=MASS, aliases=('g',), base_form=BaseForm(factors=((kilogram, 1.0),), prefactor=0.001))
gray = Unit(name='gray', dimension=ENERGY, aliases=('Gy',))
henry = Unit(name='henry', dimension=INDUCTANCE, aliases=('H',))
hertz = Unit(name='hertz', dimension=FREQUENCY, aliases=('Hz',), base_form=BaseForm(factors=((second, -1.0),), prefactor=1.0))
joule = Unit(name='joule', dimension=ENERGY, aliases=('J',), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -2.0)), prefactor=1.0))
joule_per_kelvin = Unit(name='joule_per_kelvin', dimension=ENTROPY, aliases=('J/K',))
katal = Unit(name='katal', dimension=CATALYTIC_ACTIVITY, aliases=('kat',), base_form=BaseForm(factors=((mole, 1.0), (second, -1.0)), prefactor=1.0))
liter = Unit(name='liter', dimension=VOLUME, aliases=('L', 'l'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=1.0))
lumen = Unit(name='lumen', dimension=LUMINOUS_INTENSITY, aliases=('lm',))
lux = Unit(name='lux', dimension=ILLUMINANCE, aliases=('lx',), base_form=BaseForm(factors=((meter, -2.0), (candela, 1.0)), prefactor=1.0))
newton = Unit(name='newton', dimension=FORCE, aliases=('N',), base_form=BaseForm(factors=((meter, 1.0), (kilogram, 1.0), (second, -2.0)), prefactor=1.0))
ohm = Unit(name='ohm', dimension=RESISTANCE, aliases=('Ω',), base_form=BaseForm(factors=((ampere, -2.0), (meter, 2.0), (kilogram, 1.0), (second, -3.0)), prefactor=1.0))
pascal = Unit(name='pascal', dimension=PRESSURE, aliases=('Pa',), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -2.0)), prefactor=1.0))
radian = Unit(name='radian', dimension=ANGLE, aliases=('rad',))
siemens = Unit(name='siemens', dimension=CONDUCTANCE, aliases=('S',))
sievert = Unit(name='sievert', dimension=ENERGY, aliases=('Sv',))
steradian = Unit(name='steradian', dimension=SOLID_ANGLE, aliases=('sr',))
tesla = Unit(name='tesla', dimension=MAGNETIC_FLUX_DENSITY, aliases=('T',))
volt = Unit(name='volt', dimension=VOLTAGE, aliases=('V',), base_form=BaseForm(factors=((ampere, -1.0), (meter, 2.0), (kilogram, 1.0), (second, -3.0)), prefactor=1.0))
watt = Unit(name='watt', dimension=POWER, aliases=('W',), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -3.0)), prefactor=1.0))
weber = Unit(name='weber', dimension=MAGNETIC_FLUX, aliases=('Wb',))
webers_per_meter = Unit(name='webers_per_meter', dimension=MAGNETIC_PERMEABILITY, aliases=('Wb/m',))
# ----------------------------------------------------------------------


# -- Named SI Intermediates (for cross-basis Unit→Unit edges) ----------
pascal_second = Unit(name='pascal_second', dimension=DYNAMIC_VISCOSITY, aliases=('Pa·s', 'Pa*s'), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -1.0)), prefactor=1.0))
square_meter_per_second = Unit(name='square_meter_per_second', dimension=KINEMATIC_VISCOSITY, aliases=('m²/s', 'm2/s'), base_form=BaseForm(factors=((meter, 2.0), (second, -1.0)), prefactor=1.0))
ampere_per_meter = Unit(name='ampere_per_meter', dimension=MAGNETIC_FIELD_STRENGTH, aliases=('A/m',))
meter_per_second_squared = Unit(name='meter_per_second_squared', dimension=ACCELERATION, aliases=('m/s²', 'm/s2'), base_form=BaseForm(factors=((meter, 1.0), (second, -2.0)), prefactor=1.0))
reciprocal_meter = Unit(name='reciprocal_meter', dimension=WAVENUMBER, aliases=('m⁻¹', '1/m'), base_form=BaseForm(factors=((meter, -1.0),), prefactor=1.0))
joule_per_square_meter = Unit(name='joule_per_square_meter', dimension=RADIANT_EXPOSURE, aliases=('J/m²', 'J/m2'), base_form=BaseForm(factors=((kilogram, 1.0), (second, -2.0)), prefactor=1.0))
coulomb_meter = Unit(name='coulomb_meter', dimension=ELECTRIC_DIPOLE_MOMENT, aliases=('C·m', 'C*m'))
coulomb_per_kilogram = Unit(name='coulomb_per_kilogram', dimension=EXPOSURE, aliases=('C/kg',), base_form=BaseForm(factors=((ampere, 1.0), (kilogram, -1.0), (second, 1.0)), prefactor=1.0))
# ----------------------------------------------------------------------


# -- Time Units --------------------------------------------------------
minute = Unit(name='minute', dimension=TIME, aliases=('min',), base_form=BaseForm(factors=((second, 1.0),), prefactor=60.0))
hour = Unit(name='hour', dimension=TIME, aliases=('h', 'hr'), base_form=BaseForm(factors=((second, 1.0),), prefactor=3600.0))
day = Unit(name='day', dimension=TIME, aliases=('d',), base_form=BaseForm(factors=((second, 1.0),), prefactor=86400.0))
week = Unit(name='week', dimension=TIME, aliases=('wk', 'weeks'), base_form=BaseForm(factors=((second, 1.0),), prefactor=604800.0))
year = Unit(name='year', dimension=TIME, aliases=('yr', 'years'), base_form=BaseForm(factors=((second, 1.0),), prefactor=31557600.0))
month = Unit(name='month', dimension=TIME, aliases=('mo', 'months'), base_form=BaseForm(factors=((second, 1.0),), prefactor=2629800.0))
fortnight = Unit(name='fortnight', dimension=TIME, aliases=('fn', 'fortnights'), base_form=BaseForm(factors=((second, 1.0),), prefactor=1209600.0))
shake = Unit(name='shake', dimension=TIME, aliases=('shakes',), base_form=BaseForm(factors=((second, 1.0),), prefactor=1e-08))
# ----------------------------------------------------------------------


# -- Imperial / US Customary Units -------------------------------------
# Length
foot = Unit(name='foot', dimension=LENGTH, aliases=('ft', 'feet'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=0.3047999902464003))
inch = Unit(name='inch', dimension=LENGTH, aliases=('in', 'inches'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=0.025399999187200026))
yard = Unit(name='yard', dimension=LENGTH, aliases=('yd', 'yards'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=0.914399970739201))
mile = Unit(name='mile', dimension=LENGTH, aliases=('mi', 'miles'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=1609.3439485009937))
nautical_mile = Unit(name='nautical_mile', dimension=LENGTH, aliases=('nmi', 'NM'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=1852.0))
fathom = Unit(name='fathom', dimension=LENGTH, aliases=('ftm', 'fathoms'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=1.828799941478402))
furlong = Unit(name='furlong', dimension=LENGTH, aliases=('fur', 'furlongs'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=201.168))
chain = Unit(name='chain', dimension=LENGTH, aliases=('ch', 'chains'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=20.1168))
rod = Unit(name='rod', dimension=LENGTH, aliases=('rd', 'rods', 'perch', 'pole'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=5.0292))
mil = Unit(name='mil', dimension=LENGTH, aliases=('thou',), base_form=BaseForm(factors=((meter, 1.0),), prefactor=2.5399999187200026e-05))
hand = Unit(name='hand', dimension=LENGTH, aliases=('hh', 'hands'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=0.1015999967488001))
league = Unit(name='league', dimension=LENGTH, aliases=('lea', 'leagues'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=4828.031845502982))
cable = Unit(name='cable', dimension=LENGTH, aliases=('cables',), base_form=BaseForm(factors=((meter, 1.0),), prefactor=185.2))

# Mass
pound = Unit(name='pound', dimension=MASS, aliases=('lb', 'lbs'), base_form=BaseForm(factors=((kilogram, 1.0),), prefactor=0.45359290943563974))
ounce = Unit(name='ounce', dimension=MASS, aliases=('oz', 'ounces'), base_form=BaseForm(factors=((kilogram, 1.0),), prefactor=0.028349556839727483))
metric_ton = Unit(name='metric_ton', dimension=MASS, aliases=('t', 'tonne', 'tonnes'), base_form=BaseForm(factors=((kilogram, 1.0),), prefactor=1000.0))
stone = Unit(name='stone', dimension=MASS, aliases=('st',), base_form=BaseForm(factors=((kilogram, 1.0),), prefactor=6.350300732098956))
grain = Unit(name='grain', dimension=MASS, aliases=('gr', 'grains'), base_form=BaseForm(factors=((kilogram, 1.0),), prefactor=6.479898706223426e-05))
slug = Unit(name='slug', dimension=MASS, aliases=('slug',), base_form=BaseForm(factors=((kilogram, 1.0),), prefactor=14.5939))
carat = Unit(name='carat', dimension=MASS, aliases=('ct_mass', 'carats'), base_form=BaseForm(factors=((kilogram, 1.0),), prefactor=0.0002))
troy_ounce = Unit(name='troy_ounce', dimension=MASS, aliases=('ozt', 'troy_oz'), base_form=BaseForm(factors=((kilogram, 1.0),), prefactor=0.031103500000000003))
long_ton = Unit(name='long_ton', dimension=MASS, aliases=('long_tons', 'imperial_ton'), base_form=BaseForm(factors=((kilogram, 1.0),), prefactor=1016.0481171358331))
short_ton = Unit(name='short_ton', dimension=MASS, aliases=('short_tons', 'US_ton'), base_form=BaseForm(factors=((kilogram, 1.0),), prefactor=907.1858188712795))
dram = Unit(name='dram', dimension=MASS, aliases=('dr', 'drams'), base_form=BaseForm(factors=((kilogram, 1.0),), prefactor=0.0017718473024829677))
pennyweight = Unit(name='pennyweight', dimension=MASS, aliases=('dwt', 'pennyweights'), base_form=BaseForm(factors=((kilogram, 1.0),), prefactor=0.0015551756894936224))

# Temperature
fahrenheit = Unit(name='fahrenheit', dimension=TEMPERATURE, aliases=('°F', 'degF'))
rankine = Unit(name='rankine', dimension=TEMPERATURE, aliases=('°R', 'degR', 'R'))
reaumur = Unit(name='reaumur', dimension=TEMPERATURE, aliases=('°Ré', 'degRe'))

# Historical electrical
international_ampere = Unit(name='international_ampere', dimension=CURRENT, aliases=('A_int',), base_form=BaseForm(factors=((ampere, 1.0),), prefactor=1.000022))
international_volt = Unit(name='international_volt', dimension=VOLTAGE, aliases=('V_int',), base_form=BaseForm(factors=((ampere, -1.0), (meter, 2.0), (kilogram, 1.0), (second, -3.0)), prefactor=1.00034))
international_ohm = Unit(name='international_ohm', dimension=RESISTANCE, aliases=('ohm_int',), base_form=BaseForm(factors=((ampere, -2.0), (meter, 2.0), (kilogram, 1.0), (second, -3.0)), prefactor=1.00049))

# Volume
gallon = Unit(name='gallon', dimension=VOLUME, aliases=('gal', 'gallons'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=3.785412534257983))
quart = Unit(name='quart', dimension=VOLUME, aliases=('qt', 'quarts'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=0.9463531335644958))
pint_volume = Unit(name='pint', dimension=VOLUME, aliases=('pt', 'pints'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=0.4731765667822479))
cup = Unit(name='cup', dimension=VOLUME, aliases=('cp', 'cups'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=0.23658828339112395))
fluid_ounce = Unit(name='fluid_ounce', dimension=VOLUME, aliases=('floz', 'fl_oz'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=0.029573535423890494))
tablespoon = Unit(name='tablespoon', dimension=VOLUME, aliases=('tbsp',), base_form=BaseForm(factors=((meter, 3.0),), prefactor=0.014786767711945247))
teaspoon = Unit(name='teaspoon', dimension=VOLUME, aliases=('tsp',), base_form=BaseForm(factors=((meter, 3.0),), prefactor=0.004928922570648415))
barrel = Unit(name='barrel', dimension=VOLUME, aliases=('bbl', 'barrels'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=158.9873264388353))
imperial_gallon = Unit(name='imperial_gallon', dimension=VOLUME, aliases=('imp_gal',), base_form=BaseForm(factors=((meter, 3.0),), prefactor=4.54609))
imperial_pint = Unit(name='imperial_pint', dimension=VOLUME, aliases=('imp_pt',), base_form=BaseForm(factors=((meter, 3.0),), prefactor=0.56826125))
bushel = Unit(name='bushel', dimension=VOLUME, aliases=('bu', 'bushels'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=35.23907016688))
peck = Unit(name='peck', dimension=VOLUME, aliases=('pk', 'pecks'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=8.80976754172))
gill = Unit(name='gill', dimension=VOLUME, aliases=('gi', 'gills'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=0.11829414169556197))
minim = Unit(name='minim', dimension=VOLUME, aliases=('min_vol', 'minims'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=6.161153213310519e-05))
cubic_foot = Unit(name='cubic_foot', dimension=VOLUME, aliases=('ft³', 'cu_ft'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=28.316846592000005))
cubic_inch = Unit(name='cubic_inch', dimension=VOLUME, aliases=('in³', 'cu_in'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=0.016387064))
cubic_yard = Unit(name='cubic_yard', dimension=VOLUME, aliases=('yd³', 'cu_yd'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=764.5548579840001))
acre_foot = Unit(name='acre_foot', dimension=VOLUME, aliases=('ac_ft', 'acre_feet'), base_form=BaseForm(factors=((meter, 3.0),), prefactor=1233481.83754752))
stere = Unit(name='stere', dimension=VOLUME, aliases=('st_vol',), base_form=BaseForm(factors=((meter, 3.0),), prefactor=1000.0))
imperial_quart = Unit(name='imperial_quart', dimension=VOLUME, aliases=('imp_qt',), base_form=BaseForm(factors=((meter, 3.0),), prefactor=1.1365225))
imperial_fluid_ounce = Unit(name='imperial_fluid_ounce', dimension=VOLUME, aliases=('imp_floz',), base_form=BaseForm(factors=((meter, 3.0),), prefactor=0.028413062499999996))
imperial_gill = Unit(name='imperial_gill', dimension=VOLUME, aliases=('imp_gi',), base_form=BaseForm(factors=((meter, 3.0),), prefactor=0.1420653125))
imperial_cup = Unit(name='imperial_cup', dimension=VOLUME, aliases=('imp_cup',), base_form=BaseForm(factors=((meter, 3.0),), prefactor=0.284130625))

# Energy
calorie = Unit(name='calorie', dimension=ENERGY, aliases=('cal', 'calories'), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -2.0)), prefactor=4.184))
btu = Unit(name='btu', dimension=ENERGY, aliases=('BTU',), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -2.0)), prefactor=1055.06))
watt_hour = Unit(name='watt_hour', dimension=ENERGY, aliases=('Wh',), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -2.0)), prefactor=3600.0))
therm = Unit(name='therm', dimension=ENERGY, aliases=('thm', 'therms'), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -2.0)), prefactor=105506000.0))
foot_pound = Unit(name='foot_pound', dimension=ENERGY, aliases=('ft_lb', 'ft_lbf'), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -2.0)), prefactor=1.3558179483314))
thermochemical_calorie = Unit(name='thermochemical_calorie', dimension=ENERGY, aliases=('cal_th',), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -2.0)), prefactor=4.184))
ton_tnt = Unit(name='ton_tnt', dimension=ENERGY, aliases=('tTNT',), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -2.0)), prefactor=4184000000.0))
tonne_oil_equivalent = Unit(name='tonne_oil_equivalent', dimension=ENERGY, aliases=('toe',), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -2.0)), prefactor=41868000000.0))

# Power
horsepower = Unit(name='horsepower', dimension=POWER, aliases=('hp',), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -3.0)), prefactor=745.7))
volt_ampere = Unit(name='volt_ampere', dimension=POWER, aliases=('VA',), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -3.0)), prefactor=1.0))
metric_horsepower = Unit(name='metric_horsepower', dimension=POWER, aliases=('PS',), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -3.0)), prefactor=735.4987500000001))
electrical_horsepower = Unit(name='electrical_horsepower', dimension=POWER, aliases=('hp_e',), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -3.0)), prefactor=746.0))
boiler_horsepower = Unit(name='boiler_horsepower', dimension=POWER, aliases=('hp_boiler',), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -3.0)), prefactor=9809.5))
refrigeration_ton = Unit(name='refrigeration_ton', dimension=POWER, aliases=('TR', 'ton_ref'), base_form=BaseForm(factors=((meter, 2.0), (kilogram, 1.0), (second, -3.0)), prefactor=3516.8525))

# Pressure
bar = Unit(name='bar', dimension=PRESSURE, aliases=('bar',), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -2.0)), prefactor=99999.99999999999))
psi = Unit(name='psi', dimension=PRESSURE, aliases=('psi', 'lbf/in²'), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -2.0)), prefactor=6894.744825494008))
atmosphere = Unit(name='atmosphere', dimension=PRESSURE, aliases=('atm',), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -2.0)), prefactor=101325.0))
torr = Unit(name='torr', dimension=PRESSURE, aliases=('Torr',), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -2.0)), prefactor=133.322368))
millimeter_mercury = Unit(name='millimeter_mercury', dimension=PRESSURE, aliases=('mmHg',), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -2.0)), prefactor=133.322368))
inch_mercury = Unit(name='inch_mercury', dimension=PRESSURE, aliases=('inHg',), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -2.0)), prefactor=3386.3890000000006))
centimeter_water = Unit(name='centimeter_water', dimension=PRESSURE, aliases=('cmH2O', 'cmAq'), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -2.0)), prefactor=98.0665))
centimeter_mercury = Unit(name='centimeter_mercury', dimension=PRESSURE, aliases=('cmHg',), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -2.0)), prefactor=1333.22))
ksi = Unit(name='ksi', dimension=PRESSURE, aliases=('ksi',), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -2.0)), prefactor=6894744.825494008))
technical_atmosphere = Unit(name='technical_atmosphere', dimension=PRESSURE, aliases=('at',), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -2.0)), prefactor=98066.5))
millimeter_water = Unit(name='millimeter_water', dimension=PRESSURE, aliases=('mmH2O', 'mmAq'), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -2.0)), prefactor=9.80665))
inch_water = Unit(name='inch_water', dimension=PRESSURE, aliases=('inH2O', 'inAq'), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -2.0)), prefactor=249.08891))

# Force
pound_force = Unit(name='pound_force', dimension=FORCE, aliases=('lbf',), base_form=BaseForm(factors=((meter, 1.0), (kilogram, 1.0), (second, -2.0)), prefactor=4.4482216152605))
kilogram_force = Unit(name='kilogram_force', dimension=FORCE, aliases=('kgf',), base_form=BaseForm(factors=((meter, 1.0), (kilogram, 1.0), (second, -2.0)), prefactor=9.80665))
kip = Unit(name='kip', dimension=FORCE, aliases=('klbf',), base_form=BaseForm(factors=((meter, 1.0), (kilogram, 1.0), (second, -2.0)), prefactor=4448.2216152605))
poundal = Unit(name='poundal', dimension=FORCE, aliases=('pdl',), base_form=BaseForm(factors=((meter, 1.0), (kilogram, 1.0), (second, -2.0)), prefactor=0.138255))
gram_force = Unit(name='gram_force', dimension=FORCE, aliases=('gf',), base_form=BaseForm(factors=((meter, 1.0), (kilogram, 1.0), (second, -2.0)), prefactor=0.00980665))
ounce_force = Unit(name='ounce_force', dimension=FORCE, aliases=('ozf',), base_form=BaseForm(factors=((meter, 1.0), (kilogram, 1.0), (second, -2.0)), prefactor=0.2780138509537812))
ton_force = Unit(name='ton_force', dimension=FORCE, aliases=('tnf', 'short_ton_force'), base_form=BaseForm(factors=((meter, 1.0), (kilogram, 1.0), (second, -2.0)), prefactor=8896.443230521))
metric_ton_force = Unit(name='metric_ton_force', dimension=FORCE, aliases=('tf', 'tonne_force'), base_form=BaseForm(factors=((meter, 1.0), (kilogram, 1.0), (second, -2.0)), prefactor=9806.65))
# ----------------------------------------------------------------------


# -- Area Units --------------------------------------------------------
acre = Unit(name='acre', dimension=AREA, aliases=('ac', 'acres'))
hectare = Unit(name='hectare', dimension=AREA, aliases=('ha',))
# ----------------------------------------------------------------------


# -- Velocity Units ----------------------------------------------------
knot = Unit(name='knot', dimension=VELOCITY, aliases=('kn', 'kt', 'knots'))
mile_per_hour = Unit(name='mile_per_hour', dimension=VELOCITY, aliases=('mph',))
# ----------------------------------------------------------------------


# -- Scientific Units --------------------------------------------------
# Length
angstrom = Unit(name='angstrom', dimension=LENGTH, aliases=('Å', 'angstroms'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=1e-10))
light_year = Unit(name='light_year', dimension=LENGTH, aliases=('ly', 'light_years'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=9460730472580800.0))
parsec = Unit(name='parsec', dimension=LENGTH, aliases=('pc', 'parsecs'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=3.085677581491367e+16))
astronomical_unit = Unit(name='astronomical_unit', dimension=LENGTH, aliases=('au', 'AU'), base_form=BaseForm(factors=((meter, 1.0),), prefactor=149597870700.0))

# Mass
dalton = Unit(name='dalton', dimension=MASS, aliases=('Da', 'u', 'amu'), base_form=BaseForm(factors=((kilogram, 1.0),), prefactor=1.6605390666e-27))

# Area
barn = Unit(name='barn', dimension=AREA, aliases=('b_area',))

# Charge
ampere_hour = Unit(name='ampere_hour', dimension=CHARGE, aliases=('Ah',), base_form=BaseForm(factors=((ampere, 1.0), (second, 1.0)), prefactor=3600.0))


# Radiation
curie = Unit(name='curie', dimension=FREQUENCY, aliases=('Ci',))
rem = Unit(name='rem', dimension=ENERGY, aliases=('rem',))
rad_dose = Unit(name='rad_dose', dimension=ENERGY, aliases=('rad_absorbed',))
roentgen = Unit(name='roentgen', dimension=EXPOSURE, aliases=('R_exp',), base_form=BaseForm(factors=((ampere, 1.0), (kilogram, -1.0), (second, 1.0)), prefactor=0.000258))


# Catalytic activity
enzyme_unit = Unit(name='enzyme_unit', dimension=CATALYTIC_ACTIVITY, aliases=('U', 'IU'), base_form=BaseForm(factors=((mole, 1.0), (second, -1.0)), prefactor=1.6666666666666667e-08))

# Typography
point_typo = Unit(name='point', dimension=LENGTH, aliases=('pt_typo',), base_form=BaseForm(factors=((meter, 1.0),), prefactor=0.00035277776648888926))
pica = Unit(name='pica', dimension=LENGTH, aliases=('pica',), base_form=BaseForm(factors=((meter, 1.0),), prefactor=0.0042333331978666715))

# Textile (linear density)
tex = Unit(name='tex', dimension=LINEAR_DENSITY, aliases=('tex',), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0)), prefactor=9.0))
denier = Unit(name='denier', dimension=LINEAR_DENSITY, aliases=('den', 'D_tex'), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0)), prefactor=1.0))

# Photometry
foot_candle = Unit(name='foot_candle', dimension=ILLUMINANCE, aliases=('fc', 'ftc'), base_form=BaseForm(factors=((meter, -2.0), (candela, 1.0)), prefactor=10.763910417))
# phot uses SI-basis ILLUMINANCE (cd·m⁻²) despite being conventionally called
# "CGS" because its dimensional formula involves candela, which belongs to the
# SI basis — CGS has no luminous intensity component.
phot = Unit(name='phot', dimension=ILLUMINANCE, aliases=('ph',), base_form=BaseForm(factors=((meter, -2.0), (candela, 1.0)), prefactor=10000.0))
nit = Unit(name='nit', dimension=ILLUMINANCE, aliases=('nt',), base_form=BaseForm(factors=((meter, -2.0), (candela, 1.0)), prefactor=1.0))
stilb = Unit(name='stilb', dimension=ILLUMINANCE, aliases=('sb',), base_form=BaseForm(factors=((meter, -2.0), (candela, 1.0)), prefactor=10000.0))
lambert = Unit(name='lambert', dimension=ILLUMINANCE, aliases=('La',), base_form=BaseForm(factors=((meter, -2.0), (candela, 1.0)), prefactor=3183.0988618379067))
apostilb = Unit(name='apostilb', dimension=ILLUMINANCE, aliases=('asb',), base_form=BaseForm(factors=((meter, -2.0), (candela, 1.0)), prefactor=0.3183098861837907))

# Viscosity
reyn = Unit(name='reyn', dimension=DYNAMIC_VISCOSITY, aliases=('reyn',), base_form=BaseForm(factors=((meter, -1.0), (kilogram, 1.0), (second, -1.0)), prefactor=6894.757))

# Spectroscopy / Radiation (SI-basis)
jansky = Unit(name='jansky', dimension=RADIANT_EXPOSURE, aliases=('Jy',), base_form=BaseForm(factors=((kilogram, 1.0), (second, -2.0)), prefactor=1.0000000000000002e-26))

# Acceleration
galileo = Unit(name='galileo', dimension=CGS_ACCELERATION, aliases=('Gal',))
standard_gravity = Unit(name='standard_gravity', dimension=ACCELERATION, aliases=('g0', 'gn'), base_form=BaseForm(factors=((meter, 1.0), (second, -2.0)), prefactor=9.80665))

# Concentration
molar = Unit(name='molar', dimension=CONCENTRATION, aliases=('mol/L',))
# ----------------------------------------------------------------------


# -- CGS Mechanical Units (native CGS basis) ---------------------------
dyne = Unit(name='dyne', dimension=CGS_FORCE, aliases=('dyn',))
erg = Unit(name='erg', dimension=CGS_ENERGY, aliases=('erg',))
barye = Unit(name='barye', dimension=CGS_PRESSURE, aliases=('Ba',))
poise = Unit(name='poise', dimension=CGS_DYNAMIC_VISCOSITY, aliases=('P',))
stokes = Unit(name='stokes', dimension=CGS_KINEMATIC_VISCOSITY, aliases=('St',))
kayser = Unit(name='kayser', dimension=CGS_WAVENUMBER, aliases=('K_wave',))
langley = Unit(name='langley', dimension=CGS_RADIANT_EXPOSURE, aliases=('Ly_rad',))
# ----------------------------------------------------------------------


# -- CGS-ESU Electromagnetic Units (native CGS-ESU basis) --------------
statcoulomb = Unit(name='statcoulomb', dimension=CGS_ESU_CHARGE, aliases=('statC', 'esu', 'franklin', 'Fr'))
statampere = Unit(name='statampere', dimension=CGS_ESU_CURRENT, aliases=('statA',))
statvolt = Unit(name='statvolt', dimension=CGS_ESU_VOLTAGE, aliases=('statV',))
statohm = Unit(name='statohm', dimension=CGS_ESU_RESISTANCE, aliases=('statΩ',))
statfarad = Unit(name='statfarad', dimension=CGS_ESU_CAPACITANCE, aliases=('statF',))
gauss = Unit(name='gauss', dimension=CGS_ESU_MAGNETIC_FLUX_DENSITY, aliases=('G', 'Gs'))
maxwell = Unit(name='maxwell', dimension=CGS_ESU_MAGNETIC_FLUX, aliases=('Mx',))
oersted = Unit(name='oersted', dimension=CGS_ESU_MAGNETIC_FIELD_STRENGTH, aliases=('Oe',))
debye = Unit(name='debye', dimension=CGS_ESU_ELECTRIC_DIPOLE_MOMENT, aliases=('D_dipole',))
# ----------------------------------------------------------------------


# -- CGS-EMU Electromagnetic Units (native CGS basis) -----------------
biot = Unit(name='biot', dimension=CGS_EMU_CURRENT, aliases=('Bi', 'abampere', 'abA'))
abcoulomb = Unit(name='abcoulomb', dimension=CGS_EMU_CHARGE, aliases=('abC',))
abvolt = Unit(name='abvolt', dimension=CGS_EMU_VOLTAGE, aliases=('abV',))
abohm = Unit(name='abohm', dimension=CGS_EMU_RESISTANCE, aliases=('abΩ',))
abfarad = Unit(name='abfarad', dimension=CGS_EMU_CAPACITANCE, aliases=('abF',))
abhenry = Unit(name='abhenry', dimension=CGS_EMU_INDUCTANCE, aliases=('abH',))
gilbert = Unit(name='gilbert', dimension=CGS_EMU_CURRENT, aliases=('Gb', 'Gi'))
# ----------------------------------------------------------------------


# -- Natural Units (native natural basis) ------------------------------
electron_volt = Unit(name='electron_volt', dimension=NATURAL_ENERGY, aliases=('eV',))
hartree = Unit(name='hartree', dimension=NATURAL_ENERGY, aliases=('Eh', 'Ha'))
rydberg = Unit(name='rydberg', dimension=NATURAL_ENERGY, aliases=('Ry',))
# ----------------------------------------------------------------------


# -- Information Units -------------------------------------------------
byte = Unit(name='byte', dimension=INFORMATION, aliases=('B', 'bytes'), base_form=BaseForm(factors=((bit, 1.0),), prefactor=8.0))
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


# -- Logarithmic Units (v0.9.1) ----------------------------------------
# Base logarithmic units (dimensionless ratio)
# Note: 'B' alias omitted for bel to avoid conflict with byte ('B')
bel = Unit(name='bel', dimension=RATIO, aliases=())
decibel = Unit(name='decibel', dimension=RATIO, aliases=('dB',))
neper = Unit(name='neper', dimension=RATIO, aliases=('Np',))

# Reference-level variants (carry dimension of the reference)
decibel_milliwatt = Unit(
    name='decibel_milliwatt',
    dimension=POWER,
    aliases=('dBm',),
)
decibel_watt = Unit(
    name='decibel_watt',
    dimension=POWER,
    aliases=('dBW',),
)
decibel_volt = Unit(
    name='decibel_volt',
    dimension=VOLTAGE,
    aliases=('dBV',),
)
decibel_spl = Unit(
    name='decibel_spl',
    dimension=PRESSURE,
    aliases=('dBSPL', 'dB_SPL'),
)

# pH (chemistry) - logarithmic measure of hydrogen ion concentration
# pH has concentration dimension (amount_of_substance/volume), consistent with
# how dBm has POWER dimension, dBV has VOLTAGE dimension, etc.
# This enables mol/L <-> pH conversions via the ConversionGraph.
_CONCENTRATION = AMOUNT_OF_SUBSTANCE / VOLUME
pH = Unit(name='pH', dimension=_CONCENTRATION, aliases=())
# ----------------------------------------------------------------------


# -- Count Units -------------------------------------------------------
each = Unit(name='each', dimension=COUNT, aliases=('ea', 'item', 'ct'))
# ----------------------------------------------------------------------


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


# -- Populate resolver registry at module load time --------------------------

def _populate_registry() -> None:
    """Register all units defined in this module with the resolver."""
    for obj in globals().values():
        if isinstance(obj, Unit) and obj.name:
            register_unit(obj)
    # Medical conventions
    register_priority_scaled_alias('mcg', gram, Scale.micro)   # microgram
    register_priority_scaled_alias('cc', liter, Scale.milli)    # cubic centimeter = 1 mL

    # -- Spelled-out scale aliases (v1.1.2) ------------------------------------
    # Enable natural-language unit names like "kilometer" or "millisecond".
    # NOTE: "kilogram" is intentionally omitted — it exists as a registered Unit.

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


_populate_registry()

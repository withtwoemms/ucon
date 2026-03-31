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
from ucon.core import Dimension, Scale, Unit, UnitSystem, UnknownUnitError  # noqa: F401
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


# -- Named SI Intermediates (for cross-basis Unit→Unit edges) ----------
pascal_second = Unit(name='pascal_second', dimension=DYNAMIC_VISCOSITY, aliases=('Pa·s', 'Pa*s'))
square_meter_per_second = Unit(name='square_meter_per_second', dimension=KINEMATIC_VISCOSITY, aliases=('m²/s', 'm2/s'))
ampere_per_meter = Unit(name='ampere_per_meter', dimension=MAGNETIC_FIELD_STRENGTH, aliases=('A/m',))
meter_per_second_squared = Unit(name='meter_per_second_squared', dimension=ACCELERATION, aliases=('m/s²', 'm/s2'))
reciprocal_meter = Unit(name='reciprocal_meter', dimension=WAVENUMBER, aliases=('m⁻¹', '1/m'))
joule_per_square_meter = Unit(name='joule_per_square_meter', dimension=RADIANT_EXPOSURE, aliases=('J/m²', 'J/m2'))
coulomb_meter = Unit(name='coulomb_meter', dimension=ELECTRIC_DIPOLE_MOMENT, aliases=('C·m', 'C*m'))
coulomb_per_kilogram = Unit(name='coulomb_per_kilogram', dimension=EXPOSURE, aliases=('C/kg',))
# ----------------------------------------------------------------------


# -- Time Units --------------------------------------------------------
second = Unit(name='second', dimension=TIME, aliases=('s', 'sec'))
minute = Unit(name='minute', dimension=TIME, aliases=('min',))
hour = Unit(name='hour', dimension=TIME, aliases=('h', 'hr'))
day = Unit(name='day', dimension=TIME, aliases=('d',))
week = Unit(name='week', dimension=TIME, aliases=('wk', 'weeks'))
year = Unit(name='year', dimension=TIME, aliases=('yr', 'years'))
month = Unit(name='month', dimension=TIME, aliases=('mo', 'months'))
fortnight = Unit(name='fortnight', dimension=TIME, aliases=('fn', 'fortnights'))
shake = Unit(name='shake', dimension=TIME, aliases=('shakes',))
# ----------------------------------------------------------------------


# -- Imperial / US Customary Units -------------------------------------
# Length
foot = Unit(name='foot', dimension=LENGTH, aliases=('ft', 'feet'))
inch = Unit(name='inch', dimension=LENGTH, aliases=('in', 'inches'))
yard = Unit(name='yard', dimension=LENGTH, aliases=('yd', 'yards'))
mile = Unit(name='mile', dimension=LENGTH, aliases=('mi', 'miles'))
nautical_mile = Unit(name='nautical_mile', dimension=LENGTH, aliases=('nmi', 'NM'))
fathom = Unit(name='fathom', dimension=LENGTH, aliases=('ftm', 'fathoms'))
furlong = Unit(name='furlong', dimension=LENGTH, aliases=('fur', 'furlongs'))
chain = Unit(name='chain', dimension=LENGTH, aliases=('ch', 'chains'))
rod = Unit(name='rod', dimension=LENGTH, aliases=('rd', 'rods', 'perch', 'pole'))
mil = Unit(name='mil', dimension=LENGTH, aliases=('thou',))
hand = Unit(name='hand', dimension=LENGTH, aliases=('hh', 'hands'))
league = Unit(name='league', dimension=LENGTH, aliases=('lea', 'leagues'))
cable = Unit(name='cable', dimension=LENGTH, aliases=('cables',))

# Mass
pound = Unit(name='pound', dimension=MASS, aliases=('lb', 'lbs'))
ounce = Unit(name='ounce', dimension=MASS, aliases=('oz', 'ounces'))
metric_ton = Unit(name='metric_ton', dimension=MASS, aliases=('t', 'tonne', 'tonnes'))
stone = Unit(name='stone', dimension=MASS, aliases=('st',))
grain = Unit(name='grain', dimension=MASS, aliases=('gr', 'grains'))
slug = Unit(name='slug', dimension=MASS, aliases=('slug',))
carat = Unit(name='carat', dimension=MASS, aliases=('ct_mass', 'carats'))
troy_ounce = Unit(name='troy_ounce', dimension=MASS, aliases=('ozt', 'troy_oz'))
long_ton = Unit(name='long_ton', dimension=MASS, aliases=('long_tons', 'imperial_ton'))
short_ton = Unit(name='short_ton', dimension=MASS, aliases=('short_tons', 'US_ton'))
dram = Unit(name='dram', dimension=MASS, aliases=('dr', 'drams'))
pennyweight = Unit(name='pennyweight', dimension=MASS, aliases=('dwt', 'pennyweights'))

# Temperature
fahrenheit = Unit(name='fahrenheit', dimension=TEMPERATURE, aliases=('°F', 'degF'))
rankine = Unit(name='rankine', dimension=TEMPERATURE, aliases=('°R', 'degR', 'R'))
reaumur = Unit(name='reaumur', dimension=TEMPERATURE, aliases=('°Ré', 'degRe'))

# Historical electrical
international_ampere = Unit(name='international_ampere', dimension=CURRENT, aliases=('A_int',))
international_volt = Unit(name='international_volt', dimension=VOLTAGE, aliases=('V_int',))
international_ohm = Unit(name='international_ohm', dimension=RESISTANCE, aliases=('ohm_int',))

# Volume
gallon = Unit(name='gallon', dimension=VOLUME, aliases=('gal', 'gallons'))
quart = Unit(name='quart', dimension=VOLUME, aliases=('qt', 'quarts'))
pint_volume = Unit(name='pint', dimension=VOLUME, aliases=('pt', 'pints'))
cup = Unit(name='cup', dimension=VOLUME, aliases=('cp', 'cups'))
fluid_ounce = Unit(name='fluid_ounce', dimension=VOLUME, aliases=('floz', 'fl_oz'))
tablespoon = Unit(name='tablespoon', dimension=VOLUME, aliases=('tbsp',))
teaspoon = Unit(name='teaspoon', dimension=VOLUME, aliases=('tsp',))
barrel = Unit(name='barrel', dimension=VOLUME, aliases=('bbl', 'barrels'))
imperial_gallon = Unit(name='imperial_gallon', dimension=VOLUME, aliases=('imp_gal',))
imperial_pint = Unit(name='imperial_pint', dimension=VOLUME, aliases=('imp_pt',))
bushel = Unit(name='bushel', dimension=VOLUME, aliases=('bu', 'bushels'))
peck = Unit(name='peck', dimension=VOLUME, aliases=('pk', 'pecks'))
gill = Unit(name='gill', dimension=VOLUME, aliases=('gi', 'gills'))
minim = Unit(name='minim', dimension=VOLUME, aliases=('min_vol', 'minims'))
cubic_foot = Unit(name='cubic_foot', dimension=VOLUME, aliases=('ft³', 'cu_ft'))
cubic_inch = Unit(name='cubic_inch', dimension=VOLUME, aliases=('in³', 'cu_in'))
cubic_yard = Unit(name='cubic_yard', dimension=VOLUME, aliases=('yd³', 'cu_yd'))
acre_foot = Unit(name='acre_foot', dimension=VOLUME, aliases=('ac_ft', 'acre_feet'))
stere = Unit(name='stere', dimension=VOLUME, aliases=('st_vol',))
imperial_quart = Unit(name='imperial_quart', dimension=VOLUME, aliases=('imp_qt',))
imperial_fluid_ounce = Unit(name='imperial_fluid_ounce', dimension=VOLUME, aliases=('imp_floz',))
imperial_gill = Unit(name='imperial_gill', dimension=VOLUME, aliases=('imp_gi',))
imperial_cup = Unit(name='imperial_cup', dimension=VOLUME, aliases=('imp_cup',))

# Energy
calorie = Unit(name='calorie', dimension=ENERGY, aliases=('cal', 'calories'))
btu = Unit(name='btu', dimension=ENERGY, aliases=('BTU',))
watt_hour = Unit(name='watt_hour', dimension=ENERGY, aliases=('Wh',))
therm = Unit(name='therm', dimension=ENERGY, aliases=('thm', 'therms'))
foot_pound = Unit(name='foot_pound', dimension=ENERGY, aliases=('ft_lb', 'ft_lbf'))
thermochemical_calorie = Unit(name='thermochemical_calorie', dimension=ENERGY, aliases=('cal_th',))
ton_tnt = Unit(name='ton_tnt', dimension=ENERGY, aliases=('tTNT',))
tonne_oil_equivalent = Unit(name='tonne_oil_equivalent', dimension=ENERGY, aliases=('toe',))

# Power
horsepower = Unit(name='horsepower', dimension=POWER, aliases=('hp',))
volt_ampere = Unit(name='volt_ampere', dimension=POWER, aliases=('VA',))
metric_horsepower = Unit(name='metric_horsepower', dimension=POWER, aliases=('PS',))
electrical_horsepower = Unit(name='electrical_horsepower', dimension=POWER, aliases=('hp_e',))
boiler_horsepower = Unit(name='boiler_horsepower', dimension=POWER, aliases=('hp_boiler',))
refrigeration_ton = Unit(name='refrigeration_ton', dimension=POWER, aliases=('TR', 'ton_ref'))

# Pressure
bar = Unit(name='bar', dimension=PRESSURE, aliases=('bar',))
psi = Unit(name='psi', dimension=PRESSURE, aliases=('psi', 'lbf/in²'))
atmosphere = Unit(name='atmosphere', dimension=PRESSURE, aliases=('atm',))
torr = Unit(name='torr', dimension=PRESSURE, aliases=('Torr',))
millimeter_mercury = Unit(name='millimeter_mercury', dimension=PRESSURE, aliases=('mmHg',))
inch_mercury = Unit(name='inch_mercury', dimension=PRESSURE, aliases=('inHg',))
centimeter_water = Unit(name='centimeter_water', dimension=PRESSURE, aliases=('cmH2O', 'cmAq'))
centimeter_mercury = Unit(name='centimeter_mercury', dimension=PRESSURE, aliases=('cmHg',))
ksi = Unit(name='ksi', dimension=PRESSURE, aliases=('ksi',))
technical_atmosphere = Unit(name='technical_atmosphere', dimension=PRESSURE, aliases=('at',))
millimeter_water = Unit(name='millimeter_water', dimension=PRESSURE, aliases=('mmH2O', 'mmAq'))
inch_water = Unit(name='inch_water', dimension=PRESSURE, aliases=('inH2O', 'inAq'))

# Force
pound_force = Unit(name='pound_force', dimension=FORCE, aliases=('lbf',))
kilogram_force = Unit(name='kilogram_force', dimension=FORCE, aliases=('kgf',))
kip = Unit(name='kip', dimension=FORCE, aliases=('klbf',))
poundal = Unit(name='poundal', dimension=FORCE, aliases=('pdl',))
gram_force = Unit(name='gram_force', dimension=FORCE, aliases=('gf',))
ounce_force = Unit(name='ounce_force', dimension=FORCE, aliases=('ozf',))
ton_force = Unit(name='ton_force', dimension=FORCE, aliases=('tnf', 'short_ton_force'))
metric_ton_force = Unit(name='metric_ton_force', dimension=FORCE, aliases=('tf', 'tonne_force'))
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
angstrom = Unit(name='angstrom', dimension=LENGTH, aliases=('Å', 'angstroms'))
light_year = Unit(name='light_year', dimension=LENGTH, aliases=('ly', 'light_years'))
parsec = Unit(name='parsec', dimension=LENGTH, aliases=('pc', 'parsecs'))
astronomical_unit = Unit(name='astronomical_unit', dimension=LENGTH, aliases=('au', 'AU'))

# Mass
dalton = Unit(name='dalton', dimension=MASS, aliases=('Da', 'u', 'amu'))

# Area
barn = Unit(name='barn', dimension=AREA, aliases=('b_area',))

# Charge
ampere_hour = Unit(name='ampere_hour', dimension=CHARGE, aliases=('Ah',))


# Radiation
curie = Unit(name='curie', dimension=FREQUENCY, aliases=('Ci',))
rem = Unit(name='rem', dimension=ENERGY, aliases=('rem',))
rad_dose = Unit(name='rad_dose', dimension=ENERGY, aliases=('rad_absorbed',))
roentgen = Unit(name='roentgen', dimension=EXPOSURE, aliases=('R_exp',))


# Catalytic activity
enzyme_unit = Unit(name='enzyme_unit', dimension=CATALYTIC_ACTIVITY, aliases=('U', 'IU'))

# Typography
point_typo = Unit(name='point', dimension=LENGTH, aliases=('pt_typo',))
pica = Unit(name='pica', dimension=LENGTH, aliases=('pica',))

# Textile (linear density)
tex = Unit(name='tex', dimension=LINEAR_DENSITY, aliases=('tex',))
denier = Unit(name='denier', dimension=LINEAR_DENSITY, aliases=('den', 'D_tex'))

# Photometry
foot_candle = Unit(name='foot_candle', dimension=ILLUMINANCE, aliases=('fc', 'ftc'))
phot = Unit(name='phot', dimension=ILLUMINANCE, aliases=('ph',))

# Viscosity
reyn = Unit(name='reyn', dimension=DYNAMIC_VISCOSITY, aliases=('reyn',))

# Spectroscopy / Radiation (SI-basis)
jansky = Unit(name='jansky', dimension=RADIANT_EXPOSURE, aliases=('Jy',))

# Acceleration
galileo = Unit(name='galileo', dimension=CGS_ACCELERATION, aliases=('Gal',))
standard_gravity = Unit(name='standard_gravity', dimension=ACCELERATION, aliases=('g0', 'gn'))

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


_populate_registry()

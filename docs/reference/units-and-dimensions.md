# Units & Dimensions

Complete reference of built-in units grouped by physical dimension.

---

## Base Dimensions

These are the fundamental SI base dimensions.

### Length

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| meter | m | m | Yes |
| foot | ft | ft, feet | No |
| inch | in | in, inches | No |
| yard | yd | yd, yards | No |
| mile | mi | mi, miles | No |

### Mass

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| gram | g | g | Yes |
| kilogram | kg | kg | No |
| pound | lb | lb, lbs | No |
| ounce | oz | oz, ounces | No |

### Time

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| second | s | s, sec | Yes |
| minute | min | min | No |
| hour | h | h, hr | No |
| day | d | d | No |

### Temperature

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| kelvin | K | K | Yes |
| celsius | degC | degC | No |
| fahrenheit | degF | degF | No |
| rankine | degR | degR, R | No |

### Electric Current

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| ampere | A | A, I, amp | Yes |

### Amount of Substance

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| mole | mol | mol, n | Yes |

### Luminous Intensity

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| candela | cd | cd | Yes |
| lumen | lm | lm | Yes |

### Information

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| bit | b | b, bits | Yes |
| byte | B | B, bytes | Yes |

---

## Derived Dimensions

### Force

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| newton | N | N | Yes |
| pound_force | lbf | lbf | No |
| kilogram_force | kgf | kgf | No |
| dyne | dyn | dyn | No |

### Energy

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| joule | J | J | Yes |
| calorie | cal | cal, calories | No |
| btu | BTU | BTU | No |
| watt_hour | Wh | Wh | No |
| gray | Gy | Gy | Yes |
| sievert | Sv | Sv | Yes |

### Power

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| watt | W | W | Yes |
| horsepower | hp | hp | No |

### Pressure

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| pascal | Pa | Pa | Yes |
| bar | bar | bar | No |
| psi | psi | psi, lbf/in | No |
| atmosphere | atm | atm | No |
| torr | Torr | Torr | No |
| millimeter_mercury | mmHg | mmHg | No |
| inch_mercury | inHg | inHg | No |

### Volume

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| liter | L | L, l | Yes |
| gallon | gal | gal, gallons | No |

### Frequency

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| hertz | Hz | Hz | Yes |
| becquerel | Bq | Bq | Yes |

### Electrical

| Unit | Shorthand | Aliases | Dimension | Scalable |
|------|-----------|---------|-----------|----------|
| volt | V | V | voltage | Yes |
| ohm | ohm | ohm | resistance | Yes |
| farad | F | F | capacitance | Yes |
| coulomb | C | C | charge | Yes |
| siemens | S | S | conductance | Yes |
| henry | H | H | inductance | Yes |
| weber | Wb | Wb | magnetic_flux | Yes |
| tesla | T | T | magnetic_flux_density | Yes |

### Illuminance

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| lux | lx | lx | Yes |

### Catalytic Activity

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| katal | kat | kat | Yes |

### Entropy

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| joule_per_kelvin | J/K | J/K | No |

### Viscosity

| Unit | Shorthand | Aliases | Dimension | Scalable |
|------|-----------|---------|-----------|----------|
| poise | P | P | dynamic_viscosity | No |
| stokes | St | St | kinematic_viscosity | No |

---

## Pseudo-Dimensions

These share a zero-vector but are semantically distinct.

### Angle

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| radian | rad | rad | No |
| degree | deg | deg | No |
| gradian | grad | grad, gon | No |
| arcminute | arcmin | arcmin, ' | No |
| arcsecond | arcsec | arcsec, " | No |
| turn | rev | rev, revolution | No |

### Solid Angle

| Unit | Shorthand | Aliases | Scalable |
|------|-----------|---------|----------|
| steradian | sr | sr | No |
| square_degree | sq_deg | sq_deg | No |

### Ratio (Dimensionless)

| Unit | Shorthand | Aliases | Notes |
|------|-----------|---------|-------|
| fraction | frac | frac, 1 | 0.0 to 1.0 |
| percent | % | % | 0.0 to 100.0 |
| permille | permille | permille | Parts per thousand |
| ppm | ppm | - | Parts per million |
| ppb | ppb | - | Parts per billion |
| basis_point | bp | bp, bps | 1 bp = 0.01% |
| nines | 9s | 9s | Reliability notation |

### Count

| Unit | Shorthand | Aliases | Notes |
|------|-----------|---------|-------|
| each | ea | ea, item, ct | Discrete items |

---

## Logarithmic Units

Units that use logarithmic scales for representing ratios or absolute values relative to a reference.

### Pure Ratio (Dimensionless)

These express power or amplitude ratios without a fixed reference level.

| Unit | Shorthand | Aliases | Formula | Notes |
|------|-----------|---------|---------|-------|
| bel | - | - | log₁₀(ratio) | Rarely used directly |
| decibel | dB | dB | 10·log₁₀(ratio) | 1 bel = 10 dB |
| neper | Np | Np | ln(ratio) | Natural log scale |

```python
from ucon import units

# Power ratio to decibels
ratio = units.fraction(100)
db = ratio.to(units.decibel)  # <20.0 dB>

# Amplitude ratio to nepers
import math
ratio = units.fraction(math.e ** 2)
np = ratio.to(units.neper)  # <2.0 Np>
```

### Reference-Level Units

These express absolute values on a logarithmic scale relative to a defined reference.

| Unit | Shorthand | Dimension | Reference | Formula |
|------|-----------|-----------|-----------|---------|
| decibel_milliwatt | dBm | power | 1 mW | 10·log₁₀(P / 1 mW) |
| decibel_watt | dBW | power | 1 W | 10·log₁₀(P / 1 W) |
| decibel_volt | dBV | voltage | 1 V | 20·log₁₀(V / 1 V) |
| decibel_spl | dBSPL | pressure | 20 µPa | 20·log₁₀(P / 20 µPa) |

```python
from ucon import units

# Power to dBm
power = units.watt(1.0)
dbm = power.to(units.decibel_milliwatt)  # <30.0 dBm>

# dBm back to watts
dbm = units.decibel_milliwatt(0.0)
power = dbm.to(units.watt)  # <0.001 W> (1 mW)

# Voltage to dBV
voltage = units.volt(10.0)
dbv = voltage.to(units.decibel_volt)  # <20.0 dBV>

# Sound pressure to dBSPL
pressure = units.pascal(1.0)
dbspl = pressure.to(units.decibel_spl)  # <~94 dBSPL>
```

### Chemistry

| Unit | Shorthand | Dimension | Reference | Formula |
|------|-----------|-----------|-----------|---------|
| pH | pH | concentration | 1 mol/L | -log₁₀([H⁺] / 1 mol/L) |

pH measures hydrogen ion concentration on a logarithmic scale. It has concentration dimension (`amount_of_substance / volume`), enabling direct conversion with mol/L.

```python
from ucon import units

# Concentration to pH
mol_per_liter = units.mole / units.liter
conc = mol_per_liter(1e-7)
ph = conc.to(units.pH)  # <7.0 pH> (neutral)

# pH to concentration
ph = units.pH(4.0)
conc = ph.to(mol_per_liter)  # <1e-4 mol/L> (acidic)

# Common pH values
mol_per_liter(1e-1).to(units.pH)   # <1.0 pH>  (strong acid)
mol_per_liter(1e-7).to(units.pH)   # <7.0 pH>  (neutral)
mol_per_liter(1e-14).to(units.pH)  # <14.0 pH> (strong base)
```

---

## Priority Aliases

Some aliases take precedence to prevent ambiguous parses:

| Alias | Resolves To | Reason |
|-------|-------------|--------|
| `min` | minute | Not milli-inch |
| `mcg` | microgram | Medical convention |
| `cc` | milliliter | Cubic centimeter = 1 mL |

---

## Creating Custom Units

For units not in the built-in set, create them with `Unit`:

### Python API

```python
from ucon.core import Unit, Dimension

# Define a custom unit
drop = Unit(
    name="drop",
    dimension=Dimension.count,
    aliases=("gtt", "drop")
)

# Use immediately
drops = drop(15)  # <15 gtt>
```

### With ConversionGraph

To enable conversions with custom units, register them in a graph:

```python
from ucon import get_default_graph
from ucon.core import Unit, Dimension
from ucon.maps import LinearMap

# Create custom unit
slug = Unit(name="slug", dimension=Dimension.mass, aliases=("slug",))

# Get graph and register
graph = get_default_graph().copy()
graph.register_unit(slug)

# Add conversion edge
from ucon import units
graph.add_edge(slug, units.kilogram, LinearMap(14.5939))

# Now conversions work
from ucon.graph import using_graph
with using_graph(graph):
    mass = slug(1).to(units.kilogram)  # <14.5939 kg>
```

### Via MCP Server

```python
# Register unit for session
define_unit(name="slug", dimension="mass", aliases=["slug"])

# Add conversion edge
define_conversion(src="slug", dst="kg", factor=14.5939)

# Use in conversions
convert(value=1, from_unit="slug", to_unit="lb")
```

### Common Custom Units

| Domain | Unit | Dimension | Aliases |
|--------|------|-----------|---------|
| Medical | drop | count | gtt |
| Aerospace | slug | mass | slug |
| Maritime | nautical_mile | length | nmi, NM |
| Energy | therm | energy | therm |
| Nuclear | curie | frequency | Ci |

---

## All Dimensions

| | | | |
|-------------------------|-------------------------|-------------------------|-------------------------|
| acceleration            | dynamic_viscosity       | luminous_intensity      | ratio                   |
| angle                   | electric_field_strength | magnetic_flux           | resistance              |
| angular_momentum        | energy                  | magnetic_flux_density   | resistivity             |
| area                    | entropy                 | magnetic_permeability   | solid_angle             |
| capacitance             | force                   | mass                    | specific_heat_capacity  |
| catalytic_activity      | frequency               | molar_mass              | temperature             |
| charge                  | gravitation             | molar_volume            | thermal_conductivity    |
| conductance             | illuminance             | momentum                | time                    |
| conductivity            | inductance              | none                    | velocity                |
| count                   | information             | permittivity            | voltage                 |
| current                 | kinematic_viscosity     | power                   | volume                  |
| density                 | length                  | pressure                |                         |

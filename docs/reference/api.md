# API Reference

Core Python API for ucon.

---

## parse

Parse human-readable quantity strings into Number objects.

```python
from ucon import parse
```

### Basic Usage

```python
# Simple quantities
parse("60 mi/h")           # <60 mi/h>
parse("9.81 m/s^2")        # <9.81 m/s²>
parse("1.5 kg")            # <1.5 kg>

# Pure numbers (dimensionless)
parse("100")               # <100>
parse("3.14159")           # <3.14159>

# Scientific notation
parse("1.5e3 m")           # <1500 m>
parse("6.022e23")          # <6.022e23>

# Negative values
parse("-273.15 degC")      # <-273.15 °C>
```

### Uncertainty

```python
# Plus-minus notation
parse("1.234 ± 0.005 m")   # <1.234 ± 0.005 m>
parse("1.234 +/- 0.005 m") # ASCII alternative

# Parenthetical (metrology convention)
parse("1.234(5) m")        # means 1.234 ± 0.005
parse("1.234(56) m")       # means 1.234 ± 0.056

# Uncertainty with unit
parse("1.234 m ± 0.005 m") # <1.234 ± 0.005 m>
```

### Error Handling

```python
from ucon.parsing import ParseError

# Unknown unit
parse("60 foobar")         # raises UnknownUnitError

# Invalid number
parse("abc m")             # raises ParseError (subclass of ValueError)

# Empty string
parse("")                  # raises ValueError
```

### ParseError

Raised when a quantity string cannot be parsed. Subclass of `ValueError`.

```python
from ucon.parsing import ParseError

try:
    parse("abc m")
except ParseError as e:
    print(e)  # parse error details
```

---

## Number

The primary type for representing dimensional quantities.

```python
from ucon import Number, units, Scale
```

### Creating Numbers

```python
# Via unit callable
distance = units.meter(5)           # <5 m>
mass = units.gram(250)              # <250 g>

# With scale prefix
km = Scale.kilo * units.meter
mg = Scale.milli * units.gram
d = km(10)                          # <10 km>
dose = mg(500)                      # <500 mg>

# Directly
n = Number(quantity=9.8, unit=units.meter / units.second ** 2)
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `quantity` | float | The numeric magnitude |
| `unit` | Unit \| UnitProduct | The unit of measurement |
| `dimension` | Dimension | Physical dimension |
| `uncertainty` | float \| None | Optional uncertainty value |

### Methods

#### `to(target, graph=None, propagate_factor_uncertainty=False)`

Convert to a different unit.

```python
d = units.meter(1000)
d.to(Scale.kilo * units.meter)  # <1.0 km>

weight = units.pound(154)
weight.to(Scale.kilo * units.gram)  # <69.85... kg>
```

When `propagate_factor_uncertainty=True`, the uncertainty of the conversion
factor itself (from measured physical constants like Eₕ, mₚ, a₀) is
included in the result via GUM quadrature:

```python
# Exact conversion — no uncertainty even with flag
units.meter(1).to(units.foot, propagate_factor_uncertainty=True)
# <3.28084 ft>  (meter→foot is exact by definition)

# Measured conversion — factor uncertainty propagated
units.joule(1).to(units.hartree, propagate_factor_uncertainty=True)
# <2.2937e17 ± ~2.5e5 Eh>  (reflects Hartree energy uncertainty)

# Combined with measurement uncertainty
n = Number(quantity=1.0, unit=units.joule, uncertainty=1e-10)
n.to(units.hartree, propagate_factor_uncertainty=True)
# Both measurement and factor uncertainties combined in quadrature
```

The default `False` preserves backward compatibility — only measurement
uncertainty (from `Number.uncertainty`) is propagated through `Map.derivative()`.

#### `simplify()`

Express in base scale (no prefix).

```python
d = (Scale.kilo * units.meter)(5)
d.simplify()  # <5000 m>
```

### Arithmetic

Numbers support arithmetic with dimensional consistency:

```python
# Addition/subtraction (same dimension required)
a = units.meter(10)
b = units.meter(5)
a + b  # <15 m>
a - b  # <5 m>

# Multiplication/division (dimensions combine)
distance = units.meter(100)
time = units.second(10)
velocity = distance / time  # <10.0 m/s>

# Scalar multiplication
dose = units.gram(5)
dose * 3  # <15 g>
```

---

## Unit

Atomic representation of a base or derived unit.

```python
from ucon.core import Unit, Dimension
```

### Predefined Units

```python
from ucon import units

units.meter      # length
units.gram       # mass
units.second     # time
units.ampere     # current
units.kelvin     # temperature
units.mole       # amount of substance
units.candela    # luminous intensity
units.newton     # force
units.joule      # energy
units.watt       # power
# ... see Units & Dimensions reference
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | str | Canonical name |
| `shorthand` | str | Primary symbol |
| `aliases` | tuple[str] | Alternative symbols |
| `dimension` | Dimension | Physical dimension |
| `basis` | Basis | Dimensional basis (e.g., SI, CGS) |

### Methods

#### `is_compatible(other, basis_graph=None)`

Check if conversion to another unit is possible.

```python
# Same dimension — always compatible
units.meter.is_compatible(units.foot)  # True

# Different dimensions — incompatible
units.meter.is_compatible(units.second)  # False

# Cross-basis — requires BasisGraph
from ucon.basis import BasisGraph
from ucon.basis.transforms import SI_TO_CGS_ESU

bg = BasisGraph().with_transform(SI_TO_CGS_ESU)
units.ampere.is_compatible(statampere, basis_graph=bg)  # True
```

### Creating Custom Units

```python
from ucon.core import Unit, Dimension

drop = Unit(
    name="drop",
    dimension=Dimension.count,
    aliases=("gtt", "drop")
)
```

---

## Scale

SI and binary scale prefixes.

```python
from ucon import Scale
```

### Available Scales

| Scale | Prefix | Factor |
|-------|--------|--------|
| `Scale.peta` | P | 10^15 |
| `Scale.tera` | T | 10^12 |
| `Scale.giga` | G | 10^9 |
| `Scale.mega` | M | 10^6 |
| `Scale.kilo` | k | 10^3 |
| `Scale.hecto` | h | 10^2 |
| `Scale.deca` | da | 10^1 |
| `Scale.one` | - | 10^0 |
| `Scale.deci` | d | 10^-1 |
| `Scale.centi` | c | 10^-2 |
| `Scale.milli` | m | 10^-3 |
| `Scale.micro` | u | 10^-6 |
| `Scale.nano` | n | 10^-9 |
| `Scale.pico` | p | 10^-12 |
| `Scale.femto` | f | 10^-15 |
| `Scale.gibi` | Gi | 2^30 |
| `Scale.mebi` | Mi | 2^20 |
| `Scale.kibi` | Ki | 2^10 |

### Usage

```python
# Apply to unit
km = Scale.kilo * units.meter
mg = Scale.milli * units.gram
GiB = Scale.gibi * units.byte

# Scale composition
Scale.kilo * Scale.milli  # → Scale.one
```

---

## Dimension

Physical dimension enumeration.

```python
from ucon import Dimension
```

### Base Dimensions

```python
Dimension.length
Dimension.mass
Dimension.time
Dimension.current
Dimension.temperature
Dimension.luminous_intensity
Dimension.amount_of_substance
Dimension.information
```

### Derived Dimensions

```python
Dimension.velocity      # length / time
Dimension.acceleration  # length / time^2
Dimension.force         # mass * length / time^2
Dimension.energy        # mass * length^2 / time^2
Dimension.power         # energy / time
Dimension.pressure      # force / area
# ... see Units & Dimensions reference
```

### Pseudo-Dimensions

```python
Dimension.angle       # radian, degree
Dimension.solid_angle # steradian
Dimension.ratio       # percent, ppm
Dimension.count       # discrete items
```

### Arithmetic

```python
Dimension.length / Dimension.time      # velocity
Dimension.mass * Dimension.acceleration  # force
Dimension.energy ** 0.5                # sqrt(energy)
```

---

## Constant

Physical constants with CODATA 2022 uncertainties.

```python
from ucon import constants
from ucon.constants import Constant, c, h, G
```

### Built-in Constants

**SI Defining Constants (exact):**

| Constant | Symbol | Value | Unit |
|----------|--------|-------|------|
| `speed_of_light` | c | 299792458 | m/s |
| `planck_constant` | h | 6.62607015e-34 | J·s |
| `elementary_charge` | e | 1.602176634e-19 | C |
| `boltzmann_constant` | k_B | 1.380649e-23 | J/K |
| `avogadro_constant` | N_A | 6.02214076e23 | 1/mol |
| `luminous_efficacy` | K_cd | 683 | lm/W |
| `hyperfine_transition_frequency` | ΔνCs | 9192631770 | Hz |

**Derived Constants (exact):**

| Constant | Symbol | Derivation |
|----------|--------|------------|
| `reduced_planck_constant` | ℏ | h / 2π |
| `molar_gas_constant` | R | k_B × N_A |
| `stefan_boltzmann_constant` | σ | (derived) |

**Measured Constants (with uncertainty):**

| Constant | Symbol | Uncertainty |
|----------|--------|-------------|
| `gravitational_constant` | G | 1.5e-15 |
| `fine_structure_constant` | α | 1.1e-12 |
| `electron_mass` | m_e | 2.8e-40 |
| `proton_mass` | m_p | 5.1e-37 |
| `neutron_mass` | m_n | 9.5e-37 |
| `vacuum_permittivity` | ε₀ | 1.3e-21 |
| `vacuum_permeability` | μ₀ | 1.9e-16 |

### Usage

```python
from ucon import constants, units

# Access by name
c = constants.speed_of_light
c.value        # 299792458
c.unit         # m/s
c.is_exact     # True
c.category     # "exact"

# Access by symbol (Unicode or ASCII)
constants.c    # speed_of_light
constants.h    # planck_constant
constants.G    # gravitational_constant
constants.hbar # reduced_planck_constant (ASCII)
constants.ℏ    # reduced_planck_constant (Unicode)

# Arithmetic with constants (returns Number)
mass = units.kilogram(1)
energy = mass * c ** 2  # E = mc²
energy.quantity  # ~8.99e16
energy.dimension # energy

# Measured constants propagate uncertainty
F = G * mass * mass / units.meter(1) ** 2
F.uncertainty is not None  # True
```

### Enumeration

```python
from ucon.constants import all_constants, get_constant_by_symbol

# List all constants
for const in all_constants():
    print(f"{const.symbol}: {const.name}")

# Lookup by symbol
c = get_constant_by_symbol("c")     # speed_of_light
h = get_constant_by_symbol("hbar")  # reduced_planck_constant
```

### Constant Properties

| Property | Type | Description |
|----------|------|-------------|
| `symbol` | str | Standard symbol (e.g., "c", "h") |
| `name` | str | Full name (e.g., "speed of light in vacuum") |
| `value` | float | Numeric value in SI units |
| `unit` | Unit \| UnitProduct | SI unit of the constant |
| `uncertainty` | float \| None | Standard uncertainty (None if exact) |
| `source` | str | Data source (default: "CODATA 2022") |
| `category` | str | "exact", "derived", "measured", or "session" |
| `is_exact` | bool | True if uncertainty is None |
| `dimension` | Dimension | Physical dimension |

### Methods

#### `as_number()`

Convert to a Number for calculations.

```python
c_num = c.as_number()
type(c_num)  # Number
```

### Creating Custom Constants

```python
from ucon.constants import Constant
from ucon import units

# Domain-specific constant
custom_k = Constant(
    symbol="k_custom",
    name="custom spring constant",
    value=250.0,
    unit=units.newton / units.meter,
    uncertainty=0.5,  # or None for exact
    source="Lab measurement",
    category="session",
)

# Use in calculations
x = units.meter(0.1)
F = custom_k.as_number() * x  # Hooke's law
```

---

## ConversionGraph

Registry of conversion edges between units.

```python
from ucon import get_default_graph
from ucon.graph import ConversionGraph
```

### Default Graph

```python
graph = get_default_graph()
```

### Custom Graph

```python
from ucon.graph import ConversionGraph
from ucon.maps import LinearMap

graph = ConversionGraph()

# Register a unit
graph.register_unit(custom_unit)

# Add conversion edge
graph.add_edge(
    src=units.foot,
    dst=units.meter,
    map=LinearMap(0.3048)
)

# Convert
result = graph.convert(units.foot, units.meter)
result(12)  # 3.6576
```

### Cross-Basis Edges

For units in different dimensional bases, use `basis_transform`:

```python
from ucon.basis.transforms import SI_TO_CGS_ESU

graph.add_edge(
    src=units.ampere,
    dst=statampere,
    map=LinearMap(2.998e9),
    basis_transform=SI_TO_CGS_ESU,
)
```

Bulk registration with `connect_systems()`:

```python
graph.connect_systems(
    basis_transform=SI_TO_CGS,
    edges={
        (units.meter, centimeter_cgs): LinearMap(100),
        (units.gram, gram_cgs): LinearMap(1),
    },
)
```

### Introspection

```python
# List rebased units (cross-basis bridges)
graph.list_rebased_units()  # {ampere: [RebasedUnit(...), ...], ...}

# List registered transforms
graph.list_transforms()  # [SI_TO_CGS_ESU, ...]
```

### Context Manager

```python
from ucon.graph import using_conversion_graph

with using_conversion_graph(my_graph):
    # Unit parsing uses my_graph for resolution
    value = convert(1, "custom_unit", "kg")
```

---

## ConversionContext

Scoped cross-dimensional conversions for physical relationships that connect different dimensions (e.g., wavelength and frequency).

```python
from ucon.contexts import ConversionContext, ContextEdge, using_context
from ucon.contexts import spectroscopy, boltzmann
```

### Built-in Contexts

| Context | Edges | Physical Laws |
|---------|-------|---------------|
| `spectroscopy` | meter↔hertz, hertz→joule, meter→joule, joule→reciprocal_meter | f=c/λ, E=hf, E=hc/λ, k=E/(hc) |
| `boltzmann` | kelvin→joule | E=k_B·T |

### Usage

```python
from ucon import units
from ucon.contexts import spectroscopy, boltzmann, using_context

# Spectroscopy: wavelength to frequency
with using_context(spectroscopy):
    result = units.meter(500e-9).to(units.hertz)
    print(f"{result.quantity:.3e} Hz")  # 5.996e+14 Hz

    # Energy from frequency
    result = units.hertz(5e14).to(units.joule)
    print(f"{result.quantity:.3e} J")   # 3.313e-19 J

# Boltzmann: temperature to energy
with using_context(boltzmann):
    result = units.kelvin(300).to(units.joule)
    print(f"{result.quantity:.3e} J")   # 4.142e-21 J

# Multiple contexts
with using_context(spectroscopy, boltzmann):
    # Both spectroscopy and Boltzmann edges available
    pass
```

Cross-dimensional conversions only work inside `using_context()` blocks. Outside the block, `DimensionMismatch` is raised as expected.

### Custom Contexts

```python
from ucon.contexts import ConversionContext, ContextEdge
from ucon.maps import LinearMap

my_context = ConversionContext(
    name="custom",
    edges=(
        ContextEdge(
            src=units.kelvin,
            dst=units.joule,
            map=LinearMap(1.380649e-23),
        ),
    ),
    description="Custom thermal context.",
)

with using_context(my_context):
    result = units.kelvin(300).to(units.joule)
```

---

## Maps

Composable conversion morphisms used as edges in the ConversionGraph.

```python
from ucon.maps import Map, LinearMap, AffineMap, LogMap, ExpMap, ReciprocalMap, ComposedMap
```

### Class Hierarchy

| Class | Formula | Use Case |
|-------|---------|----------|
| `LinearMap(a, rel_uncertainty=0.0)` | y = a * x | Most unit conversions (m -> ft, kg -> lb) |
| `AffineMap(a, b, rel_uncertainty=0.0)` | y = a * x + b | Temperature conversions (C -> F) |
| `ReciprocalMap(a, rel_uncertainty=0.0)` | y = a / x | Inversely proportional (wavelength -> frequency) |
| `LogMap(scale, base, reference)` | y = scale * log(x/ref) + offset | Decibels, pH |
| `ExpMap(scale, base, reference)` | y = ref * base^(scale*x + offset) | Inverse of LogMap |
| `ComposedMap(outer, inner)` | y = outer(inner(x)) | Heterogeneous composition fallback |

All maps are `@dataclass(frozen=True)` --- immutable and hashable.

### Factor Uncertainty

Maps carry an optional `rel_uncertainty` field (relative uncertainty of the
conversion factor). This is `0.0` for exact conversions and nonzero for
edges derived from measured physical constants (e.g., Hartree energy,
Planck mass).

```python
# Exact conversion factor
m_to_ft = LinearMap(3.28084)
m_to_ft.rel_uncertainty  # 0.0

# Factor from a measured constant
j_to_hartree = LinearMap(2.2937e17, rel_uncertainty=1.1e-12)
j_to_hartree.rel_uncertainty  # 1.1e-12
```

Uncertainty composes through the standard operations:

- **Composition** (`f @ g`): `sqrt(f.rel_uncertainty**2 + g.rel_uncertainty**2)`
- **Inverse**: preserved (inversion doesn't change relative uncertainty)
- **Power** (`f ** n`): `abs(n) * f.rel_uncertainty`

`ComposedMap` computes `rel_uncertainty` as a property from its inner and
outer maps. `LogMap` and `ExpMap` inherit the default `0.0` from the ABC
(they represent definitional transforms, not measured factors).

### Creating Maps

```python
from ucon.maps import LinearMap, AffineMap, ReciprocalMap, LogMap

# Linear: meters to feet
m_to_ft = LinearMap(3.28084)
m_to_ft(1.0)  # 3.28084

# Affine: Celsius to Fahrenheit
c_to_f = AffineMap(1.8, 32)
c_to_f(100)  # 212.0

# Reciprocal: wavelength to frequency (f = c / λ)
c = 299792458.0
lambda_to_freq = ReciprocalMap(c)
lambda_to_freq(500e-9)  # ~5.996e14 Hz

# Logarithmic: watts to dBm
w_to_dbm = LogMap(scale=10, reference=0.001)
w_to_dbm(1.0)  # 30.0 (1 W = 30 dBm)

# pH: concentration to pH
conc_to_ph = LogMap(scale=-1)
conc_to_ph(1e-7)  # 7.0
```

### Inverse

Every map has an `inverse()` that returns the reverse conversion:

```python
ft_to_m = m_to_ft.inverse()
ft_to_m(3.28084)  # ~1.0

f_to_c = c_to_f.inverse()
f_to_c(212)  # 100.0

# ReciprocalMap is self-inverse: if f = c/λ, then λ = c/f
freq_to_lambda = lambda_to_freq.inverse()
freq_to_lambda(5.996e14)  # ~500e-9 (back to 500 nm)

dbm_to_w = w_to_dbm.inverse()  # returns ExpMap
dbm_to_w(30)  # 1.0
```

### Composition

Maps compose via `@` (outer @ inner = apply inner first, then outer):

```python
# Chain: meters -> feet -> inches
m_to_ft = LinearMap(3.28084)
ft_to_in = LinearMap(12)
m_to_in = ft_to_in @ m_to_ft
m_to_in(1.0)  # ~39.37

# Linear @ Linear stays Linear
isinstance(m_to_in, LinearMap)  # True

# Mixed types fall back to ComposedMap
mixed = LogMap(scale=10) @ AffineMap(1, 5)
isinstance(mixed, ComposedMap)  # True
```

### Derivative (Uncertainty Propagation)

Maps provide `derivative(x)` for uncertainty propagation: `delta_y = |f'(x)| * delta_x`.

```python
m = LinearMap(3.28084)
m.derivative(1.0)  # 3.28084 (constant for linear)

log_m = LogMap(scale=10)
log_m.derivative(100)  # 10 / (100 * ln(10)) ≈ 0.0434
```

### Worked Example: ReciprocalMap in Spectroscopy

`ReciprocalMap` models inversely proportional physical relationships
where `y = constant / x`. The canonical example is the wavelength–frequency
relation `f = c / λ`.

```python
from ucon.maps import ReciprocalMap, LinearMap

c = 299792458.0   # speed of light (m/s)
h = 6.62607015e-34  # Planck constant (J·s)

# Wavelength (m) → frequency (Hz): f = c / λ
wl_to_freq = ReciprocalMap(c)

# Green light at 532 nm (Nd:YAG laser second harmonic)
freq = wl_to_freq(532e-9)       # 5.635e14 Hz

# Self-inverse: frequency → wavelength uses the same constant
freq_to_wl = wl_to_freq.inverse()
freq_to_wl(freq)                 # 532e-9 m (round-trips exactly)

# Chain with LinearMap for frequency → energy: E = h * f
freq_to_energy = LinearMap(h)
energy = freq_to_energy(freq)    # 3.734e-19 J (one green photon)

# Compose: wavelength → energy in one step via E = hc / λ
wl_to_energy = ReciprocalMap(c * h)
wl_to_energy(532e-9)             # 3.734e-19 J

# Uncertainty propagation: d/dx[a/x] = -a/x²
wl_to_freq.derivative(532e-9)    # -1.059e+21 Hz/m
```

These maps are what the built-in `spectroscopy` context uses internally.
For end-user conversions, prefer `using_context(spectroscopy)` over
constructing maps directly — see the
[Conversion Contexts](../guides/conversion-contexts.md) guide.

---

## Packages

Load domain-specific units and conversions from TOML files.

```python
from ucon.packages import load_package, UnitPackage, UnitDef, EdgeDef, PackageLoadError
```

### TOML Schema

```toml
[package]
name = "aerospace"
version = "1.0.0"
description = "Aerospace and aviation units"
requires = []  # Names of required packages

[[units]]
name = "slug"
dimension = "mass"
aliases = ["slug"]

[[units]]
name = "nautical_mile"
dimension = "length"
shorthand = "nmi"        # Explicit display symbol
aliases = ["NM"]

[[edges]]
src = "slug"
dst = "kilogram"
factor = 14.5939

[[edges]]
src = "nautical_mile"
dst = "meter"
factor = 1852
```

Edges support affine conversions for temperature-like units:

```toml
[[edges]]
src = "celsius"
dst = "fahrenheit"
factor = 1.8
offset = 32
```

Edges derived from measured constants can carry a relative uncertainty:

```toml
[[edges]]
src = "joule"
dst = "hartree"
factor = 2.2937e17
rel_uncertainty = 1.1e-12
```

For non-linear conversions, use the explicit `map` inline table with a
`type` key. Supported types: `linear`, `affine`, `log`, `reciprocal`.

```toml
# Logarithmic (e.g., decibels)
[[edges]]
src = "decibel_power"
dst = "ratio"
map = { type = "log", scale = 10, base = 10 }

# Reciprocal (e.g., wavelength ↔ frequency)
[[edges]]
src = "wavelength_unit"
dst = "frequency_unit"
map = { type = "reciprocal", a = 299792458.0 }
```

Constants can be defined for domain-specific values:

```toml
[[constants]]
symbol = "vs"
name = "speed of sound in dry air at 20C"
value = 343.0
unit = "m/s"
source = "ISA standard atmosphere"
category = "exact"
```

### Loading

```python
from ucon.packages import load_package
from ucon import get_default_graph

package = load_package("aerospace.ucon.toml")
print(package.name)       # "aerospace"
print(package.units)      # (UnitDef(...), ...)
print(package.edges)      # (EdgeDef(...), ...)
print(package.constants)  # (ConstantDef(...), ...)

# Apply to graph
graph = get_default_graph().with_package(package)

# Access materialized constants
for const in graph.package_constants:
    print(f"{const.symbol} = {const.value} {const.unit}")
```

### UnitDef, EdgeDef, and ConstantDef

```python
# UnitDef holds the declaration before materialization
for unit_def in package.units:
    print(unit_def.name)        # "slug"
    print(unit_def.dimension)   # "mass"
    print(unit_def.aliases)     # ("slug",)
    print(unit_def.shorthand)   # None or explicit symbol

# EdgeDef holds the conversion specification
for edge_def in package.edges:
    print(edge_def.src)               # "slug"
    print(edge_def.dst)               # "kilogram"
    print(edge_def.factor)            # 14.5939
    print(edge_def.offset)            # 0.0 (non-zero for affine)
    print(edge_def.rel_uncertainty)   # 0.0 (nonzero for measured factors)

# ConstantDef holds the constant specification
for const_def in package.constants:
    print(const_def.symbol)       # "vs"
    print(const_def.value)        # 343.0
    print(const_def.unit)         # "m/s"
    print(const_def.uncertainty)  # None or float
```

### Error Handling

```python
from ucon.packages import load_package, PackageLoadError

try:
    load_package("nonexistent.toml")
except PackageLoadError as e:
    print(e)  # file not found or invalid schema
```

---

## enforce_dimensions

Decorator for runtime dimension checking.

```python
from ucon import enforce_dimensions, Number, Dimension
```

### Usage

```python
@enforce_dimensions
def speed(
    distance: Number[Dimension.length],
    time: Number[Dimension.time],
) -> Number:
    return distance / time

# Valid
speed(units.meter(100), units.second(10))  # <10.0 m/s>

# Raises ValueError
speed(units.second(100), units.second(10))
# ValueError: distance: expected dimension 'length', got 'time'

# Raises TypeError
speed(100, units.second(10))
# TypeError: distance: expected Number, got int
```

---

## UnitProduct

Composite unit from multiplication/division of units.

```python
from ucon.core import UnitProduct, UnitFactor
```

### Creation

```python
# Via arithmetic
velocity = units.meter / units.second
acceleration = units.meter / units.second ** 2

# Via Scale
km = Scale.kilo * units.meter  # Returns UnitProduct

# Explicit
up = UnitProduct({
    UnitFactor(units.meter, Scale.one): 1,
    UnitFactor(units.second, Scale.one): -2,
})
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `factors` | dict[UnitFactor, float] | Factor-to-exponent mapping |
| `dimension` | Dimension | Combined dimension |
| `shorthand` | str | Formatted string (e.g., "m/s") |

---

## Exceptions

```python
from ucon.graph import (
    ConversionNotFound,
    DimensionMismatch,
    CyclicInconsistency,
)
from ucon.basis import (
    NoTransformPath,
    LossyProjection,
)
from ucon.units import UnknownUnitError
```

| Exception | When Raised |
|-----------|-------------|
| `ConversionNotFound` | No path between units in graph |
| `DimensionMismatch` | Operation on incompatible dimensions |
| `CyclicInconsistency` | Adding edge creates inconsistent cycle |
| `NoTransformPath` | No BasisTransform connects the two bases |
| `LossyProjection` | Dimension cannot be represented in target basis |
| `UnknownUnitError` | Unit string cannot be parsed |

---

## Basis System

For cross-basis conversions (e.g., SI ↔ CGS).

```python
from ucon.basis import Basis, BasisGraph, BasisTransform
from ucon.basis.builtin import SI, CGS, CGS_ESU
from ucon.basis.transforms import SI_TO_CGS, SI_TO_CGS_ESU, SI_TO_CGS_EMU
```

### Standard Bases

| Basis | Components | Description |
|-------|------------|-------------|
| `SI` | T, L, M, I, Θ, J, N, B | International System (8 dimensions) |
| `CGS` | L, M, T | Centimetre-gram-second (mechanical) |
| `CGS_ESU` | L, M, T, Q | CGS electrostatic (charge is fundamental) |

### Standard Transforms

| Transform | Source | Target | Notes |
|-----------|--------|--------|-------|
| `SI_TO_CGS` | SI | CGS | Mechanical dimensions (L, M, T) |
| `CGS_TO_SI` | CGS | SI | Inverse of SI_TO_CGS |
| `SI_TO_CGS_ESU` | SI | CGS_ESU | Current → L^(3/2)·M^(1/2)·T^(-2) |
| `SI_TO_CGS_EMU` | SI | CGS | Current → L^(1/2)·M^(1/2)·T^(-1) |
| `SI_TO_NATURAL` | SI | NATURAL | All dimensions → powers of energy |
| `NATURAL_TO_SI` | NATURAL | SI | Inverse with constant bindings |

### BasisGraph

Track connectivity between bases:

```python
from ucon.basis import BasisGraph
from ucon.basis.transforms import SI_TO_CGS_ESU

bg = BasisGraph()
bg = bg.with_transform(SI_TO_CGS_ESU)

bg.are_connected(SI, CGS_ESU)  # True
```

### BasisTransform

Matrix mapping dimension vectors between bases:

```python
from ucon.basis.transforms import SI_TO_CGS_ESU

# Transform a dimension vector
si_current = units.ampere.dimension.vector
cgs_current = SI_TO_CGS_ESU(si_current)
# Result: L^(3/2) M^(1/2) T^(-2) in CGS-ESU
```

See [Dual-Graph Architecture](../architecture/dual-graph-architecture.md) for details.

### Basis Context Scoping

Basis and BasisGraph are scoped through the active `UnitSystem`. Use `use()`
with a derived system to override them:

```python
from ucon import active_system, use, CGS, Dimension

# Override the active basis
cgs_system = active_system().with_basis(CGS)
with use(cgs_system):
    dim = Dimension.from_components(L=1, T=-1)
    dim.basis  # CGS
```

```python
from ucon import active_system, use
from ucon.basis import BasisGraph

# Override the active BasisGraph
custom_bg = BasisGraph()
custom_system = active_system().with_basis_graph(custom_bg)
with use(custom_system):
    # All operations see custom_bg
    pass
```

The active system's basis and basis graph are accessible via the `UnitSystem`
fields:

```python
system = active_system()
system.basis        # Current basis (SI by default)
system.basis_graph  # Current BasisGraph
```

---

## Natural Units

Support for natural units where physical constants c = h_bar = k_B = 1.

```python
from ucon import NATURAL, SI_TO_NATURAL, NATURAL_TO_SI
from ucon.basis import ConstantBinding, ConstantBoundBasisTransform
```

### NATURAL Basis

Single-dimensional basis where all quantities reduce to powers of energy:

```python
from ucon import NATURAL, BasisVector
from fractions import Fraction

# NATURAL has one component: energy (E)
len(NATURAL)  # 1
NATURAL[0].name  # "energy"
NATURAL[0].symbol  # "E"

# Create natural unit vectors
energy = BasisVector(NATURAL, (Fraction(1),))  # E^1
inverse_energy = BasisVector(NATURAL, (Fraction(-1),))  # E^-1
dimensionless = BasisVector(NATURAL, (Fraction(0),))  # E^0
```

### Dimension Mappings

With c = h_bar = k_B = 1:

| SI Dimension | Natural Units | Physical Meaning |
|--------------|---------------|------------------|
| Length (L) | E^-1 | L = h_bar*c / E |
| Time (T) | E^-1 | T = h_bar / E |
| Mass (M) | E | E = mc^2 |
| Temperature (Theta) | E | E = k_B * T |
| Velocity (L/T) | E^0 | Dimensionless (c=1) |
| Action (ML^2/T) | E^0 | Dimensionless (h_bar=1) |
| Energy (ML^2/T^2) | E | Energy is fundamental |

### SI_TO_NATURAL Transform

Transform SI dimensions to natural units:

```python
from ucon import SI, NATURAL, SI_TO_NATURAL, BasisVector
from fractions import Fraction

# Velocity: L^1 T^-1 in SI
si_velocity = BasisVector(SI, (
    Fraction(-1),  # T^-1
    Fraction(1),   # L^1
    Fraction(0), Fraction(0), Fraction(0),
    Fraction(0), Fraction(0), Fraction(0),
))

natural_velocity = SI_TO_NATURAL(si_velocity)
natural_velocity.is_dimensionless()  # True! (c = 1)

# Energy: M^1 L^2 T^-2 in SI
si_energy = BasisVector(SI, (
    Fraction(-2),  # T^-2
    Fraction(2),   # L^2
    Fraction(1),   # M^1
    Fraction(0), Fraction(0),
    Fraction(0), Fraction(0), Fraction(0),
))

natural_energy = SI_TO_NATURAL(si_energy)
natural_energy["E"]  # Fraction(1) - pure energy
```

### Lossy Projections

Electromagnetic dimensions (current, luminous intensity, etc.) are not representable in pure natural units:

```python
from ucon import SI, SI_TO_NATURAL, BasisVector, LossyProjection
from fractions import Fraction

# Current has no representation in natural units
si_current = BasisVector(SI, (
    Fraction(0), Fraction(0), Fraction(0), Fraction(1),
    Fraction(0), Fraction(0), Fraction(0), Fraction(0),
))

# Raises LossyProjection
try:
    SI_TO_NATURAL(si_current)
except LossyProjection as e:
    print(e)  # "current has no representation in natural"

# Use allow_projection=True to drop
result = SI_TO_NATURAL(si_current, allow_projection=True)
result.is_dimensionless()  # True (projected to zero)
```

### NATURAL_TO_SI (Inverse)

Transform natural unit dimensions back to SI using constant bindings:

```python
from ucon import NATURAL, NATURAL_TO_SI, BasisVector
from fractions import Fraction

# Energy in natural units
natural_energy = BasisVector(NATURAL, (Fraction(1),))

# Transform back to SI
si_result = NATURAL_TO_SI(natural_energy)
si_result.basis.name  # "SI"
```

### ConstantBinding

Records the relationship between source and target dimensions via physical constants:

```python
from ucon import ConstantBinding, NATURAL, BasisVector
from ucon.basis import BasisComponent
from fractions import Fraction

# Length relates to inverse energy via h_bar*c
binding = ConstantBinding(
    source_component=BasisComponent("length", "L"),
    target_expression=BasisVector(NATURAL, (Fraction(-1),)),
    constant_symbol="h_bar_c",  # h_bar * c
    exponent=Fraction(1),
)

binding.constant_symbol  # "h_bar_c"
binding.exponent  # Fraction(1)
```

### ConstantBoundBasisTransform

Basis transform with bindings that enable inversion of non-square matrices:

```python
from ucon import ConstantBoundBasisTransform

# SI_TO_NATURAL is a ConstantBoundBasisTransform (8x1 matrix)
isinstance(SI_TO_NATURAL, ConstantBoundBasisTransform)  # True

# Inverse works despite non-square matrix
NATURAL_TO_SI = SI_TO_NATURAL.inverse()
NATURAL_TO_SI.source.name  # "natural"
NATURAL_TO_SI.target.name  # "SI"

# Convert to plain BasisTransform (loses binding info)
plain = SI_TO_NATURAL.as_basis_transform()
```

---

## UnitSystem (`system=` kwarg)

A `UnitSystem` is a frozen value type that bundles a `Basis`, the unit / dimension / conversion / basis-graph registries, a `BaseUnits` mapping, and a per-instance `AlgebraCache`.

```python
from ucon import UnitSystem, BaseUnits, active_system, use, active
```

### Activation

```python
sys = active_system()
with use(sys):
    assert active() is sys
```

### Resolution Priority

Entry points that accept `system=` resolve their basis-graph and conversion-graph in this order:

```
explicit kwarg (graph=, basis_graph=, …)
    > system.basis_graph / system.conversion_graph
    > active() snapshot
    > module-level default
```

### Threaded Entry Points

The `system=` kwarg is accepted by:

| Entry point | Module |
|-------------|--------|
| `Number.to(target, *, system=None, graph=None, ...)` | `ucon.quantity` |
| `parse(text, *, system=None, ...)` | `ucon.parsing` |
| `parse_unit(text, *, system=None, ...)` | `ucon.parsing` |
| `parse_dimension(text, *, system=None, ...)` | `ucon.parsing` |
| `enforce_dimensions(*, system=None)` | `ucon.checking` |

Each entry point falls back to `active()` (and then to module-level globals) when `system=` is omitted, preserving v1.7 call sites verbatim.

### AlgebraCache

`UnitSystem` owns a per-instance `AlgebraCache` (sub-caches `mul` / `div` / `pow`). `Dimension` algebra routes through the active system's cache.

See [ucon.system](modules/system.md) for the full reference and [ucon.basis.ops](modules/basis-ops.md) for the explicit cross-basis helpers that the new value type composes with.

---

### Particle Physics Applications

Common particle physics dimensions:

```python
from ucon import SI, SI_TO_NATURAL, BasisVector
from fractions import Fraction

# Cross-section (area): L^2 -> E^-2
si_cross_section = BasisVector(SI, (
    Fraction(0), Fraction(2), Fraction(0), Fraction(0),
    Fraction(0), Fraction(0), Fraction(0), Fraction(0),
))
SI_TO_NATURAL(si_cross_section)["E"]  # Fraction(-2)

# Decay width (inverse time): T^-1 -> E
si_decay_width = BasisVector(SI, (
    Fraction(-1), Fraction(0), Fraction(0), Fraction(0),
    Fraction(0), Fraction(0), Fraction(0), Fraction(0),
))
SI_TO_NATURAL(si_decay_width)["E"]  # Fraction(1)

# Momentum: M*L/T -> E
si_momentum = BasisVector(SI, (
    Fraction(-1), Fraction(1), Fraction(1), Fraction(0),
    Fraction(0), Fraction(0), Fraction(0), Fraction(0),
))
SI_TO_NATURAL(si_momentum)["E"]  # Fraction(1)
```

---

## Kinds

A *kind* is a sortal refinement *within* a single dimension. Where
pseudo-dimensions and basis abstraction distinguish quantities by changing
their dimensional signature, a `KindLattice` records a partial order over
named kinds that all share the same dimension (e.g.,
`kinetic_energy ≤ energy`, `equivalent_dose ≤ absorbed_dose`).

```python
from ucon import Kind, KindLattice
from ucon.kinds import JoinPolicy, lca
```

`Kind` and `KindLattice` are re-exported from the top-level `ucon` package.
`Number` carries an optional `kind` field; arithmetic dispatch consults the
active `KindLattice` and `FormulaRegistry`.
See [Kind-of-Quantity Problem](../architecture/kind-of-quantity.md) for the
conceptual framing.

### Kind

Frozen dataclass representing a single kind:

```python
from ucon.dimension import LENGTH, MASS, TIME
from ucon.kinds import Kind, JoinPolicy

ENERGY_DIM = (LENGTH ** 2) * MASS / (TIME ** 2)

energy = Kind("energy", dimension=ENERGY_DIM)
kinetic = Kind(
    name="kinetic_energy",
    dimension=ENERGY_DIM,
    parent=energy,
    aliases=("KE",),
    join_policy=JoinPolicy.LCA,
)
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Canonical name (must be unique within a lattice) |
| `dimension` | Dimension | required | Physical dimension carried by this kind |
| `parent` | Kind \| None | `None` | Parent in the refinement lattice; must share dimension |
| `aliases` | tuple[str, ...] | `()` | Alternative names for lookup |
| `join_policy` | JoinPolicy | `LCA` | What happens when two distinct sibling kinds combine |

Equality and hash key off `name` only — two `Kind` instances with the same
name are considered the same kind regardless of other fields.

### JoinPolicy

Enum that controls operations between distinct sibling kinds:

| Member | Behavior |
|--------|----------|
| `JoinPolicy.LCA` | Result takes the least-common-ancestor kind |
| `JoinPolicy.REFUSE` | Operation is rejected at the kind layer |

`LCA` is the default and is appropriate for energies, doses, and other
refinements where the union is physically meaningful. `REFUSE` is used by
`ratio` and `dimensionless`, where mixing yields no sensible interpretation.

### KindLattice

Container that validates structural invariants and provides LCA-based
lookup:

```python
from ucon.kinds import KindLattice

lat = KindLattice([energy, kinetic])
lat.get("kinetic_energy")        # Kind('kinetic_energy')
lat.get("KE")                    # resolves via alias
"KE" in lat                      # True
lat.names()                      # ('energy', 'kinetic_energy')
lat.lca(kinetic, kinetic)        # (kinetic, JoinPolicy.LCA)
```

Adding a `Kind` whose parent is unknown, whose parent has a different
dimension, or that creates a cycle is rejected when the lattice is
constructed (see Exceptions below).

#### Module-level `lca()`

`ucon.kinds.lca(a, b, lattice)` is a thin functional wrapper around
`KindLattice.lca` for code that prefers a free function.

### Exceptions

```python
from ucon.kinds import (
    KindError,           # base class
    KindCycle,           # parent edges form a cycle
    OrphanParent,        # parent name does not resolve
    CrossDimensionParent,# parent has a different dimension
    NameCollision,       # two distinct Kinds share a name
    AliasCollision,      # an alias overlaps another kind's name/alias
    KindNotFound,        # lookup by name/alias missed
    JoinRefused,         # JoinPolicy.REFUSE triggered
)
```

| Exception | When raised |
|-----------|-------------|
| `KindCycle` | Adding a kind would create a cycle in parent edges |
| `OrphanParent` | A parent name does not resolve in the lattice |
| `CrossDimensionParent` | A child kind's dimension differs from its parent's |
| `NameCollision` | Two distinct `Kind` instances are registered under the same name |
| `AliasCollision` | An alias overlaps the name or alias of another kind |
| `KindNotFound` | `lat.get(...)` is called with an unknown name or alias |
| `JoinRefused` | An operation is refused by `JoinPolicy.REFUSE` |

---

## Formulas

Kind-formula dispatch for multiplication and division. Aspect rules control
propagation (see [Aspects](#aspects) below).

A `FormulaRegistry` records named relationships between input kinds and an
output kind. Given a sequence of `Kind` instances, the registry can resolve
the formula that produces the corresponding output — and, as of v1.9.1,
project aspect sets through the formula's rules in one step via `apply`.

```python
from ucon.formulas import (
    KindFormula,
    AspectRule,
    FormulaRegistry,
)
```

### KindFormula

Frozen dataclass describing a single relationship:

```python
from ucon.kinds import Kind
from ucon.formulas import AspectRule, KindFormula
from ucon.dimension import LENGTH, MASS, TIME

ABSORBED_DOSE_DIM = (LENGTH ** 2) / (TIME ** 2)
DIMENSIONLESS = LENGTH / LENGTH

D = Kind("absorbed_dose", dimension=ABSORBED_DOSE_DIM)
wR = Kind("radiation_weighting_factor", dimension=DIMENSIONLESS)
H = Kind("equivalent_dose", dimension=ABSORBED_DOSE_DIM)

f = KindFormula(
    name="radiation_weighting",
    expression="D * w_R",
    input_kinds={"D": D, "w_R": wR},
    output_kind=H,
    commutative=True,
    aspect_rules={"w_R": AspectRule.CONSUME},
    notes="w_R per ICRP 103; caller selects.",
)
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Unique formula identifier within a registry |
| `expression` | str | required | Free-form expression string (e.g. `"D * w_R"`) |
| `input_kinds` | dict[str, Kind] | required | Named inputs in declaration order |
| `output_kind` | Kind | required | Kind of the resulting quantity |
| `aspect_rules` | dict[str, AspectRule] | `{}` | Per-binding propagation rules (keys are binding names from `input_kinds`; see [Aspects](#aspects)) |
| `generalizes` | bool | `False` | Reserved; effective in v1.9.2 |
| `commutative` | bool | `True` | Two-input formulas are mirrored on registration |
| `notes` | str | `""` | Free-form annotation |

Equality and hash key off `name` only. `input_kind_tuple()` returns the
kinds in insertion order.

### AspectRule

Enum classifying how a formula treats an operand's aspects. Declared per
binding name in `KindFormula.aspect_rules`. Bindings not mentioned default
to `CARRY`. The canonical import is `from ucon.aspects import AspectRule`;
the v1.9.0 path `from ucon.formulas import AspectRule` continues to work.

| Member | String value | Meaning |
|--------|--------------|---------|
| `AspectRule.CONSUME` | `"consume"` | The binding's aspects are dropped from the output |
| `AspectRule.CARRY` | `"carry"` | The binding's aspects are unioned into the output |

See [Aspects](#aspects) for the full propagation model.

### `KindFormula.project_aspects(inputs)`

Pure method that projects input aspect sets through this formula's
`aspect_rules`, returning the output `AspectSet`. Called internally by
`FormulaRegistry.apply`.

```python
aspects = f.project_aspects({
    "D":   frozenset({"signal_summary"}),
    "w_R": frozenset({"calibrated"}),
})
# aspects == frozenset({"signal_summary"})  — w_R consumed
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `inputs` | Mapping[str, AspectSet] | Map of binding names to aspect sets |

Returns `AspectSet` (the union of all carried inputs' aspects).

### FormulaRegistry

Indexed collection of `KindFormula` instances supporting name lookup and
input-tuple lookup:

```python
from ucon.formulas import FormulaRegistry

reg = FormulaRegistry([f])
reg.get("radiation_weighting")        # the KindFormula
reg.lookup(D, wR).name                # "radiation_weighting"
reg.lookup(wR, D).name                # "radiation_weighting" (commutative)
"radiation_weighting" in reg          # True
len(reg)                              # 1
reg.names()                           # ('radiation_weighting',)
```

| Method | Purpose |
|--------|---------|
| `register(formula)` | Add a formula; raises `DuplicateFormula` on name reuse |
| `get(name)` | Return the named formula or raise `FormulaNotFound` |
| `lookup(*kinds)` | Resolve a formula by exact input-kind tuple |
| `resolve(*kinds)` | Tiered formula resolution returning `LookupResult` (v1.9.2) |
| `apply(inputs)` | Resolve formula **and** project aspects in one step (v1.9.1, extended v1.9.2) |
| `names()` | Tuple of registered names |

Commutative formulas are indexed under both the original key and a
canonical sorted key, so permuted orderings resolve at any arity.

#### `resolve(*input_kinds, lattice=None, dimension_fallback=False)`

New in v1.9.2. Tiered formula resolution through successive match tiers,
checked in strict priority order — the first to produce a match wins:

1. **EXACT** — direct input-kind tuple match.
2. **COMMUTATIVE** — canonical sorted-key match (any arity).
3. **GENERALIZED** — ancestor-walk via `lattice` at increasing L1 distance
   (only formulas with `generalizes=True`).
4. **DIMENSIONAL** — dimension-tuple match ignoring kind identity
   (only when `dimension_fallback=True`).

```python
from ucon.formulas import MatchKind

result = reg.resolve(D, wR)
result.formula.name   # "radiation_weighting"
result.match_kind     # MatchKind.EXACT
result.distance       # 0

# Generalized: child kind climbs to parent
result = reg.resolve(child_kind, wR, lattice=lat)
result.match_kind     # MatchKind.GENERALIZED
result.distance       # 1 (L1 distance in ancestor walk)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `*input_kinds` | Kind | Kinds to match, in caller-supplied order |
| `lattice` | KindLattice \| None | Enables GENERALIZED matching via ancestor walk |
| `dimension_fallback` | bool | Enables DIMENSIONAL matching as a last resort |

Returns `LookupResult`. Raises `FormulaNotFound` if no formula matched
at any enabled tier, or `AmbiguousFormula` if multiple formulas matched
at the same GENERALIZED distance.

#### `apply(inputs, *, lattice=None, dimension_fallback=False)`

New in v1.9.1, extended in v1.9.2. Single entry point that resolves the
formula by input kinds and projects aspect sets through it:

```python
from ucon.aspects import AspectSet
from ucon.formulas import MatchKind

formula, out_kind, out_aspects, match_kind = reg.apply({
    "D":   (D,  AspectSet("signal_summary")),
    "w_R": (wR, AspectSet("calibrated")),
})
# formula     == <KindFormula "radiation_weighting">
# out_kind    == H (equivalent_dose)
# out_aspects == frozenset({"signal_summary"})
# match_kind  == MatchKind.EXACT
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `inputs` | Mapping[str, tuple[Kind, AspectSet]] | Map of binding names to (kind, aspects) pairs |
| `lattice` | KindLattice \| None | Enables GENERALIZED matching via ancestor walk |
| `dimension_fallback` | bool | Enables DIMENSIONAL matching as a last resort |

Returns `tuple[KindFormula, Kind, AspectSet, MatchKind]`. Raises
`FormulaNotFound` if no formula matches the input kinds, or
`AmbiguousFormula` if multiple formulas match at the same GENERALIZED
distance.

### Types

New in v1.9.2.

```python
from ucon.formulas import MatchKind, LookupResult
```

| Type | Description |
|------|-------------|
| `MatchKind` | Enum: `EXACT`, `COMMUTATIVE`, `GENERALIZED`, `DIMENSIONAL` |
| `LookupResult` | Frozen dataclass with `formula`, `match_kind`, and `distance` (L1 distance for GENERALIZED; 0 for others) |

### Exceptions

```python
from ucon.formulas import (
    FormulaError,         # base class
    FormulaNotFound,      # name or kind-tuple did not resolve
    DuplicateFormula,     # name already registered
    AmbiguousFormula,     # multiple formulas match at same distance
)
```

| Exception | When raised |
|-----------|-------------|
| `FormulaNotFound` | `get(name)`, `lookup(*kinds)`, or `resolve(*kinds)` did not match |
| `DuplicateFormula` | A formula with the same name is already registered |
| `AmbiguousFormula` | Multiple formulas matched at the same GENERALIZED distance; carries `candidates` and `distance` |

---

## Aspects

An *aspect* is a covariant tag (a string) carried alongside a quantity
that describes its provenance, processing, or calibration state — not its
physical identity. Aspects are orthogonal to kinds: two values with the
same kind can differ in aspects, and vice versa.

```python
from ucon.aspects import (
    AspectSet,
    AspectRule,
    AspectJoinPolicy,
    join_aspects,
)
```

### AspectSet

An immutable set of aspect names. `AspectSet` is a `frozenset` subclass
with a variadic constructor for ergonomic construction:

```python
# Variadic (primary form)
AspectSet("calibrated", "ICRP103")

# From an existing collection
AspectSet({"calibrated", "ICRP103"})
AspectSet(some_frozenset)

# Empty
AspectSet()

# Single string is one aspect, not iterated as characters
AspectSet("calibrated") == frozenset({"calibrated"})  # True
```

`AspectSet` is fully interchangeable with plain `frozenset[str]` at every
internal surface. Set algebra (`&`, `|`, `-`, `^`) returns plain `frozenset`
instances.

### AspectJoinPolicy

Enum controlling how aspect sets combine when kinds join at the lattice
(addition path):

| Member | String value | Behaviour |
|--------|--------------|-----------|
| `AspectJoinPolicy.INTERSECT` | `"intersect"` | Keep only aspects present on **both** sides (default) |
| `AspectJoinPolicy.UNION` | `"union"` | Keep every aspect from **either** side |

### `join_aspects(a, b, policy=INTERSECT)`

Pure function combining two aspect sets under the given policy. Does not
consult a kind lattice; callers compose with `KindLattice.join` explicitly.

```python
from ucon.aspects import join_aspects, AspectJoinPolicy

# Default: INTERSECT
join_aspects(
    frozenset({"signal_summary", "calibrated"}),
    frozenset({"signal_summary"}),
)
# frozenset({"signal_summary"})

# Explicit UNION
join_aspects(
    frozenset({"signal_summary", "calibrated"}),
    frozenset({"signal_summary"}),
    policy=AspectJoinPolicy.UNION,
)
# frozenset({"signal_summary", "calibrated"})
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `a`, `b` | AspectSet | required | Aspect sets to combine |
| `policy` | AspectJoinPolicy | `INTERSECT` | Combination policy |

Raises `ValueError` if `policy` is not a recognised `AspectJoinPolicy`.

---

## TOML Loaders for Kinds & Formulas

New in v1.9.0. Kinds and formulas can be authored in TOML and loaded into
a `KindLattice` and `FormulaRegistry`. The loaders are **independent of**
the `ConversionGraph` TOML schema documented in
[Serialization Format](serialization-format.md) — they read the `[[kinds]]`
and `[[formulas]]` sections from any TOML file, and the two sections can
share a file.

```python
from ucon.parsing import (
    parse_kinds_payload,
    load_kinds_file,
    parse_formulas_payload,
    load_formulas_file,
)
```

### Schema: `[[kinds]]`

```toml
[[kinds]]
name = "energy"
dimension = "L^2 * M / T^2"
aliases = ["E"]
join_policy = "lca"

[[kinds]]
name = "kinetic_energy"
dimension = "L^2 * M / T^2"
parent = "energy"
aliases = ["KE"]
```

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `name` | string | yes | Canonical kind name |
| `dimension` | string | yes | Dimension expression (e.g. `"L^2 * M / T^2"`, `"1"`) |
| `parent` | string | no | Name of an existing kind (forward references resolved) |
| `aliases` | array of strings | no | Alternative names |
| `join_policy` | string | no | `"lca"` (default) or `"refuse"` |

### Schema: `[[formulas]]`

```toml
[[formulas]]
name = "radiation_weighting"
expression = "D * w_R"
output_kind = "equivalent_dose"
commutative = true
notes = "w_R per ICRP 103."

[formulas.inputs]
D = { kind = "absorbed_dose" }
w_R = { kind = "radiation_weighting_factor" }

[formulas.aspect_rules]
w_R = "consume"
```

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `name` | string | yes | Formula name |
| `expression` | string | yes | Free-form expression text |
| `output_kind` | string | yes | Name of an existing kind |
| `inputs` | table | yes | Map of input names to `{ kind = "..." }` |
| `commutative` | bool | no | Defaults to `true` |
| `generalizes` | bool | no | Defaults to `false` |
| `aspect_rules` | table | no | Map of binding names to `"consume"` or `"carry"` (keys must match `inputs`) |
| `notes` | string | no | Free-form notes |

### Loading

```python
from pathlib import Path
from ucon.parsing import load_kinds_file, load_formulas_file

lat = load_kinds_file(Path("radiation.ucon.toml"))
reg = load_formulas_file(Path("radiation.ucon.toml"), lattice=lat)

reg.get("radiation_weighting").output_kind.name  # "equivalent_dose"
```

`load_formulas_file` requires a `KindLattice` because formula inputs and
outputs reference kinds by name. Unknown kind references raise
`KindNotFound`.

### Payload-Level Helpers

`parse_kinds_payload(payload)` and `parse_formulas_payload(payload, lattice=...)`
accept already-decoded dictionaries and are useful for testing or for
embedding kind definitions inside a larger TOML document.

```python
from ucon.parsing import parse_kinds_payload

lat = parse_kinds_payload({
    "kinds": [
        {"name": "energy", "dimension": "L^2 * M / T^2"},
        {"name": "kinetic_energy", "dimension": "L^2 * M / T^2", "parent": "energy"},
    ]
})
lat.get("kinetic_energy").parent.name  # "energy"
```

Parser-level validation surfaces the same exceptions as the lattice itself
(`KindCycle`, `OrphanParent`, `CrossDimensionParent`, `AliasCollision`) plus
`ValueError` for malformed payloads (missing `name`, unknown `join_policy`,
non-string aliases, etc.).

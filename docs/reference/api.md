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

#### `to(target, graph=None)`

Convert to a different unit.

```python
d = units.meter(1000)
d.to(Scale.kilo * units.meter)  # <1.0 km>

weight = units.pound(154)
weight.to(Scale.kilo * units.gram)  # <69.85... kg>
```

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
from ucon.graph import using_graph

with using_graph(my_graph):
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
| `LinearMap(a)` | y = a * x | Most unit conversions (m -> ft, kg -> lb) |
| `AffineMap(a, b)` | y = a * x + b | Temperature conversions (C -> F) |
| `ReciprocalMap(a)` | y = a / x | Inversely proportional (wavelength -> frequency) |
| `LogMap(scale, base, reference)` | y = scale * log(x/ref) + offset | Decibels, pH |
| `ExpMap(scale, base, reference)` | y = ref * base^(scale*x + offset) | Inverse of LogMap |
| `ComposedMap(outer, inner)` | y = outer(inner(x)) | Heterogeneous composition fallback |

All maps are `@dataclass(frozen=True)` --- immutable and hashable.

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
    print(edge_def.src)     # "slug"
    print(edge_def.dst)     # "kilogram"
    print(edge_def.factor)  # 14.5939
    print(edge_def.offset)  # 0.0 (non-zero for affine)

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

Thread-safe basis isolation via ContextVars.

```python
from ucon import (
    get_default_basis,
    get_basis_graph,
    set_default_basis_graph,
    reset_default_basis_graph,
    using_basis,
    using_basis_graph,
)
```

#### `get_default_basis()`

Returns the current default basis (context-local or SI fallback).

```python
from ucon import get_default_basis, SI

get_default_basis()  # SI (when no context set)
```

#### `using_basis(basis)`

Context manager for scoped basis override.

```python
from ucon import using_basis, CGS, Dimension

with using_basis(CGS):
    # Dimensions created here use CGS basis
    dim = Dimension.from_components(L=1, T=-1)
    dim.basis  # CGS
```

#### `get_basis_graph()`

Returns the current BasisGraph (context-local or module default).

```python
from ucon import get_basis_graph, SI, CGS

graph = get_basis_graph()
graph.are_connected(SI, CGS)  # True (standard graph has SI/CGS transforms)
```

#### `using_basis_graph(graph)`

Context manager for scoped BasisGraph override.

```python
from ucon import using_basis_graph, BasisGraph

custom_graph = BasisGraph()
with using_basis_graph(custom_graph):
    get_basis_graph() is custom_graph  # True
```

#### `set_default_basis_graph(graph)` / `reset_default_basis_graph()`

Module-level control over the default BasisGraph.

```python
from ucon import set_default_basis_graph, reset_default_basis_graph, BasisGraph

# Replace module default
custom = BasisGraph()
set_default_basis_graph(custom)

# Restore standard graph (lazy rebuild on next access)
reset_default_basis_graph()
```

| Function | Purpose |
|----------|---------|
| `get_default_basis()` | Get context-local basis or SI |
| `using_basis(basis)` | Scoped basis override |
| `get_basis_graph()` | Get context-local or default BasisGraph |
| `using_basis_graph(graph)` | Scoped BasisGraph override |
| `set_default_basis_graph(graph)` | Replace module default |
| `reset_default_basis_graph()` | Restore standard graph |

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

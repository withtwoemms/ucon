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
# Unknown unit
parse("60 foobar")         # raises UnknownUnitError

# Invalid number
parse("abc m")             # raises ValueError

# Empty string
parse("")                  # raises ValueError
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
from ucon.bases import SI_TO_CGS_ESU

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
from ucon.bases import SI_TO_CGS_ESU

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
graph.list_rebased_units()  # {ampere: RebasedUnit(...)}

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
from ucon.bases import SI, CGS, CGS_ESU, SI_TO_CGS, SI_TO_CGS_ESU
```

### Standard Bases

| Basis | Components | Description |
|-------|------------|-------------|
| `SI` | T, L, M, I, Θ, J, N, B | International System (8 dimensions) |
| `CGS` | L, M, T | Centimetre-gram-second (mechanical) |
| `CGS_ESU` | L, M, T, Q | CGS electrostatic (charge is fundamental) |

### BasisGraph

Track connectivity between bases:

```python
from ucon.basis import BasisGraph
from ucon.bases import SI_TO_CGS_ESU

bg = BasisGraph()
bg = bg.with_transform(SI_TO_CGS_ESU)

bg.are_connected(SI, CGS_ESU)  # True
```

### BasisTransform

Matrix mapping dimension vectors between bases:

```python
from ucon.bases import SI_TO_CGS_ESU

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

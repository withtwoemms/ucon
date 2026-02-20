# API Reference

Core Python API for ucon.

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
    map_=LinearMap(0.3048)
)

# Convert
result = graph.convert(units.foot, units.meter)
result(12)  # 3.6576
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
from ucon.units import UnknownUnitError
```

| Exception | When Raised |
|-----------|-------------|
| `ConversionNotFound` | No path between units in graph |
| `DimensionMismatch` | Operation on incompatible dimensions |
| `CyclicInconsistency` | Adding edge creates inconsistent cycle |
| `UnknownUnitError` | Unit string cannot be parsed |

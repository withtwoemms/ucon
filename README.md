<table>
  <tr>
    <td width="200">
      <img src="https://gist.githubusercontent.com/withtwoemms/0cb9e6bc8df08f326771a89eeb790f8e/raw/221c60e85ac8361c7d202896b52c1a279081b54c/ucon-logo.png" align="left" width="200" />
    </td>
    <td>

# ucon

> Pronounced: _yoo · cahn_

[![tests](https://github.com/withtwoemms/ucon/workflows/tests/badge.svg)](https://github.com/withtwoemms/ucon/actions?query=workflow%3Atests)
[![codecov](https://codecov.io/gh/withtwoemms/ucon/graph/badge.svg?token=BNONQTRJWG)](https://codecov.io/gh/withtwoemms/ucon)
[![publish](https://github.com/withtwoemms/ucon/workflows/publish/badge.svg)](https://github.com/withtwoemms/ucon/actions?query=workflow%3Apublish)

   </td>
  </tr>
</table>

> A lightweight, **unit-aware computation library** for Python — built on first-principles.

---

## Overview

`ucon` helps Python understand the *physical meaning* of your numbers.
It combines **units**, **scales**, and **dimensions** into a composable algebra that supports:

- Dimensional analysis through `Number` and `Ratio`
- Scale-aware arithmetic via `UnitFactor` and `UnitProduct`
- Metric and binary prefixes (`kilo`, `kibi`, `micro`, `mebi`, etc.)
- Pseudo-dimensions for angles, solid angles, ratios, and counts with semantic isolation
- Uncertainty propagation through arithmetic and conversions
- Pydantic v2 integration for API validation and JSON serialization
- A clean foundation for physics, chemistry, data modeling, and beyond

Think of it as **`decimal.Decimal` for the physical world** — precise, predictable, and type-safe.

## Introduction

The crux of this tiny library is to provide abstractions that simplify the answering of questions like:

> _"If given two milliliters of bromine (liquid Br<sub>2</sub>), how many grams of bromine does one have?"_

To best answer this question, we turn to an age-old technique ([dimensional analysis](https://en.wikipedia.org/wiki/Dimensional_analysis)) which essentially allows for the solution to be written as a product of ratios. `ucon` comes equipped with some useful primitives:
| Type                          | Defined In                              | Purpose                                                                                             | Typical Use Cases                                                                                                      |
| ----------------------------- | --------------------------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **`Vector`**                  | `ucon.algebra`                          | Represents the 8-component exponent tuple of a physical quantity's base dimensions (T, L, M, I, Θ, J, N, B). | Internal representation of dimensional algebra; building derived quantities (e.g., area, velocity, force).             |
| **`Exponent`**                | `ucon.algebra`                          | Represents base-power pairs (e.g., 10³, 2¹⁰) used by `Scale`.                                       | Performing arithmetic on powers and bases; normalizing scales across conversions.                                      |
| **`Dimension`**               | `ucon.core`                             | Encapsulates physical dimensions (e.g., length, time, mass) as algebraic combinations of vectors.   | Enforcing dimensional consistency; defining relationships between quantities (e.g., length / time = velocity).         |
| **`Scale`**                   | `ucon.core`                             | Encodes powers of base magnitudes (binary or decimal prefixes like kilo-, milli-, mebi-).           | Adjusting numeric scale without changing dimension (e.g., kilometer ↔ meter, byte ↔ kibibyte).                         |
| **`Unit`**                    | `ucon.core`                             | An atomic, scale-free measurement symbol (e.g., meter, second, joule) with a `Dimension`.           | Defining base units; serving as graph nodes for future conversions.                                                    |
| **`UnitFactor`**              | `ucon.core`                             | Pairs a `Unit` with a `Scale` (e.g., kilo + gram = kg). Used as keys inside `UnitProduct`.          | Preserving user-provided scale prefixes through algebraic operations.                                                  |
| **`UnitProduct`**             | `ucon.core`                             | A product/quotient of `UnitFactor`s with exponent tracking and simplification.                      | Representing composite units like m/s, kg·m/s², kJ·h.                                                                 |
| **`Number`**                  | `ucon.core`                             | Combines a numeric quantity with a unit; the primary measurable type. Supports `Number[Dimension]` for type-safe annotations. | Performing arithmetic with units; representing physical quantities like 5 m/s; annotating function parameters with dimensional constraints. |
| **`Ratio`**                   | `ucon.core`                             | Represents the division of two `Number` objects; captures relationships between quantities.         | Expressing rates, densities, efficiencies (e.g., energy / time = power, length / time = velocity).                     |
| **`Map`** hierarchy           | `ucon.maps`                             | Composable conversion morphisms: `LinearMap`, `AffineMap`, `LogMap`, `ExpMap`, `ComposedMap`.       | Defining conversion functions between units (e.g., meter→foot, celsius→kelvin, availability→nines).                    |
| **`ConversionGraph`**         | `ucon.graph`                            | Registry of unit conversion edges with BFS path composition.                                        | Converting between units via `Number.to(target)`; managing default and custom graphs.                                  |
| **`UnitSystem`**              | `ucon.core`                             | Named mapping from dimensions to base units (e.g., SI, Imperial).                                   | Defining coherent unit systems; grouping base units by dimension.                                                      |
| **`BasisTransform`**          | `ucon.core`                             | Matrix-based transformation between dimensional exponent spaces.                                    | Converting between incompatible dimensional structures; exact arithmetic with `Fraction`.                              |
| **`RebasedUnit`**             | `ucon.core`                             | A unit rebased to another system's dimension, preserving provenance.                                | Cross-basis conversions; tracking original unit through basis changes.                                                 |
| **`units` module**            | `ucon.units`                            | Defines canonical unit instances (SI, imperial, information, and derived units).                    | Quick access to standard physical units (`units.meter`, `units.foot`, `units.byte`, etc.).                             |
| **`pydantic` module**         | `ucon.pydantic`                         | Pydantic v2 integration with `Number` type for model validation and JSON serialization.             | Using `Number` in Pydantic models; API request/response validation; JSON round-trip serialization.                     |

### Under the Hood

`ucon` models unit math through a hierarchy where each layer builds on the last:

<img src=https://gist.githubusercontent.com/withtwoemms/429d2ca1f979865aa80a2658bf9efa32/raw/5df6a7fb2a6426ee6804096c092c10bed1b30b6f/ucon.data-model_v040.png align="center" alt="ucon Data Model" width=600/>

## Why `ucon`?

Python already has mature libraries for handling units and physical quantities — Pint, SymPy, and Unum — each solving part of the same problem from different angles:

| Library   | Focus                                                   | Limitation                                                                                                             |
| --------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Pint**  | Runtime unit conversion and compatibility checking      | Treats quantities as decorated numbers — conversions work, but the algebra behind them isn't inspectable or type-safe. |
| **SymPy** | Symbolic algebra and simplification of unit expressions | Excellent for symbolic reasoning, but not designed for runtime validation, conversion, or serialization.               |
| **Unum**  | Unit-aware arithmetic and unit propagation              | Tracks units through arithmetic but lacks explicit dimensional algebra, conversion taxonomy, or runtime introspection. |

Together, these tools can _use_ units, but none can explicitly represent and verify the relationships between units and dimensions.

That's the gap `ucon` fills.

It treats units, dimensions, and scales as first-class objects and builds a composable algebra around them.
This allows you to:
- Represent dimensional meaning explicitly (`Dimension`, `Vector`);
- Compose and compute with type-safe, introspectable quantities (`Unit`, `Number`);
- Extend the system with custom unit registries and conversion families.

Where Pint, Unum, and SymPy focus on _how_ to compute with units,
`ucon` focuses on why those computations make sense. Every operation checks the dimensional structure, _not just the unit labels_. This means ucon doesn't just track names: it enforces physics:
```python
from ucon import units

length = units.meter(5)
time = units.second(2)

speed = length / time     # ✅ valid: L / T = velocity
invalid = length + time   # ❌ raises: incompatible dimensions
```

## Setup

Simple:
```bash
pip install ucon
```

With Pydantic v2 support:
```bash
pip install ucon[pydantic]
```

## Usage

### Quantities and Arithmetic

Dimensional analysis like this:
```
 2 mL bromine | 3.119 g bromine
--------------x-----------------  #=> 6.238 g bromine
      1       |  1 mL bromine
```
becomes straightforward:
```python
from ucon import Scale, units

mL = Scale.milli * units.liter
two_mL_bromine = mL(2)

bromine_density = (units.gram / mL)(3.119)

grams_bromine = bromine_density * two_mL_bromine
print(grams_bromine)  # <6.238 g>
```

### Scale Prefixes

```python
km = Scale.kilo * units.meter       # UnitProduct with kilo-scaled meter
mg = Scale.milli * units.gram       # UnitProduct with milli-scaled gram

print(km.shorthand)  # 'km'
print(mg.shorthand)  # 'mg'

print(km.fold_scale())  # 1000.0
print(mg.fold_scale())  # 0.001
```

### Callable Units and Conversion

```python
from ucon import units, Scale

# Callable syntax: unit(quantity) → Number
height = units.meter(1.8)
speed = (units.mile / units.hour)(60)

# Convert between units
height_ft = height.to(units.foot)
print(height_ft)  # <5.905... ft>

# Scaled units work too
km = Scale.kilo * units.meter
distance = km(5)
distance_mi = distance.to(units.mile)
print(distance_mi)  # <3.107... mi>
```

### Dimensionless Units

Angles, solid angles, ratios, and counts are semantically isolated pseudo-dimensions:
```python
import math
from ucon import units

angle = units.radian(math.pi)
print(angle.to(units.degree))  # <180.0 deg>

ratio = units.percent(50)
print(ratio.to(units.ppm))  # <500000.0 ppm>

# Cross-family conversions are prevented
units.radian(1).to(units.percent)  # raises ConversionNotFound

# SRE "nines" for availability (99.999% = 5 nines)
uptime = units.percent(99.999)
print(uptime.to(units.nines))  # <5.0 nines>
```

### Counting Units

The `each` unit represents discrete, countable items (tablets, doses, events):
```python
from ucon import units, Scale

# "each" is a generic counting unit with aliases: ea, item, ct
items = units.each(30)
print(items)  # <30 ea>

# Express rates per item (e.g., mg per tablet)
mg = Scale.milli * units.gram
dose_rate = mg(500) / units.each(1)  # 500 mg/ea

# Factor-label calculations cancel correctly
total = items * dose_rate
print(total)  # <15000 mg> — count dimension cancels

# Count is isolated from other pseudo-dimensions
units.each(5).to(units.percent)  # raises ConversionNotFound
```

**Design note:** `each` is intentionally generic. Domain-specific atomizers (dose, tablet, capsule) are application-layer metadata, not core units. This keeps the unit system tractable while supporting any counting context.

### Uncertainty Propagation

```python
from ucon import units

length = units.meter(1.234, uncertainty=0.005)
width = units.meter(0.567, uncertainty=0.003)

print(length)  # <1.234 ± 0.005 m>

# Propagates through arithmetic (quadrature)
area = length * width
print(area)  # <0.699678 ± 0.00424... m²>

# Propagates through conversion
length_ft = length.to(units.foot)
print(length_ft)  # <4.048... ± 0.0164... ft>
```

### Pydantic Integration

```python
from pydantic import BaseModel
from ucon.pydantic import Number
from ucon import units

class Measurement(BaseModel):
    value: Number

# From JSON/dict input
m = Measurement(value={"quantity": 5, "unit": "km"})
print(m.value)  # <5 km>

# From Number instance
m2 = Measurement(value=units.meter(10))

# Serialize to JSON
print(m.model_dump_json())
# {"value": {"quantity": 5.0, "unit": "km", "uncertainty": null}}

# Supports both Unicode and ASCII unit notation
m3 = Measurement(value={"quantity": 9.8, "unit": "m/s^2"})  # ASCII
m4 = Measurement(value={"quantity": 9.8, "unit": "m/s²"})   # Unicode
```

**Design notes:**
- **Serialization format**: Units serialize as human-readable shorthand strings (`"km"`, `"m/s^2"`) rather than structured dicts, aligning with how scientists express units.
- **Parsing priority**: When parsing `"kg"`, ucon returns `Scale.kilo * gram` rather than looking up a `kilogram` Unit, ensuring consistent round-trip serialization and avoiding redundant unit definitions.

### Type-Safe Dimensional Annotations

`Number` supports subscript syntax for declaring dimensional constraints in function signatures:

```python
from ucon import Number, Dimension

def speed(
    distance: Number[Dimension.length],
    time: Number[Dimension.time],
) -> Number[Dimension.velocity]:
    return distance / time
```

This produces `typing.Annotated[Number, DimConstraint(dim)]`, enabling runtime introspection:

```python
from typing import get_origin, get_args, Annotated
from ucon import Number, Dimension, DimConstraint

hint = Number[Dimension.time]
assert get_origin(hint) is Annotated
assert get_args(hint)[1].dimension == Dimension.time
```

The `@enforce_dimensions` decorator validates these constraints at call time:

```python
from ucon import enforce_dimensions

@enforce_dimensions
def speed(
    distance: Number[Dimension.length],
    time: Number[Dimension.time],
) -> Number:
    return distance / time

speed(units.meter(100), units.second(10))  # ✅ <10.0 m/s>
speed(units.second(100), units.second(10)) # ❌ ValueError: distance: expected dimension 'length', got 'time'
speed(100, units.second(10))               # ❌ TypeError: distance: expected Number, got int
```

### MCP Server

ucon ships with an MCP server for AI agent integration (Claude Desktop, Claude Code, Cursor, etc.):

```bash
pip install ucon[mcp]
```

Configure in Claude Desktop (`claude_desktop_config.json`):

**Via uvx (recommended, zero-install):**
```json
{
  "mcpServers": {
    "ucon": {
      "command": "uvx",
      "args": ["--from", "ucon[mcp]", "ucon-mcp"]
    }
  }
}
```

**Local development:**
```json
{
  "mcpServers": {
    "ucon": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/ucon", "--extra", "mcp", "ucon-mcp"]
    }
  }
}
```

Available tools:
- `convert(value, from_unit, to_unit)` — Unit conversion with dimensional validation
- `compute(initial_value, initial_unit, factors)` — Multi-step factor-label calculations
- `list_units(dimension?)` — Discover available units
- `list_scales()` — List SI and binary prefixes
- `check_dimensions(unit_a, unit_b)` — Check dimensional compatibility
- `list_dimensions()` — List physical dimensions

**Factor-label calculations** with `compute`:
```python
# Convert 154 lb patient weight to mg/dose for a drug dosed at 15 mg/kg/day, 3 doses/day
compute(
    initial_value=154,
    initial_unit="lb",
    factors=[
        {"value": 1, "numerator": "kg", "denominator": "2.205 lb"},
        {"value": 15, "numerator": "mg", "denominator": "kg*day"},
        {"value": 1, "numerator": "day", "denominator": "3 ea"},
    ]
)
# → {"quantity": 349.2, "unit": "mg/ea", "dimension": "mass/count", "steps": [...]}
```

Each step in the response shows the intermediate quantity, unit, and dimension — enabling AI agents to verify dimensional consistency throughout the calculation chain.

### Custom Unit Systems

`BasisTransform` enables conversions between incompatible dimensional structures (e.g., fantasy game physics, CGS units, domain-specific systems).

See full example: [docs/examples/basis-transform-fantasy-units.md](./docs/examples/basis-transform-fantasy-units.md)

---

## Roadmap Highlights

| Version | Theme | Focus | Status |
|----------|-------|--------|--------|
| **0.3.x** | Dimensional Algebra | Unit/Scale separation, `UnitFactor`, `UnitProduct` | ✅ Complete |
| **0.4.x** | Conversion System | `ConversionGraph`, `Number.to()`, callable units | ✅ Complete |
| **0.5.0** | Dimensionless Units | Pseudo-dimensions for angle, solid angle, ratio | ✅ Complete |
| **0.5.x** | Uncertainty | Propagation through arithmetic and conversions | ✅ Complete |
| **0.5.x** | Unit Systems | `BasisTransform`, `UnitSystem`, cross-basis conversion | ✅ Complete |
| **0.6.x** | Pydantic + MCP | API validation, AI agent integration | ✅ Complete |
| **0.7.x** | MCP Compute | Factor-label chains, error suggestions, count dimension | ✅ Complete |
| **0.8.x** | String Parsing | `parse("60 mph")` → Number | ⏳ Planned |
| **0.10.x** | NumPy Arrays | Vectorized conversion and arithmetic | ⏳ Planned |

See full roadmap: [ROADMAP.md](./ROADMAP.md)

---

## Contributing

Contributions, issues, and pull requests are welcome!

Set up your development environment:
```bash
make venv
source .ucon-3.12/bin/activate
```

Run the test suite before committing:
```bash
make test
```

Run tests across all supported Python versions:
```bash
make test-all
```
---

> "If it can be measured, it can be represented.
If it can be represented, it can be validated.
If it can be validated, it can be trusted."

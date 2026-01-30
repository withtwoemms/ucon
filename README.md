<img src="https://gist.githubusercontent.com/withtwoemms/0cb9e6bc8df08f326771a89eeb790f8e/raw/dde6c7d3b8a7d79eb1006ace03fb834e044cdebc/ucon-logo.png" align="left" width="200" />

# ucon

> Pronounced: _yoo · cahn_

[![tests](https://github.com/withtwoemms/ucon/workflows/tests/badge.svg)](https://github.com/withtwoemms/ucon/actions?query=workflow%3Atests)
[![codecov](https://codecov.io/gh/withtwoemms/ucon/graph/badge.svg?token=BNONQTRJWG)](https://codecov.io/gh/withtwoemms/ucon)
[![publish](https://github.com/withtwoemms/ucon/workflows/publish/badge.svg)](https://github.com/withtwoemms/ucon/actions?query=workflow%3Apublish)

> A lightweight, **unit-aware computation library** for Python — built on first-principles.

---

## Overview

`ucon` helps Python understand the *physical meaning* of your numbers.
It combines **units**, **scales**, and **dimensions** into a composable algebra that supports:

- Dimensional analysis through `Number` and `Ratio`
- Scale-aware arithmetic via `UnitFactor` and `UnitProduct`
- Metric and binary prefixes (`kilo`, `kibi`, `micro`, `mebi`, etc.)
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
| **`Number`**                  | `ucon.core`                             | Combines a numeric quantity with a unit; the primary measurable type.                               | Performing arithmetic with units; representing physical quantities like 5 m/s.                                         |
| **`Ratio`**                   | `ucon.core`                             | Represents the division of two `Number` objects; captures relationships between quantities.         | Expressing rates, densities, efficiencies (e.g., energy / time = power, length / time = velocity).                     |
| **`Map`** hierarchy           | `ucon.maps`                             | Composable conversion morphisms: `LinearMap`, `AffineMap`, `ComposedMap`.                           | Defining conversion functions between units (e.g., meter→foot, celsius→kelvin).                                        |
| **`ConversionGraph`**         | `ucon.graph`                            | Registry of unit conversion edges with BFS path composition.                                        | Converting between units via `Number.to(target)`; managing default and custom graphs.                                  |
| **`units` module**            | `ucon.units`                            | Defines canonical unit instances (SI, imperial, information, and derived units).                    | Quick access to standard physical units (`units.meter`, `units.foot`, `units.byte`, etc.).                             |

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
from ucon import Number, units

length = Number(quantity=5, unit=units.meter)
time = Number(quantity=2, unit=units.second)

speed = length / time     # ✅ valid: L / T = velocity
invalid = length + time   # ❌ raises: incompatible dimensions
```

## Setup

Simple:
```bash
pip install ucon
```

## Usage

This sort of dimensional analysis:
```
 2 mL bromine | 3.119 g bromine
--------------x-----------------  #=> 6.238 g bromine
      1       |  1 mL bromine
```
becomes straightforward when you define a measurement:
```python
from ucon import Number, Scale, units
from ucon.quantity import Ratio

# Two milliliters of bromine
mL = Scale.milli * units.liter
two_mL_bromine = Number(quantity=2, unit=mL)

# Density of bromine: 3.119 g/mL
bromine_density = Ratio(
    numerator=Number(unit=units.gram, quantity=3.119),
    denominator=Number(unit=mL),
)

# Multiply to find mass
grams_bromine = bromine_density.evaluate() * two_mL_bromine
print(grams_bromine)  # <6.238 g>
```

Scale prefixes compose naturally:
```python
km = Scale.kilo * units.meter       # UnitProduct with kilo-scaled meter
mg = Scale.milli * units.gram       # UnitProduct with milli-scaled gram

print(km.shorthand)  # 'km'
print(mg.shorthand)  # 'mg'

# Scale arithmetic
print(km.fold_scale())  # 1000.0
print(mg.fold_scale())  # 0.001
```

Units are callable for ergonomic quantity construction:
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

---

## Roadmap Highlights

| Version | Theme | Focus | Status |
|----------|-------|--------|--------|
| **0.3.5** | Dimensional Algebra | Unit/Scale separation, `UnitFactor`, `UnitProduct` | ✅ Complete |
| [**0.4.x**](https://github.com/withtwoemms/ucon/milestone/2) | Conversion System | `ConversionGraph`, `Number.to()`, callable units | 🚧 In Progress |
| [**0.6.x**](https://github.com/withtwoemms/ucon/milestone/4) | Nonlinear / Specialized Units | Decibel, Percent, pH | ⏳ Planned |
| [**0.8.x**](https://github.com/withtwoemms/ucon/milestone/6) | Pydantic Integration | Type-safe quantity validation | ⏳ Planned |

See full roadmap: [ROADMAP.md](./ROADMAP.md)

---

## Contributing

Contributions, issues, and pull requests are welcome!
Ensure `nox` is installed.
```
pip install -r requirements.txt
```
Then run the full test suite (against all supported python versions) before committing:

```bash
nox -s test
```
---

> "If it can be measured, it can be represented.
If it can be represented, it can be validated.
If it can be validated, it can be trusted."

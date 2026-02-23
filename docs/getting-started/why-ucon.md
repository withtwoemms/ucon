# Why ucon

## The Problem

Unit errors are catastrophic.

In 1999, the Mars Climate Orbiter disintegrated because one team used pound-force seconds while another expected newton-seconds. A $327 million mission lost to a unit mismatch.

In healthcare, tenfold dosing errors kill patients when milligrams become grams or vice versa. The difference between "mg/kg" and "mg/lb" can be fatal.

These aren't edge cases. They're the predictable result of treating units as afterthoughts.

## What ucon Does

ucon makes Python understand the physical meaning of your numbers.

```python
from ucon import units

length = units.meter(5)
time = units.second(2)

speed = length / time     # L / T = velocity
invalid = length + time   # raises: incompatible dimensions
```

Every operation checks dimensional structure, not just unit labels. ucon doesn't just track names—it enforces physics.

### Core Capabilities

- **Dimensional analysis** through `Number` and `Ratio`
- **Scale-aware arithmetic** via `UnitFactor` and `UnitProduct`
- **Metric and binary prefixes** (`kilo`, `kibi`, `micro`, `mebi`, etc.)
- **Uncertainty propagation** through arithmetic and conversions
- **Pydantic v2 integration** for API validation and JSON serialization
- **MCP server** for AI agent integration

## How ucon Is Different

Python has mature libraries for units—Pint, SymPy, Unum—each solving part of the problem:

| Library | Focus | Limitation |
|---------|-------|------------|
| **Pint** | Runtime conversion and compatibility | Treats quantities as decorated numbers—conversions work, but the algebra isn't type-safe |
| **SymPy** | Symbolic algebra and simplification | Not designed for runtime validation or serialization |
| **Unum** | Unit-aware arithmetic | Lacks explicit dimensional algebra or runtime introspection |

These tools can *use* units, but none explicitly represent and verify the relationships between units and dimensions.

**That's the gap ucon fills.**

ucon treats units, dimensions, and scales as first-class objects and builds a composable algebra around them:

- Represent dimensional meaning explicitly (`Dimension`, `Vector`)
- Compose and compute with type-safe, introspectable quantities (`Unit`, `Number`)
- Extend the system with custom unit registries and conversion graphs

Where Pint, Unum, and SymPy focus on *how* to compute with units, ucon focuses on *why* those computations make sense.

## Who Is ucon For

### Developers

Build applications where unit correctness matters—scientific computing, engineering tools, financial systems with currency/quantity handling.

### AI Toolchain Builders

The MCP server exposes ucon to AI agents. Claude, GPT, and other models can perform dimensionally-validated calculations without hallucinating unit conversions.

### Domain Experts

Scientists, engineers, and healthcare professionals who need their code to enforce the same dimensional rigor they apply mentally.

## Design Philosophy

> _"If it can be measured, it can be represented._
> _If it can be represented, it can be validated._
> _If it can be validated, it can be trusted."_

ucon is built on first principles:

1. **Units are algebraic objects**, not string labels
2. **Dimensions are checked at every operation**, not just at boundaries
3. **Conversions are explicit and traceable**, via injectable graphs
4. **The system is extensible**, supporting custom units and conversions

---

**Ready to start?** See [Installation](installation.md) and [Quickstart](quickstart.md).

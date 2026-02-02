# ADR-002: Composite Units and Algebraic Closure

**Status:** Accepted
**Date:** 2025-11-29
**Context:** v0.3.x Dimensional Algebra

## Summary

`CompositeUnit` (now `UnitProduct`) transforms ucon from a **registry of facts** into an **engine of derivation** by enabling algebraic composition of units.

---

## Context

Composite dimensions (e.g., velocity, acceleration, density) arise as products or quotients of base dimensions. In the continuous model, these combine algebraically in exponent space.

Example: velocity = length / time

| Quantity | Formula | Exponent Form |
|-----------|----------|---------------|
| Velocity | L/T | x_L - x_T |
| Acceleration | L/T² | x_L - 2x_T |
| Force | M·L/T² | x_M + x_L - 2x_T |
| Density | M/L³ | x_M - 3x_L |

Each component dimension (L, T, M, etc.) maintains its own graph — conversions for composite units are vector sums.

---

## Decision

Implement `CompositeUnit` (later renamed to `UnitProduct`) as a formal algebraic structure that enables unit composition, inversion, and simplification.

### What CompositeUnit Enables

| Capability | Without CompositeUnit | With CompositeUnit |
|-------------|------------------------|-----------------------|
| Unit algebra | Flat mapping of names | Free abelian group of composable morphisms |
| Derived dimensions | Pre-registered only | Algebraically inferred |
| Simplification | Manual or string-based | Symbolic, lossless cancellation |
| Conversion chaining | Requires graph heuristics | Structural traversal via decomposition |
| Reasoning | String pattern matching | Category-theoretic functor between symbolic and numeric domains |
| Expressiveness | Lookup tables | Algebraic system of morphisms |
| Extensibility | Must predefine all derived units | Derived units emerge from composition |

### CompositeUnit as Morphism

`CompositeUnit` is both an **element** and a **morphism** in the unit group:

```
f: U_1 → U_2, f(a · b) = f(a) · f(b)
```

This gives the unit algebra:
- **Associativity** (composition)
- **Identity** (`dimensionless`)
- **Inverses** (`u⁻¹`)
- **Closure** (`U × U → CompositeUnit ⊂ Unit`)

---

## Rationale

### Why the ConversionGraph Depends on It

The ConversionGraph functor acts over this unit algebra:

```
F: (Unit Algebra) → (Numeric Transformations)
```

`CompositeUnit` guarantees totality — all symbolic unit expressions can be decomposed and recomposed in graph traversal.

Example:
```python
force = units.kilogram * units.meter / (units.second ** 2)
graph.convert(force, "N")  # Converts via decomposed path
```

Without `CompositeUnit`, such a conversion is not possible, since the graph would have no way to represent composite relationships between base units.

---

## Alternatives Considered

| Library | Composite Concept | Limitations |
|----------|------------------|--------------|
| **Pint** | Implicit via registry | Composite logic is hidden, not a first-class algebraic type |
| **SymPy.physics.units** | Symbolic `Mul` trees | Algebraic but non-canonical; requires tree simplification |
| **Unyt** | Exponents over strings | Conversion graph is registry-based only; no morphic algebra |
| **Unum** | Lazy dimension algebra | Symbolic but not categorical; operations can lose context |

---

## Consequences

### Positive

- ucon can **derive** (not just define) relationships
- **Normalize** representations algebraically
- **Reason** about systems symbolically and numerically
- Forms the foundation for ConversionGraph

### Negative

- More complex internal representation than simple string-based units
- Requires understanding of algebraic structures

---

## Philosophical Note

> In most libraries, a "unit" is a label.
> In ucon, a unit is a **morphism** in a composable algebra.

`CompositeUnit` makes ucon a **structural model** of physics — not as a string or a heuristic, but as a typed algebraic expression.

# ADR-003: UnitFactor as Foundation for Composable Unit Algebra

**Status:** Accepted
**Date:** 2025-11-29
**Context:** v0.3.x Dimensional Algebra

## Summary

`UnitFactor` is introduced as a **structural atom** of the unit algebra — a pair of `(unit, scale)` that enables lossless, composable, and reversible unit expressions.

---

## Context

### The Problem: Scale Entanglement

Legacy `Unit` objects encoded scale internally:

```python
mg = Unit("mg", dimension=MASS, scale=milli)
```

This resulted in:
- Duplicate definitions (`mg` vs `milli * gram`)
- Unwanted normalization of prefixes
- Scale leaking into numeric magnitude
- Loss of provenance during calculations

### Loss of User Intent

`CompositeUnit` formerly stored raw `Unit` instances, which meant user-intent information was immediately lost:

- `mL` and `L` collapsed unpredictably
- `(mg/mL) * mL` produced incorrect quantities
- Scale information disappeared inside normalization
- Mathematically identical expressions yielded structurally different objects

---

## Decision

Introduce `UnitFactor` as:

```
UnitFactor = (unit, scale)
```

where:
- `unit` is a stable, canonical unit identity (e.g., gram, liter, meter)
- `scale` is a prefix-like symbolic modifier (e.g., milli, kilo, micro)

### Architectural Symmetry

`UnitFactor` parallels dimensional algebra:

| Dimensional Layer | Unit Layer |
|-------------------|------------|
| BasisDimension | UnitFactor |
| Vector | UnitProduct |
| Dimension | UnitForm |

**Unit Algebra (with UnitFactor)**
```
UnitProduct({ UnitFactor → exponent })
```

---

## Rationale

### What UnitFactor Enables

1. **Lossless, Predictable Unit Arithmetic**
   - User prefixes remain intact
   - Cancellation is structural, not heuristic
   - Scale never leaks into numeric magnitude

   ```python
   (g/mL) * mL  → g
   (mg/mL) * mL → mg
   ```

2. **Algebraic Normalization without Canonicalization**
   - No forced SI normalization
   - No heuristic prefix adjustments
   - No implicit conversion to base units

3. **Foundation for ConversionGraph**
   - Exposes base identity, scale prefix, and dimension as independent coordinates
   - Enables semantic conversions like `kJ·h/s → J·h/s → W·h`

---

## Consequences

### Positive

- Restores clean structural separation
- Enables lossless, composable, reversible unit expressions
- Paves the way for ConversionGraph integration
- `Unit` becomes purely declarative (no scale)

### Negative

- Some renaming churn during adoption
- Two concepts to understand (Unit vs UnitFactor)

---

## The Path Forward

1. **Unit becomes purely declarative**: `Unit(name="gram", dimension=MASS)`
2. **CompositeUnit evolves into UnitProduct**: `{ UnitFactor → exponent }`
3. **User-facing layer becomes UnitForm**: Parsing, printing, registry integration

---

## Philosophical Note

> A unit is not a label.
> It is a structural atom in an algebra whose interactions encode physical meaning.

`UnitFactor` restores this foundation.

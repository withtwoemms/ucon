# Design Note: Quantifiable and the Ucon Algebra

## Overview

`Quantifiable` defines the core behavioral contract for all measurable entities in *ucon* —
including `Number`, `Ratio`, and any future algebraic quantity (e.g. `VectorQuantity`, `TensorQuantity`, or `UncertainQuantity`).

It establishes a unified interface for interacting with physical quantities that carry *unit*,
*scale*, and *magnitude*, providing both consistency and extensibility across the library.

---

## Why It Exists

Before `Quantifiable`, `Number` and `Ratio` implemented overlapping methods such as
`evaluated`, `simplify`, and `to`, but independently. This led to duplicated logic,
ad hoc comparisons, and specialized handling in conversions and arithmetic.

`Quantifiable` resolves this by formalizing the idea of “quantity-ness” as an algebraic
typeclass — a single interface for all objects that represent measurable magnitudes.

This abstraction brings:
- **Polymorphism**: shared behavior across `Number`, `Ratio`, and future types.
- **Code reuse**: common equality, serialization, and algebraic defaults.
- **Type safety**: all measurable types must define the same contract.
- **Simplified conversions**: the conversion graph can treat all quantities uniformly.

---

## The Quantifiable Contract

Every `Quantifiable` must define:

| Method | Purpose |
|---------|----------|
| `unit` | The dimensional anchor (e.g., meter, second, volt). |
| `scale` | The exponential prefix (e.g., kilo, milli, one). |
| `evaluated` | Numeric magnitude as `quantity × scale`. |
| `simplify()` | Collapse scale to base (Scale.one). |
| `to(target)` | Convert to another unit or scale. |

Optional methods (provided by defaults):
- `__eq__()` — Dimension-aware equality.
- `__repr__()` — Standardized developer representation.
- `as_dict()` — Serialization for persistence or validation.

---

## What It Enables

### 1. Unified Algebraic Operations

Functions can now operate generically on *any measurable thing*:

```python
def normalize(q: Quantifiable) -> Quantifiable:
    return q.simplify()
```

Works for both `Number` and `Ratio` — no branching required.

### 2. Simplified Conversion Logic

The conversion system can be defined once:

```python
def convert(q: Quantifiable, target_unit: Unit) -> Quantifiable:
    factor = conversion_graph[q.unit, target_unit]
    return q.__class__(
        quantity=q.evaluated * factor,
        unit=target_unit,
        scale=q.scale
    )
```

### 3. Pydantic Integration

A single model can represent any measurable value:

```python
class Measurement(BaseModel):
    value: Quantifiable
```

This allows runtime validation of units, scales, and dimensions.

### 4. Cross-Type Extensibility

New classes like `VectorQuantity`, `MatrixQuantity`, or `UncertainQuantity`
can integrate by simply implementing the same interface.

```python
class VectorQuantity(Quantifiable):
    def evaluated(self): ...
    def simplify(self): ...
    def to(self, target): ...
```

### 5. Formalization and Verification

The Quantifiable interface defines the algebraic properties of measurable quantities,
making it possible to express invariants in TLA+, Coq, or other formal tools:

```
∀ q1, q2 ∈ Quantifiable :
    q1.unit == q2.unit ⇒ simplify(q1 + q2) == simplify(q2 + q1)
```

This provides a pathway for formal verification of `ucon`'s correctness across languages.

---

## Summary

| Benefit | Description |
|----------|--------------|
| **Polymorphism** | All measurable types share a common interface. |
| **Code Simplification** | Shared behavior eliminates duplication. |
| **Conversion Consistency** | The conversion system can treat all quantities uniformly. |
| **Type Safety** | Explicitly enforces dimensional and scale semantics. |
| **Formal Verifiability** | Provides a foundation for mathematical proofs of correctness. |
| **Extensibility** | Future types can plug into `ucon`'s algebra seamlessly. |

---

## Closing Thoughts

`Quantifiable` transforms *ucon* from a collection of data structures into a true **domain algebra** —
a framework that defines measurable quantities as first-class algebraic entities. It bridges
type safety, composability, and mathematical rigor, making future extensions — from vectorization
to distributed computation — both safe and elegant.

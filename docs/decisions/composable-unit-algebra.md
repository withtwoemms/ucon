# UnitFactor — Structure for a Composable Unit Algebra

## 1. Overview

`UnitFactor` is introduced as a **structural atom** of the unit algebra:

```
UnitFactor = (unit, scale)
```

where:
- `unit` is a stable, canonical unit identity (e.g., gram, liter, meter),  
- `scale` is a prefix-like symbolic modifier (e.g., milli, kilo, micro).

Unlike the legacy `Unit` object—which merged name, dimension, formatting hints, and scale—`UnitFactor` is **atomic**, **unambiguous**, and **hashable**.  
It acts as the _basis element_ of the unit algebra — the analogue of a "BasisDimension" (i.e. Length, Time, etc.) in dimensional algebra.

By elevating scale into a first-class algebraic component,  
`UnitFactor` restores clean structural separation and enables unit expressions that are lossless, composable, and reversible.

---

## 2. The Problem It Solves

### 2.1. Scale Entanglement in Legacy Unit Semantics

Legacy `Unit` objects encoded scale internally:

```
mg = Unit("mg", dimension=MASS, scale=milli)
```

This resulted in a system where scale and identity were inseparable, leading to:

- duplicate definitions (`mg` vs `milli * gram`),  
- unwanted normalization of prefixes,  
- scale leaking into numeric magnitude,  
- loss of provenance during calculations.

The system could _represent_ scaled units but could not _reason_ about them consistently.

**`UnitFactor` resolves this by making scale a distinct algebraic coordinate.**

---

### 2.2. Loss of User Intent During Composite Operations

`CompositeUnit` formerly stored raw `Unit` instances, which meant that user-intent information, especially regarding prefixes, was immediately lost.

Example issues:

- `mL` and `L` collapsed unpredictably
- `(mg/mL) * mL` produced incorrect quantities
- scale information disappeared inside normalization (absorbed by numeric magnitude)
- mathematically identical expressions yielded structurally different objects

By shifting to:

```
{ UnitFactor(base=gram, scale=milli) → +1,
  UnitFactor(base=liter, scale=milli) → -1 }
```

the algebra becomes **lossless**, **deterministic**, and fully **transparent**.

---

### 2.3. Embedding Interpretation Inside Algebra

Prior to `UnitFactor`, unit multiplication/division required interpretation:

- Should prefix scale merge?
- Should the result canonicalize to SI?
- Should scale affect numeric magnitude?
- Should shorthand labels collapse?

These semantic choices polluted the algebra layer.

**`UnitFactor` restores algebraic purity by keeping scale symbolic rather than interpretive.**

---

## 3. `UnitFactor` as an Atom in Unit Space

`UnitFactor` parallels dimensional algebra:

**Dimensional Algebra**
```
Vector({ BasisDimension → exponent })
```

**Unit Algebra (with `UnitFactor`)**
```
UnitProduct({ UnitFactor → exponent })
```

`UnitProduct` is the successor to `CompositeUnit`: _a free abelian product over `UnitFactor`s._

This yields a clean architectural symmetry:

| Dimensional Layer | Unit Layer (future) |
|-------------------|----------------------|
| BasisDimension | UnitFactor |
| Vector | UnitProduct |
| Dimension | UnitForm |

`UnitFactor` is the “basis atom” that makes this composite unit space possible.

---

## 4. What `UnitFactor` Enables

### 4.1. Lossless, Predictable Unit Arithmetic

- user prefixes remain intact
- cancellation is structural, not heuristic
- unit cancellation _before_ scale factor reconciliation
- algebraic operations preserve user intent
- scale never leaks into numeric magnitude

Examples:

```
(g/mL) * mL  → g
(mg/mL) * mL → mg
```

Correctness is now a mathematical property, not an accidental outcome.

---

### 4.2. Algebraic Normalization without Canonicalization

`UnitFactor` supports strict algebraic behavior:

- no forced SI normalization
- no heuristic prefix adjustments
- no implicit conversion to base units

Canonicalization moves into higher layers (`UnitForm`, `ConversionGraph`).

---

### 4.3. Foundation for ConversionGraph

`UnitFactor` exposes:

- base identity
- scale prefix
- dimension

as independent coordinates, enabling semantic conversions such as:

```
kJ·h/s → J·h/s → W·h
```

`UnitFactor` & `UnitProduct` provide the structural substrate, while `ConversionGraph` handles meaning.

---

## 5. The Path It Paves

### 5.1. Eliminating `Unit.scale`

`Unit` becomes purely declarative:

```
Unit(name="gram", dimension=MASS)
```

All scaling semantics shift into `FactoredUnit`.
Once scale is removed, `Unit` no longer participates in algebraic operations.
It becomes a **canonical identity object**, analogous to a basis `Dimension` (e.g. time, length, mass, etc.):
a stable nameable anchor used by registries, `UnitForm`, and `ConversionGraph`.

A Unit carries only semantic information (name, aliases, dimension) and does _not_ combine multiplicatively.
All algebraic behavior moves exclusively into `UnitFactor` and `UnitProduct`, allowing `Unit` to remain a pure symbolic identity within the broader type ecosystem.

---

### 5.2. CompositeUnit Evolves into UnitProduct

`CompositeUnit` is ultimately replaced by:

```
UnitProduct = { UnitFactor → exponent }
```

This yields a principled free abelian structure paralleling dimensional vectors.

---

### 5.3. User-Facing Layer Becomes UnitForm

**UnitForm** becomes the user-visible representation layer:

- parses expressions (`"g/mL"`)  
- prints canonical or preferred forms  
- integrates with registries  
- applies prefix or display policies  
- guarantees round-trip stability  

`UnitProduct` becomes the algebra;  
`UnitForm` becomes the language.

---

### 5.4. Integration with ConversionGraph

`UnitFactor` and `UnitProduct` act as the structural substrate for semantic conversions:

- J ↔ W·s  
- cal ↔ J  
- mL ↔ L  
- h ↔ 3600 s

`ConversionGraph` operates on meaning; `UnitProduct` ensures consistent structure.

---

## 6. Architectural Summary

| Layer | Role | Value |
|-------|------|--------|
| **Unit** | atomic, canonical identity | base symbol for units |
| **UnitFactor** | algebraic atom | scale-inclusive symbolic factor |
| **UnitProduct** | formal product | composable, invertible algebra |
| **UnitForm** | user-facing interface | formatting, parsing, canonicalization |
| **ConversionGraph** | semantic layer | derived-unit conversions |

For a deep dive into the new naming conventions check [this](./unit-algebra-naming.md) out

---

## 7. Philosophical Note

> A unit is not a label.  
> It is a structural atom in an algebra whose interactions encode physical meaning.

`UnitFactor` restores this foundation, revealing the future shape of `ucon`’s unit algebra.

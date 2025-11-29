# Future Naming Scheme for the `Unit` Algebra  
*(UnitFactor, UnitProduct, UnitForm)*

## 1. Context

ucon’s evolving unit system is transitioning toward a more explicit algebraic foundation.
Recent advances—particularly the introduction of `FactoredUnit`—have clarified the need for:

- cleaner separation between *atomic unit components*  
- purely algebraic composite unit structures  
- a stable, user-facing layer for rendering, parsing, and canonicalization

As ucon’s unit semantics converge toward a **free abelian group** model (mirroring the dimensional algebra), the existing naming (`CompositeUnit`, `FactoredUnit`, `Unit`) no longer captures the distinctions between:

- the algebraic substrate
- the atomic symbolic components
- the user interface layer

This document outlines a naming scheme aligned with that architecture.

---

## 2. Decision

Adopt the following naming triad for a future ucon unit algebra:

### **1. UnitFactor**  
The atomic building block of unit expressions.

- Represents a pair: _(canonical unit identity, scale)_
- Corresponds structurally to a “coordinate” or “basis element” of the unit algebra
- Replaces and generalizes the existing `FactoredUnit`
- Holds no formatting, registry, or canonicalization responsibilities
- Exists solely for algebraic manipulation

### **2. UnitProduct**  
The algebraic combination of UnitFactors.

- A mapping `{UnitFactor → exponent}`
- Represents a formal multiplicative product
- Free abelian group structure (addition/subtraction of exponents)
- Replaces the current `CompositeUnit`
- Pure algebraic core: no interpretation, no formatting, no normalization
- Positionally analogous to the dimensional `Vector` type, but specialized to units

### **3. UnitForm**  
The user-facing representation of units.

- Provides formatting, parsing, canonicalization rules, alias handling, and registry integration
- Wraps a `UnitProduct` internally
- Represents what users write and see (`"g/mL"`, `"kW·h"`, `"psi"`)
- Cleanly decouples UI semantics from algebraic mechanics
- Replaces the conceptual role of “Unit” as the object users interact with

---

## 3. Rationale

### 3.1. Why **UnitFactor**  
“Factor” is:

- algebraically accurate
- readable and intuitive
- directly compatible with the term “product”
- expressive of the role: a scaled, atomic unit element that participates in multiplication

Compared to alternatives (“Term”, “BasisUnit”, “Atom”, “Coordinate”),  
**UnitFactor** strikes the ideal balance between mathematical precision and everyday usability.

---

### 3.2. Why **UnitProduct**  
The algebra underlying ucon unit combinations is not vector algebra  
(in the sense of magnitude-1 unit vectors), but **formal multiplicative algebra**.

A UnitProduct is:

- a product of UnitFactors
- a free abelian group element
- the natural analogue of a symbolic monomial

“Product” is accessible to users without sacrificing correctness.  
It avoids the misleading connotation of “vector” and is friendlier than “monomial.”

---

### 3.3. Why **UnitForm**  
The system needs a distinct layer that:

- users interact with
- ties into the registry
- controls printing and parsing
- decides when/how to reflect prefixes
- chooses canonical representations
- remains stable across refactors

“UnitExpression” was serviceable but generic.  
“UnitForm” is:

- concise
- semantically clean
- visually and conceptually distinct from algebraic layers
- evocative of representation rather than structure

It completes the tiered architecture:

```
UnitFactor    → structural atom
UnitProduct   → algebraic composite
UnitForm      → user-facing representation
```

---

## 4. Consequences

### Positive

- Clear conceptual separation between algebra and user semantics
- Naming aligns with physical intuition and mathematical structure
- Improves API clarity and documentation readability
- Prepares the codebase for future features:
  - ConversionGraph
  - Semantic canonicalization
  - Unit registry enhancements
  - Parsing/formatting improvements

### Neutral/Deferred

- No immediate refactor is required; this ADR guides future work  
- CompositeUnit and FactoredUnit can coexist temporarily during transition
- Existing APIs remain intact until migration pathways are established

### Negative

- Some renaming churn is expected during adoption
- Downstream references to “CompositeUnit” and “FactoredUnit” will need updating

---

## 5. Alternatives Considered

- **UnitMonomial / UnitTerm**  
  - Mathematically elegant but feels overly academic
- **UnitCoordinate / UnitVector**  
  - Accurate but too abstract, and “unit vector” is overloaded in linear algebra
- **UnitExpression**  
  - Adequate, but less crisp than “UnitForm” as a representation-layer concept
- **Retaining existing names**  
  - Would perpetuate conceptual muddiness as the system grows

---

## 6. Future Work (Nonbinding)

- Introduce `UnitFactor` and `UnitProduct` in parallel with existing structures
- Evolve `UnitForm` as the primary user-facing unit API
- Gradually refactor internal algebra toward the new architecture
- Propose complementary ADRs covering:
  - CanonicalUnit identity objects
  - Registry architecture
  - ConversionGraph integration
  - Unit parsing and pretty-printing models

---

## 7. Acknowledgements

This naming scheme emerged from design discussions surrounding the FactoredUnit refactor, the need for scale-preserving operations, and the broader goal of unifying unit algebra with dimensional algebra in ucon’s long-term architecture.

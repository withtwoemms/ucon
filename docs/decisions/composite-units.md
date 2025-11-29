# Unit Combination and Algebraic Closure in `ucon`

## 1. Composite Units

Composite dimensions (e.g., velocity, acceleration, density) arise as products or quotients of base dimensions.
In the continuous model, these combine algebraically in exponent space.

Example: velocity = length / time

$$
V = \frac{L}{T} = a^{x_L - x_T}
$$

If the length and time graphs are independent CCGs, their exponents combine by **subtraction of vectors**.
This allows multi-dimensional conversion to be expressed purely algebraically.

| Quantity | Formula | Exponent Form |
|-----------|----------|---------------|
| Velocity | L/T | \( $x_L - x_T$ \) |
| Acceleration | L/T² | \( $x_L - 2x_T$ \) |
| Force | M·L/T² | \( $x_M + x_L - 2x_T$ \) |
| Density | M/L³ | \( $x_M - 3x_L$ \) |

Each component dimension (L, T, M, etc.) maintains its own graph — conversions for composite units are vector sums.

---

## 2. What Would Be Impossible Without `CompositeUnit`

Without `CompositeUnit`, **ucon would be descriptive, not algebraic.**  
It could *store* conversions but not *derive* them.  

| Capability | Without `CompositeUnit` | With `CompositeUnit` |
|-------------|------------------------|-----------------------|
| Unit algebra | Flat mapping of names | Free abelian group of composable morphisms |
| Derived dimensions | Pre-registered only | Algebraically inferred |
| Simplification | Manual or string-based | Symbolic, lossless cancellation |
| Conversion chaining | Requires graph heuristics | Structural traversal via decomposition |
| Reasoning | String pattern matching | Category-theoretic functor between symbolic and numeric domains |
| Expressiveness | Lookup tables | Algebraic system of morphisms |
| Extensibility | Must predefine all derived units | Derived units emerge from composition |

> `CompositeUnit` transforms ucon from a **registry of facts** into an **engine of derivation.**

---

## 3. CompositeUnit, Exponent, and Scale: Cohesive Closure

| Role | Domain | Operation | Closure Guarantee |
|------|---------|------------|------------------|
| **Exponent** | Algebra | Powers of numeric bases (10, 2, etc.) | Defines magnitude algebra |
| **Scale** | Ontology | Named prefixes for exponents | Names exponent values |
| **Unit** | Ontology | Typed measure symbol | Couples dimension + scale |
| **CompositeUnit** | Algebra on units | Product, quotient, powers | Closes the group |

This creates the **closure chain**:

$$
\text{Exponent} \Rightarrow \text{Scale} \Rightarrow \text{Unit} \Rightarrow \text{CompositeUnit}
$$

Each layer embeds the previous one, while adding new semantics (naming, dimension, composability).

---

## 4. CompositeUnit as Morphism

`CompositeUnit` is both an **element** and a **morphism** in the unit group:

$$
f: U_1 \to U_2, \quad f(a \cdot b) = f(a) \cdot f(b)
$$

This gives the unit algebra:

- **Associativity** (composition)
- **Identity** (`dimensionless`)
- **Inverses** (`u⁻¹`)
- **Closure** (`U × U → CompositeUnit ⊂ Unit`)

It forms a **monoidal category** of units where:
- objects = base units,
- morphisms = composite transformations,
- functors = conversions between systems (SI, CGS, Imperial).

---

## 5. Why the ConversionGraph Depends on It

The ConversionGraph functor acts over this unit algebra:

$$
F: (\text{Unit Algebra}) \to (\text{Numeric Transformations})
$$

`CompositeUnit` guarantees totality — all symbolic unit expressions can be decomposed and recomposed in graph traversal.

Example:
```python
force = units.kilogram * units.meter / (units.second ** 2)
graph.convert(force, "N")  # Converts via decomposed path
```

Without `CompositeUnit`, such a conversion is not possible,  
since the graph would have no way to represent composite relationships between base units.

---

## 6. How Competitors Handle This (or Don’t)

| Library | Composite Concept | Mechanism | Limitations |
|----------|------------------|------------|--------------|
| **Pint** | Implicit composite via `Quantity` + registry | Tuple of (unit, exponent) pairs parsed from strings | Composite logic is hidden, not a first-class algebraic type; no symbolic morphisms |
| **SymPy.physics.units** | Composition through symbolic `Mul(Unit, Unit)` trees | Full symbolic representation | Algebraic but non-canonical; requires tree simplification and lacks registry consistency |
| **Unyt** | `UnitRegistry` + array wrapper | Exponents over strings | Conversion graph is registry-based only; no morphic algebra |
| **Astropy.units** | `UnitBase` and compound units via operator overloads | Functional for end users | No first-class algebra for composition; context-dependent simplification |
| **Unum** | Explicit *universal number* with lazy dimension algebra | Arithmetic objects track dimension exponents | Symbolic but not categorical: lacks conversion composition semantics and no functorial conversion; operations can lose context |
| **ucon** | **`CompositeUnit` as morphism in a composable unit group** | Explicit algebraic closure; conversion is a functor | Symbolic reasoning, compositional simplification, direct ConversionGraph integration |

### 🔍 Commentary on *Unum*
- **Strength:** Unum pioneered embedding dimensional arithmetic directly into number objects (`Unum(3, 'm/s²')`).
- **Weakness:** Its algebra is _monolithic_, coupling value, dimension, and conversion rules in one type.
  - There’s no separation of concerns — no morphism layer between symbolic representation and numeric transformation.
  - Conversions are _eager_ rather than structural, meaning they cannot be composed functorially.
- **Contrast with ucon:**  
  ucon’s `CompositeUnit` isolates the symbolic structure from numeric evaluation.  
  This allows deferred evaluation, symbolic simplification, and graph-based reasoning across systems of units.  
  Thus, ucon’s algebra is **refactorable and extensible**, while unum’s is **monolithic and eager**.

---

## 7. Philosophical Summary

> In most libraries, a “unit” is a label.  
> In ucon, a unit is a **morphism** in a composable algebra.

`CompositeUnit` makes ucon a **structural model** of physics:

$$
\frac{L}{T^2} \Rightarrow \text{Acceleration}
$$

not as a string or a heuristic, but as a typed algebraic expression.

It allows ucon to:
- **derive** (not just define) relationships,
- **normalize** representations,
- **reason** about systems symbolically and numerically.

Thus:
> ucon is not merely a _unit-aware computation library_ — it is a **dimensional reasoning framework.**

---

## 7. Next Steps (Implementation Implications)

1. Keep `CompositeUnit` algebraically pure (no conversion logic).  
1. Allow `Unit` and `Scale` to compose naturally.  
1. Ensure simplification of reciprocal terms (`g·mL/mL → g`).  
1. Use canonical hashing for composite signatures.  

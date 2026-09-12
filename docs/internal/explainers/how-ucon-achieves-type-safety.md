# How `ucon` Achieves Type Safety

`ucon`'s type safety doesn't rely on Python's static type system — it is
**algebraic** and **semantic**, not syntactic. Correctness isn't checked
after the fact; it is prevented by construction, layer by layer. Each
layer refuses a class of error the layers below cannot see.

As of v2.1.x there are four enforcement layers, with two more scheduled
(see the trajectory note at the end):

1. **Dimensional algebra** — `Vector` and `Dimension`
2. **The kind lattice** — `Kind`, `KindLattice`, formulas
3. **Validated transformation** — the conversion graph and its `Map`s
4. **Coercion and integration** — `@enforce_dimensions`, Pydantic

---

## 1. Dimensional algebra (`Vector` and `Dimension`)

At the foundation is the **`Vector`**: exponents over the base components
of a **`Basis`** (SI by default; CGS, Natural, Planck, Atomic, and
user-extended bases are first-class, related by `BasisTransform`s). A
`Dimension` wraps a vector; dimensional arithmetic is vector arithmetic:

```python
>>> from ucon.dimension import Dimension
>>> Dimension.length / Dimension.time
Dimension(velocity)
```

Every `Unit` carries its `Dimension`; every `Number` binds a quantity to
a `Unit`. Incompatible combinations refuse at the moment of combination:

```python
>>> from ucon import Number, units
>>> Number(5, units.meter) / Number(2, units.second)
<2.5 m/s>
>>> Number(5, units.meter) + Number(2, units.second)
TypeError: Cannot add Numbers with different dimensions: ...
```

**What this layer catches:** physically meaningless combinations —
length + time, money + meters. **What it cannot see:** two quantities
with the *same* dimension that mean different things.

## 2. The kind lattice (`Kind`, `KindLattice`)

Dimension is too coarse for safety: absorbed dose (Gy) and dose
equivalent (Sv) are both L²·T⁻²; torque and energy are both M·L²·T⁻².
The **kind lattice** discriminates within a dimension: kinds form trees
per dimension fiber, and addition consults the lowest common ancestor's
`join_policy`:

```python
>>> gy = Number(1.5, units.gray,    kind="absorbed_dose")
>>> sv = Number(2.0, units.sievert, kind="dose_equivalent")
>>> gy + sv            # siblings under a refuse-join parent
JoinRefused: Cannot join kinds 'absorbed_dose' and 'dose_equivalent': ...
>>> a = Number(1, units.one, kind="apples")   # disjoint trees (v2.1.5+)
>>> gy + a
DisjointKinds: Kinds ... have no common ancestor
```

Legitimate cross-kind operations go through **formulas**
(`FormulaRegistry`): `absorbed_dose × radiation_weighting_factor →
dose_equivalent` is a declared, named transformation — not an accident of
matching vectors.

**What this layer catches:** same-dimension, different-sort mixing.
**What it cannot see:** the numeral scheme itself (see the trajectory
note).

## 3. Validated transformation (the conversion graph)

Conversions are not ad-hoc scale factors. They are **registered
morphisms** on a `ConversionGraph`: `LinearMap`, `AffineMap` (°C ↔ K),
`LogMap` (dB, nepers), each with a validated inverse.

```python
from ucon.graph import get_default_graph

graph = get_default_graph().copy()
graph.add_edge(src=units.celsius, dst=units.kelvin,
               map=AffineMap(a=1.0, b=273.15))
```

The graph enforces its own invariants:

- **Dimension agreement** — an edge between incompatible dimensions
  refuses (`DimensionMismatch`), unless an explicit `BasisTransform`
  licenses a cross-basis rebase (`RebasedUnit`).
- **Cyclic consistency** — registering an edge whose round-trip is not
  the identity raises `CyclicInconsistency`: the graph refuses to hold
  contradictory conversion facts.
- **Definitional anchoring** — every purely multiplicative unit carries
  an exact `BaseForm` (prefactor × base-unit factors), CI-verified
  against a BFS oracle (`make base-forms-check`), so conversion factors
  are *derived from definitions* rather than accumulated as literals.
  Since v2.1.7, `base_form is None` means exactly one of two things: no
  linear factorization exists (affine/logarithmic charts), or the
  factorization is dimensionally ill-typed across bases (EM CGS units) —
  never "not filled in."
- **Scoped conversion** — `ConversionContext` licenses conversions that
  are only true given extra data (spectroscopy's λ ↔ ν via `c`), valid
  only inside `using_context(...)`. Absence of a context is a refusal,
  not a default.

## 4. Coercion and integration

- **`@enforce_dimensions`** validates `Number[Dimension.x]` annotations
  at call time and coerces cross-basis arguments to named SI units
  (erg → joule, poise → pascal·second) — graph route preferred,
  algebraic `base_form` decomposition as fallback.
- **Pydantic integration** carries the same constraints into configs and
  APIs (`DimensionConstraint`, `KindConstraint`).

---

## Honesty: what is *not* yet caught

Stating the boundary is part of the safety story
(`../decisions/009-turnstile.md` §2 documents it as the motivating
defect): today's arithmetic consults dimension and kind, **not the
numeral scheme**. `2 × Number(20, units.celsius)` returns 40 °C even
though the result is chart-dependent; unkinded `1 Gy + 1 Sv` admits if
kinds are not declared. Kind safety is opt-in by declaration; scheme
safety is scheduled.

## Trajectory

The layers above are the shipped half of a six-layer design:

| Layer | Status |
|---|---|
| dimension | shipped |
| kind | shipped (v2.0+; typed disjoint refusals v2.1.5) |
| conversion graph invariants | shipped |
| **chart** (numeral-scheme admissibility: interval/log refusals) | declared field v2.2.0; enforced v3.1.0 (`../decisions/009-turnstile.md`, `../decisions/010-chart-nomenclature.md`) |
| **aspect** (provenance/convention discrimination) | v2.3.0 (`../decisions/008-aspect-stratum.md`) |
| coercion / integration | shipped |

---

> **`ucon` doesn't just track units — it encodes meaning.** Each layer
> refuses a class of confusion the others cannot express, and every
> refusal names what it caught.

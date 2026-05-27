# ADR-007: Bridge as Cross-System Value-Movement Primitive

**Status:** Accepted
**Date:** 2026-05-26
**Context:** v2.0 UnitSystem promotion

## Summary

`Bridge` is introduced as the **only sanctioned primitive for moving a
`Number` between two `UnitSystem` instances when the move is not
trivially expressible as `dst.adopt(n)`**. It handles synonym renames,
cross-basis movement, and combinations of the two, with all invariants
validated at construction time.

---

## Context

### The Problem: Multiple Systems in One Process

v2.0 promotes `UnitSystem` to a first-class value type with an algebra
(`extend`, `restrict`, `merge`, `with_*`) and relations (`subsystem_of`,
`compatible_with`, `diff`). Once `UnitSystem` is a value, applications
will hold more than one at the same time:

- a library defines its own `UnitSystem` and exposes APIs typed against it
- an application composes several such libraries
- a single application carries multiple subsystems / locales / bases
- serialization round-trips a `Number` through TOML and back into a
  system whose `Unit` objects are not identical to the producer's

A `Number` instance carries direct references to `Unit` objects owned
by one specific `UnitSystem`. Moving it across a boundary is a real
operation that the library must offer as a typed, validated primitive.

### Why Movement is Non-Trivial: Object Identity

`Number` holds direct references to `Unit` instances — not just names.
Several mechanisms in `ucon` rely on `Unit` *object identity*, not
structural equality:

- conversion-graph edges are keyed by `Unit` identity;
- per-instance caches (e.g. `_algebra_cache`) are keyed by identity;
- active-system routing in v2.0 dispatches through the active
  `UnitSystem`'s owned `Unit` objects;
- subsystem coherence (after `restrict`, `extend`, `merge`) depends
  on `Number` instances referencing the *current* system's `Unit`
  objects, not stale parents.

Therefore moving a `Number` across systems is not a relabeling — it
is a *reference rebind*. Even when the source and destination systems
are structurally identical, a `Number` produced against one will not
satisfy identity checks in the other until its `Unit` references are
updated to point at the destination's owned objects.

### Two Movement Scenarios

| | condition | semantics |
|---|---|---|
| `adopt` | names match, same base | pure reference rebind; raises if name missing |
| `Bridge` | names diverge, or basis differs | validated synonym / transform application |

The `adopt` scenario is satisfied by `UnitSystem.adopt(n)`. The
`Bridge` scenario is the subject of this ADR.

---

## Decision

Introduce `ucon.system.Bridge` as a frozen dataclass:

```
Bridge(
    src: UnitSystem,
    dst: UnitSystem,
    rename: Mapping[str, str] = {},
    basis_transform: BasisTransform | None = None,
)
```

with `apply(n)`, `inverse()`, and `__matmul__(other)`.

### Invariants

- **Synonym-only renames.** For every `(a, b)` in `rename`,
  `src.units[a]` and `dst.units[b]` represent the same physical unit:
  same `dimension` (or matching under `basis_transform`), same
  `base_form`. Definitional differences (e.g. `meter ↔ foot`) are
  rejected at construction with `InvalidRename`; they belong to the
  conversion graph, not to `Bridge`.

- **Apply order is pinned.** `apply(n)` runs
  `rename → basis_transform → identity-bind`. The layers commute under
  the synonym constraint; the order is fixed for trace-readability.

- **Construction-time validation.** All invariants are checked in
  `__post_init__`. A misconfigured `Bridge` cannot exist. Validation
  cost is paid once per bridge, not once per `apply()`.

- **Algebraic closure.** Bridges form a category:
  identity is `Bridge(src=s, dst=s)`; composition is `b2 @ b1` with
  `b1.dst is b2.src` required and re-validation against the final
  endpoints; inverse is `b.inverse()`, exact in the name layer.

---

## Diagrams

### Single bridge

```
          rename             basis_transform        identity-bind
          (names)            (numbers)              (object refs)
            │                    │                      │
            ▼                    ▼                      ▼
   ┌─────────────┐       ┌──────────────┐       ┌─────────────┐
   │  src        │──────▶│  intermediate│──────▶│  dst        │
   │  UnitSystem │       │  (transient) │       │  UnitSystem │
   └─────────────┘       └──────────────┘       └─────────────┘
        Number                                       Number
        @ src.units                                  @ dst.units
```

### `apply` pipeline

```
                ┌─────────────────────────────────────────┐
                │             Bridge.apply(n)             │
                │                                         │
   n: Number    │   ┌────────┐   ┌─────────────┐   ┌────┐ │   n': Number
   @ src   ────▶│──▶│ rename │──▶│ basis_xform │──▶│bind│─┼──▶ @ dst
                │   └────────┘   └─────────────┘   └────┘ │
                │     name         numeric          ref   │
                │     layer        layer            layer │
                └─────────────────────────────────────────┘
```

### Composition `b2 @ b1`

```
                              composition validates
                              against final endpoints
                                        ▼
   ┌────────┐  b1   ┌────────┐  b2   ┌────────┐
   │   A    │──────▶│   B    │──────▶│   C    │
   └────────┘       └────────┘       └────────┘
        │                                  ▲
        └──────────  b2 @ b1  ─────────────┘
                  (single bridge,
                   B vanishes from the type)
```

### Topology (hub-and-spoke)

```
                    ┌──────────┐
                    │ canonical│
                    └──────────┘
                   ╱     │     ╲
            b_A,c╱    b_B,c│   b_D,c╲
                ╱          │         ╲
        ┌──────┐     ┌──────┐     ┌──────┐
        │  A   │     │  B   │     │  D   │
        └──────┘     └──────┘     └──────┘

   Any edge A→D synthesized on demand:
     A_to_D = b_D,c.inverse() @ b_A,c
```

### `adopt` vs `Bridge` decision

```
              Need to move Number n from src → dst?
                              │
                              ▼
              ┌─────────────────────────────────┐
              │ Same names? Same base?          │
              └─────────────────────────────────┘
                  yes │              │ no
                      ▼              ▼
              ┌──────────────┐  ┌──────────────────────────┐
              │ dst.adopt(n) │  │ Names diverge or basis    │
              │ pure rebind  │  │ differs?                  │
              │ no math      │  └──────────────────────────┘
              └──────────────┘     │              │
                                   ▼              ▼
                              synonyms?      definitional
                                  │           difference?
                                  ▼              │
                          ┌──────────────┐       ▼
                          │   Bridge     │  Number.to(...)
                          │ rename +     │  (conversion
                          │ basis_xform  │   graph)
                          └──────────────┘
```

---

## Use Cases

1. **Locale / spelling divergence.** UK (`metre`, `litre`, `gramme`)
   feeding a US-spelling pipeline (`meter`, `liter`, `gram`).
2. **Domain vocabulary swap.** Clinical `mmHg` ↔ engineering `torr`.
3. **Cross-basis movement.** `NATURAL` simulation values feeding an
   SI reporting layer; `rename` empty, work in `basis_transform`.
4. **Cross-basis and renaming.** CGS (`dyne`, `erg`, `gauss`) ↔ SI
   (`newton`, `joule`, `tesla`); names diverge, basis differs.
5. **Serialization round-trip.** Producer writes with `bridge_out`;
   consumer reads with `bridge_out.inverse()`. Exact in the name layer.
6. **Package fan-in.** Host application links two third-party `ucon`
   packages; one `Bridge` becomes the documented interop edge.
7. **Restriction with renaming.** Composition re-validates that
   rename targets survive a subsequent `restrict`.
8. **Versioned migration.** Library renames a unit between majors
   (`elementary_charge → e_charge`); downstream values move forward
   without conversion math.
9. **Hub-and-spoke topology.** Teams each define a `Bridge` to a
   canonical system; A→B is `B_to_canonical.inverse() @ A_to_canonical`,
   validated at composition.

---

## Counterfactual: ucon Without `Bridge`

This section describes the realistic state of the project if we
declined to add this primitive. It is what the surface area degrades
into when the algebra is missing.

### 1. Callers reach across boundaries by hand

The only way to move a `Number` between systems with diverging names
becomes:

```python
# anti-pattern: no validation, no algebra
new_unit = dst_system.units[name_map[n.unit.name]]
n_moved = Number(quantity=n.quantity, unit=new_unit, uncertainty=n.uncertainty)
```

Every caller hand-rolls this. There is no central place where the
synonym constraint is enforced. The first time someone writes
`name_map = {"meter": "foot"}` — a perfectly natural-looking typo —
the library produces silently wrong answers. `meter` and `foot`
share the dimension `length`; nothing catches it.

### 2. Validation moves to runtime — or disappears

`Bridge` validates at `__post_init__`. Without it, validation either:

- happens at every call site (boilerplate, easy to forget); or
- happens at value time, after a `Number` has already been
  constructed against the wrong `Unit` (loud failures deep in
  pipelines with no clear blame); or
- doesn't happen, and the wrong number is reported.

`InvalidRename` (with its `src_name`, `dst_name`, `reason` attributes)
only makes sense as the rejection signal of a construction-time
validator. Without `Bridge`, there is no place for it to live.

### 3. Cross-basis movement has no home

`BasisTransform` exists, but applying it to a `Number` requires a
caller to pull the value, rewrite the dimension vector, look up
matching `Unit` objects in the destination, and rebuild the `Number`.
Every caller writes this; the steps are easy to reorder and the
ordering matters for trace-readability. `Bridge.apply` pins the order
once.

### 4. No algebra over multi-system topologies

Without `@` and `inverse()`, multi-hop moves become sequences of
statements:

```python
n_mid = step1_apply(n)
n_dst = step2_apply(n_mid)
```

Endpoint mismatches fail at the second `apply()`, after a real
intermediate value has been produced. There is no way to ask "is
this pipeline well-formed?" without running data through it. The
hub-and-spoke topology (use case 9) is not expressible — each pair of
systems needs its own hand-rolled cross-mapping, *O(n²)* in the
number of systems.

### 5. `adopt`/`Bridge` dichotomy collapses

`adopt` and `Bridge` together define a clean split: names-match-no-math
vs validated-structured-movement. Without `Bridge`, `adopt` either has
to grow rename/basis-transform parameters (becoming `Bridge` with a
different name and weaker validation), or callers fall back to ad-hoc
constructions for the structured case. The meaningful distinction
collapses into one overloaded function with a harder-to-state contract.

### 6. Definitional/synonym confusion bleeds into the conversion graph

`Bridge`'s synonym constraint is what keeps the conversion graph
honest. Definitional differences belong to the graph; synonym/basis
differences belong to `Bridge`. Without `Bridge`, there is pressure
to add "name aliases" or "system bridges" to the conversion graph
itself, which pollutes it with non-physical edges, couples cross-system
interop to single-system conversion logic, and makes the graph harder
to reason about and harder to serialize.

### 7. Replacement cost is concentrated, not amortized

Hand-rolled moves pay the validation and rebinding cost on every
call. `Bridge` pays validation once at construction and reuses the
result. For pipelines that move many `Number` instances between the
same two systems (the common production case), the difference
compounds.

### Net Effect

Without `Bridge`, `ucon` would still convert units correctly within
a single `UnitSystem`. It would lose the ability to be a structured
*interop substrate* between systems. The library would work for
single-package use; it would degrade sharply at the boundaries where
real applications actually live.

---

## Alternatives Considered

### 1. Overload `UnitSystem.adopt` with renames and `basis_transform`

**Rejected because:** conflates the trivial case (pure rebind, no
validation needed) with the structured case (synonym validation,
basis math). The trivial case becomes more expensive; the structured
case loses its dedicated type and the construction-time validation
surface.

### 2. Express cross-system movement through the conversion graph

**Rejected because:** pollutes the graph with non-physical edges
(name synonyms, basis transforms) and couples interop to physics.
Definitional differences and synonym/basis differences are
categorically different operations and should not share a mechanism.

### 3. Leave it to callers

**Rejected because:** produces *O(n²)* hand-rolled cross-mappings
with no shared validation, recreates the same boilerplate at every
boundary, and pushes errors to value time. The counterfactual section
above describes the failure mode in detail.

### 4. A more general "system transform" type covering arbitrary mappings

**Rejected for v2.0 because:** the synonym-only constraint is what
makes construction-time validation tractable and what keeps the
distinction from the conversion graph sharp. A more general mechanism
would weaken both guarantees. Revisitable in a future release if a
concrete use case demands it.

---

## Consequences

### Positive

- Cross-system movement has a single, typed, validated entry point.
- Errors move from value time to construction time
  (`InvalidRename` in `__post_init__`).
- Multi-hop topologies are expressible algebraically (`@`, `inverse()`).
- The conversion graph stays focused on physics; interop is a separate
  concern with a separate primitive.
- The `adopt`/`Bridge` dichotomy maps cleanly onto the two real
  scenarios; neither primitive carries the other's weight.

### Negative

- New public symbols (`Bridge`, `InvalidRename`) — surface area to
  document and maintain.
- The synonym constraint is strict by design; users who want to
  cross definitional differences must learn to reach for the conversion
  graph instead. This is a teaching cost.
- Composition re-runs validation, which can surface late errors during
  refactors when intermediate systems change. This is the intended
  behavior; it is still a behavior users must understand.

### Neutral

- `BasisTransform` composition semantics are inherited; no new
  category-theoretic content is introduced beyond what already exists
  in `ucon.basis`.

---

## Philosophical Note

> A `UnitSystem` boundary is not an obstacle.
> It is a place where invariants are checked and structure is named.

`Bridge` makes the boundary itself a first-class object — composable,
invertible, validated at construction. Interop becomes algebra.

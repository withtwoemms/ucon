# Toward a Unified Algebraic Core for `ucon`

## Table of Contents

1. [Goals](#goals)
1. [Guiding Principles](#guiding-principles)
1. [Release Roadmap Overview](#release-roadmap-overview)
1. [Risk & Mitigation Summary](#risk--mitigation-summary)
1. [Success Criteria](#success-criteria)
1. [Open Questions](#open-questions)

## Context
The current public `ucon` modules grew organically: algebraic primitives, dimension definitions, unit metadata, and quantity arithmetic all evolved in place.
As the project expands to richer quantity types and more conversion features, the legacy layout makes it difficult to reason about cross-module dependencies, implement clean prefix/scale semantics, or deliver predictable pretty-printing.
This document outlines how to graduate recent prototype work into the mainline library with a series of safe, releasable steps.

---

## Goals

- Establish a single algebraic foundation so every dimension, unit, and quantity composes from the same primitives without circular imports.
- Unify scale and unit semantics so prefix math happens once and carries through all quantity operations and displays.
- Deliver canonical unit algebra (automatic cancellation, normalized shorthands)
  to users while preserving backwards compatibility during the transition.
- Create a roadmap that keeps the library shippable at each milestone, with
  clear deprecation guidance and minimal ecosystem disruption.

---

## Guiding Principles

- **Incrementalism:** each release is self-contained, backwards compatible, and
  surfaces deprecation warnings where needed.
- **Separation of concerns:** algebraic helpers, unit metadata, and quantity
  logic live in layered modules to prevent future tangles.
- **User empathy:** external behaviour changes (e.g., repr output) are opt-in
  until the ecosystem is ready, and documentation highlights migration steps.
- **Future readiness:** the landing zone must accommodate new quantity types
  (vectors, tensors, uncertainty) without re-litigating scale/dimension design.

---

## Release Roadmap Overview

1. [**Algebra Extraction**](#release-1--algebra-extraction) – carve shared primitives into `ucon.algebra`.
2. [**Dimension Enhancements**](#release-2--dimension-enhancements) – add runtime resolution and exponentiation.
3. [**Unit Representation Refresh**](#release-3--unit-representation-refresh) – align scale-aware units and prefix logic.
4. [**Composite Units**](#release-4--composite-units) – introduce canonical composite handling and reprs.
5. [**Quantity & Ratio Unification**](#release-5--quantity--ratio-unification) – rework quantity arithmetic atop the new core.

### Release 1 — Algebra Extraction

**Objective:** create a reusable algebra layer (housing `Vector`, `Exponent`, and beyone) that both other modules can depend on without behavioural change.

- **Scope**
  - Move `Vector` & `Exponent` definitions into `ucon.algebra`.
  - Re-export the primitives via existing modules (`ucon.dimension`, `ucon.core`)
    so public imports stay stable.
- **Justification**
  - Eliminates duplication of exponent logic and prepares for shared updates
    (e.g., scalar multiplication).
  - Enables subsequent releases to rely on the same arithmetic core.
- **Compatibility Strategy**
  - No API changes; introduce deprecation notices for direct instantiation from
    legacy modules pointing to the new home.
  - Ship additional unit tests verifying old import paths still work.

### Release 2 — Dimension Enhancements

**Objective:** enrich `Dimension` with dynamic resolution and exponent support,
removing the need for ad-hoc enum extensions.

- **Scope**
  - Add `_resolve` helper and `__pow__` on `Dimension`.
  - Update legacy `ucon.dimension.Dimension` to delegate to the new behaviour.
- **Justification**
  - Allows runtime-derived composite dimensions to remain stable and printable.
  - Supports exponentiation required for clean composite-unit canonicalization.
- **Compatibility Strategy**
  - Keep enum member names unchanged.
  - Provide migration note explaining that dynamically created dimensions now
    produce deterministic names (e.g., `derived(Vector(...))`).

### Release 3 — Unit Representation Refresh

**Objective:** align units and scales so prefix math is applied once at unit
construction time rather than per-quantity operation.

- **Scope**
  - Introduce the new `Unit` structure with aliases, base name, dimension, and
    scale.
  - Teach `Scale.__mul__` to decorate `Unit` instances.
  - Keep legacy `Number.scale` field but mark it deprecated, deriving from the
    unit where possible.
- **Justification**
  - Centralizes prefix application, enabling canonical shorthands.
  - Reduces duplicated handling of scale factors during arithmetic.
- **Compatibility Strategy**
  - `Scale * Unit` becomes the preferred API but `Number(scale=...)` continues
    to work; emit warnings when scale and unit disagree.
  - Document how to migrate custom units to the new constructor arguments.

### Release 4 — Composite Units

**Objective:** make compound-unit algebra first-class, ensuring cancellation and
display logic are consistent across conversions.

- **Scope**
  - Add `CompositeUnit` that merges duplicate factors, strips dimensionless
    terms, and computes normalized shorthands.
  - Update unit arithmetic (`__mul__`, `__truediv__`, `__pow__`) to return the
    new type.
- **Justification**
  - Allows expressions like `(g/mL) * (mL)` to simplify to `g` automatically.
  - Provides stable hashing/equality for composite units, vital for caches.
- **Compatibility Strategy**
  - Initial repr retains legacy formatting behind a feature flag or environment
    variable; default to legacy strings until clients opt in.
  - Add regression tests for string representations and hash behaviour.

### Release 5 — Quantity & Ratio Unification

**Objective:** rebuild `Number` and `Ratio` atop the new unit semantics so that
all arithmetic, comparisons, and reprs are canonical.

- **Scope**
  - Derive quantity scale from the unit, eliminating the redundant `scale`
    attribute.
  - Route `Number * Ratio` through ratio logic; clean up `Ratio.__mul__` to
    normalize denominator units.
  - Adopt the new pretty-printing pipeline that evaluates ratios before repr.
- **Justification**
  - Delivers the user-facing wins (e.g., `<6.238 g>`, `<3 m/s>`) promised by the
    earlier releases.
  - Prepares the codebase for future quantity families without further rewrites.
- **Compatibility Strategy**
  - Provide helper constructors or shims for code still passing explicit scale
    values.
  - Highlight behaviour differences (repr changes, stricter equality) in release
    notes and migration guide.

---

## Risk & Mitigation Summary

- **Behavioural regressions:** maintain dual-implementation tests (legacy vs.
  new) until the final release, ensuring parity.
- **Third-party integrations:** publish early alpha packages or feature flags so
  downstream consumers can validate ahead of time.
- **Documentation drift:** update API references and design notes at each step,
  with a cumulative migration guide linked from the README.

---

## Success Criteria
- All unit arithmetic (`Number`, `Ratio`, `CompositeUnit`) produces canonical
  representations without caller intervention.
- No circular imports remain between dimension, unit, and quantity modules.
- Public API consumers can adopt the new semantics gradually via logged
  deprecations and migration docs.
- The architecture supports future quantity types on top of the unified core
  with minimal additional scaffolding.

---

## Open Questions

- Level of feature flagging needed for repr changes (opt-in vs. opt-out).
- Whether to backport composite-unit hashing to the legacy modules for parity.
- Timing for removing deprecated scale arguments on `Number`.
---

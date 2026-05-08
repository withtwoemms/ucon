# ucon Roadmap

> *Major milestones from foundation through v2. `CHANGELOG.md` is the source of truth for incremental updates.*

---

## Vision

ucon is a dimensional analysis library for engineers building systems where unit handling is infrastructure, not just convenience.

**Target users:**

- Library authors embedding unit handling without global state
- Domain specialists defining dimensions that match their field
- Modern stack developers wanting first-class Pydantic, Polars, MCP support

---

## How This Document Relates to CHANGELOG

This roadmap tracks **major milestones** on the path to v2. For incremental updates — every patch and minor release, including bug fixes, new units, parser refinements, and small API additions — see `CHANGELOG.md`. The CHANGELOG is the source of truth; this roadmap exists only to surface the structural waypoints that connect releases into a coherent trajectory.

---

## Milestone Timeline

| Version | Milestone | Status |
|---------|-----------|--------|
| v0.x | Algebraic foundation: Unit/Scale separation, `UnitProduct`, `ConversionGraph`, dimension/basis abstraction, uncertainty propagation, MCP integration | Complete |
| v1.0.0 | API stability: semantic-versioning commitment, 2+ year LTS, ~215 units across 67+ dimensions, cross-dimensional contexts (spectroscopy, Boltzmann) | Complete |
| v1.2.0 | TOML round-trip `ConversionGraph` serialization | Complete |
| v1.3.0 | Graph-independent arithmetic via `BaseForm` decomposition | Complete |
| v1.4.0 | Basis isomorphisms: Atomic and Planck units as first-class bases | Complete |
| v1.5.0 | Conversion factor uncertainty (GUM propagation) | Complete |
| **v1.6.0** | **TOML takeover** — TOML as single source of truth (~1,250 lines of hand-written Python collapsed to a ~150-line loader) | Complete |
| v1.6.x | Cross-basis arithmetic completion: base-form conversion fallback, `@enforce_dimensions` coercion, transform-graph-aware `Vector` arithmetic | Complete |
| v1.7.0 | Basis subpackage layout: `types`/`vector` extraction, deferred-import reduction | In Progress |
| **v2.0** | **Basis subpackage restructure** — clean DAG, zero deferred imports, explicit cross-basis arithmetic | Proposed |

---

## v2.0 (Proposed) — Basis Subpackage Restructure

**Theme:** Eliminate cyclic imports in `ucon.basis` by changing the API, not the file layout.

**Motivation:**
The `ucon.basis` subpackage carries a structural cycle (`vector → graph → transforms → vector`) that originates from the 1.6.6 implicit cross-basis arithmetic feature: `Vector.__mul__` / `__truediv__` consult the active `BasisGraph` at runtime, which depends on `BasisTransform`, which depends on `Vector`. No file reorganization can break this cycle while the cycle is encoded in the public API. The 1.7.x refactors mitigated symptoms (deferred imports, lazy default-graph construction) but the underlying triangle remains.

**API change (breaking):**

- `Vector.__mul__` / `__truediv__` raise on different bases instead of consulting `BasisGraph`. Vector becomes strictly same-basis.
- Cross-basis arithmetic moves to explicit helpers in `ucon.basis.ops`:
  - `ops.unify(a, b) -> tuple[Vector, Vector]`
  - `ops.multiply_via(a, b, graph=None) -> Vector`
  - `ops.divide_via(a, b, graph=None) -> Vector`
- Migration: callers relying on implicit cross-basis arithmetic call the explicit `ops.*` helper.

**Module layout (clean DAG, no cycles):**

```
ucon/basis/
├── types.py        — Basis, BasisComponent, exceptions
├── builtin.py      — SI, CGS, NATURAL, ATOMIC, PLANCK, …
├── vector.py       — Vector with strict same-basis arithmetic
├── transforms.py   — BasisTransform, ConstantBinding, ConstantBoundBasisTransform
├── graph.py        — BasisGraph (pure registry + path-finding)
├── standard.py     — standard transform instances + standard-graph factory
├── active.py       — ContextVars + accessors (get_basis_graph, using_basis, …)
├── ops.py          — explicit cross-basis helpers
└── __init__.py     — re-exports
```

Dependency order: `types → {builtin, vector} → transforms → graph → standard → active → ops → __init__`. Every import lives at the top of its file. The standard graph is built eagerly at module load — no `global`, no lazy factory, no deferred imports.

**Outcomes:**

- Zero hidden global state in arithmetic operators
- Zero deferred imports in the basis subpackage
- Zero cycle-breaking hooks or holder classes
- Cross-basis intent is visible at the call site

**Status:** design captured during 1.7.x basis-types-extraction refactor. Implementation deferred until a major-version window opens.

---

## Guiding Principle

> "If it can be measured, it can be represented.
> If it can be represented, it can be validated.
> If it can be validated, it can be trusted."

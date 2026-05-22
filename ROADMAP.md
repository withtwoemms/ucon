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
| v1.7.0 | Basis subpackage layout: `types`/`vector` extraction, deferred-import reduction | Complete |
| **v1.8.0** | **`UnitSystem` value type, `ucon.basis.ops`, basis cycle break.** Introduces `ucon.system.UnitSystem` as a frozen value owning units, dimensions, conversions, basis, basis-graph, base-units, contexts, constants, and a per-instance `AlgebraCache`; renames the v1.7 `UnitSystem` to `BaseUnits` (PEP-562 alias retained with `PendingDeprecationWarning`); makes `Vector` strictly same-basis with explicit cross-basis helpers in `ucon.basis.ops` (`unify`, `multiply_via`, `divide_via`); routes `Dimension` algebra through the active system's `AlgebraCache`; threads an optional `system=` kwarg onto `Number.to`, `parse`, `parse_unit`, `parse_dimension`, `enforce_dimensions`, and the compound-unit parser. Resolves the `vector → graph → transforms → vector` load-time cycle as a side effect. | Complete |
| **v1.9.0** | **Kind-of-Quantity (KOQ) preview surface.** Introduces `ucon.kinds` (sortal lattice with `Kind`, `KindLattice`, `JoinPolicy`) and `ucon.formulas` (`KindFormula`, `FormulaRegistry`, `AspectRule`) as opt-in data models for quantities that share a dimension but differ semantically (kinetic vs. potential energy; absorbed vs. equivalent dose). TOML loaders in `ucon.parsing` (`load_kinds_file`, `load_formulas_file`) make lattices and registries authorable from the same format that defines units. Not wired to `Number` — preview surface only. | Complete |
| v1.9.1 | **Aspect propagation.** Activates the `aspect_rules` field on `KindFormula`. Adds `ucon.aspects` subpackage with `AspectSet`, `AspectJoinPolicy`, and `join_aspects(a, b, policy)`. Adds `KindFormula.project_aspects` and `FormulaRegistry.apply(inputs)` returning `(formula, output_kind, output_aspects)`. Still callable-side; still not wired to `Number`. | Complete |
| v1.9.2 | **Lookup completeness.** Makes the registry consult declared structure that v1.9.0 indexes but does not act on: full `n!` permutation for commutative formulas with `n > 2`, ancestor-walk matching for formulas declared with `generalizes=True`, and opt-in dimension-only fallback. Adds `LookupResult` with `MatchKind` (EXACT/COMMUTATIVE/GENERALIZED/DIMENSIONAL) for diagnostic inspection. No new concepts — completeness pass on existing declarations. | Complete |
| **v2.0** | **`UnitSystem` algebra, global retirement, and `Number.kind` wiring.** Closes the value-type loop: pure-function operations `extend` / `restrict` / `overlay` / `merge`, first-class relations `subsystem_of` / `compatible_with` / `diff`, explicit cross-system value movement (`system.adopt`, `Bridge(A, B)`), and retirement of the module-global registries (`_REGISTRY`, `_DIMENSION_ATTRS`, default `ConversionGraph`, default `BasisGraph`) in favour of the default `UnitSystem` value. Promotes the v1.9.x KOQ surface to first-class: `Number` accepts `kind=`, arithmetic dispatches through the active `FormulaRegistry`, and `using_kind_lattice` / `using_formula_registry` context managers make scope explicit. Removes the deprecated `UnitSystem` alias for `BaseUnits` and the `_DIM_*_CACHE` shims. | Proposed |

---

## v1.9.x — Kind-of-Quantity Preview Line

**Theme:** Land the kind subsystem as a complete, standalone data model before binding it to arithmetic.

**Motivation:**
A dimension answers *what kind of measurement is this* at the level of physics (length, energy, time). A kind answers it at the level of physical interpretation: kinetic energy and thermal energy share `Dimension.energy` but are not interchangeable in every context; absorbed dose and equivalent dose share `Dimension.absorbed_dose` (J/kg) but only the latter accounts for radiation weighting. Type systems handle the dimensional level; the conceptual level needs its own structure.

The v1.9.x line introduces that structure incrementally, in three releases of decreasing scope:

- **v1.9.0 — Structure.** The data model: `Kind`, `KindLattice`, `KindFormula`, `FormulaRegistry`, TOML loaders. Equality on name, refinement via partial order, formula lookup by input-kind tuple. Indexed but inert fields (`commutative` beyond arity 2, `generalizes`, `aspect_rules`) reserve declarative space for later releases without forcing premature semantics. Shipped as opt-in preview — no top-level `ucon` namespace export, no `Number` integration.
- **v1.9.1 — Propagation.** Aspects (covariant tags carried on quantities) become real. `FormulaRegistry.apply(inputs)` returns the joined aspect set alongside the output kind. Aspect behavior under LCA join is pinned (intersect-on-join). Still caller-side; the library does not yet store kinds on `Number`.
- **v1.9.2 — Lookup completeness.** The registry consults the lattice during lookup. `commutative=True` honors all permutations, not just pairwise swap. `generalizes=True` matches via ancestor walk. Opt-in dimension fallback covers the long tail. Diagnostic surface (`LookupResult`, `MatchKind`) exposes which match tier resolved a call.

**Why three releases and not one:**
Each release establishes a property the next depends on. 1.9.0 fixes the vocabulary and storage shape. 1.9.1 fixes the data flow through application. 1.9.2 fixes the lookup completeness. Shipping these as one release would conflate three different categories of design risk: data model (rare changes, high cost), application semantics (frequent feedback during real use), and matching policy (intricate but mechanical). Separating them lets users adopt 1.9.0 against the eventual stable model while 1.9.1 and 1.9.2 evolve under real workloads.

**Why preview, not wired:**
Wiring kinds to `Number` is a v2.0-shaped change — it modifies arithmetic dispatch, introduces context managers for the active lattice/registry, and forces decisions about how kinds interact with `enforce_dimensions`, `UnitSystem`, conversion, and serialization. v1.9.x deliberately defers all of that. The preview surface lets the data model harden against real usage patterns before the integration that locks it in.

**Status:** v1.9.0 complete. v1.9.1 implementation-complete on `activate-aspect-rules`, pending release. v1.9.2 designed but not yet branched. Full integration in v2.0.

---

## v2.0 (Proposed) — `UnitSystem` as a Value Type

**Theme:** Make a "system of units" something you *hold*, not something the module *is*. The universe of units becomes a first-class value with semantics, algebra, and lifetime.

**Motivation:**
Three structural threads in v1.x share a root cause and resolve together:

1. The name `UnitSystem` (`ucon/core.py:670`) currently labels a small record — `name + Dict[Dimension, Unit]` — while the responsibilities the name implies (the universe of known units, dimension singletons, conversion topology, parser context, algebra caches) live in module-level globals: `_REGISTRY`, `_DIMENSION_ATTRS`, `_DIM_*_CACHE`, the default `ConversionGraph`, the default `BasisGraph`, and basis-related ContextVars. The class is anemic; the module is the real aggregate. This split makes isolation hard, composition impossible, and invalidation a debugging exercise rather than a structural property. It is also the root cause of the v1.7.0 dimension-cache id-reuse bug.

2. The `ucon.basis` subpackage carries a type-level cycle (`vector → graph → transforms → vector`) that originated with the 1.6.6 implicit cross-basis arithmetic feature: `Vector.__mul__` / `__truediv__` consult the active `BasisGraph` at runtime. The 1.7.x refactors mitigated symptoms (deferred imports, lazy default-graph construction) but the underlying triangle remains.

3. The v1.9.x kind subsystem ships as a preview because wiring it to `Number` requires the same scope decisions v2.0 must make for `UnitSystem`: where does the active lattice/registry live, how do context managers compose with the active system, how do kinds survive conversion and serialization. Promoting KOQ to first-class is a v2.0-shaped problem precisely because it touches the same ambient-state surface.

All three are forms of *ambient state in the arithmetic path*. Eliminating one without eliminating the others leaves the principle violated. Adopting the value-type principle therefore implies the basis cycle break and the KOQ promotion, and each implies the others. They are one piece of work.

**API changes (breaking):**

*Universe of units becomes a value:*

- Today's `UnitSystem` is renamed `BaseUnits` (a mapping from dimension to chosen base unit).
- A new `UnitSystem` is introduced as a frozen value owning:
  - `units`, `dimensions`, `conversion_graph` (formerly `_REGISTRY`, `_DIMENSION_ATTRS`, the default `ConversionGraph`),
  - `basis`, `basis_graph`, `base_units`,
  - per-instance algebra caches (replacing the module-level `_DIM_*_CACHE`).
- Operations on `UnitSystem` are pure functions returning new systems: `extend`, `restrict`, `overlay`, `merge`.
- Relations between systems are first-class queries: `subsystem_of`, `compatible_with`, `diff`.
- Cross-system value movement is explicit: `system.adopt(number)` and `Bridge(A, B)` for translation.
- The default global system is retained as a convenience but is now *one* `UnitSystem` value among many, not the only universe.
- One `ContextVar` (`ucon.system.active._active`) replaces the family of basis-related ContextVars and module globals.

*Kind-of-Quantity becomes first-class:*

- `Number` accepts an optional `kind=` argument; the field is preserved through arithmetic and conversion.
- Arithmetic dispatches through the active `FormulaRegistry`: `a * b` consults the registry, applies the matching `KindFormula`, propagates aspects per `AspectRule`, and stamps the result kind.
- Scope is made explicit via `using_kind_lattice(lat)` and `using_formula_registry(reg)` context managers, parallel to the `system=` plumbing.
- Conversion preserves kind by default (`Number.to(unit)` does not change kind); cross-kind movement is explicit.
- Pydantic and TOML serialization round-trip `kind` alongside `unit` and `quantity`.
- `@enforce_dimensions` gains an optional `kind=` constraint that complements the dimensional check.

*Basis arithmetic becomes explicit:*

- `Vector.__mul__` / `__truediv__` raise on different bases instead of consulting `BasisGraph`. `Vector` becomes strictly same-basis. This breaks the type-level cycle at its source: `Vector` no longer references `BasisGraph` or `BasisTransform`.
- Cross-basis arithmetic moves to explicit helpers in `ucon.basis.ops`:
  - `ops.unify(a, b) -> tuple[Vector, Vector]`
  - `ops.multiply_via(a, b, graph=None) -> Vector`
  - `ops.divide_via(a, b, graph=None) -> Vector`
  - The `graph` parameter defaults to `active().basis_graph`. Passing `system=` is also accepted.
- Migration: callers relying on implicit cross-basis arithmetic call the explicit `ops.*` helper.

**Module layout consequences:**

With ambient state retired, the basis subpackage falls into a clean DAG as a side effect — no separate file-reorganization workstream is needed. `Vector` no longer references `BasisGraph`, so deferred imports disappear; `_default_basis_graph` retires because `system.basis_graph` owns it; the `ucon.basis.active` ContextVars consolidate into one in `ucon.system.active`.

```
ucon/basis/
├── types.py        — Basis, BasisComponent, exceptions
├── builtin.py      — SI, CGS, NATURAL, ATOMIC, PLANCK, …
├── vector.py       — Vector with strict same-basis arithmetic (no BasisGraph reference)
├── transforms.py   — BasisTransform, ConstantBinding, ConstantBoundBasisTransform
├── graph.py        — BasisGraph (pure registry + path-finding)
└── ops.py          — explicit cross-basis helpers
```

Dependency order in `basis/`: `types → {builtin, vector} → transforms → graph → ops`. Every import lives at the top of its file. No `global`, no lazy factory, no deferred imports. The active-state plumbing that previously lived in `basis/active.py` and `basis/standard.py` moves to `ucon/system/` and `ucon/system/default.py` respectively, since "what is the current basis graph" is now equivalent to "what is the current system."

**Outcomes:**

- **Value semantics for the universe of units.** Two `UnitSystem`s coexist, can be compared, combined, and discarded without affecting each other.
- **Invalidation collapses into construction.** Caches are per-instance; "stale" cannot mean "across systems," and id-reuse hazards (the v1.7.0 cache-keying class of bug) are structurally impossible.
- **Closure under composition.** `extend` / `restrict` / `overlay` give `UnitSystem` an algebra with associativity and identity laws callers can rely on.
- **Zero hidden global state in arithmetic operators.** No basis graph consulted implicitly, no unit registry mutated implicitly, no dimension cache shared across logical scopes.
- **Zero deferred imports in `ucon.basis`.** The cycle is broken at the API level, not papered over with import tricks.
- **Cross-basis intent visible at the call site.** `ops.multiply_via(a, b)` instead of `a * b` doing something subtle.
- **Concurrency- and multi-tenant-ready.** Independent systems on independent threads/tasks/tenants without shared mutable state or locks.
- **Test isolation by default.** Tests construct the system they need; nothing leaks across imports.
- **Honest naming.** `UnitSystem` denotes a system; `BaseUnits` denotes a base-unit mapping; each name matches its contract.

**Status:** Combines the value-type work captured during 1.7.0 dimension-cache investigation, the basis-cycle work captured during 1.7.x basis-types-extraction refactor, and the KOQ promotion deferred from v1.9.x. Implementation deferred until a major-version window opens.

---

## Guiding Principle

> "If it can be measured, it can be represented.
> If it can be represented, it can be validated.
> If it can be validated, it can be trusted."

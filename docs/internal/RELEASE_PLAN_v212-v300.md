# Release Plan: v2.1.2 → v3.0.0

> Delivery path for the six issues filed 2026-09-06 (#278–#283) and the
> three design workstreams in flight (aspects, packages/contexts,
> Turnstile/operator-flow). Sequencing rationale recorded here; per-release
> scope details live in the referenced implementation plans and issues.

**Status:** SUPERSEDED (2026-09-09) by `RELEASE_PLAN_v212-v310.md` — the
five-release shape: a lean 3.0.0 major carrying only the structural breaks,
with the Turnstile following as a 3.1.0 minor. Kept for historical context.
Originally: Proposed (2026-09-06)
**Supersedes:** the version numbering implied by
`IMPLEMENTATION_PLAN_v220_aspect_threading.md` (aspects move to v2.3.0; see
Renumbering below).

---

## The trajectory at a glance

| Release | Type | Contents | Gate to next |
|---|---|---|---|
| **v2.1.2** | patch | Correctness train: #278, #279, #280 (narrow), #281, #283 (docs) | All six issue reproductions resolve or refuse correctly |
| **v2.2.0** | minor | Package ecosystem: #282 contexts-in-TOML | #279 landed (context edges are constant-licensed) |
| **v2.3.0** | minor | Aspects (the plan currently stamped v2.2.0) | Nothing in v2.2.0 blocks it; renumbering only |
| **v3.0.0** | major | Turnstile / operator-flow: scale-aware arithmetic, warrants, decision-table pipeline | Behavioral break (raw-numeral addition ends) requires a major |

Principle: patches restore documented behavior, minors add capability,
the one behavioral break waits for the major. Nothing user-visible changes
meaning inside a minor.

---

## v2.1.2 — correctness patch train

Five commits, one per issue, each independently bisectable. Order within
the train is by user impact; there are no inter-commit dependencies.

1. **#278 — customary prefactors.** Derive every customary prefactor from
   four exact seeds (inch 0.0254 m, pound 0.45359237 kg, US gallon 231 in³,
   Imperial gallon 4.54609e−3 m³), computed in `Fraction`, converted once.
   Regression test re-derives and compares. Touches the catalog →
   `make cache`, `make stubs`, `make base-forms-check` all in the same
   commit. **Loud CHANGELOG entry**: downstream conversion results shift at
   ppm level (corrections, but numeric diffs nonetheless).
2. **#279 — constant symbols in edge factors.** `_parse_factor` resolves
   symbols against the package's `[[constants]]` (and `requires`-imported
   ones) before numeric evaluation; unresolvable symbols still refuse.
   Acceptance: `load_package` on the bundled `comprehensive.ucon.toml`
   succeeds.
3. **#280 (narrow) — composite endpoints in path resolution.** Path search
   treats endpoints with identical `BaseForm` as the same node. Only
   `ConversionNotFound` outcomes become successes; no passing behavior
   changes. Acceptance: the `us_gallon → meter^3 → liter` reproduction.
   The `__eq__` unification half is explicitly **deferred** (see v3.0.0).
4. **#281 — typed disjoint-roots refusal.** `DisjointKinds(KindError,
   ValueError)` — dual inheritance keeps every existing `except ValueError`
   handler working while `except KindError` starts working. Carries
   `left`/`right` payload per the exceptions-module convention. Export
   through `ucon/__init__.py` alongside the existing kind exceptions.
   The fuller ⊤_d design is deferred to whichever release first ships
   multi-root fibers (earliest v2.2.0, see below).
5. **#283 — `base_form` contract docs.** Decision recorded + docstring
   corrected (`base_form is None` for CGS-native units is basis-scoping,
   not "inexpressible"), plus the consumer audit noted in the issue.
   Docs-only; no code change expected.

Exit criteria: full suite + structural guards (`test_import_dag`,
`test_no_cross_module_injection`, `stubs-check`, `base-forms-check`) green;
each issue's reproduction script demonstrates the fix.

## v2.2.0 — package ecosystem

Scope: **#282** — `contexts: tuple[ContextDef, ...]` on `UnitPackage`,
`[[contexts]]` / `[[contexts.edges]]` parsing, registration through
`Graph.with_package` mirroring `Graph.register_context`, TOML round-trip
in `serialization.py` (→ cache rebuild rules apply).

Optional stretch, decide at planning time: the ⊤_d per-fiber top from #281's
fuller design. Rationale for considering it here: v2.2.0 is the release
that makes third-party kind packages (and hence multi-root fibers)
practical, so the structural fix lands with the capability that arms the
hazard. If deferred, `DisjointKinds` from v2.1.2 already makes the failure
mode typed and diagnosable.

Explicitly NOT in v2.2.0: aspects (moved to v2.3.0), equality unification
(v3.0.0), any `Number` arithmetic change.

## v2.3.0 — aspects

Content unchanged from the current implementation plan (9 Laws,
`axis:position` grammar, context-free decision tables, `__eq__`
discrimination, coherence sweep). Renumbering actions:

- Rename `IMPLEMENTATION_PLAN_v220_aspect_threading.md` →
  `IMPLEMENTATION_PLAN_v230_aspect_threading.md`; update version stamps
  throughout (the hybrid draft keeps its filename — it is historical).
- ROADMAP gains the v2.1.2 → v2.3.0 waypoints when this plan is adopted.

Aspects deliberately do not depend on v2.2.0 content; if the package
ecosystem release slips, aspects can leapfrog and take v2.2.0 after all —
in that case only the renumbering paragraph above is revisited.

## v3.0.0 — Turnstile / operator-flow

The behavioral break that cannot ride a minor: `Number.__add__` today adds
raw numerals across scales (`1 m + 50 cm = 51 m`) with unit-blind
uncertainty; the Turnstile replaces this with coerced, warrant-compiled,
sensitivity-weighted arithmetic. Scope and phases:
`DESIGN_turnstile-implementation-brief.md`; theory:
`DESIGN_operator-flow-decision-tables.md`.

Items parked here from earlier releases:

- **#280 (full)** — `UnitProduct`/`Unit` equality unification and canonical
  node identity, rebuilt as part of the map-layer/graph-version work rather
  than patched twice.
- Any `numeral` rename and other deferred deprecation removals per the
  deprecation policy (pending → deprecated → removed at major).

## Dependency graph

```
#279 ──────────► #282 (v2.2.0)          #278, #283: independent
#281 (typed) ──► ⊤_d (v2.2.0 stretch)   #280-narrow: independent
#280-narrow ───► #280-full (v3.0.0, with map-layer node identity)
v2.3.0 aspects: independent of all of the above (Law 0: kind/aspect orthogonality)
v3.0.0: builds on #280-narrow's endpoint unification; consumes aspects' gate shape
```

## CHANGELOG discipline

Every item above gets its entry under the release that ships it (#278 under
**Fixed** with the numeric-shift warning; #279/#280/#281 under **Fixed**;
#283 under **Documentation**; #282 under **Added**). ROADMAP records only
the four waypoints, not the per-issue detail.

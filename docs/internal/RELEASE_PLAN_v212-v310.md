# Release Plan: v2.1.2 → v3.1.0

> Delivery path for issues #278–#285 and the three design workstreams
> (packages, aspects, Turnstile). Sequencing rationale lives here; design
> detail lives in the ADRs (`ADR_aspect-stratum.md`, `ADR_turnstile.md`) and
> their evidence records once landed in `docs/internal/`.

**Status:** Adopted (2026-09-09); revised 2026-09-09 — the patch train
ships as **one tag per issue** (2.1.2–2.1.7), not a single bundled 2.1.2.
The per-issue rhythm proved itself in delivery: each tag maps to exactly
one issue, one PR, one CHANGELOG section, with downstream (ucon-tools)
validated per release.
**Supersedes:** `RELEASE_PLAN_v212-v300.md` (four-release shape; Turnstile
as the major) and the version numbering in
`IMPLEMENTATION_PLAN_v220_aspect_threading.md` (aspects move to 2.3.0 with
a redesigned data model — see the Aspect Stratum ADR, which supersedes that
plan's flat-`AspectSet` design).

---

## The trajectory

| Release | Bump | Contents | Status / rationale |
|---|---|---|---|
| **2.1.2** | patch | #278 customary prefactors (exact seeds) | ✅ shipped 2026-09-09 |
| **2.1.3** | patch | #279 constant symbols in edge factors | ✅ shipped 2026-09-09 |
| **2.1.4** | patch | #280-narrow composite-endpoint paths | ✅ shipped 2026-09-09 |
| **2.1.5** | patch | #281-narrow `DisjointKinds` typed refusal | PR #289 green |
| **2.1.6** | patch | #284 idempotent identical-object re-add | built, awaiting PR |
| **2.1.7** | patch | #283 mechanical-CGS `base_form`s + `BaseForm` contract + coercion ordering | built, awaiting PR |
| **2.2.0** | minor | #282 contexts-in-TOML, `PolynomialMap`, `Unit.chart` + validator, ⊤_d (stretch), deprecations land (`PendingDeprecationWarning`: pseudo-dims, `AspectSet`) | package infrastructure, all additive |
| **2.3.0** | minor | Aspects per ADR (flat `Number.aspects`), D3 namespacing (+#285), deprecations escalate to `DeprecationWarning` | additive — `Number.kind` unchanged, new field defaults empty |
| **3.0.0** | major | pseudo-dimension retirement (TOML schema), `Number` frozen, #280-full identity unification, removals (`AspectSet`, other ripened deprecations) | the true breaks, and only the breaks |
| **3.1.0** | minor | Turnstile per ADR: four strata, `Unit.chart` consumption, displacement seam, cyclic/ordinal kind flags, `Refused` + `explain()` | new refusals on previously-wrong paths are fixes; new types are additive |

Principles: patches restore documented behavior; minors add capability; the
one lean major carries only the breaks; the arithmetic rework rides after
it as fixes-plus-additions. Deprecation ladder honored: Pending (2.2.0) →
Deprecation (2.3.0) → removal (3.0.0).

---

## v2.1.2–v2.1.7 — correctness patch train

One tag per issue, independently bisectable, ordered by user impact. No
inter-release dependencies. Each release: branch `ucon#<issue>-<desc>`,
PR with `Closes #<issue>`, CHANGELOG re-sectioning + compare link folded
into the next PR's rebase, downstream job validated per PR. ucon-tools
rides the train at `ucon>=2.1.2a1` and graduates its floor once at train
end (`>=2.1.7`), per the established adoption pattern.

1. **#278 — customary prefactors.** Derive every customary prefactor from
   four exact seeds — inch 0.0254 m, pound 0.45359237 kg, US gallon 231 in³,
   Imperial gallon 4.54609e−3 m³ — computed in `Fraction`, converted once.
   Regression test re-derives and compares. Catalog touched → `make cache`,
   `make stubs`, `make base-forms-check` in the same commit. **Loud
   CHANGELOG entry**: conversion results shift at ppm level.
2. **#279 — constant symbols in edge factors.** `_parse_factor` resolves
   symbols against the package's `[[constants]]` (and `requires`-imported)
   before numeric evaluation; unresolvable symbols still refuse. Acceptance:
   `load_package` on the bundled catalog succeeds.
3. **#280-narrow — composite endpoints in path resolution.** Endpoints with
   identical `BaseForm` unify during path search. Only `ConversionNotFound`
   becomes success; `__eq__` untouched (full unification: 3.0.0).
   Acceptance: the `us_gallon → meter^3 → liter` reproduction.
4. **#281-narrow — typed disjoint-roots refusal.**
   `DisjointKinds(KindError, ValueError)` with `left`/`right` payload; dual
   inheritance keeps `except ValueError` working. Export beside the existing
   kind exceptions. ⊤_d deferred (2.2.0 stretch / 3.1.0).
5. **#283 — populate CGS `base_form`s.** Exact values for dyne, erg, poise,
   gauss, maxwell, …, verified by the `base-forms-check` oracle;
   `base_form is None` recovers its single meaning (no linear factorization
   exists). Docstring updated. Consumer audit doubles as the test checklist;
   #280-narrow's path starts covering CGS units for free. (degree stays
   `None` until 3.0.0 pseudo-dim retirement.)
6. **#284 — identical-object re-add.** Decide idempotent no-op vs typed
   duplicate; either way `AliasCollision` becomes unreachable when no alias
   is involved.

Exit criteria: full suite + structural guards green; each issue's
reproduction demonstrates the fix.

## v2.2.0 — package infrastructure

- **#282**: `[[contexts]]` / `[[contexts.edges]]` on `UnitPackage`;
  registration via `Graph.with_package`; round-trip in `serialization.py`
  (cache rebuild rules apply). Gated on #279.
- **`PolynomialMap`** with T5 branch-inverse declarations (ratified):
  invertible iff a monotonic branch + domain is declared; reverse traversal
  refuses otherwise, with a hint naming the missing declaration.
- **`Unit.chart`** declared field (`ratio` | `interval` | `logarithmic`,
  default ratio) + TOML key; reference-edge Map derivation demoted to a
  validator running at load, `extend`, and merge. Fixtures: dyne (no edge),
  decibel (linear sibling edge).
- **⊤_d per fiber (stretch):** lands with the capability that arms the
  hazard (multi-root fibers via packages). If deferred, `DisjointKinds`
  keeps the failure typed.
- **Deprecations land** (`PendingDeprecationWarning`): pseudo-dimension
  declarations; `AspectSet` and `join_aspects` (superseded by the aspect
  stratum; the shipped INTERSECT default is laundering-vulnerable — see
  ADR §4).
- **Housekeeping:**
  - `[2.1.7]` CHANGELOG re-sectioning + compare link (no later train PR
    to fold it into).
  - **Local-import sweep across `tests/`** (~1,100 lines, ~45 files): all
    imports hoisted to module top per the no-local-imports rule
    (`test_checking.py` done in 2.1.7). Carve-outs: `integrations/`
    optional-dependency imports become guarded module-level patterns
    (`pytest.importorskip` at top), never blind hoists;
    `tests/ucon/.archive/` and `tests/ucon/evals/` out of scope (not in
    CI).
  - `RELEASE_PLAN_v212-v310.md` status column flipped to shipped for
    2.1.5–2.1.7.

## v2.3.0 — aspects

Per the Aspect Stratum ADR: one `Aspect` type (peer of `Kind`, root = family
= ⊤), flat additive `Number.aspects`, family-wise resolution (LCA within
tree, partial policy `inherit`/`refuse`, `drop` prohibited), carry rule,
`applies_to` at attachment, `[[aspects]]` TOML, D3 full qualification +
`namespace` rewriter. Law 0 as test oracle.

Also: **#285** resolves here — D3 qualification for the cross-package case,
plus the `(name, dimension)` index decision for the within-package case.
Deprecations escalate to `DeprecationWarning`.

## v3.0.0 — the lean structural major

Pseudo-dimension retirement (TOML schema change; degree et al. become
first-class); `Number` frozen; #280-full (`UnitProduct`/`Unit` equality and
canonical node identity); removals: `AspectSet`/`join_aspects`, ripened
deprecations. Nothing else — users migrating across the major face identity
and schema changes only, not an arithmetic rework.

## v3.1.0 — the Turnstile

Per the Turnstile ADR: four inline strata (dimension, chart via `Unit.chart`,
kind with ⊤_d, aspect), point/displacement derived via the frozen-dataclass
seam, cyclic (`modulus`) and ordinal kind flags, lazy warrants
(`Refused` + `explain()`), merge-time upward-closure validation, no cache.
Gate: the refusal inventory — every new refusal targets a previously-wrong
result (C1–C4 completeness tests); anything breaking a defensible current
result gets a deprecation path instead.

## Dependency graph

```
#279 ──► #282 (2.2.0)                    #278, #284: independent
#283-populate ──► Unit.chart validator fixtures (2.2.0) ──► chart stratum (3.1.0)
#281-narrow ──► ⊤_d (2.2.0 stretch or 3.1.0)
#280-narrow ──► #280-full (3.0.0) ──► Turnstile node identity (3.1.0)
#285 ──► D3 (2.3.0)
aspects (2.3.0): independent of packages and Turnstile (Law 0, test-enforced)
Number frozen (3.0.0) ──► displacement seam (3.1.0)
```

## CHANGELOG discipline

Every item under the release that ships it: #278 under **Fixed** with the
numeric-shift warning; #279/#280/#281/#283/#284 under **Fixed**; #282 and
the 2.2.0 additions under **Added**; deprecations under **Deprecated** at
each ladder step; 3.0.0 removals under **Removed**. ROADMAP records the five
waypoints only.

> **SUPERSESSION NOTE (2026-09-10).** Superseded by
> [`../decisions/009-turnstile.md`](../decisions/009-turnstile.md): the
> compile-once-per-signature framing (warrant cache, signature interning,
> `graph_version`) was withdrawn on measurement — the cache key costs what
> the four checks cost. Kept for the deviation analysis of shipped
> arithmetic (§2) and the concept inventory, much of which survives in the
> ADR's strata.

# BRIEF: Turnstile — warrant-compiled Number operations

**Status:** Draft for review
**Date:** 2026-07-20
**Companion:** `operator-flow-decision-tables.md` (the tables this
compiles; esp. T3, T4, T8b, T9, T11 and the proposed value-independence
invariant). Prototypes (dispatch v2, turnstile) are session artifacts,
superseded by these documents.

---

## 1. What the Turnstile is — and is not

The Turnstile governs **binary `Number` operations** (`+ − × ÷`, later `⊕`).
For each *operation signature* — `(op, unit_a, unit_b, kind_a, kind_b,
graph_version)` — it runs the decision-table gates once, compiles the outcome
into a **Warrant**, and caches it. Subsequent operations with the same
signature skip the gates entirely: a dict hit, then a fused multiply-add.

It does **not** participate in map composition. The map layer (compose +
T3 normalization) is upstream: at compile time the Turnstile *asks* the
graph for a resolved path, receives its normal form, and reads coefficients
off it. Composition is the producer; the Turnstile is a consumer. One
sentence: *maps are the source language, T3 is the optimizer, Warrants are
the object code.*

A Warrant is one of:

- **ADMIT** — coefficients `A, B, C`, sensitivity `|B|`, precomputed
  `out_unit` / `out_kind`. Execution: `v = A·a.v + B·b.v + C`,
  `δ = √((A·δa)² + (|B|·δb)²)`.
- **REFUSE** — a stored structured refusal (error type + legal spellings),
  re-raised without re-running gates (negative cache).

## 2. Deviation from current state

Current `Number.__add__` / `__sub__` (`ucon/core/_types.py:2201–2255`):

| aspect | today (v2.1.x) | under Turnstile |
|---|---|---|
| gating | dimension equality only | full gate ladder (dimension → chart path → kind → role → menu), per the tables doc |
| numeral math | **raw**: `self.quantity + other.quantity`, result keeps `self.unit` — `1 m + 50 cm = 51 m` | coerced: `B` carries the transition's factor/offset — `1 m + 50 cm = 1.5 m` |
| uncertainty | RSS of raw δs, unit-blind — mixes δ(m) with δ(cm) | RSS of *sensitivity-weighted* δs (`A`, `|B|` are the GUM coefficients) |
| consistency with `__eq__` | `__eq__` (:2307) is scale-aware/canonical; add is not — `a + b` and `==` disagree about what a cm is | one transition source for both |
| kind resolution | `_resolve_add_kind` per call | resolved once at compile, frozen into `out_kind` |
| refusal | `TypeError` with prose | structured `Refusal` carrying spellings; cached |
| cost profile | per-call resolution, no caching | per-signature compile, per-call FMA; refusals amortize too |

The coercion row is a **behavioral break** (current results are silently
wrong across scales, but they are current behavior). This cannot ship as a
patch; it is the correctness centerpiece of the release that adopts the
Turnstile, called out in CHANGELOG as such.

`__mul__` / `__truediv__` deviate less initially (they already resolve kinds
via formulas); they join the Turnstile for caching and for the T8b menu gates
(`× point,*` refusals) in a later phase.

## 3. New concepts to add (inventory)

None of these exist in ucon today:

| concept | shape | notes |
|---|---|---|
| **Map types** | `LinearMap(a)`, `AffineMap(a, b)` first; `LogMap`/`ExpMap`/`PowerMap`/`PolynomialMap` per tables-doc Appendix C later | today's ConversionGraph edges are linear factors only; maps generalize edges to typed, *inspectable* data — closed parametrization is what makes compilation possible |
| **Transition normalization** | compose + the affine subset of T3 rewrites | multi-hop paths fold to one normal form at compile time |
| **`Warrant`** | slotted record; verdict + coefficients/guards or error+spellings | tiers: REFUSE / FMA / GUARDED-FMA (adds a T5 domain interval check) / INTERPRETED (holds a map handle when the normal form is non-affine) |
| **Tier rule** | FMA iff normal form ∈ {Linear, Affine} | theorem-backed (closure theorem, tables-doc Appendix A); never silently linearize — the prototype's `else 1.0` fallback is forbidden |
| **Signature interning** | small int ids for units and kinds; packed int key | ids are per-`UnitSystem`; key includes `graph_version` |
| **`graph_version`** | monotone counter on `ConversionGraph`, bumped on any edge/declared-table mutation | stale warrants orphaned by key miss; periodic sweep optional |
| **Warrant cache** | dict on `UnitSystem` (or `ActiveContext`) | per-instance state only — CLAUDE.md forbids module-level mutable globals; the existing AST audit will enforce this |
| **Structured `Refusal` + `Spelling`** | exception carrying enumerated alternatives (T10 subset) | machine-applicable payload for MCP consumers |
| **Roles / menus** | `ChartRole` computed from kind links; per-class `OperationMenu`; T9 counting | phase 2+ — not needed to land phase 1 |

## 4. Invariants (the discipline that keeps warrants sound)

1. **Gates read only the signature, never numerals.** Any check that must
   inspect a value (T5 domains, log positivity) is a *guard* attached to the
   warrant and evaluated per call — declared as such, never smuggled into a
   gate.
2. **No silent linearization.** Non-affine normal forms compile to
   INTERPRETED warrants, not approximate coefficients.
3. **Aspects stay out of the key.** The v2.2.0 aspect gate is a context-free
   set comparison run beside the warrant lookup (peer of the kind gate),
   keeping the signature space small and preserving Kind/chart orthogonality.
4. **Warrant replay ≡ interpreted pipeline.** Property test: for random
   signatures and values, executing via warrant equals running the gates and
   transition uninterpreted. This is the Turnstile's whole correctness
   obligation.
5. **Executor symmetry via compile-time canonicalization.** Commutative-op
   operand order is canonicalized by permuting `(A, B)` and out-slots during
   compile (amendment G4 of the tables doc) — zero hot-path cost.

## 5. Phasing

- **Phase 1 — soundness + cache, existing semantics.** LinearMap/AffineMap,
  transitions from existing graph factors, FMA/REFUSE warrants, coerced
  add/sub, sensitivity-weighted δ, `graph_version`. No roles, no menus:
  gate ladder = dimension + path + existing `_resolve_add_kind`. Fixes the
  `1 m + 50 cm` and unit-blind-δ defects; benchmarks vs current add.
- **Phase 2 — T-add.** Affine charts (°C), `displacement_of` links, roles,
  the T-add menu, T9 counting, spellings. `degC + degC` starts refusing.
- **Phase 3 — T-mult / P / C.** Log/exp/power maps, level/ratio menus,
  pushforwards, `.to()` warrants (unary shape, positional `|f′(x)|`,
  GUARDED tiers for calibration domains).

Each phase's gates compile into the same Warrant type; the tiering rule and
invariants do not change as gates are added.

## 6. Open questions

1. Which release vehicle carries the phase-1 coercion break (v3.0, or a
   flagged pre-release of it)? Current behavior, though wrong, is shipped
   behavior.
2. Cache residency: `UnitSystem` (per-system, survives context switches) vs
   `ActiveContext` (per-context, simpler invalidation)?
3. `NumberArray` (`_types.py:2646+`) — warrants apply per signature, so array
   ops get the *same* warrant across the whole array: likely the largest
   performance win, but the executor is vectorized. Same warrant, second
   executor? Decide in phase 1.

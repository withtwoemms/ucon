> **SUPERSESSION NOTE (2026-09-10).** Superseded by
> [`decisions/008-aspect-stratum.md`](decisions/008-aspect-stratum.md):
> the flat-`AspectSet` data model this plan is built on was withdrawn
> (an unkeyed set cannot distinguish conflict from absence). The aspect
> release moves to v2.3.0 (see `ROADMAP.md`). Kept for the
> Laws framing and code grounding, parts of which survive in the ADR.

# Implementation Plan: ucon v2.2.0 — Aspects as Orthogonal Discriminators

> **Status:** Draft (rewritten 2026-07-20 — "flat aspects, structurally
> undergirded": context-free discriminator semantics with the `axis:position`
> grammar, forward-compatible with the facet system)
> **Supersedes:** `IMPLEMENTATION_PLAN_v220_aspect_threading.hybrid.md`
> (the 2026-07-12 hybrid-gating revision, preserved) and
> `IMPLEMENTATION_PLAN_v220_aspect_threading.original.md` (pre-revision draft)
> **Trajectory:** the aspect-facets proposal (registry-backed
> `Mapping[str, str]` facets) remains the destination; see §Trajectory
> **Depends on:** v2.1.x (Kind threading, #276/#277)
> **Coordinates with:** `DESIGN_operator-flow-decision-tables.md` (amendment
> G5) and `DESIGN_turnstile-implementation-brief.md` (invariant 3)

---

## Motivation

v2.1.x threaded Kind through `Number` arithmetic. Aspects — covariant
provenance/convention tags — have a shipped data model
(`ucon/aspects/types.py`: `AspectSet`, `AspectRule`, `AspectJoinPolicy`)
but no runtime presence: `Number` has no `aspects` field.

v2.2.0 gives aspects one job and does it completely: **an aspect is an
orthogonal discriminator for quantity comparison and algebra.** Two
quantities that differ in aspects are not interchangeable — not equal,
not addable — until the caller explicitly says so. This is the error
class Hall's M-Layer program exists to prevent (the 1990 conventional
volt vs. the SI volt), caught here **out of the box, with zero
configuration**: no policy object, no registry, no context required.

What this plan deliberately does *not* build (each deferred to the facet
system, §Trajectory): declared facet registries, per-axis combination
policies, species splits (lineage vs identity), and formula-mediated
aspect projection. The prior hybrid draft's policy machinery
(`AspectPolicy.identity_namespaces`) made discrimination opt-in and
context-dependent; this plan makes it the definition.

---

## The Laws

Aspect semantics are fixed by nine laws. Every table below is a
consequence; any implementation question is settled by them.

- **Law 0 — Orthogonality to Kind.** Aspect resolution reads only
  `(A(x), A(y), op-class, strict)`. It never consults kinds, formulas,
  the lattice, or the registry. Kind resolvers (`_resolve_mul_kind`,
  `_resolve_add_kind`, `_types.py:2082–2163`) are **untouched
  byte-for-byte** — including the hardcoded `frozenset()`s at
  `_types.py:2118–2119`, which are now correct by design rather than a
  gap: formulas do not see aspects in v2.2.0.
- **Law 1 — Discrimination.** `A(x) ≠ A(y)` ⇒ `x == y` is `False`.
- **Law 2 — Additive commensurability.** `x ± y` is aspect-legal iff
  `A(x) == A(y)`.
- **Law 3 — Multiplicative composition.** `A(x·y) = A(x) ∪ A(y)` when
  the union is coherent (no axis conflict).
- **Law 4 — Single-operand transparency.** Scalar mul/div, `__pow__`,
  `__neg__`, `.to()`, `adopt()`, `Bridge.apply()` preserve aspects
  unchanged; no gate applies.
- **Law 5 — Representation invariance.** Conversion changes the
  numeral's chart, never its provenance.
- **Law 6 — Commutativity.** Aspect outcomes are symmetric in the
  operands.
- **Law 7 — Context-freedom.** The outcome depends on the operand
  aspect sets, the op class, and the single ambient `strict` bit —
  nothing else. Two programs with the same operands get the same
  aspect result regardless of loaded formulas, kinds, or systems.
- **Law 8 — ⊤-strictness.** The empty set is a coordinate ("unqualified
  everywhere"), not a wildcard. `{“calibrated”} + {}` refuses under
  strict: absence of a claim is not agreement with one.

Law 7 is also an engineering constraint: the operator-flow design
(amendment G5) places the aspect gate as a peer of the kind gate, and
the Turnstile brief (invariant 3) requires it to stay **out of the
warrant key** — both are only possible because the gate is a pure set
comparison.

---

## The Grammar

Tags are strings. Two forms:

- **Qualified:** `"axis:position"` — e.g. `"convention:V90"`,
  `"signal:rms"`. `axis(t) = t.split(":", 1)[0]`; the remainder is the
  position.
- **Bare:** no colon — e.g. `"calibrated"`. A boolean marker; bare tags
  never conflict with anything.

**Construction invariant (one position per axis):** within a single
aspect set, at most one qualified tag per axis.
`{"signal:rms", "signal:peak"}` is rejected at construction with
`AspectConflict(ValueError)` — enforced in `Number.__post_init__`
(alongside the existing `KindDimensionMismatch` check at
`_types.py:1522–1526`), in `with_aspects()`, and in `Unit.__call__`.

The grammar is what rescues flat sets from their two classic failures:
union under `×` cannot manufacture contradictions (`{rms} ∪ {peak}`
trips the axis guard instead of silently coexisting), and conflicts are
judged **coordinatewise** (per axis), so tags on unrelated axes never
interfere.

---

## Semantics

### Equality (Law 1)

`__eq__` (`_types.py:2307–2325`) gains one clause after the magnitude
comparison: `self.aspects != other.aspects` ⇒ `False`. Context-free,
never raises on aspect difference. (Kind remains outside `__eq__` — an
existing, unchanged behavior; aspects differ because discrimination *is
their charter*. Reopening kind-in-`__eq__` is out of scope.)

### Addition / subtraction (Laws 2, 8)

`_resolve_add_aspects(self, other)` — consulted by `__add__`/`__sub__`
after the existing dimension and kind steps:

| `A(x)` vs `A(y)` | strict (or no context) | permissive (`ctx.strict=False`) |
|---|---|---|
| equal (incl. both empty) | pass; result = `A(x)` | same |
| different | raise `AspectMismatch` | warn; result = `A(x) ∩ A(y)` |

The permissive intersection is coordinatewise drop-to-⊤ for free: a
shared axis with differing positions loses both tags (the result makes
no claim on that axis); unshared tags vanish. Only what both operands
agree on survives — "what can I guarantee about this result?"

The strictness source is the ambient `strict` bit only: `ctx.strict`
when a context is active, `True` when none is. Note the deliberate
divergence from the kind path's no-context leniency (mixed
kinded/unkinded inherits silently at `_types.py:2147–2162` when no
context is active): that is a compatibility artifact of kind threading;
aspects, born strict, do not reproduce it.

### Multiplication / division (Law 3)

`_resolve_mul_aspects(self, other)` — consulted by `__mul__`/
`__truediv__` (and `Ratio.evaluate`):

| condition | strict (or no context) | permissive |
|---|---|---|
| union coherent (no axis holds two positions) | `A(x) ∪ A(y)` | same |
| axis conflict across operands | raise `AspectMismatch` | warn; drop every tag of each conflicted axis, union the rest |

Union is the natural provenance semantics for products ("this power
figure came from this voltage *and* this current"). Idempotence makes
shared tags contribute once.

### Single-operand operations (Laws 4, 5)

`aspects=self.aspects` threaded through: scalar `__mul__`/`__truediv__`
(`_types.py:2170–2179`), `__pow__` (`_types.py:2327–2349` — which
**currently drops `kind` too**; both fixed together, see §Coherence
sweep), `.to()` (all three paths, `_types.py:1960–2046`),
`UnitSystem.adopt()` and `Bridge.apply()`
(`system/__init__.py:841–908, 1170–1226`), `Ratio.evaluate`.

### Explicit rebinding — the only way across a refusal

```python
Number.with_aspects(*tags)   # returns a copy with aspects REPLACED by
                             # the validated set (grammar-checked)
Number.without_aspects()     # returns a copy with aspects == frozenset()
```

Replacement (not merge) semantics: rebinding is an assertion of the new
state, made at the call site, visible in review. This is the M-Layer
posture — crossing a convention boundary is a conversion someone signs.

---

## Worked examples

**Convention gating, zero configuration** (the headline):

```python
v90 = volt(1.0, aspects={"convention:V90"})
vsi = volt(1.0, aspects={"convention:SI"})

v90 + vsi         # AspectMismatch — no context, no policy needed
v90 + volt(0.5)   # AspectMismatch — Law 8: unqualified ≠ V90
v90 == vsi        # False — Law 1 (same magnitude, different identity)

corrected = (v90 * KJ_RATIO).with_aspects("convention:SI")  # explicit
```

Under the superseded hybrid draft, all of the above required declaring
`AspectPolicy(identity_namespaces={"convention"})` inside an active
context first — silent by default, exactly backwards for a correctness
feature.

**Provenance through products:**

```python
v = volt(12.0, aspects={"source:psu_A", "calibrated"})
i = ampere(2.0, aspects={"source:psu_A"})
(v * i).aspects   # {"source:psu_A", "calibrated"} — union, idempotent

i2 = ampere(2.0, aspects={"source:psu_B"})
v * i2            # strict: AspectMismatch (axis "source" conflict)
                  # permissive: warns → {"calibrated"} (axis dropped)
```

**Harmonizing at a boundary** (the pipeline-poisoning answer):

```python
total = sensor_a + sensor_b.with_aspects(*sensor_a.aspects)  # asserted
total = sensor_a.without_aspects() + sensor_b.without_aspects()  # shed
```

Untagged code never meets a gate (`{} == {}` passes trivially), so
adoption is pay-as-you-tag. The hybrid draft's UNION-accumulating
addition ("which sensors fed this total?") is real but belongs to a
per-axis policy — a facet capability, deferred (§Trajectory).

---

## Scope

### In scope

| # | Change | Files |
|---|---|---|
| 1 | `aspects: FrozenSet[str] = frozenset()` field on `Number`; grammar validation in `__post_init__` | `ucon/core/_types.py` |
| 2 | `AspectMismatch(TypeError)`, `AspectConflict(ValueError)`, `axis()` helper | `ucon/aspects/types.py` |
| 3 | `_resolve_add_aspects` / `_resolve_mul_aspects` (pure; read only operands + `strict`) wired into `__add__`, `__sub__`, `__mul__`, `__truediv__` | `ucon/core/_types.py` |
| 4 | `__eq__` aspect clause (Law 1) | `ucon/core/_types.py` |
| 5 | `with_aspects()` / `without_aspects()` | `ucon/core/_types.py` |
| 6 | `__repr__` `#tag` tokens, sorted (scaffold at `_types.py:2351–2368`) | `ucon/core/_types.py` |
| 7 | Single-operand transparency: scalar paths, `__pow__` (incl. the kind-drop fix), `.to()`, `adopt()`, `Bridge.apply()`, `Ratio.evaluate` | `ucon/core/_types.py`, `ucon/system/__init__.py` |
| 8 | `Unit.__call__` gains `kind=None`, `aspects=frozenset()` kwargs (`_types.py:676–708`) | `ucon/core/_types.py` |
| 9 | Construction-site audit test (AST scan, in the spirit of `test_no_cross_module_injection.py`); pickle round-trip | `tests/ucon/` |
| 10 | Exports: `AspectSet`, `AspectMismatch`, `AspectConflict` | `ucon/__init__.py` |
| 11 | Tests (template: `tests/ucon/kinds/test_arithmetic_dispatch.py`) | `tests/ucon/` |
| 12 | CHANGELOG (incl. `__pow__` kind fix under Fixed); ROADMAP; terminology docs note (M-Layer "aspect" = ucon `Kind`; ucon `Aspect` = provenance/convention tag) | `CHANGELOG.md`, `ROADMAP.md`, `docs/` |

### Explicitly NOT in scope (deltas from the hybrid draft)

- **No `AspectPolicy`, no `identity_namespaces`, no join-policy
  selection.** There is no policy object at all.
- **No `ActiveContext` changes.** The hybrid draft's item 10 is gone;
  aspects read the existing `strict` field only.
- **No formula wiring.** `KindFormula.project_aspects` and `AspectRule`
  stay shipped-but-dormant; `ctx.formulas.apply()` continues to receive
  empty frozensets (Law 0). Formula-mediated CARRY/CONSUME returns as a
  *facet-keyed* capability in the facet system, where it can be precise.
- **No species split.** Every tag discriminates. "Lineage that never
  gates" was the hybrid's mechanism for provenance accumulation across
  `+`; that capability moves to facets (per-axis policies).
- `AspectRule`, `AspectJoinPolicy`, `join_aspects` remain **unexported**
  (private module paths; freely changeable later).
- Unchanged from the hybrid draft's out-of-scope list: aspect-pair
  conversions (`V90 → SI` factors in `.to()`), aspect value validation,
  `NumberArray` threading, cache-codec changes, TOML serialization of
  Number aspects, `enforce_dimensions` aspects.

---

## Coherence sweep (bundled)

Same rationale as the hybrid draft's §10 — fix metadata-dropping
construction sites once, for kind and aspects together:

1. `Unit.__call__` kwargs (scope #8) — primary construction ergonomics.
2. `Ratio.evaluate` (`_types.py:2389–2411`) — currently drops kind in
   both branches; delegates to the division resolvers for both channels.
3. `Number.to()` — `aspects=self.aspects` in all three paths (kind
   already threaded).
4. `adopt()` / `Bridge.apply()` — `aspects=n.aspects` every branch.
5. `__pow__` (`_types.py:2327–2349`) — split treatment. **Kind:**
   preserved when `power == 1`; deliberately dropped (with an in-code
   comment) for any other power, since `speed²` is not `speed` and kind
   exponentiation is out of scope. This makes the current silent drop
   *documented* rather than accidental. **Aspects:** preserved for all
   powers per Law 4. The asymmetry is principled: kind transforms under
   the operation and must not be copied blindly; aspects are provenance
   and do not transform.
6. Construction-site audit + pickle round-trip (scope #9).

---

## Commit plan

| # | Scope | Files |
|---|---|---|
| 1 | `aspects` field + grammar validation + `AspectConflict` + `__repr__` + `with_aspects`/`without_aspects` | `ucon/core/_types.py`, `ucon/aspects/types.py` |
| 2 | `AspectMismatch` + `_resolve_add_aspects`/`_resolve_mul_aspects` + wiring into the four operators + `__eq__` clause | `ucon/core/_types.py`, `ucon/aspects/types.py` |
| 3 | Single-operand transparency sweep (scalar, `__pow__` incl. kind fix, `.to()`, `adopt()`, `Bridge.apply()`, `Ratio.evaluate`) + `Unit.__call__` kwargs | `ucon/core/_types.py`, `ucon/system/__init__.py` |
| 4 | Exports | `ucon/__init__.py` |
| 5 | Tests (laws, gates, sweep, audit, pickle) | `tests/ucon/` |
| 6 | CHANGELOG + ROADMAP + terminology note | docs |

Import-DAG note: `ucon.aspects.types` imports only stdlib (`enum`,
`typing`) — a Layer-0 leaf. `core/_types.py` gains one top-level import
from it; no deferred import, no `KNOWN_DEFERRED` change, structural
guards (`test_import_dag.py`, `test_no_cross_module_injection.py`)
unaffected.

---

## Test plan

Organized by law, then by surface:

- **Law 1:** equal magnitudes, different aspects ⇒ `==` is `False`;
  equal aspects ⇒ magnitude comparison decides (existing behavior).
- **Law 2/8:** `+`/`−` — equal sets pass (incl. both-empty); any
  difference: strict raises `AspectMismatch`, no-context raises,
  permissive warns and intersects (verify coordinatewise drop: shared
  axis / differing position loses both).
- **Law 3:** `×`/`÷` — coherent union; axis conflict: strict raises,
  permissive warns and drops the conflicted axis only; idempotence.
- **Law 4/5:** scalar mul/div, `__pow__`, `.to()` (all three paths),
  `adopt()`, `Bridge.apply()`, `Ratio.evaluate` preserve aspects; no
  gate on any single-operand path.
- **Law 0:** existing `tests/ucon/kinds/test_arithmetic_dispatch.py`
  passes **without modification**; assert `apply()` still receives
  empty frozensets (spy).
- **Law 6:** pairwise outcomes symmetric under operand swap.
- **Law 7:** same operands, different loaded formulas/kinds/systems ⇒
  identical aspect outcomes.
- **Grammar:** one-position-per-axis rejected at `Number(...)`,
  `with_aspects()`, `Unit.__call__`; bare tags never conflict;
  `"a:b:c"` parses as axis `a`.
- **`__pow__` kind fix:** regression test for the current drop.
- **Structural:** construction-site audit; pickle/copy round-trip.
- **Integration:** V90/SI scenario (refuse silently mixed; explicit
  `with_aspects` crosses); provenance-through-products chain.

---

## Trajectory — forward compatibility with facets

The facet proposal (registry-declared `AspectFacet(name, positions,
applies_to, multiplication_policy)`, `Mapping[str, str]` storage) is
the destination; this release is its L1 rung, built so the climb is
mechanical. The ADR should be imported to
`docs/internal/proposals/aspect-facets.md` when adopted. Guarantees:

1. **Storage isomorphism.** A grammar-valid `FrozenSet[str]` is
   isomorphic to `Mapping[str, str]` (qualified tags → entries; bare
   tags → boolean axes). The one-position-per-axis invariant *is* the
   Mapping key-uniqueness property, enforced early.
2. **Refusal monotonicity.** Facets may only *relax* v2.2.0 outcomes
   (a declared per-axis policy turning a refusal into a defined
   combination). Nothing admitted in v2.2.0 is refused later, and no
   admitted result changes value. Code written against v2.2.0 semantics
   survives the migration.
3. **Vocabulary.** "axis" and "position" here are the ADR's terms.
4. **API surface kept minimal.** Only `AspectSet`, `AspectMismatch`,
   `AspectConflict` go public; the facet system can restructure
   everything unexported without deprecation debt.
5. **Gate shape preserved.** The context-free set-comparison gate (Law
   7) is what the operator-flow pipeline (G5) and Turnstile (invariant
   3: aspects out of the warrant key, hot-path peer gate) assume; the
   facet registry must keep the hot-path gate registry-free (compile
   facet policies ahead of the gate, in the spirit of the Turnstile).

---

## Resolved questions

1. **Species split (hybrid Q5)?** Withdrawn. All tags discriminate;
   "lineage flow" returns as per-axis facet policy. The hybrid's
   pipeline-poisoning objection is answered by pay-as-you-tag (`{}⊕{}`
   never gates), explicit rebinding, and permissive mode.
2. **Unified `_resolve_mul_metadata` (hybrid Q2)?** Withdrawn — it
   coupled aspect resolution to `formulas.apply()`, violating Law 0.
   Kind and aspect resolvers stay separate functions.
3. **`__eq__` and aspects (hybrid Q3)?** Reversed: aspects participate
   (Law 1). Discrimination-at-comparison is the feature's definition;
   an aspect system whose `==` ignores aspects cannot catch the V₉₀
   error at the surface where it bites.
4. **Pass-through for mixed aspected/unaspected (hybrid Q4)?**
   Reversed for `+`/`−` (Law 8: ⊤-strict). Preserved for single-operand
   ops (Law 4) and for `×`/`÷` (union with an empty set is the present
   set — same visible behavior, principled reason).
5. **`AspectPolicy` on `ActiveContext` (hybrid Q1/§6)?** Withdrawn
   entirely (Law 7).

## References

Unchanged from the hybrid draft: Hall & Kuster (2021); Hall (2022);
Acta IMEKO (2023) — the V₉₀ → SI identity-gating precedent; Flater,
NIST TN 1943; Scontras (2014). Terminology mapping recorded in scope
item 12.

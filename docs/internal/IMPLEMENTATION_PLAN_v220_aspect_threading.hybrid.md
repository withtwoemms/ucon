# Implementation Plan: ucon v2.2.0 — Aspect Threading

> **Status:** Draft (revised 2026-07-12 — open questions resolved; scope
> updated: hybrid gating (lineage vs identity aspects), unified metadata
> resolver, coherence sweep bundled, cache-codec item dropped)
> **Supersedes:** `IMPLEMENTATION_PLAN_v220_aspect_threading.original.md`
> (preserved pre-revision draft)
> **Depends on:** v2.1.0 (Kind threading), v2.1.1 (cosmetic fixes)

---

## Motivation

v2.1.0 threaded Kind-of-Quantity through `Number` arithmetic: `__mul__`,
`__truediv__`, and `__add__`/`__sub__` now consult the `FormulaRegistry`
and `KindLattice` to propagate kind semantics. Aspects — covariant
provenance/calibration tags — already have the data model (`AspectSet`,
`AspectRule`, `AspectJoinPolicy`, `join_aspects`) and the formula
projection logic (`KindFormula.project_aspects`), but they remain
caller-side. `Number` has no `aspects` field; the runtime ignores them.

The gap is narrower than it looks: `_resolve_mul_kind`
(`ucon/core/_types.py:2117`) already calls `ctx.formulas.apply()`, which
computes and returns `output_aspects` on every kinded multiplication —
and the caller discards it, passing hardcoded empty `frozenset()`s in.
v2.2.0 closes this gap by threading aspects through `Number`, structurally
parallel to how v2.1.0 threaded kinds, with gating semantics split by
aspect species (see Design Principles 1–3).

The species split is grounded in the metrology literature: Hall's
M-Layer program treats convention/reference distinctions (e.g. the 1990
conventional volt vs. the SI volt) as *identity-bearing* — mixing them
without an explicit conversion is precisely the error class the M-Layer
exists to prevent — while traceability/lineage annotations flow with the
data. See References.

---

## Design Principles

1. **Mirror Kind threading structurally; gate only what is
   identity-bearing.** Aspects reuse the Kind threading *architecture* —
   resolver helpers on `Number`, `ActiveContext` policy field,
   formula-registry projection — and split semantically into two
   species (Principle 2):

   - **Lineage aspects never gate arithmetic.** No exception, no
     strict-mode raise, no permissive warning for mixed
     aspected/unaspected operands.
   - **Identity aspects gate exactly like kinds.** Conflicting or
     ambiguous identity tags raise `AspectMismatch` under
     `strict=True` and warn-and-degrade under permissive mode — the
     same decision table as `KindMismatch`.

   *Justification:* an empty **lineage** set means "no claims recorded",
   not "conflicting claim"; every literal, intermediate, and
   `Unit.__call__` product is unaspected, so gating lineage would make a
   single tagged operand poison entire pipelines. An **identity** tag,
   by contrast, marks a reference convention under which the *value
   itself* is expressed (V₉₀ vs V_SI); silently combining across
   conventions is a correctness error of the same class as mixing
   kinds, and the literature (Hall, M-Layer) treats it as such. Because
   identity aspects reuse the kind decision table, `strict` gains no
   third semantics — its meaning remains "identity mismatches raise".

2. **Two species of aspects, split by declared namespace.** A tag of
   the form `"ns:value"` belongs to namespace `ns` (text before the
   first `:`); tags without `:` have no namespace. A namespace declared
   in `AspectPolicy.identity_namespaces` makes its tags
   **identity-bearing**; all other tags (including all un-namespaced
   tags) are **lineage**. The default policy declares no identity
   namespaces, so out of the box **nothing gates** — gating is fully
   opt-in and v2.2.0's default behavior is pure pass-through.

3. **Unaspected operands are transparent — for lineage.** An empty
   lineage set is the neutral element: present lineage aspects flow
   through it unchanged; join policies apply only when **both**
   operands carry lineage aspects. For a *declared identity namespace*,
   absence on one operand is ambiguity, not neutrality: strict raises,
   permissive adopts the present tag with a warning (mirroring
   kinded + unkinded arithmetic in v2.1.0).

4. **Aspects are orthogonal to kinds.** Two Numbers sharing a kind can
   differ in aspects; two Numbers with different kinds can share aspects.
   Aspect propagation never gates on kind identity, and aspect resolution
   proceeds even when both operands are unkinded.

5. **Default INTERSECT for addition (both-aspected lineage only).**
   When two non-empty lineage sets combine under `__add__`/`__sub__`,
   the conservative default keeps only shared aspects ("what can I
   guarantee about this result?"). The caller can opt in to `UNION` via
   `AspectPolicy.join`. Per Principle 3, INTERSECT is **not** applied
   literally against an empty operand — that would silently annihilate
   provenance ({calibrated} ∩ {} = {}). Identity tags that survive the
   gate (both sides agree, or permissive adoption) are kept regardless
   of join policy.

6. **Formula multiplication uses UNION over CARRY bindings.** Already
   implemented in `KindFormula.project_aspects`
   (`ucon/formulas/types.py:145-188`); does not change. v2.2.0 wires the
   real operand aspect sets into `apply()` and the projected output into
   the result `Number`. `CONSUME` remains the formula author's tool for
   dropping operand aspects.

7. **UNION as provenance accumulation.** Under `UNION` policy, lineage
   aspects model additive provenance: "either operand was calibrated",
   "this quantity touched sensors A and B". This supports calibration
   chain tracking, where successive operations accumulate provenance
   tags rather than filtering them down.

---

## Scope

### In scope

| # | Change | Files |
|---|--------|-------|
| 1 | Add `aspects: FrozenSet[str]` field to `Number` | `ucon/core/_types.py` |
| 2 | `__repr__` renders `#aspect` tokens (scaffold at `_types.py:2356`) | `ucon/core/_types.py` |
| 3 | `Number.__class_getitem__` accepts `AspectSet` constraint | `ucon/core/_types.py` |
| 4 | `AspectPolicy` dataclass (join policy + identity namespaces) and `AspectMismatch(TypeError)` | `ucon/aspects/types.py` |
| 5 | Unified `_resolve_mul_metadata` returning `(kind, aspects)` — replaces `_resolve_mul_kind`, single `apply()` call | `ucon/core/_types.py` |
| 6 | `_resolve_add_aspects` helper (identity gate → pass-through → policy join) | `ucon/core/_types.py` |
| 7 | `_check_identity_aspects` shared gate (invoked by both resolvers) | `ucon/core/_types.py` |
| 8 | Wire aspect resolution into `__mul__`, `__truediv__`, `__add__`, `__sub__` | `ucon/core/_types.py` |
| 9 | Scalar multiplication/division preserves aspects (parallels scalar × kind; single-operand, no gate) | `ucon/core/_types.py` |
| 10 | Add `aspect_policy: AspectPolicy` to `ActiveContext` (`system/__init__.py:917-1002`) and thread through `use()` | `ucon/system/__init__.py` |
| 11 | Export `AspectSet`, `AspectRule`, `AspectJoinPolicy`, `AspectPolicy`, `AspectMismatch`, `join_aspects` from `ucon/__init__.py` | `ucon/__init__.py` |
| 12 | **Metadata coherence sweep** (see §10) — `Unit.__call__` kwargs, `Ratio.evaluate`, `.to()` / `adopt()` / `Bridge.apply()` aspect preservation, construction-site audit | `ucon/core/_types.py`, `ucon/system/__init__.py`, `tests/ucon/` |
| 13 | Tests (template: `tests/ucon/kinds/test_arithmetic_dispatch.py`) | `tests/ucon/` |
| 14 | CHANGELOG entry; docs note on terminology (ucon `Kind` ≈ VIM/M-Layer "aspect"/kind-of-quantity; ucon `Aspect` ≈ provenance/convention tag) | `CHANGELOG.md`, `docs/` |

### Out of scope

- **Registered aspect-pair conversions** (full M-Layer parity: e.g.
  `register_conversion("convention:V90", "convention:SI", factor=…)`
  with automatic application in `.to()`). Deferred; crossing an
  identity gate in v2.2.0 is explicit via `with_aspects()` rebinding.
  Candidate v2.3+ scope alongside `ConversionGraph` integration.
- **Cache codec changes.** Dropped: `ucon/_cache.py` serializes the
  conversion graph and formulas, not `Number` instances. Numbers are
  transient runtime values. Coverage instead via a pickle round-trip
  test (`tests/ucon/test_pickle.py`).
- **Aspect value validation.** Identity *namespaces* are declared, but
  tag *values* remain free-form strings — no `AspectLattice`, no
  `AspectNotFound`, no enumeration of legal values per namespace.
- **`NumberArray` aspect support.** Deferred to a follow-up; array
  operations are not kind-threaded yet either. (Candidate v2.3 scope:
  thread kind + aspects through `NumberArray` and the pandas/polars
  integrations together.)
- **TOML serialization of aspects on Number.** Numbers are not serialized
  to TOML; aspects on formulas already round-trip.
- **`enforce_dimensions` extension for aspects.** Deferred; the
  `Number[Dimension, Kind]` annotation syntax is sufficient for v2.2.0.

---

## Detailed Design

### 1. `Number.aspects` field

```python
@dataclass
class Number:
    quantity: Union[float, int] = 1.0
    unit: Union[Unit, UnitProduct] = None
    uncertainty: Union[float, None] = None
    kind: Union[Kind, None] = None
    aspects: FrozenSet[str] = frozenset()   # NEW
```

Default is `frozenset()` (no aspects), not `None`. This avoids
`None`-checks throughout the arithmetic path and mirrors how
`AspectSet()` is empty rather than absent. `frozenset` is immutable, so
a plain class-level default is safe (no `default_factory` needed).

No validation in `__post_init__`: aspects are orthogonal to dimension
and kind (Principle 4), and identity semantics are a property of the
active policy, not of the tag.

`__eq__` **ignores aspects** (resolved question 3): equality remains
physical (quantity/unit/uncertainty/kind as today). Two Numbers with
identical physical value but different provenance compare equal. If
provenance-sensitive comparison is needed later, add a `provenance_eq`
method — not in v2.2.0 scope.

### 2. `__repr__`

The scaffold at `_types.py:2356` already anticipates `#aspect` tokens:

```
<{q} [± {u}] [{shorthand}] [[kind_name]] [#aspect ...]>
```

Implementation:

```python
if self.aspects:
    for a in sorted(self.aspects):
        parts.append(f"#{a}")
```

### 3. `AspectPolicy` and the identity gate

```python
# ucon/aspects/types.py

@dataclass(frozen=True)
class AspectPolicy:
    join: AspectJoinPolicy = AspectJoinPolicy.INTERSECT
    identity_namespaces: FrozenSet[str] = frozenset()


class AspectMismatch(TypeError):
    """Identity-bearing aspects conflict or are ambiguous.

    Raised only for namespaces declared in
    AspectPolicy.identity_namespaces, only under strict mode.
    Parallel to KindMismatch.
    """
```

Namespace rule: for tag `t`, `namespace(t) = t.split(":", 1)[0]` if
`":" in t`, else no namespace (always lineage). A tag is
identity-bearing iff its namespace is in the active policy's
`identity_namespaces`.

**The gate** — `_check_identity_aspects(self, other, ctx)`, invoked by
both the mul and add resolvers *before* any join/projection. For each
declared identity namespace `ns`, with `L`/`R` = the operands' tags in
`ns` (each a set of zero or more tags):

| L (ns tags) | R (ns tags) | strict | permissive |
|---|---|---|---|
| ∅ | ∅ | pass (namespace unused) | pass |
| {x} | {x} | pass; `x` kept in result | same |
| {x} | {y}, x ≠ y | raise `AspectMismatch` | warn; drop all `ns:*` from result ("degrade to unknown") |
| {x} | ∅ (or vice versa) | raise `AspectMismatch` (ambiguous operand) | warn; result adopts `x` |

Rows 3–4 are the kind decision table verbatim (`KindMismatch` /
permissive warn-and-inherit at `_types.py:2128-2164`); this is the
Principle 1 mirror. Multiple tags in one namespace on a single operand
are treated as a conflict per row 3.

Only Number⊕Number arithmetic consults the gate. Scalar paths (§8),
`.to()`, `adopt()`, and `Bridge.apply()` are single-Number operations —
identity tags are preserved unconditionally there.

With **no active context**, no namespaces are declared, so the gate is
a no-op and all tags behave as lineage.

### 4. Multiplication metadata resolution (`_resolve_mul_metadata`)

**Resolved question 2: unified resolver.** `_resolve_mul_kind` is
renamed/refactored to `_resolve_mul_metadata(other, *, op)` returning
`(kind, aspects)`. One `ctx.formulas.apply()` call yields both; the
current implementation's discarded third tuple element
(`output_aspects`) is captured. `_resolve_mul_kind` is private, so no
deprecation surface exists.

Kind behavior is **unchanged from v2.1.0** (strict `KindMismatch` /
`FormulaNotFound` raising, permissive warn-and-degrade). Aspect
resolution proceeds in two stages: the identity gate (§3) first, then
lineage combination:

| self lineage | other lineage | Result lineage aspects |
|---|---|---|
| empty | empty | `frozenset()` |
| non-empty | empty (or vice versa) | the present set, unchanged (transparent pass-through) |
| non-empty | non-empty, formula resolved | `project_aspects` output (UNION over CARRY bindings; CONSUME drops) |
| non-empty | non-empty, no formula path* | `self ∪ other` (union — both operands contributed) |

Result aspects = surviving identity tags (per §3) ∪ resulting lineage
set.

\* "No formula path" covers: both operands unkinded, mixed
kinded/unkinded under permissive mode, `FormulaNotFound` under
permissive mode, and no active context. Union is the consistent default
because formula projection is itself union-over-CARRY; a formula's only
additional power is `CONSUME`.

When both operands are kinded and a formula resolves, the real aspect
sets are passed in (replacing the hardcoded empty frozensets at
`_types.py:2118-2119`):

```python
_, result_kind, result_aspects, _ = ctx.formulas.apply(
    {"left": (self.kind, self.aspects),
     "right": (other.kind, other.aspects)},
    lattice=ctx.kinds,
)
```

Note the transparent-pass-through row applies to the *no-formula*
resolution tiers; when a formula **is** consulted, its `aspect_rules`
govern even if one operand's set is empty (an empty set simply
contributes nothing to the union). Formula `CONSUME` may drop identity
tags like any other tag — a formula author explicitly modeling the
operation outranks the default gate outcome.

### 5. Addition aspect resolution (`_resolve_add_aspects`)

Parallel in shape to `_resolve_add_kind` (`_types.py:2128-2164`).
Stage 1: identity gate (§3) — the only path by which addition raises
on aspects. Stage 2: lineage combination, which never raises and never
warns:

| self lineage | other lineage | Result lineage aspects |
|---|---|---|
| empty | empty | `frozenset()` |
| non-empty | empty (or vice versa) | the present set, unchanged (transparent pass-through; policy **not** applied) |
| non-empty | non-empty | `join_aspects(self, other, ctx.aspect_policy.join)` |

Identity tags surviving the gate are kept regardless of join policy
(Principle 5): agreement means both sides carry the tag, so INTERSECT
would keep it anyway; permissive adoption re-adds it after the join.

Default join is `INTERSECT` — only shared lineage aspects survive when
both sides carry them. Callers opt in to `UNION` (and/or declare
identity namespaces) via:

```python
ctx = ActiveContext(
    system=sys,
    formulas=reg,
    kinds=lattice,
    aspect_policy=AspectPolicy(
        join=AspectJoinPolicy.UNION,
        identity_namespaces=frozenset({"convention"}),
    ),
)
```

With no active context, mixed and both-aspected cases fall back to the
default `INTERSECT` semantics above (pass-through still applies to the
mixed case — it does not depend on a context), and no identity gating
occurs.

`__sub__` mirrors `__add__`.

### 6. `ActiveContext.aspect_policy`

```python
@dataclass(frozen=True)
class ActiveContext:
    system: 'UnitSystem'
    formulas: FormulaRegistry
    kinds: KindLattice
    strict: bool = True
    aspect_policy: AspectPolicy = AspectPolicy()   # NEW
```

`use()` gains an `aspect_policy=` override with the same
enclosing-context inheritance as `formulas`/`kinds`/`strict`.

### 7. Strict-mode errors

`AspectMismatch(TypeError)` — raised **only** for declared identity
namespaces, **only** under `strict=True`, per the §3 table. Lineage
aspects never raise. `strict` retains a single unified meaning across
kinds and identity aspects: "identity mismatches raise"; it gains no
third semantics. With the default (empty) `AspectPolicy`,
`AspectMismatch` is unreachable.

### 8. Scalar operations

Scalar × Number and Number / scalar preserve aspects, same as they
preserve kind. Single-operand: the identity gate does not apply.

```python
if isinstance(other, (int, float)):
    return Number(
        quantity=self.quantity * other,
        unit=self.unit,
        uncertainty=...,
        kind=self.kind,
        aspects=self.aspects,  # preserved
    )
```

### 9. Worked examples

**Lineage: UNION as provenance vehicle** — calibration chain tracking.

```python
sensor_a = Number(100, joule, aspects=AspectSet("sensor_A", "calibrated_2026"))
sensor_b = Number(50, joule, aspects=AspectSet("sensor_B", "calibrated_2026"))

with ucon.context(aspect_policy=AspectPolicy(join=AspectJoinPolicy.UNION)):
    total = sensor_a + sensor_b
    # total.aspects == {"sensor_A", "sensor_B", "calibrated_2026"}
    # Provenance: "this total incorporates data from both sensors"
```

Under the default `INTERSECT`:

```python
total = sensor_a + sensor_b
# total.aspects == {"calibrated_2026"}
# Guarantee: "this total is calibrated" (both inputs were)
```

The two policies answer different questions:
- **INTERSECT**: "What can I guarantee about this result?"
- **UNION**: "What went into this result?"

And per Principle 3, adding an unaspected constant to either sensor
reading leaves its lineage intact under **both** policies:

```python
adjusted = sensor_a + Number(3, joule)
# adjusted.aspects == {"sensor_A", "calibrated_2026"}
```

**Identity: convention gating** — Hall's canonical error class, the
1990 conventional volt.

```python
policy = AspectPolicy(identity_namespaces=frozenset({"convention"}))

with ucon.context(aspect_policy=policy):          # strict=True
    v90 = volt(1.0, aspects={"convention:V90"})
    vsi = volt(1.0, aspects={"convention:SI"})

    v90 + vsi          # raises AspectMismatch: conflict in 'convention'
    v90 + volt(0.5)    # raises AspectMismatch: ambiguous operand
    v90 + volt(0.5, aspects={"convention:V90"})   # fine → {"convention:V90"}

    # crossing the gate is explicit, never silent:
    vsi_val = (v90 * KJ_RATIO).with_aspects("convention:SI")
```

Species compose independently within one expression:

```python
a = volt(1.0, aspects={"convention:V90", "measured:sensor_a"})
b = volt(2.0, aspects={"convention:V90", "measured:sensor_b"})
(a + b).aspects
# identity ns:  V90 == V90 → kept
# lineage:      {measured:sensor_a} ∩ {measured:sensor_b} → ∅
# == {"convention:V90"}
```

### 10. Metadata coherence sweep (bundled)

Kind threading (v2.0.0/v2.1.0) left construction sites that silently
drop metadata; aspects would inherit every hole. Fix once, for both,
in this release:

1. **`Unit.__call__`** (`_types.py:676-708`) gains `kind=None` and
   `aspects=frozenset()` keyword parameters, passed through to the
   constructed `Number`. This makes the primary construction ergonomics
   able to express metadata at all
   (`joule(100, aspects=AspectSet("sensor_A"))`).
2. **`Ratio.evaluate`** (`_types.py:2389-2411`) currently drops kind and
   would drop aspects in both branches. It delegates metadata resolution
   to the same rules as `__truediv__` (i.e. `_resolve_mul_metadata`
   semantics): kind per division rules, aspects per §4 tables including
   the identity gate.
3. **`Number.to()`** (all three paths: fast, scale-only, general —
   `_types.py:1960-2046`) passes `aspects=self.aspects` alongside the
   existing `kind=self.kind`. Conversion changes representation, not
   provenance; identity tags ride along (an aspect-pair conversion
   registry that could *change* them is out of scope).
4. **`UnitSystem.adopt()` and `Bridge.apply()`**
   (`system/__init__.py:841-908, 1170-1226`) pass `aspects=n.aspects`
   in every branch, matching the v2.1.0 kind fix.
5. **Construction-site audit test.** A test enumerates `Number(...)`
   construction sites in `ucon/` (AST scan, in the spirit of
   `test_no_cross_module_injection.py`) and asserts each either threads
   `kind`/`aspects` or appears in an explicit, commented allowlist of
   sanctioned drops (e.g. dimensionless-division `kind=None`). This
   prevents a third leak-patching pass in a future release.
6. **Pickle round-trip.** `aspects` survive `pickle`/`copy`
   (`tests/ucon/test_pickle.py`).

---

## Commit Plan

| # | Scope | Files |
|---|-------|-------|
| 1 | `Number.aspects` field + `__repr__` + scalar preservation | `ucon/core/_types.py` |
| 2 | `AspectPolicy` + `AspectMismatch` + namespace helpers | `ucon/aspects/types.py` |
| 3 | `_resolve_mul_metadata` (unified; captures `output_aspects`) + `_check_identity_aspects` | `ucon/core/_types.py` |
| 4 | `_resolve_add_aspects` + `aspect_policy` on `ActiveContext` + `use()` override | `ucon/core/_types.py`, `ucon/system/__init__.py` |
| 5 | Wire aspects into `__mul__`, `__truediv__`, `__add__`, `__sub__` | `ucon/core/_types.py` |
| 6 | Coherence sweep: `Unit.__call__` kwargs, `Ratio.evaluate`, `.to()`, `adopt()`, `Bridge.apply()` | `ucon/core/_types.py`, `ucon/system/__init__.py` |
| 7 | Public API exports | `ucon/__init__.py` |
| 8 | Tests (incl. identity gate, construction-site audit, pickle round-trip) | `tests/ucon/` |
| 9 | CHANGELOG + ROADMAP + terminology docs note | `CHANGELOG.md`, `ROADMAP.md`, `docs/` |

---

## Test Plan

Template: `tests/ucon/kinds/test_arithmetic_dispatch.py` (same
scenario structure, substituting aspect assertions; identity-gate tests
reuse the kind gating scenarios directly).

- **Unit:** aspect round-trip through all four arithmetic operators
- **Unit:** scalar multiplication/division preserves aspects (incl.
  identity tags — no gate on single-operand paths)
- **Unit:** transparent pass-through — lineage-aspected ⊕ unaspected
  keeps the present set for all four operators, under both INTERSECT
  and UNION, with and without an active context, no warnings emitted
- **Unit:** `INTERSECT` keeps shared lineage only (both-aspected)
- **Unit:** `UNION` accumulates all lineage (both-aspected)
- **Unit:** no-formula multiplication of two aspected Numbers unions
  aspects (both-unkinded, permissive-mixed, permissive-FormulaNotFound
  tiers)
- **Unit:** identity gate — conflicting tags in a declared namespace:
  strict raises `AspectMismatch`, permissive warns and drops `ns:*`
- **Unit:** identity gate — identity tag vs untagged operand: strict
  raises, permissive warns and adopts (mirror of kinded + unkinded)
- **Unit:** identity gate — agreement passes and tag survives under
  both join policies; undeclared namespaces never gate; default
  (empty) policy makes `AspectMismatch` unreachable
- **Unit:** mixed-species expression — identity kept while lineage
  intersects away (the §9 composition example)
- **Unit:** formula `project_aspects` with `CARRY`/`CONSUME` rules wired
  through `__mul__` — real operand sets reach `apply()`; `CONSUME` may
  drop identity tags
- **Unit:** kind behavior unchanged — existing
  `test_arithmetic_dispatch.py` passes without modification
- **Unit:** `__repr__` renders `#aspect` tokens sorted; `__eq__` ignores
  aspects
- **Unit:** `Unit.__call__(q, kind=..., aspects=...)`; `Ratio.evaluate`
  threads metadata; `.to()` / `adopt()` / `Bridge.apply()` preserve
  aspects
- **Structural:** construction-site audit (allowlisted drops only)
- **Unit:** pickle/copy round-trip preserves aspects
- **Integration:** calibration chain scenario (UNION accumulation across
  multiple additions, with unaspected constants interleaved)
- **Integration:** V90/SI convention scenario — gate raises on silent
  mix; explicit `with_aspects()` rebind crosses it
- **Integration:** radiation weighting formula with `CONSUME` drops
  sensor aspects

---

## Resolved Questions

1. ~~Should `AspectMismatch` subclass `TypeError`?~~ **Yes, reinstated
   and narrowed:** `AspectMismatch(TypeError)` exists but fires only
   for declared identity namespaces under strict mode; lineage aspects
   never gate (2026-07-12, superseding the same-day "no gating"
   resolution — see question 5).

2. ~~Merge `_resolve_mul_kind` and `_resolve_mul_aspects`?~~ **Merged:**
   single `_resolve_mul_metadata` returning `(kind, aspects)`; one
   `FormulaRegistry.apply()` call per multiplication (2026-07-12).

3. ~~Should `Number.__eq__` consider aspects?~~ **No:** equality remains
   physical. A `provenance_eq` method may be added later if a concrete
   need surfaces (2026-07-12).

4. Mixed aspected/unaspected under default INTERSECT: **pass-through
   for lineage** — the empty set is "no information", not a claim; join
   policies apply only when both operands carry lineage aspects
   (2026-07-12).

5. *(New)* Gate everything (original draft) vs gate nothing (first
   revision)? **Hybrid:** aspects split into lineage (pass-through,
   never gate) and identity (declared namespaces; kind-style gating).
   Grounded in Hall's M-Layer treatment of convention distinctions
   (V₉₀ vs V_SI) as identity-bearing, while traceability annotations
   flow. Default policy declares no identity namespaces, so gating is
   strictly opt-in (2026-07-12).

---

## References

- Hall & Kuster, *Metrological support for quantities and units in
  digital systems*, Measurement: Sensors (2021) — three independent
  aspects of measurement data.
- Hall, *Representing and Expressing Measurement Data in Digital
  Systems*, SN Computer Science (2022) — ⟨aspect, value, scale⟩
  triples; "aspect" as extension of kind-of-quantity.
- *Toward a metrology-information layer for digital systems*, Acta
  IMEKO (2023) — AspectID registry prototype; V₉₀ → SI volt conversion
  demo (the identity-gating precedent).
- Flater, NIST TN 1943, *Architecture for Software-Assisted Quantity
  Calculus* — kinds must be tracked in addition to units; explicit kind
  arithmetic (ucon's `FormulaRegistry` design point).
- Scontras, *The Semantics of Measurement*, Harvard dissertation
  (2014) — measurement identity as ⟨measure, kind, partition, degree⟩;
  independent convergence on "number + unit underdetermines".
- Terminology note: in the M-Layer literature "aspect" *means*
  kind-of-quantity — i.e. ucon's `Kind`. ucon's `Aspect` corresponds to
  provenance/convention tags (closest to Hall's traceability
  modelling). The docs note in scope item 14 records this mapping.

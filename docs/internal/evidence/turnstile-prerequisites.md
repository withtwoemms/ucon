# VETTED FINDINGS — Turnstile prerequisites

**Status:** Evidence record. Every claim below was executed, not argued.
**Environment:** ucon 2.1.1 — confirmed latest on PyPI and the installed version.
**Convention:** `[live]` = executed against installed 2.1.1. `[fixture]` = executed
against a constructed lattice. `[v4]`/`[v6]` = read from the architecture documents.
**Unvetted claims are listed in §9 and must not be treated as results.**

---

## 1. Shipped defects (baseline)

| # | Behavior | Expected | Method |
|---|----------|----------|--------|
| 1.1 | `1 Gy + 1 Sv` → `<2 Gy>` | REFUSE | `[live]` |
| 1.2 | `1 rad + 180 deg` → `<181 rad>` | convert | `[live]` |
| 1.3 | `5 °C → °F` = `41.0` | 41.0 if point; 9.0 if displacement — no way to express the second | `[live]` |
| 1.4 | `2 × Number(20, celsius)` → `<40 °C>` | REFUSE (chart-dependent) | `[live]` |
| 1.5 | `1 m + 1 s` → `TypeError` | correct | `[live]` |

**Diagnosis (from `inspect.getsource(Number.__add__)`):** gates on
`self.unit.dimension != other.unit.dimension`, calls `_resolve_add_kind`, then
constructs `Number(self.quantity + other.quantity, unit=self.unit, ...)`.

> **`__add__` consults φ (dimension) and never ψ (scale).** Kind resolution runs
> correctly and is stapled onto a raw magnitude addition.

**1.4 rationale** — the operation is not chart-invariant:
20 °C = 293.15 K. Doubling in celsius gives 40 °C = 313.15 K; doubling in kelvin
gives 586.30 K = 313.15 °C. Two different answers from an arbitrary convention.

---

## 2. Structural facts about the kind layer

| Fact | Method |
|------|--------|
| `Number` fields: `quantity, unit, uncertainty, kind` — **no `aspect`** | `[live]` `dataclasses.fields` |
| `Number.__dataclass_params__.frozen` is **False** | `[live]` |
| `Kind.__eq__` / `__hash__` are **name-only** — same name, different dimension/parent/policy compare equal | `[live]` |
| `KindLattice` is a **forest**: no ⊤, no meets, disjoint components | `[live]` |
| `lca` raises `ValueError` on disjoint roots — a crash, not a verdict | `[live]` |
| `CrossDimensionParent` enforces the fibration (parent must share dimension) | `[live]` |
| `base_form is None` for `celsius`, `decibel`, `pH` — but the marker is impure: `dyne` shares it for basis-scoping reasons (see appendix), so `None` does NOT extensionally mark non-ratio charts; chart class is a declared `Unit.chart` field per the Turnstile ADR §4 | `[live]` |
| `AspectFacet`, `Aspect`, `AspectPosition` are **absent**; flat `AspectSet` shipped instead | `[live]` |
| `join_aspects` default policy is `INTERSECT`; returns a frozenset, **no exception path** | `[live]` |

---

## 3. Shipped catalog shape

`load_kinds_file('comprehensive.ucon.toml')` `[live]`:

```
26 kinds, 9 fibers, max tree depth 1, one root per fiber
mixed-policy fibers: NONE
```

Depth 1 means the LCA of any two kinds in a fiber is always the root, so there is
only ever one policy to consult. **Non-associativity requires depth ≥ 2 and is
therefore unreachable in the shipped catalog.**

---

## 4. Associativity — the inversion result

### 4.1 The pathology `[fixture]`

```
R(policy=lca) ▸ Q(policy=refuse) ▸ {a, b};   c under R

a ⊔ b        = JoinRefused
b ⊔ c        = R
(a ⊔ b) ⊔ c  = REFUSED
a ⊔ (b ⊔ c)  = R              ← same operands, different bracketing
```

LCA in a tree **is** associative — values agreed (`R` under both groupings). What
differs is **policy consultation**, because the intermediate LCA differs between
groupings. **A refusing node is escapable by routing around it.**

### 4.2 Mixed policies are NOT the problem `[fixture]`

Realistic depth-3 ICRP lattice with mixed policies:

```
specific_energy(refuse) ▸ dose(refuse) ▸ absorbed_dose(lca) ▸ {photon, neutron}
                                       ▸ equivalent_dose(refuse)

photon ⊔ neutron    = absorbed_dose
photon ⊔ equivalent = REFUSE
associativity violations: NONE
```

Physically correct *and* associative. The pathology is specifically **inversion**
— permissive above refusing.

### 4.3 The constraint `[fixture]`

300 random lattices, depth-varied:

| Constraint | Lattices with ≥1 violation |
|-----------|---------------------------|
| unconstrained | **111 / 300** |
| REFUSE set upward-closed | **0 / 300** |

> **Constraint: a node may be `refuse` only if its parent is `refuse`.**
> Equivalently: permissiveness, once granted, is inherited downward. A refusal
> cannot be overridden by a more general context.

Not an arbitrary restriction — it rules out a semantically inverted configuration
where *distant relatives combine freely while close relatives refuse*.

---

## 5. Merge laundering — demonstrated

Two packages, **each self-consistent** `[fixture]`:

*Package A (radiation safety):* `specific_energy(refuse)` ▸ `{absorbed_dose, equivalent_dose}`
*Package B (thermodynamics):* permissive `energy_per_mass` umbrella; re-parents A's root under it

Merged:

```
energy_per_mass (lca)
├── specific_enthalpy
└── specific_energy (refuse)
    ├── absorbed_dose
    └── equivalent_dose
```

```
absorbed ⊔ equivalent           = REFUSE            (still correct)
(absorbed ⊔ enthalpy) ⊔ equiv   = energy_per_mass   ← LAUNDERED

1 Gy + 1 Sv          → REFUSE
1 Gy + 1 J/kg + 1 Sv → ADMITTED
```

**Adding an unrelated third term makes the forbidden pair legal.** Neither package
contains a bug; the inversion exists only in the composite.

**Consequence: upward-closure must be validated at MERGE time, not only at load.**

---

## 6. ⊤_d — VETTED

Synthetic per-fiber top; roots parent to it; `join_policy = refuse`.

### 6.1 Base fixture `[fixture]`

Two disjoint trees over `specific_energy` (radiation dose; thermodynamics):

| Requirement | Result |
|------------|--------|
| R1 no crashes with ⊤_d | **PASS** — 15 crashes → 15 refusals |
| R2 no REFUSE became ADMIT | **PASS** |
| R3 admitted results unchanged | **PASS** |

### 6.2 Adversarial `[fixture]`

**T1 — ⊤_d policy must be non-overridable `refuse`:**

```
⊤_d policy=refuse | Gy⊔Sv = REFUSE | (Gy⊔J/kg)⊔Sv = REFUSE
⊤_d policy=lca    | Gy⊔Sv = REFUSE | (Gy⊔J/kg)⊔Sv = TOP     ← laundered
```

> A permissive ⊤_d is **strictly worse than no ⊤_d** — it converts crashes into
> silent admissions. Non-overridability is load-bearing, not a precaution.

**T2 — no-op on single-root fibers:** identical outcomes. Zero behavior change on
every fiber in the shipped catalog.

**T3 — orthogonal to associativity:** 0 violations before, 0 after.

**T4 — 300 random multi-root fibers:** crashes **2251 → 0**; REFUSE→ADMIT
regressions **0**.

### 6.3 Gap closure

**Gap 1 — fibration.** A single global ⊤ spanning dimensions is **already
rejected** `[live]`:

```
CrossDimensionParent: Kind 'torque' (dimension=Dimension(energy)) declares
parent 'TOP_GLOBAL' with different dimension (Dimension(specific_energy))
```

The wrong design is structurally impossible; ⊤_d **must** be per-fiber, enforced
without new code. Cross-fiber `lca` still raises `ValueError` but is unreachable
through arithmetic — `[live]` `Gy + J` → `TypeError` from the dimension gate.
Remains reachable via direct `lca` calls (public-API wart).

**Gap 2 — n-ary `[fixture]`.** With ⊤_d + upward-closure, over random multi-root
fibers, all permutations per trial:

```
n=4: orderings disagreeing on ADMIT/REFUSE: 0/200   crashes: 0
n=5: orderings disagreeing on ADMIT/REFUSE: 0/200   crashes: 0
```

> **Grouping invariance holds beyond triples.** This suggests upward-closure +
> ⊤_d may be *sufficient* for n-ary invariance without a separate order/policy
> split refactor. That refactor should be re-justified before scheduling.

**Gap 3 — real load path `[live]`.** `comprehensive.ucon.toml` via
`load_kinds_file`: 26 kinds, 9 fibers, 30 within-fiber pairs.

```
multi-root fibers: none
crashes before 0 → after 0
REFUSE→ADMIT regressions: 0   changed ADMIT results: 0
```

**⊤_d is invisible today and load-bearing the moment a second package adds a root
to an existing fiber** — the packages.ucon.dev case.

---

## 7. ⊤_facet — VETTED

Facet trees instantiated as **real `KindLattice` objects** (isomorphism
hypothesis). The new element under test is sparse multi-facet resolution.

**T1 — ⊤_facet works; isomorphism confirmed `[fixture]`:**

```
without ⊤_facet: icrp60 ⊔ iso4037 → CRASH: ValueError
with    ⊤_facet: icrp60 ⊔ iso4037 → REFUSE
```

**T2 — multi-facet composition `[fixture]`:**

```
{ws:icrp60,  proc:measured} ⊔ {ws:icrp103, proc:simulated}
  → REFUSE: facet 'weighting_standard': icrp60 vs icrp103

{ws:icrp103, proc:measured} ⊔ {ws:icrp103, proc:simulated}
  → ADMIT {ws:icrp103, proc:estimated}
```

The second is the case flat `AspectSet` cannot produce — one facet degrades to its
LCA, the other carries unchanged.

**T3 — sparseness laundering `[fixture]`:**

| partial policy | `A⊔B` | `(A⊔{})⊔B` | |
|---------------|-------|-----------|---|
| `inherit` | REFUSE | REFUSE | ok |
| `drop` | REFUSE | **ADMIT** | **LAUNDERED** |
| `refuse` | REFUSE | REFUSE | ok |

> **`drop` must be prohibited as a partial policy.** It is not a lenient choice —
> it is a soundness hole reachable with a completely innocent unqualified operand.
> **[live]** `join_aspects` defaults to `INTERSECT`, which *is* `drop`: the shipped
> flat model is laundering-vulnerable by default.

**T4 — n-ary invariance across facets:** 24 orderings of 4 operands with mixed
facet coverage → 1 distinct outcome. **INVARIANT.**

**T5 — no facets declared → no-op.** Pay-for-use confirmed.

---

## 8. Namespacing (D3) — PARTIALLY VETTED

Six requirements a scheme must satisfy. Scheme tested: qualified names
`pkg:node`, no type change.

| | Requirement | Result |
|---|------------|--------|
| R1 | two packages may both declare `procedure` | **PASS** `[fixture]` |
| R2 | unqualified reference resolves to own package | **FAIL** — `KindNotFound`; callers must fully qualify |
| R3 | name-only `__eq__` must not conflate | **PASS** — distinct, hashes differ |
| R4 | aliases must not collide across packages | **FAIL** — `AliasCollision: 'proc' collides with 'radsafe:x'` |
| R5 | cross-package graft works | **PASS** |
| R6 | upward-closure still checkable after merge | **PASS** — `lca` under `refuse` permitted |

**Baseline `[live]`:** flat index gives `NameCollision: Duplicate kind name:
'procedure'`; and `Kind('procedure', refuse) == Kind('procedure', lca)` → `True`,
so distinct nodes are indistinguishable as dict keys.

**R4 is the substantive defect** — aliases share the flat index, so qualification
of primary names alone is insufficient. Any scheme must qualify aliases too.

**R2 is a design choice, not a bug.** Full qualification works; the ergonomic
alternative (per-package default namespace) is **unvetted**.

### 8.1 Namespacing does NOT subsume upward-closure `[fixture]`

With every node fully qualified:

```
a ⊔ b       = REFUSE
(a ⊔ c) ⊔ b = umbrella:top     ← still laundered
```

> **Orthogonal mechanisms.** Qualification solves *identity*; upward-closure solves
> *soundness*. Both required.

---

## 9. UNVETTED — do not treat as results

| Claim | Status |
|-------|--------|
| Upward-closure transfers to aspect trees | inferred from structural identity; **not tested** |
| Per-package default namespace (R2 ergonomic variant) | **not tested** |
| Order/policy split is necessary | §6.3 Gap 2 suggests it may be **unnecessary**; needs re-justification |
| Chart class taxonomy (ratio/interval/log/cyclic) is closed | asserted from `[v4 §7]`; not tested |
| Cyclic `point − point` arc convention | open; deferred by decision |
| `CoercionPlan` field list | proposal only |
| Any calendar duration for this work | **no basis** — sequence and parallelism only |

---

## 10. Design conclusions warranted by §1–§8

1. **⊤_d per fiber, `join_policy = refuse`, non-overridable.** T1 shows the
   alternative is actively harmful.
2. **⊤_facet is ⊤_d instantiated per facet** — same engine, confirmed by T1/§7.
3. **Upward-closure validated at load AND merge.** §5 shows merge creates
   violations neither input has.
4. **`drop`/`INTERSECT` prohibited as a partial policy.** §7 T3.
5. **Freeze `Number`.** §2 — a derived, non-settable chart field is incoherent on
   a mutable dataclass.
6. **Point/displacement derived, not declared.** §1.3 is a live wrong answer;
   derivation forces the ISO 80000 idiom (differences in kelvin) without
   annotation.
7. **`Aspect` gains `join_policy`; aspects are tree nodes grouped by family
   root; `Number` carries a flat `frozenset[Aspect]`.** `Kind` and `Aspect`
   are visible peers sharing one order+policy engine. *(Wording updated
   2026-09-09: `AspectPosition` and the `Mapping[Facet, Aspect]` field shape
   were superseded by the facet elimination — see Addendum 2026-09-08 — and
   by the flat-field decision in the Aspect ADR §1/§11.)*
8. **Qualify names AND aliases.** §8 R4.

---

## Appendix — incidental bugs found

| Bug | Method |
|-----|--------|
| `load_package` fails on ucon's own bundled `comprehensive.ucon.toml`: `PackageLoadError: Unsupported expression in factor: 'gₙ'` — blocks all constant-bearing packages | `[live]` |
| `parse_unit("meter^3")` returns a `UnitProduct` that does not compare equal to `Unit("liter")`; a package binding a unit to a composite SI expression creates a disconnected graph node | `[live]` |
| `_add` falls through to `AliasCollision(name, name)` when the identical object is re-added — message reads "Alias 'x' collides with existing entry 'x'" | source read |
| `NameCollision` fires across dimensions — `dose` in a specific-energy fiber and `dose` in an energy fiber cannot coexist despite being unambiguous | `[live]` |
| `dyne.base_form is None` — dyne is coherent CGS force, neither affine nor logarithmic; should have a `BaseForm` | `[live]` |
| Constant prefactors corrupted in **families** (shared relative error): pound/short_ton/long_ton 1.19e−6; foot/mile 3.2e−8; volume family 2.0e−7 — indicates ~3 corrupted seeds, not 15 bad literals | `[live]` |

---

## Addendum — 2026-09-08: facet eliminated as a type

§7 was executed under a framing in which a "facet" was a separate index type
and ⊤_facet a synthetic node placed above each facet's trees. That framing was
withdrawn on 2026-09-08: **a facet is the root of an aspect tree**, and the
root is ⊤ for its family by construction.

No result in §7 changes. Every test was on join semantics — grouping by
family, componentwise LCA, partial policy, carry — and grouping-by-root is the
same algorithm as keying-by-facet. Specifically:

| §7 result | status under the new framing |
|---|---|
| T1 — ⊤_facet converts crash → verdict | holds; the "synthetic top" is now simply the declared root, so the crash case cannot arise |
| T2 — multi-facet composition | holds; "facet" reads as "family" |
| T3 — `drop` launders | holds unchanged |
| T4 — n-ary invariance across facets | holds unchanged |
| T5 — no-op when none declared | holds unchanged |

§8's namespacing results are unaffected; aspects were already being qualified
as tree nodes.

The evidence above is left in its original wording so that the fixtures remain
reproducible as written. Read "facet" as "aspect family" and "⊤_facet" as "the
family's root."


---

## Addendum — 2026-09-09: ⊤_d as an operand

§6 tested ⊤_d only as a *meeting point* — two specific kinds whose LCA is ⊤_d.
It was never an operand. Closed by the following `[fixture]`, exhaustive over
all 344 internal-upward-closed 5-node lattices, multisets to size 4, all
orderings:

| ancestor⊔descendant rule | invariant |
|---|---|
| LCA + policy always (shipped) | **344 / 344** |
| return the descendant (inherit specific) | 284 / 344 |
| return the ancestor, skip policy | 36 / 344 |

Consequences: the join rule is unchanged; ⊤_d as an operand refuses against
every specific kind in its fiber, by design; `None` (unspecified, partial
policy) and ⊤_d (provably unrelated, `refuse`) are distinct and must not be
merged. Kind-independent aspects attach to `None`.

Two rules were proposed and withdrawn on the strength of this fixture. Both
sounded reasonable. Neither was.

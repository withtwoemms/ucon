# ADR — The Turnstile

**Status:** Accepted — design closed 2026-09-05; aspect terminology aligned 2026-09-08; kind-slot semantics fixed 2026-09-09; chart source fixed to declared `Unit.chart` and ⊤_d constructibility stated 2026-09-09
**Target release:** 3.1.0 (minor; new refusals on previously-wrong paths are fixes)
**Prerequisites:** 2.2.0 infrastructure (#279, #280, #282); 3.0.0 pseudo-dimension retirement, `Number` frozen, #280-full identity
**Supersedes:** `PROPOSAL_turnstile-completeness-v2.md`; the "compile once per signature" framing
**Evidence:** `../evidence/turnstile-prerequisites.md` §1–§6; `../evidence/aspect-turnstile-case-studies.md` cases 2, 3, 4, 6

---

## 1. Decision

Every arithmetic operation passes through four checks in dependency order,
each either refusing or contributing to the coercion, then executes. There is
no cache and no compile step. Warrants are lazy.

```
                          a ⊕ b
                            │
              ┌─────────────┼─────────────┐
              │ 1 dimension  φ(a) ? φ(b)   │  category 1
              │ 2 chart      admissible?   │  categories 2, 3
              │ 3 kind       join, ⊤_d     │  categories 4, 5, 6
              │ 4 aspect     componentwise │  categories 7, 8
              └─────────────┼─────────────┘
                            │  first refusal → Refused(warrant)
                            ▼
                factor lookup · fma + offset · construct Number
```

## 2. The defect

`[live]` `Number.__add__` gates on `self.unit.dimension != other.unit.dimension`,
resolves kind, then constructs `Number(self.quantity + other.quantity,
unit=self.unit)`. **It consults φ (dimension) and never ψ (scale).** Kind
resolution runs correctly and is stapled onto a raw magnitude addition.

```
1 Gy  + 1 Sv     →  <2 Gy>
1 rad + 180 deg  →  <181 rad>
5 °C  → °F       →  41.0        (a 5 °C difference is 9 °F; inexpressible)
2 × 20 °C        →  <40 °C>     (313.15 °C via kelvin — chart-dependent)
```

## 3. The four strata

| Stratum | Owned by | Refuses on | Contributes |
|---|---|---|---|
| dimension | `Unit` → `Vector` | incompatible φ | `result_unit` |
| chart | `Unit.chart` + kind flags | operation ill-formed on this chart | factors, offset, `result_displacement` |
| kind | `Kind` lattice | different trees; LCA `refuse`; partial+strict | `result_kind` |
| aspect | `Aspect` (see ADR) | family conflict; partial+strict | `result_aspects` |

**Chart is the only stratum that refuses on identical operands.** Every other
check is difference-based; `20 °C + 5 °C` has identical dimension, kind,
aspect, and unit, and is ill-formed anyway.

### Regression finding

**[v4 §8.4]** had a scale-type check as dispatch step 2. **[v6 §7.4]**
deleted it, along with §7's Map-type→scale-type table and the v1.9.2
"scale-type inference" deliverable. The v6 six-category taxonomy is internally
consistent with v6's own dispatch; both omit the same thing. Restoring it
yields categories 2–3 and the eight-category taxonomy below.

## 4. Chart

**Three classes, on the unit:** ratio, interval, logarithmic. **Declared as
`Unit.chart` and read from there** — never inferred from `base_form`, and
never from an edge to a sibling unit. The derivation from Map type (Linear →
ratio, Affine → interval, Log → logarithmic, read off the edge to the
fiber's canonical ratio unit) survives only as a load- and merge-time
validator; units with no such edge default to ratio and are re-validated
when an edge arrives.

Two `[live]` misclassifications force the declared field over inference, and
both become validator fixtures: `dyne` has no direct edge to read, and its
`base_form is None` for basis-scoping reasons, not chart structure (#283) —
inference would refuse `2 × 20 dyn` like `2 × 20 °C`; `decibel`'s direct
edge is a `LinearMap` to `bel` — sibling edges are automorphisms *within* a
chart, so edge-reading misreads log units as ratio.

**Two kind flags refine the effective chart:**

| flag | admits | refuses | executed as |
|---|---|---|---|
| `modulus = "1 revolution"` | `+` displacement, `==` mod | `<`, `+` point, `×` point | quotient of the ratio chart |
| `ordinal = true` | `<`, `==`, `max`, `sorted` | `+`, `−`, `×` | order only |

The unit fixes the chart; the kind may impose a quotient or discard everything
but order. Cyclic and ordinal are not chart classes because they are
properties of the *measurand*, not the numeral scheme — `degree` is a clean
ratio unit; what's cyclic is the bearing.

`[vetted]` — full operation tables for both flags, including the seam
(`359° − 1° = −2°`), antipodal convention (`+½M`), and Mohs (`10 − 9` spans
1100 absolute units, `2 − 1` spans 2).

**Point / displacement** — derived on `Number`, never declared:

1. A literal on an affine chart is a point.
2. `point − point → displacement` — the only producer.
3. `point ± displacement → point`; `displacement ± displacement → displacement`.

`[vetted]` mechanism: `_displacement` is `init=False` on a frozen dataclass,
written by exactly one seam in `__sub__` via `object.__setattr__`.
`Number(1, C, _displacement=True)` → `TypeError`; `dataclasses.replace` rejects
it; `setattr` → `FrozenInstanceError`. Literal 15 °C ≠ displacement 15 °C.

"A 5 °C rise" is `Number(5, celsius).as_displacement()` — origin subtraction,
which is a no-op on ratio, drops the offset on interval, drops the reference
on logarithmic. **No `delta_*` units.**

Refusals from the affine algebra are not policy; they are the absence of an
operation: `point + point` and `scalar × point` do not exist in an affine
space. `2 × 20 °C` is 40 °C in celsius and 313.15 °C via kelvin — a result
that depends on an arbitrary convention computes nothing about the quantity.

Circular aggregation refuses when `|resultant| / n < ε` (category 3); naive
`sum` over cyclic points refuses at the first `point + point`.

## 5. Kind

**⊤_d per fiber, non-overridable `refuse`.** Roots parent to it implicitly;
`lca` becomes total within a fiber; disjoint roots yield a verdict.

`[vetted]`: 300 random multi-root fibers — 2251 crashes → 0, zero
REFUSE→ADMIT regressions; no-op on every fiber in the shipped catalog (26
kinds, 9 fibers, depth 1, single-root); a global ⊤ spanning dimensions is
**already rejected** by `CrossDimensionParent`.

**Non-overridability is load-bearing.** A ⊤_d with `join_policy = lca`
reproduces merge laundering exactly (§7). A settable policy is strictly worse
than no ⊤_d — it converts crashes into silent admissions.

**Multiplication degrades to ⊤_d, not `None`.** Under `None`, permissive mode
lets `dose_rate × time` (unkinded) inherit a neighbor's `equivalent_dose` on
the next addition. Under ⊤_d the addition refuses.

**⊤_d is constructible on demand for any dimension**, including fibers where
no package has declared a kind: kind-degrading multiplication lands on the ⊤
of the *product* dimension (`⊤_specific_energy·time`), whether or not that
fiber is populated. "Roots parent to it implicitly" therefore covers the
zero-root case — the top exists per dimension by construction, not per
declared forest.

**`None` and ⊤_d are distinct, and the join rule has no ancestor exception.**

| slot | meaning | governed by | produced by |
|---|---|---|---|
| `None` | *unspecified* — nobody said | partial policy (strict/permissive) | user omitted `kind` |
| ⊤_d | *provably not any declared kind* | `refuse`, non-overridable | `×` with no formula; two unrelated kinds meeting |

⊤_d as an **operand** refuses against every specific kind in its fiber, by
design: `⊤_length + height` → REFUSE. That is correct — the ⊤ was earned by an
operation with no kind, and it must not acquire a neighbor's label.

Kind-independent aspects (`applies_to = ["*"]`) therefore attach to `None`,
never to ⊤_d. Hosting them on ⊤_d would make a coverage annotation render a
plain length un-addable.

`[vetted, exhaustive]` — alternatives to plain LCA + policy for the
ancestor⊔descendant case, over all 344 internal-upward-closed 5-node lattices:

```
P0  LCA + policy always (current)          344/344 invariant   HOLDS
P1  ancestor⊔descendant → descendant       284/344             BREAKS
P2  ancestor⊔descendant → ancestor, skip   36/344              BREAKS
```

P1 fails because an accumulated LCA replaced by a more specific operand forgets
what it summarized. P2 fails by routing around a sibling refusal through the
parent. **The join rule does not change.**

## 6. Grouping invariance — theorem

> Given ⊤_d, the pairwise left fold is grouping-invariant for every operand
> multiset **iff** every internal `refuse` node has a `refuse` parent.

`[vetted, exhaustive]` — all 384 (labeled 5-node tree × policy assignment)
pairs, all multisets to size 4, all orderings:

```
upward-closed lattices:      228   invariant: 228   → sufficient
violating lattices:          156   non-invariant: 40  → 116 harmless (leaf policy never consulted)
internal-upclosed:           344   invariant: 344   → exact characterization
```

Proof: LCA in a tree is associative — values agree under every grouping. What
differs is *policy consultation*, because the intermediate LCA differs. Under
internal-upward-closure every intermediate is in the permissive set whenever
the total LCA is, so every step admits; when the total LCA refuses, the last
step necessarily hits it. Necessity: `R(lca) ▸ Q(refuse) ▸ {a, b}`, `c` under
`R` — `(a⊔b)⊔c` refuses, `a⊔(b⊔c)` admits.

**Consequences:**
- The order/policy split previously proposed is **removed** — it contributes
  nothing to the verdict.
- The validator uses the exact rule (internal nodes only), safe because merge
  revalidation is mandatory (§7).
- ⊤_d and upward-closure serve different criteria: totality and invariance
  respectively. Neither delivers the other.

## 7. Merge validation

`[vetted]` — two self-consistent packages compose into an inverted forest:

```
energy_per_mass (lca)                      ← package B's umbrella
└── specific_energy (refuse)               ← package A's root, grafted under it
    ├── absorbed_dose
    └── dose_equivalent

1 Gy + 1 Sv           → REFUSE
1 Gy + 1 J/kg + 1 Sv  → ADMITTED            ← laundered
```

Neither package contains a bug. **Upward-closure is validated at merge**, on
the composed forest, and a violating install is refused with the inverted
edge named. `[vetted]` that namespacing does not prevent this — fully
qualified names still launder — so qualification and upward-closure are
orthogonal and both required.

## 8. Runtime

**No signature cache.** `[live]` measured: today's `__add__` 0.80 µs; building
the cache key 0.26 µs; running the four checks 0.29 µs. The key costs what the
checks cost, and the cases where checks get expensive (deep lattices, many
aspect families) are the cases where the key gets expensive too. Removed.

**Hot path:** four inline checks → factor lookup (already cached at the graph
level `[live]`) → fma → construct. Target ≈ 1 µs.

**Warrants are lazy.** A refusal carries one in `Refused`. An admission builds
one only via `explain(expr)`, which re-runs the checks with a recorder. A
session context manager routes warrants to a sink for regulated users.

**No runtime coordination with packages.** Merge validation and graph extension
happen at install. Nothing at runtime depends on a lattice digest.

## 9. Taxonomy

Generating principle: four strata × operand state {equal, reconcilable,
irreconcilable, partial}. Refusals = irreconcilable ∪ (partial under strict).
Dimension has no partial state.

| # | Stratum | Category | Reachable today |
|---|---|---|---|
| 1 | dimension | incompatible | ✔ |
| 2 | chart | no conversion path / mixed charts | ✘ — v6 regression |
| 3 | chart | operation ill-formed (point+point, scalar×point, ordinal `−`, cyclic `<`, degenerate mean) | ✘ |
| 4 | kind | different trees, same dimension | ✘ — `ValueError` before `join` |
| 5 | kind | LCA `refuse` | ✔ |
| 6 | kind | partial + strict | ✔ |
| 7 | aspect | aspect family conflict | ✘ — no carriage |
| 8 | aspect | partial + strict | ✘ |

Three of eight are reachable in 2.1.1.

## 10. Completeness — as tests, not prose

| | Criterion | Test |
|---|---|---|
| C1 | totality — every pair yields ADMIT or REFUSE | exhaustive over fixture; no bare exception |
| C2 | layer coverage — every stratum contributes its categories | category closure: every (stratum, state) maps to a named category; every category reachable |
| C3 | grouping invariance | random expression trees; verdict invariant under re-association and commutation |
| C4 | soundness — ADMIT ⟹ executing the coercion is correct | differential vs exact rational arithmetic |
| C5 | operation coverage | `+ − × ÷` specified; `**` and general `<` remain open |

C1–C4 fail against 2.1.1 for the reasons in §2, §5, §6. C5 is partial: `**`
bypasses kind and aspect entirely and has no dispatch row; comparison is
`TypeError` today and only the cyclic and ordinal edges are specified.

## 11. Withdrawn during design

| Withdrawn | Reason |
|---|---|
| signature-keyed plan cache | measured: key costs what the checks cost |
| order/policy split | proven redundant by the invariance theorem |
| per-fiber digest invalidation | solved a problem the cache created |
| cyclic as a chart class | property of the measurand; kind `modulus` |
| wrapped/unwrapped displacement bit | dissolved into `bearing` vs `rotation` kinds |
| `delta_*` units | `.as_displacement()` = origin subtraction |
| `None` as multiplication fallback | permissive-mode laundering; ⊤_d instead |
| ordinal → ratio bridge | deferred by ruling — a smooth fit implies Mohs 7.5 means something |
| ancestor⊔descendant as the partial case | proposed 2026-09-08, withdrawn 2026-09-09 — breaks grouping invariance `[vetted]` |

## 12. Open, deliberately

- `**` dispatch — no row; exponentiation currently bypasses strata 3–4
- General comparison table beyond cyclic/ordinal
- Uncertainty under `×` — `[live]` propagates, but the rule producing 1.044
  for (5±0.1)·(3±0.2) needs identification before it's called right or wrong
- `Kind.__eq__` name-only — qualification makes collisions unlikely, not
  detectable
- Cross-fiber `lca` via direct call still raises — public-API wart, unreachable
  through arithmetic

None of these block 3.1.0. All belong in C5's backlog.

## 13. What the Turnstile is not

It is not a caching subsystem, a compiler, or a plan optimizer. It is four
inline checks and a lazy explainer. It got smaller as it was tested, each time
because a piece of infrastructure was measured and found unnecessary — not
because scope was cut.

# ADR — Aspect Stratum

**Status:** Accepted — design closed 2026-09-09 (`QualifiedKind` bundle proposed and withdrawn the same day; see §11)
**Target release:** 2.3.0 (minor, additive)
**Supersedes:** `AspectSet` flat model (2.1.1); `AspectPosition` and `AspectFacet` (v4/v6 §5); v1 (2026-09-07) and v2 (2026-09-08) of this ADR
**Evidence:** `../evidence/turnstile-prerequisites.md` §7–§8; `../evidence/aspect-turnstile-case-studies.md` cases 1, 5

---

## 1. Decision

A `Number` has a **kind**; it may also carry **aspects**. Aspects are adjectives: they say something further about a quantity that matters for combination, without changing what the quantity is. They qualify the *quantity* — the noun is the `Number`, which is why the field lives beside `kind`, not inside it.

```python
@dataclass
class Number:
    quantity: ...
    unit: Unit
    uncertainty: ... = None
    kind: Kind | None = None                      # unchanged
    aspects: frozenset[Aspect] = frozenset()      # new; additive
```

```python
n.kind        # dose_equivalent
n.aspects     # {icrp103, measured}
```

The constructor surface is `Number(q, unit, kind="...", aspects=[...])`. Every existing `n.kind` idiom (`is None`, `.name`, `==`) survives unchanged — the addition is genuinely additive, as this ADR's target release requires.

There is one aspect type. **`Aspect` is the peer of `Kind`** — same fields, same engine, same kind of tree. A facet is the root of an aspect tree, exactly as `dose` is a kind and not a `KindFacet`.

**The kind may be `None`.** Aspects whose root declares `applies_to = ["*"]` — coverage factor, calibration status — qualify a quantity regardless of its sort, and attach to an unkinded number. `None` means *unspecified* and is governed by the partial policy. It is **not** ⊤_d, which means *provably not any declared kind* and is governed by `refuse`. The two are distinct and must stay so (see Turnstile ADR §5).

## 2. Justification

Two dose equivalents, both `Sv`, both kind `dose_equivalent`, one weighted by ICRP-60 and one by ICRP-103. Identical at every stratum kind can see; the sum conforms to neither standard. `[live]` kind's `join` short-circuits on equality and cannot refuse identical kinds.

The shipped flat model cannot fix this. `[live]`:

```
A = {icrp60,  measured}
B = {icrp103, measured}
C = {measured}                     ← standard merely absent

A ∩ B → {measured}
A ∩ C → {measured}                 ← IDENTICAL
```

An unstructured set cannot distinguish *conflict* from *absence*. A set of tree nodes can: two members sharing a root with different values is a conflict; a root represented in one operand only is a partial.

## 3. The types

```python
@dataclass(frozen=True)
class Aspect:
    name: str
    parent: Aspect | None
    join_policy: JoinPolicy = REFUSE
    # roots only:
    applies_to: frozenset[str] = frozenset()      # kind names, or {"*"}
    multiplication_policy: MultPolicy = CARRY
```

Roots carry the family's rules; `applies_to` and `multiplication_policy` on a non-root is a load-time error. **One order+policy engine serves kinds and aspects**, instantiated per tree. `[vetted]` — aspect trees executed on real `KindLattice` objects with every behavior transferring.

`join_policy` **defaults to `refuse`**, preserving v4 §5.4's strict matching as the zero-configuration behavior. LCA degradation is opt-in per node.

**The root is ⊤ for its family.** Every family has exactly one top by construction — no synthetic node. A `Number` carrying a root aspect is *some member of this family, unspecified*, distinct from carrying nothing.

The two fields are peers, not a coupling. Kind resolution walks the lattice without reading `aspects`; aspect resolution walks the trees without reading `kind` (Law 0, §7). Law 0 also settles the representation: the two discriminators never co-travel before `Number` construction — no resolver computes both, warrants record them per stratum, and the shared order+policy engine sees one tree at a time — so the only object that ever legitimately holds the pair is `Number` itself. `applies_to` is accordingly a construction invariant of `Number` (§5), the one site where kind and aspects meet.

```toml
[[aspects]]
name = "weighting_standard"
applies_to = ["dose_equivalent", "radiation_weighting_factor"]
multiplication_policy = "carry"
join_policy = "refuse"

[[aspects]]
name   = "icrp103"
parent = "weighting_standard"

[[aspects]]
name = "coverage"
applies_to = ["*"]                    # kind-independent
join_policy = "refuse"

[[aspects]]
name   = "k2"
parent = "coverage"
```

```python
Number(2.0, sievert, kind="radsafe:dose_equivalent", aspects=["radsafe:icrp103"])
Number(5.0, meter, aspects=["metrology:k2"])          # node None; aspect attached
```

## 4. Resolution

Group both operands' aspects by root; resolve each family independently:

```
for each family present in (left ∪ right):
    both present, equal        → carry
    both present, differ       → LCA within the tree; consult policy at LCA
    one present                → partial policy
```

**Partial policy is `inherit` or `refuse`. `drop` is prohibited.** `[vetted]`:

| partial policy | `A ⊔ B` | `(A ⊔ {}) ⊔ B` |
|---|---|---|
| `inherit` | REFUSE | REFUSE |
| `drop` | REFUSE | **ADMIT** — laundered |
| `refuse` | REFUSE | REFUSE |

Under `drop`, joining with an unqualified operand erases the qualification and a refused pair then admits. `[live]` `join_aspects` defaults to `INTERSECT`, which is `drop`: **the shipped model is laundering-vulnerable by default.**

Disjoint subtrees within one family meet at the root, whose policy is `refuse` by default. `[vetted]` under the earlier ⊤_facet framing — same behavior, now structural rather than synthesized.

## 5. `applies_to`

Governs **attachment only**. Checked at `Number(...)` construction and at `[[formulas]]` load. Never re-checked during resolution or carriage.

```python
Number(1.5, gray, kind="absorbed_dose", aspects=["icrp103"])
# Refused: aspect family 'weighting_standard' does not apply to kind 'absorbed_dose'
```

Absorbed dose is the *input* to weighting; a weighting standard on it asserts something false. This is the one place the aspect layer reads a kind — construction-time, not resolution-time — and Law 0 (§7) permits it.

## 6. Carry rule

> An aspect is carried onto the result of a multiplicative operation whenever its root declares `multiplication_policy = carry`, regardless of whether the result kind lies within the root's `applies_to` scope. Out-of-scope carriage is recorded in the warrant.

`[vetted]` — the round trip decided it:

```
A  drop     (dose × t) / t  →  2 [⊤]  {}              destroyed by identity op
B  refuse   dose × t        →  REFUSE                 dose-time products blocked
C  carry    (dose × t) / t  →  2 [⊤]  {icrp103}       preserved
```

And the property that justifies the stratum:

```
p1 = 2 Sv{icrp103} × 5 s   →  [⊤_se·t] {icrp103}
p2 = 1 Sv{icrp60}  × 5 s   →  [⊤_se·t] {icrp60}
p1 + p2                     →  REFUSE on weighting_standard
```

Both kinds have degraded to the same ⊤. **Kind can no longer distinguish them. The aspect still can.**

**Formulas do not produce aspects.** A weighting factor carries its own standard; carry does the rest:

```python
w_R = Number(20, one, kind="radsafe:radiation_weighting_factor",
             aspects=["radsafe:icrp103"])
absorbed × w_R  →  30 Sv [dose_equivalent] {icrp103}
```

One formula stays standard-agnostic; each ICRP package ships an annotated w_R table as *data*.

## 7. Law 0 — kind-orthogonality (enforced invariant)

Aspect resolution reads only the two operand aspect sets and the ambient strict bit. Kind resolution never reads aspects. The empty aspect argument passed to `ctx.formulas.apply()` is correct by construction.

Not a design input — every decision above was reached independently and survives it unchanged. It is a **test oracle**: mock every kind to garbage; assert every aspect verdict is unchanged. It is what makes "aspects ship independently of packages and Turnstile" a checkable property.

## 8. Namespacing (D3)

Full qualification: `pkg:name` for every package-declared name, **including aliases**; root builtins unprefixed; cross-package references explicit.

`[vetted]` against twelve requirements. Per-package default scope — the ergonomic alternative — needs a resolution rule that **silently shadows** a root builtin when a package reuses its name. Full qualification has no such mode.

Verbosity is recovered by an optional rewriter: `namespace = "radsafe"` in `[package]` prepends the prefix to every unprefixed name; `@name` escapes to root. `[vetted]` — pure `dict → dict`, output equals the hand-qualified file, idempotent, consults nothing loaded and therefore cannot shadow.

## 9. Scope

**In:** `Aspect`, `Number.aspects` (flat, additive; `Number.kind` unchanged), `[[aspects]]` TOML, family resolution, partial policy, carry rule, `applies_to` at attachment, D3 qualification, `namespace` rewriter, `AspectSet` deprecated (removed 3.0.0).

**Out:** builtin aspects — none. Kinds are discovered from physics; aspects are declared by domains. Core ships mechanism only. Category-closure tests load a fixture package.

**Out:** unit→aspect conventions.

## 10. What this stratum provides

Cross-classification without combinatorial explosion — several independent families instead of a kind per combination. Distinctions that survive multiplication (`carry`). Refusals that survive kind degradation. And a mechanism neutral as to *what* it carries: procedure, standard, sample basis, or anything else a domain needs to gate combination on.

## 11. Withdrawn during design

| Withdrawn | Replaced by | Reason |
|---|---|---|
| `AspectSet` | aspect trees | cannot distinguish conflict from absence |
| `AspectPosition` | `Number.aspects` collection | composite needed no name |
| `Qualifier` | `Aspect` | users declare aspects; the node is the aspect |
| **`Facet` / `AspectFacet` as a type** | **the root aspect** | aspect and facet are synonyms; the root of a tree is a member of it, as `dose` is a kind |
| **`⊤_facet` as a synthetic node** | **the root** | one top per family by construction |
| **`@top` syntax** | **naming the root** | a root aspect *is* "unspecified within this family" |
| `produces` on formulas | aspect on the factor + `carry` | keeps the registry standard-agnostic |
| per-package default scope | full qualification + rewriter | silent shadowing |
| `drop` partial policy | `inherit` / `refuse` | laundering |
| "procedurally constituted" as the definition | adjective that gates combination | the mechanism is neutral; procedure is one use |
| provenance / UDI as an aspect family | carriage metadata | unbounded vocabulary; vacuous LCA |
| **`QualifiedKind` (bundle on `Number.kind`; then proposed as an internal type)** | **flat `kind` + `aspects` fields on `Number`** | Law 0 means the pair never co-travels before `Number` construction — no resolver, warrant, or engine ever holds both — so a bundle has no site, public or internal. The "adjective with no noun" rationale failed its own design: kind-independent aspects attach to `kind=None`, so the noun was the `Number` all along. Flat fields also keep the read surface additive (`n.kind` idioms survive), as the 2.3.0 target requires |
| **"every number has at least ⊤_d"** | **`None` stays distinct from ⊤_d** | ⊤_d refuses against specifics by design; hosting kind-independent aspects there produced false refusals `[vetted]` |

Rows in bold: the 2026-09-08 facet elimination and the 2026-09-09 bundle — proposed and withdrawn the same day. The rest stand from v1.

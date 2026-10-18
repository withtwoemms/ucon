# PROPOSAL: Declaring `Unit.chart` — withdrawn in favour of deriving it

**Status:** Withdrawn as an implementation plan; retained as the record of why, and of the three bugs it exposed
**Date:** 2026-10-17; revised 2026-10-18 (twice) after working the open questions one at a time
**Implements:** [`../decisions/010-chart-nomenclature.md`](../decisions/010-chart-nomenclature.md) (Accepted) and [`../decisions/009-turnstile.md`](../decisions/009-turnstile.md) §4
**Lands:** nothing, as scoped — see §6. The field, the TOML key, the cache bump and the validator are all withdrawn; what replaces them is #339, #340, #341 and one open decision on ADR 010. The chart *dispatch* remains 3.1.0.
**Disposition:** this document is now a record of why the chart stratum does not need a declared field, plus the three bugs working it exposed. Superseded by whatever decides the ADR 010 question in §6.

All evidence below verified against `main` at `dcf7f8d`, re-run after each revision.

**Revision note.** Every recommendation this document has made on questions 1–3
has been wrong at least once, and §§2–4 record why — the reasoning is the useful
part, and the retractions are kept rather than erased so the same ground is not
re-walked. Questions 1 and 2 are answered by *deletion*: no fourth chart class
(§2), no `logarithmic` parameters (§3). Question 3 is answered by deletion too,
one level up: **the catalog already declares the chart class**, distributed
across its edge-key vocabulary, and the full 222 / 3 / 9 classification derives
from 207 declared edge rows plus one physical fact (§4.1). So there is no field
to declare and no validator to write. Question 4 reverses: re-keying the 2.2.2
refusal would introduce silent magnitude corruption, because `base_form` is
load-bearing for the arithmetic and not merely for the meaningfulness check
(§5). Three bugs came out of the work — #339, #340, #341 — and one decision is
owed on ADR 010 (§6).

---

## 1. What ADR 010 already decided

010 is **Accepted**. It settles, and this proposal takes as given:

- the field is **`Unit.chart`**; the stratum is the **chart stratum**; the values are **chart classes**;
- the three classes are **`ratio`** (pure scaling, true zero), **`interval`** (scaling, conventional zero), **`logarithmic`** (log of a ratio to a reference);
- chart is read **from the declared field only** — never inferred from `base_form` (which conflates unrelated `None` causes) and never from an edge to a sibling unit (log units relate *linearly* to their siblings);
- the Map-form derivation survives **solely as a load/`extend`/merge-time validator**;
- cyclic and ordinal structure live on `Kind` (`modulus`, `ordinal`), not here;
- the taxonomy is **deliberately open**: "a declared field admits a fourth class without migration."

So the open work was taken to be the four questions 009 and 010 left unanswered,
not the naming or the inference ban.

**One of those givens does not survive.** Working question 3 showed the catalog
already declares the chart class in its edge-key vocabulary (§4.1), which makes
the inference ban the live question rather than a settled premise — see §6's
"On ADR 010". Everything else in this list stands.

## 2. Question 1 — a fourth class? **Declined.**

The first draft proposed a `transformed` class for `nines`, arguing that `nines`
addition is ambiguous. **That argument is wrong**, and the algebra refutes it in
one line:

$$-\log_{10}(1-x) \;+\; -\log_{10}(1-y) \;=\; -\log_{10}\big[(1-x)(1-y)\big]$$

Verified: both sides give `6.000000` for `x = y = 0.999`. `(1-x)(1-y)` is the
product of the *unavailabilities* — both components must fail — which is the
**parallel-redundancy** law. So addition on the nines chart has exactly one
meaning: multiply the referenced quantity. That is what a logarithmic chart
*is*.

The "series" reading (`0.999 × 0.999 = 0.998001`, ≈ 2.699 nines) multiplies
*availabilities*, not unavailabilities. It is a different function of the two
inputs, not a rival reading of the same `+`. The decibel analogue settles it:
`10 dB + 10 dB = 20 dB` (cascade, 10× then 10× = 100×), while *summing two 10×
powers* gives 13.01 dB — a different operation. Nobody calls the decibel
ambiguous because power-summation also exists.

**So `nines` is `logarithmic`**: `−log₁₀(1 − x)` is a log of a ratio taken
against unity on the complement, with a negative scale. Its shipped map is
already `ComposedMap(log(scale=−1, base=10), affine(a=−1, b=1))`.

Also declined, and recorded so they are not re-proposed:

| candidate | why declined |
|---|---|
| `transformed` | collides with `BasisTransform` / `ConstantBoundBasisTransform` (ADR 010 criterion 3, zero collisions); and *every* chart class is a transformation of the canonical one, so the word does not distinguish what it names (criterion 1) |
| `opaque` | names the mechanism and does not collide, but there is nothing to be opaque about once the addition law is derived |
| a `Kind` flag beside `modulus`/`ordinal` | ADR 009 §4's test — numeral scheme vs measurand — looked like it applied, but a bearing genuinely has no total order and Mohs genuinely has no addition, whereas availability has both |
| `derived` | collides with *derived quantity* / *derived dimension* (ISO 80000) |

`PolynomialMap` (#332) is **not** an inhabitant either, contrary to the first
draft: a chart class is a property of a unit's own numeral scheme within its
fiber, and the PT100 polynomial relates `celsius` (temperature) to `ohm`
(resistance) — a cross-dimensional conversion edge, not a numeral scheme. (The
first draft said "relation to its own fiber's canonical ratio unit"; §4.2 shows
most fibers have no such unit, so the phrasing is corrected here even though the
conclusion is unaffected.)

The taxonomy stays at three. ADR 010 guarantees a fourth can be added later
without migration, so nothing is foreclosed.

**Reframed by #341.** The conclusion survives but the reasoning above is
incomplete. `nines` does not relate affinely to `bel`/`decibel`/`neper` —
`nines → decibel` is `10·log₁₀(1 − 10⁻ⁿ)`, which is not affine — so it is *not*
interchangeable with the other levels, and §4.3 records how that falsified the
validator this document proposed. The cause is not a missing chart class: it is
that `nines`' edge is the catalog's only `composed` edge, whose inner
`affine(a=-1, b=1)` is `x ↦ 1 − x`, a change of **quantity** (availability to
unavailability) hidden inside a map whose job is a change of **scale**. The
addition law derived above is still correct; the defect is that the charted
quantity and the edge's endpoint disagree. Fix the edge and `nines` rejoins the
family — which is why a fourth class is still the wrong answer.

## 3. Question 2 — what parameters does `logarithmic` carry? **None.**

The first draft proposed `logarithmic(reference=<quantity|None>, kind=field|power)`.
Both halves are already stored elsewhere, and a second home for either would be
duplication that can disagree.

**`reference` is already on the Map.** `LogMap`/`ExpMap` carry
`scale, base, reference, offset`, and the catalog uses it:
`decibel_milliwatt → watt` is `exp, scale=0.1, base=10, reference=0.001` — one
milliwatt, expressed in the target unit. ADR 010 is explicit that the Map is
ground truth and the declared field is authority for the *class*. Putting
`reference` on the chart too would restate it.

The point-vs-displacement distinction that makes `30 dBm − 20 dBm = 10 dB` work
is therefore **derivable**: `dBm` has a real referent, so it is a point; `dB`,
`bel` and `neper` have none, so they are displacements.

**`field | power` is already in `scale`**, by the log power rule. Since
`P/P₀ = (F/F₀)²`, `ln(aᵇ) = b·ln(a)` makes the exponent and the scale factor
interchangeable: `20·log₁₀(F/F₀)` and `10·log₁₀(P/P₀)` are the same number. The
catalog already encodes the distinction correctly — verified by driving each
measurand up 10×:

```
decibel_watt       scale=0.1   10x -> +10.00 dB   expected +10 (power)  OK
decibel_milliwatt  scale=0.1   10x -> +10.00 dB   expected +10 (power)  OK
decibel_volt       scale=0.05  10x -> +20.00 dB   expected +20 (field)  OK
decibel_spl        scale=0.05  10x -> +20.00 dB   expected +20 (field)  OK
```

So the bare `dB`/`B`/`Np` are not ambiguous, merely *un-referenced*: whichever
edge brought a ratio into them carried the convention in its scale. The unit
does not need to know.

**`logarithmic` is therefore just the classification**, exactly as ADR 010 said:
declared field for the class, Map for the parameters. The first draft invented a
parameter layer the design had already placed elsewhere.

**One live bug falls out.** The dimensionless trio *is* inconsistent: `bel →
fraction` implies `fraction` is a power ratio while
`test_logarithmic.py::test_ratio_to_neper` asserts it is a field ratio, so
`bel → fraction → neper` crosses conventions and `1 Np` converts to `4.343 dB`
instead of SI Brochure Table 8's `8.686`. Filed separately — it is a catalog
convention decision, not a chart-schema gap, and it interacts with #307 and ADR
013's dissolution of `Dimension(ratio)`.

### What the four logarithmic combinations must do

The first draft discussed only addition. The acceptance criteria for the class
are all of them, and today four of the five are wrong — including one the
earlier revisions omitted entirely, scalar multiplication, which is the case
that silently succeeds:

| operands | required | today |
|---|---|---|
| level − level | **gain** (dimensionless) — the only producer of a displacement | `<10.0 dBm>` — right number, wrong type |
| level ± gain | level | `TypeError` — the legitimate case, refused |
| gain ± gain | gain | correct |
| level + level | refuse | `<50.0 dBm>` — admitted |
| **scalar × level** | **refuse** | `Number(10, dBW) * 2` → `<20 dBW>` = 100 W, i.e. 10×, not 2× — admitted (#340) |

The scalar case is the exception to what follows: it fails at no stratum at all,
because `__mul__` by a scalar consults neither `base_form` nor any chart notion
(#340). The remaining level cases fail for one reason: `dBm` is
`Dimension(power)` and `dB` is `Dimension(ratio)`, so `__add__` gates on
dimension at **stratum 1** before any
chart logic could run. A correct log chart needs stratum 1 to admit *point +
declared-displacement-unit across dimensions* — which is 3.1.0 dispatch, not
this release. Noted so the limit is explicit rather than implied.

Subtraction is not a special case of addition here. `point − point` cannot be
rewritten as `point + (−point)` because negating a point is meaningless; it is
its own rule, and it is the SNR idiom. Within displacements subtraction *does*
collapse into addition, since a gain may legitimately be negative — though
`Number` has no `__neg__` today, so `-(3 dB)` raises.

## 4. Question 3 — what does the validator check, and when?

**Answered by deletion. There is nothing to declare, so there is nothing to validate.**

The first draft specified the validator as "derive the expected class from the edge
to the fiber's canonical ratio unit." The second revision replaced that with two
sweeps and claimed both verified. **Both were wrong**, and the second was wrong in
the worse way — it reported the residue of a silent filter as evidence. What
replaces them is not a third validator but the observation that the catalog
already declares everything the field was meant to carry.

### 4.1 The classification is derivable from what the TOML already says

Across all **207** declared edges the catalog uses exactly three vocabularies:

| edge shape | n | means |
|---|---|---|
| bare `factor` | 196 | pure scaling |
| `factor` + `offset` | 2 | conventional zero (both `celsius`-sourced) |
| `map` (log / exp / composed) | 9 | the numerals are a logarithm |

That vocabulary *is* the chart declaration. Two computations over it recover the
classification:

- **coordinate** — a unit's numerals are a logarithm iff it is the **source of an
  `exp` edge** or the **target of a `log` edge**. Yields 9 units. (Direction
  matters: `decibel → fraction` is `exp`, `fraction → neper` is `log`; both
  conventions appear, and both name the log-side unit.)
- **origin** — components under pure-scaling edges only. `Dimension(temperature)`
  splits into `{kelvin, rankine}`, `{celsius, reaumur}`, `{fahrenheit}`.

Add **one** exogenous fact — thermodynamic temperature has an absolute zero,
realised by `kelvin` — and the whole catalog falls out:

```
interval      ['celsius', 'fahrenheit', 'reaumur']
logarithmic   ['bel','decibel','decibel_milliwatt','decibel_spl','decibel_volt',
               'decibel_watt','neper','nines','pH']
ratio         222 units (everything else)

inputs: 207 declared edge rows (key names only) + 1 physical fact
```

234 of 234, zero disagreements, no ADR and no census consulted. It also gets
`rankine` right, where the hand-written allowlist got it wrong (#339).

### 4.2 Why the draft's derivation could not work

The taxonomy has **two levels**, and a single three-valued enum straddles them:

| level | what varies | decidable from conversion maps? |
|---|---|---|
| **coordinate** φ | identity / `log` / … | **yes** — a coordinate change is non-affine |
| **origin** within a coordinate | ℝ₊ (`ratio`) vs Aff(1) (`interval`) | **no** — ℝ₊ is the stabilizer of 0 *inside* Aff(1) |

`ratio` and `interval` are **subgroup** labels; `logarithmic` is a **coordinate**
label. They are not the same kind of thing, which is why one check could never
cover both.

Level 2's undecidability is not an argument, it is a fact of the catalog.
`reaumur ↔ celsius` is strictly linear with **both** `interval` (they share the
freezing zero); `kelvin ↔ rankine` is strictly linear with **both** `ratio`. Same
observation, different classes. Equivalently: rotate the root through the
temperature fiber and the derived answers flip — only `kelvin` and `rankine` as
root reproduce the census, i.e. exactly the two units already known to have a true
zero. Any rule of this shape **assumes** what it claims to derive, and should be
called an anchored consistency check, never a derivation.

That is why §4.1 needs the physical fact: one bit per fiber, supplied by
metrology. Transition maps on a fiber form a groupoid with a gauge freedom in the
choice of origin; "has a true zero" is extra structure not recoverable from them.

### 4.3 The retracted sweeps, recorded so they are not re-proposed

**"Check B": a same-fiber conversion is non-affine iff exactly one endpoint is
`logarithmic`. FALSE.**

```
nines -> decibel at n = 1, 2, 3:  [-0.457574906, -0.043648054, -0.004345118]
best affine fit: max relative residual 5.6e+07
```

Both endpoints are `logarithmic`. The cause is #341: `nines`' edge is the
catalog's only `composed` edge and its inner `affine(a=-1, b=1)` is `x ↦ 1 − x`,
a change of quantity rather than of scale.

**How the claim passed, which matters more than the claim.** The sweep reported
"946 pairs, 0 violations." The catalog has **971** unordered same-fiber pairs,
**21** unreachable, **950** convertible. The evaluation sat inside a bare
`except Exception: continue`, and four convertible pairs raise
`ValueError: Logarithm argument must be positive` at the probe points used —
`bel→nines`, `decibel→nines`, `neper→nines`, `fraction→nines`. 950 − 4 = 946. The
reported evidence was the input minus exactly the counterexamples. Two further
defects compound it: the verdict **moves with the probe** (at x∈(0,1) the
ratio↔log pair `fraction↔nines`, which the check must flag, is correctly
non-affine; at x∈(1,5) it silently errors), and affinity is a second-difference
test, so residuals must be taken **relative** and over **widely separated**
probes — an absolute tolerance near `dB_SPL → ksi`'s `10⁻¹³` outputs reports
curvature as flat, which produced two phantom findings on the first pass.

Also retracted: the claim that six log↔log pairs carry a `Log ∘ Exp` that cancels
to an affine net. Three do (`dBm ↔ dBW`, `bel ↔ neper`, `decibel ↔ neper`); the
three involving `nines` do not.

**"Check A" as a derivation.** See §4.2. Retained only as an anchored consistency
check, which is what §4.1's origin computation is.

**`dyne` as a fixture.** Dropped. Its `base_form` is populated
(`prefactor=1e-05`, `m·kg·s⁻²`) and `dyne → newton` is a `LinearMap`, so both the
proxy and any composed-path reading classify it `ratio`, correctly. ADR 009 §4
states "`dyne` has no direct edge to read, and its `base_form is None` for
basis-scoping reasons." The first half is true — `dyne` has no `_unit_edges`
entry at all; the `LinearMap` is a cross-basis composition. The second half is a
flat factual error, and it is the founding example of this stratum. The operation
ADR 009 names is `2 × 20 dyn`, which does not refuse today either (#340).
## 5. Question 4 — does the 2.2.2 refusal re-key in this release?

**No. Re-keying it as the roadmap describes would introduce silent magnitude
corruption.**

The roadmap row says the `base_form is None` proxy gives way to declared
`Unit.chart`, changing which pairs refuse. The 62 same-fiber pairs it would
unblock are **not** accidental refusals. `_canonical_magnitude` is documented
"a pure function of (quantity, unit); does **not** consult any graph" and falls
back to `return self.quantity` when `base_form` is `None`:

```
50 %       base_form=None   canonical_magnitude=50
1 fraction base_form=None   canonical_magnitude=1
naive sum  = 51 %           truth: 1 fraction = 100 %, so 150 %      -> 100x wrong
20 °R + 5 K: naive 25.0     truth: 20 °R = 11.111 K, so 16.111 K
```

So the refusals are **correct**, with a misleading message. `base_form is None`
is load-bearing for the *arithmetic*, not only for the meaningfulness check.
The two predicates are independent and both are needed:

- **chart** — is the operation meaningful?
- **`base_form`** — is it computable without the graph?

ADR 010 is right that `base_form` conflates unrelated `None` causes. The
inference "therefore replace it with chart" does not follow. The 62 pairs are
unblocked by *giving those units base_forms* — #283 for the 27 non-SI-basis,
ADR 013's retirement for the 21 pseudo-dimensional, #339 for `rankine` — or by
routing the arithmetic through the conversion graph. Not by relaxing the gate.

Two corrections to the second revision's own numbers while here. The 62 pairs
span **34** units, not 50; the 50 is the count of over-refusing *units*, 16 of
which appear in no counted pair. And the composition is 61 pairs with both
endpoints `None` plus one with exactly one (`kelvin`/`rankine`), not 62 + 0.

The four causes of `base_form is None` are real and the counts hold — but they
are the generator's skip predicates (`scripts/generate_base_forms.py:188-200`
plus `_NULL_BASE_FORM_NAMES:131`), not anything derived from `base_for`
coverage, which was the second revision's broken classifier:

| cause | n | resolved by |
|---|---|---|
| non-SI-basis (`dim.vector.basis != SI`) | 27 | #283 |
| pseudo-dimensional (`dim.is_pseudo`) | 21 | ADR 013's retirement, 3.0.0 |
| genuine chart structure | 12 | derivable today, §4.1 |
| dimensionless (`not dim.base_expansion()`) | 1 | the unnamed unity unit |
| allowlisted in error | 1 | #339 |
## 6. Migration

**None required.** §4.1 derives the classification from the shipped catalog, so
there is no TOML key to add, no `to_toml` emission, no `_CACHE_SCHEMA` bump, no
frozen-dataclass field, and no 12 declarations to hand-write.

Census, derived (**234** units — counted from `comprehensive.ucon.toml`; the
"235" of earlier drafts is an *attribute* count in `ucon.units`, where 235 module
attributes resolve to 234 distinct `Unit.name`s, one being an alias binding):

| class | n | units |
|---|---|---|
| `ratio` | 222 | everything else, `rankine` included |
| `interval` | 3 | `celsius`, `fahrenheit`, `reaumur` |
| `logarithmic` | 9 | `bel`, `decibel`, `decibel_milliwatt`, `decibel_spl`, `decibel_volt`, `decibel_watt`, `neper`, `nines`, `pH` |

What *should* land instead, each independently shippable and none of it a new
field:

1. **#339** — `rankine`'s `base_form`. The generator's BFS oracle already
   computes the right value; only the allowlist suppresses it.
2. **#340** — gate scalar `*` / `/` on level-vs-gain (read from the Map's
   `reference`), validate `BaseForm` to its own documented invariants, and guard
   `_set_base_form`. That last one makes the 2.2.2 proxy sound **by
   construction** instead of by coincidence, and subsumes what
   `_NULL_BASE_FORM_NAMES` is doing by hand.
3. **#341** — the two log edges that target a quantity other than the one
   charted. `nines` is what falsified the proposed validator; `pH` is a level on
   a dimensional fiber.
4. **#283** and ADR 013's pseudo-dimension retirement — which is what actually
   unblocks the 62 pairs, correctly (§5).

A declared `Unit.chart` field earns its keep only for `extend`-time units that
arrive with no edges, where derivation has nothing to read. That is not a 2.3.0
concern, and it is a smaller question than the field as scoped here.

### On ADR 010

ADR 010 is Accepted and says chart is read "from the declared field only — never
inferred from `base_form` … and never from an edge to a sibling unit (log units
relate *linearly* to their siblings)." Both bans are well-founded: `base_form`
conflates four causes (§5) and sibling-edge reading does misclassify `decibel`
against `bel`.

§4.1 is neither procedure. It reads the **declared edge vocabulary** — the key
names the catalog author wrote — and treats `factor` / `factor`+`offset` / `map`
as the declaration they already are. It is closer to ADR 010's spirit than a new
field would be: the author still declares, in the place where the author already
declares.

It is nonetheless a departure from ADR 010's letter, and this proposal does not
have the standing to make it. **Open for decision**, and the only thing in this
document that needs one.
## 7. Not here

- **Chart dispatch** — point/displacement algebra, `20 °C + 5 K`, `2 × 20 °C` refusing, the affine mean, `dBm + dB` admitting across dimensions. All 3.1.0 (ADR 009 §4, §12).
- **Angle** stays a quantity of dimension one per ADR 013; `plane_angle`/`solid_angle` are kinds, not chart classes.
- **`PolynomialMap`'s domain** is branch selection, not input validation; `DomainExceeded` belongs to the operator stratum.

## 8. Open

One decision, and three questions that are not this document's to answer.

**The decision — §6's ADR 010 question.** §4.1 derives the chart class from the
declared edge vocabulary rather than from a new declared field. That is a
departure from ADR 010's letter ("never inferred") though arguably not its
spirit, since the author still declares in the place the author already
declares. ADR 010 is Accepted; a proposal cannot overturn it. Either ADR 010 is
amended to admit the edge vocabulary as the declaration, or a declared field
lands anyway as a second copy of derivable information. **Nothing else in this
document is blocked on anything else.**

Not this document's:

- What `fraction` denotes — a power ratio or a field ratio (#336). The answer
  should be the one #307 and ADR 013 carry forward.
- Whether a fiber gets a distinguished unit beyond the 7 SI base dimensions
  (`base_for` resolves for 7 of 72). §4.2 shows the origin bit is undecidable
  without one, so every fiber that acquires a non-ratio unit needs one declared
  fact. Today only `Dimension(temperature)` has such units and it is anchored,
  so the gap is harmless **by accident of the catalog, not by construction**.
  Same question #307 and #336 hold open for the dimensionless fiber.
- `Number.__neg__`, absent today, which displacement arithmetic will want — and
  `__rmul__`, also absent, so `2 * Number(...)` raises `TypeError` for *every*
  unit in the catalog. Both belong with `__abs__`, ordering and `__round__` in
  the 2.4.0 ergonomics row.

Closed since the last revision: whether `nines` wants its negative scale
declared beyond its Map — superseded by #341, which shows the problem is the
edge's inner map, not the scale.

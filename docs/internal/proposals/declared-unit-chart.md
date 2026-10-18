# PROPOSAL: Declaring `Unit.chart`

**Status:** Proposed — implementation plan, not a decision record
**Date:** 2026-10-17; revised 2026-10-18 after working the open questions one at a time
**Implements:** [`../decisions/010-chart-nomenclature.md`](../decisions/010-chart-nomenclature.md) (Accepted) and [`../decisions/009-turnstile.md`](../decisions/009-turnstile.md) §4
**Lands:** 2.3.0 (the field, its parameters, the validator, the catalog declarations). The chart *dispatch* is 3.1.0.
**Disposition on landing:** this document is the acceptance list; §4's two sweeps become tests and §6's census becomes the catalog declaration they check. Superseded afterwards by the CHANGELOG entry.

All evidence below verified against `main` at `dcf7f8d`.

**Revision note.** Every first-draft recommendation on questions 1–3 was wrong,
and §§2–4 record why — the reasoning is the useful part. Two of the three are
answered by *deletion*: the fourth chart class is declined (§2) and
`logarithmic` needs no parameters (§3). The third is answered by *replacement*:
the proposed edge-reading validator is not well-defined, and two checks on
different mechanisms take its place (§4). Working it also found two wrong
catalog declarations — `rankine` and `pH` — which is the validator paying for
itself before it exists.

---

## 1. What ADR 010 already decided — do not reopen

010 is **Accepted**. It settles, and this proposal takes as given:

- the field is **`Unit.chart`**; the stratum is the **chart stratum**; the values are **chart classes**;
- the three classes are **`ratio`** (pure scaling, true zero), **`interval`** (scaling, conventional zero), **`logarithmic`** (log of a ratio to a reference);
- chart is read **from the declared field only** — never inferred from `base_form` (which conflates unrelated `None` causes) and never from an edge to a sibling unit (log units relate *linearly* to their siblings);
- the Map-form derivation survives **solely as a load/`extend`/merge-time validator**;
- cyclic and ordinal structure live on `Kind` (`modulus`, `ordinal`), not here;
- the taxonomy is **deliberately open**: "a declared field admits a fourth class without migration."

So the open work is four questions 009 and 010 left unanswered, not the naming or the inference ban.

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
draft: a chart class is a unit's relation to its *own* fiber's canonical ratio
unit, and the PT100 polynomial relates `celsius` (temperature) to `ohm`
(resistance) — a cross-dimensional conversion edge, not a numeral scheme.

The taxonomy stays at three. ADR 010 guarantees a fourth can be added later
without migration, so nothing is foreclosed.

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
are all four, and today three of the five cases are wrong:

| operands | required | today |
|---|---|---|
| level − level | **gain** (dimensionless) — the only producer of a displacement | `<10.0 dBm>` — right number, wrong type |
| level ± gain | level | `TypeError` — the legitimate case, refused |
| gain ± gain | gain | correct |
| level + level | refuse | `<50.0 dBm>` — admitted |

All the level cases fail for one reason: `dBm` is `Dimension(power)` and `dB` is
`Dimension(ratio)`, so `__add__` gates on dimension at **stratum 1** before any
chart logic could run. A correct log chart needs stratum 1 to admit *point +
declared-displacement-unit across dimensions* — which is 3.1.0 dispatch, not
this release. Noted so the limit is explicit rather than implied.

Subtraction is not a special case of addition here. `point − point` cannot be
rewritten as `point + (−point)` because negating a point is meaningless; it is
its own rule, and it is the SNR idiom. Within displacements subtraction *does*
collapse into addition, since a gain may legitimately be negative — though
`Number` has no `__neg__` today, so `-(3 dB)` raises.

## 4. Question 3 — what does the validator check, and when?

010: the Map-form derivation survives as a load/`extend`/merge-time validator.
The first draft specified it as "derive the expected class from the edge to the
fiber's canonical ratio unit." **That derivation is not well-defined**, for
three independent reasons, each verified against the shipped graph.

**(a) The anchor does not exist for the fibers that need it.**
`active_system().base_units.base_for(dim)` resolves for **7 of 72** fibers — the
SI base dimensions. Every other fiber raises `DimensionNotCovered`, including
every fiber a logarithmic unit lives on:

```
celsius  rankine  reaumur   Dimension(temperature)   base_for -> <Unit K>
bel  decibel  neper  nines  Dimension(ratio)         DimensionNotCovered
decibel_milliwatt/_watt     Dimension(power)         DimensionNotCovered
decibel_spl                 Dimension(pressure)      DimensionNotCovered
decibel_volt                Dimension(voltage)       DimensionNotCovered
pH                          Dimension(concentration) DimensionNotCovered
```

So "the fiber's canonical ratio unit" names something the code cannot look up
for 9 of the 12 units the validator exists to check. Supplying one is the
question #307 and #336 are already holding open.

**(b) Conversion nonlinearity is symmetric, so no per-unit class is derivable
without an anchor.** `kelvin ↔ celsius` is affine read from either end. Running
the unanchored derivation — classify a unit by the worst nonlinearity on any
path within its own fiber — produces **31 false refusals** on a 234-unit
catalog: `kelvin` derives `interval`, and every ratio unit sharing a fiber with
a log unit (`watt`, `pascal`, `volt`, `percent`, `fraction`, `torr`,
`horsepower`, …) derives `logarithmic`. The chart class is a property of a
unit's relation to a *distinguished* unit; the graph is unrooted.

**(c) "The edge" is neither singular nor sufficient, and the map named is the
wrong one.** `celsius` has three direct edges spanning two map types (`Affine`
to `kelvin` and `fahrenheit`, `Linear` to `reaumur`). `reaumur`'s *only* direct
edge is `LinearMap → celsius`, which derives `ratio`; the right answer needs the
composed path to `kelvin`, which is `AffineMap`. And in the unit→canonical
direction every log unit's composed map is an **`ExpMap`**, not the `LogMap` the
draft keyed on — `decibel → fraction` is `Exp`, `fraction → decibel` is `Log`.
A validator reading `LogMap` in the direction it implies classifies all nine as
nothing.

Both fixtures the draft named also fail as fixtures, and `dyne` fails twice
over: it is **not a chart case at all**. Its `base_form` is populated
(`prefactor=1e-05`, `m·kg·s⁻²`) and `dyne → newton` composes to a `LinearMap`,
so the proxy and a composed-path derivation both classify it `ratio` —
correctly. What actually refuses `20 dyn + 1 N` is **stratum 1**:
`Dimension(cgs_force)` is not `Dimension(force)`. That is basis-graph territory
(#323, ADR 013), and ADR 009 §4's listing it among the chart misclassifications
is itself the error. `decibel`, meanwhile, misreads as `ratio` only if you
anchor it on `bel`; anchored on `fraction` its map is `ExpMap`. Neither is a
counterexample to edge-reading as such.

### What the validator can check

Two checks, different mechanisms, neither subsuming the other.

**Check A — anchored; separates `interval` from `ratio`.** Where
`base_for(dim)` resolves, derive from the composed map to that base unit:
offset-bearing `Affine` ⇒ `interval`, pure scaling ⇒ `ratio`. This covers the
only fiber interval units inhabit. Swept over the catalog it reports **exactly
one disagreement**, and it is a real catalog error, not a false positive — see
`rankine` below.

**Check B — anchor-free; separates `logarithmic` from the rest.** For any two
units `u, v` in one fiber, the conversion `u → v` is non-affine **iff** exactly
one of them is declared `logarithmic`. No distinguished unit is required
because the biconditional is symmetric — which is what makes it survive the
rootless fibers (a). Swept over all **946** same-fiber convertible pairs it
reports **one violation**, again a real catalog error (`pH` below).

Check B must test the **net function numerically**, not the `Map` tree. Six
log↔log pairs (`decibel_milliwatt ↔ decibel_watt`, `bel ↔ neper`,
`bel ↔ nines`, `decibel ↔ neper`, `decibel ↔ nines`, `neper ↔ nines`) route
through the fiber's ratio unit and carry a syntactic `Log ∘ Exp` that cancels to
an affine net: `30 dBm − 30 = 0 dBW` is affine however the path spells it.
Reading the tree flags all six. Affinity is a second-difference test; residuals
must be taken **relative**, since `dB_SPL → ksi` lands near `10⁻¹³` and an
absolute tolerance swallows the curvature.

Check B cannot separate `ratio` from `interval` (both relate affinely to
themselves and to each other), and Check A cannot run where there is no root.
Together they cover all 12 declarations; apart, neither does.

### Two catalog corrections the derivation earns

- **`rankine` is `ratio`, not `interval`.** `0 °R = 0 K` — verified, the
  composed map to kelvin is `LinearMap(a=5/9)` and `f(0) = 0`. Rankine is the
  absolute Fahrenheit-degree scale; it shares kelvin's true zero, and only its
  *degree size* is Fahrenheit's. The draft's census grouped it by degree size
  with the three scales that have conventional zeros.
- **`pH` is `logarithmic`, and was missing.** `molar → pH` is
  `LogMap(scale=−1, base=10, reference=1.0)`; `7 pH → 1e-07 mol/L`. It is the
  single violation Check B reports, which is the check working.

`rankine` also needs a **second, separable fix**: its TOML entry has no
`base_form`, though it is a pure scaling of kelvin on a fully covered fiber. It
sits in the catalog beside the three affine scales and inherited their omission.
`base_form = {prefactor: 5/9, factors: [[kelvin, 1.0]]}` is the whole change,
and it is independent of charts, #283 and ADR 013 — the one `None` in the table
above with no structural cause. `pH` needs no such fix: it is correctly
non-normalizable, just for the wrong stated reason.

Against the corrected census both checks report **0 disagreements and 0
violations across 946 pairs**. That is the acceptance criterion for this
release: the two sweeps become tests, and the census below becomes the catalog
declaration they check.
## 5. Question 4 — does the 2.2.2 refusal re-key in this release?

The roadmap row says the `base_form is None` proxy gives way to declared `Unit.chart`. That is the behaviour-visible half: it changes **which pairs refuse**.

**Proposal: two commits, not one.** Land the field, parameters, validator, and catalog declarations first; re-key `_is_algebraically_normalizable` second. A bisect can then separate "chart declared" from "refusal re-keyed" — they fail differently and a reviewer should be able to tell which.

The draft said "the five accidental refusals." Counted, it is **62 pairs over 50
units**. `base_form is None` holds for **62 of 234** units, and only **12** of
those are genuinely non-ratio; the proxy is *sound but imprecise* — nothing with
a populated `base_form` has a non-ratio chart, so it never under-refuses, but
it over-refuses by 50 units. The `None` splits into four causes, which is ADR
010's "conflates unrelated `None` causes" made countable:

| cause | n | resolved by |
|---|---|---|
| out of the SI basis (CGS-EM, atomic, Planck, the unnamed unity unit) | 28 | #283 |
| pseudo-dimensional (angle, ratio, count families) | 21 | ADR 013's retirement, 3.0.0 |
| genuine chart structure | 12 | this release |
| **unexplained** — `rankine` | 1 | a one-line catalog fix (below) |

So the re-key cannot deliver all 62 on its own: it owns the 12. The other 50 are
waiting on #283 and 3.0.0, and the re-key is what makes it *safe* to stop
asking `base_form` a question it was never answering.

Live, verified today: `20 °R + 5 K`, `50 % + 1 fraction` and `20 °C + 5 K` all
raise `UnitsNotNormalizable`. Only the third is correct, and even it refuses for
the wrong reason.

## 6. Migration

Census of the shipped catalog — **234 units**, counted from
`comprehensive.ucon.toml`, not the 235 the draft asserted:

| class | n | units |
|---|---|---|
| `ratio` (default) | 222 | everything else, `rankine` included |
| `interval` | 3 | `celsius`, `fahrenheit`, `reaumur` |
| `logarithmic` | 9 | `bel`, `decibel`, `decibel_milliwatt`, `decibel_spl`, `decibel_volt`, `decibel_watt`, `neper`, `nines`, `pH` |

Still **12 units** to declare, by coincidence — `rankine` left and `pH`
arrived (§4). `ratio` remains the correct default for 95% of the catalog, and
with the fourth class declined there are three values to choose from. Also
required — the TOML key, `to_toml` emission, the binary cache (another
`_CACHE_SCHEMA` bump), and `Unit`'s frozen-dataclass field alongside
`default_kind`.

## 7. Not here

- **Chart dispatch** — point/displacement algebra, `20 °C + 5 K`, `2 × 20 °C` refusing, the affine mean, `dBm + dB` admitting across dimensions. All 3.1.0 (ADR 009 §4, §12).
- **Angle** stays a quantity of dimension one per ADR 013; `plane_angle`/`solid_angle` are kinds, not chart classes.
- **`PolynomialMap`'s domain** is branch selection, not input validation; `DomainExceeded` belongs to the operator stratum.

## 8. Open

- What `fraction` denotes — a power ratio or a field ratio. Filed as #336; the
  answer should be the one #307 and ADR 013 carry forward.
- **Whether a fiber gets a canonical unit beyond the 7 SI base dimensions.**
  §4(a): `base_for` resolves for 7 of 72 fibers, which is why the validator
  needs Check B at all. If derived fibers ever acquire a distinguished unit,
  Check A generalizes and Check B becomes redundant. Not required for 2.3.0,
  and it is the same question #307 and #336 hold open for the dimensionless
  fiber.
- Whether `nines` wants its negative scale declared anywhere beyond its Map.
- `Number.__neg__`, absent today, which displacement arithmetic will want
  (flagged with `__abs__`, ordering and `__round__` in the 2.4.0 ergonomics row).

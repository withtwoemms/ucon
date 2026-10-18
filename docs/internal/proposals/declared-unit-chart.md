# PROPOSAL: Declaring `Unit.chart`

**Status:** Proposed — implementation plan, not a decision record
**Date:** 2026-10-17; revised 2026-10-18 after working the open questions
**Implements:** [`../decisions/010-chart-nomenclature.md`](../decisions/010-chart-nomenclature.md) (Accepted) and [`../decisions/009-turnstile.md`](../decisions/009-turnstile.md) §4
**Lands:** 2.3.0 (the field, its parameters, the validator, the catalog declarations). The chart *dispatch* is 3.1.0.
**Disposition on landing:** this document is the acceptance list; each block in §5 becomes a test. Superseded afterwards by the CHANGELOG entry.

All evidence below verified against `main` at `0e1d22e`.

**Revision note.** Three of the four questions below are now answered by *deletion*: the
fourth chart class is declined, and `logarithmic` needs no parameters. Both
recommendations in the first draft were wrong, and §2 and §3 record why —
the reasoning is the useful part.

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

010: the Map-form derivation survives as a load/`extend`/merge-time validator. Specify it as:

> Derive the expected class from the edge to the fiber's canonical ratio unit — Linear → `ratio`, Affine → `interval`, Log (including a `ComposedMap` whose outer map is a log, as `nines` is) → `logarithmic` — and compare against the declaration. Mismatch refuses at load.

Two `[live]` misclassifications 009 §4 names become its fixtures, and both are cases **inference alone gets wrong** — which is precisely why the declared field is the authority:

- **`dyne`** has no direct edge to read, and its `base_form is None` for basis-scoping reasons rather than chart structure (#283). Inference would refuse `2 × 20 dyn` the way it refuses `2 × 20 °C`.
- **`decibel`**'s direct edge is a `LinearMap` to `bel` — a within-chart automorphism. Edge-reading misreads log units as ratio.

## 5. Question 4 — does the 2.2.2 refusal re-key in this release?

The roadmap row says the `base_form is None` proxy gives way to declared `Unit.chart`. That is the behaviour-visible half: it changes **which pairs refuse**.

**Proposal: two commits, not one.** Land the field, parameters, validator, and catalog declarations first; re-key `_is_algebraically_normalizable` second, with the five accidental refusals enumerated in its message. A bisect can then separate "chart declared" from "refusal re-keyed" — they fail differently and a reviewer should be able to tell which.

## 6. Migration

Census of the shipped catalog (235 units):

| class | n | units |
|---|---|---|
| `ratio` (default) | 223 | everything else |
| `interval` | 4 | `celsius`, `fahrenheit`, `rankine`, `reaumur` |
| `logarithmic` | 8 | `bel`, `decibel`, `decibel_milliwatt`, `decibel_spl`, `decibel_volt`, `decibel_watt`, `neper`, `nines` |

So the work is enumerating **12 units**, not 235: `ratio` is the correct default for 95% of the catalog, and with the fourth class declined there are only three values to choose from. Also required — the TOML key, `to_toml` emission, the binary cache (another `_CACHE_SCHEMA` bump), and `Unit`'s frozen-dataclass field alongside `default_kind`.

## 7. Not here

- **Chart dispatch** — point/displacement algebra, `20 °C + 5 K`, `2 × 20 °C` refusing, the affine mean, `dBm + dB` admitting across dimensions. All 3.1.0 (ADR 009 §4, §12).
- **Angle** stays a quantity of dimension one per ADR 013; `plane_angle`/`solid_angle` are kinds, not chart classes.
- **`PolynomialMap`'s domain** is branch selection, not input validation; `DomainExceeded` belongs to the operator stratum.

## 8. Open

- What `fraction` denotes — a power ratio or a field ratio. Filed as its own
  issue; the answer should be the one #307 and ADR 013 carry forward.
- Whether `nines` wants its negative scale declared anywhere beyond its Map.
- `Number.__neg__`, absent today, which displacement arithmetic will want
  (flagged with `__abs__`, ordering and `__round__` in the 2.4.0 ergonomics row).

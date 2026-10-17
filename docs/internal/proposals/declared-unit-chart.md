# PROPOSAL: Declaring `Unit.chart`

**Status:** Proposed — implementation plan, not a decision record
**Date:** 2026-10-17
**Implements:** [`../decisions/010-chart-nomenclature.md`](../decisions/010-chart-nomenclature.md) (Accepted) and [`../decisions/009-turnstile.md`](../decisions/009-turnstile.md) §4
**Lands:** 2.3.0 (the field, its parameters, the validator, the catalog declarations). The chart *dispatch* is 3.1.0.
**Disposition on landing:** this document is the acceptance list; each block in §5 becomes a test. Superseded afterwards by the CHANGELOG entry.

All evidence below verified against `main` at `6ca4e92`.

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

## 2. Question 1 — does the taxonomy gain a fourth class now?

`nines` is `−log₁₀(1 − x)`, shipped as a `ComposedMap(outer=log(scale=−1, base=10), inner=affine(a=−1, b=1))`:

```python
>>> Number(3.0, units.nines).to(units.fraction)
<0.999 frac>          # 1 − 10⁻³
```

It is logarithmic **in the complement**, so "nines add" is the parallel-redundancy law, not the cascade law: `3 nines + 3 nines → 6 nines` is right for redundancy and wrong for series (0.999 × 0.999 ≈ 2.7 nines). Filing it under `logarithmic` would admit the wrong one silently.

**Proposal: add `transformed`** — Map-defined, conversion only; `+` and `×` refuse. It keeps `logarithmic` meaning *levels* (§3), and it pre-houses the next exotic calibration rather than forcing it into a class it does not fit. 010 explicitly reserved this room.

**`PolynomialMap` (#332, merged) is the second inhabitant**, and the reason the class is worth having now rather than later: a calibration polynomial is neither ratio, interval, nor logarithmic, and one is already in the tree. Its domain-restricted inverse is precisely a Map-defined conversion with no scaling story — the shape `transformed` names.

## 3. Question 2 — what parameters does `logarithmic` carry?

**This is the substantive question, and a shipped numerical error is attached to it.**

ISO 80000-3 / IEC 80000-15 make a *level* meaningless without a reference, and distinguish **field** from **power** quantities (`ln` vs `½ ln`; equivalently 20 log vs 10 log). The catalog has the reference right at unit level — `decibel_milliwatt` is `LogMap(scale=0.1, reference=0.001)` on `Dimension(power)` — but nothing declares field-vs-power, and the two edges disagree:

```
fraction → neper   : LogMap(scale=1, base=e)    i.e. Np = ln(x)
decibel → fraction : 10^(x/10)                  i.e. x is a power ratio
```

Measured consequence:

```python
>>> Number(1.0, units.neper).to(units.decibel)
<4.3429448190325175 dB>      # SI Brochure Table 8: 1 Np = 8.686 dB
>>> Number(1.0, units.bel).to(units.neper)
<2.302585092994046 Np>       # SI: 1 B = (ln 10)/2 Np ≈ 1.1513 Np
```

Both off by **exactly the field/power factor of 2**, because the neper is defined on the *field* quantity (`½ ln` of a power ratio) and ucon's edge logs the power ratio directly. A `logarithmic` class that cannot state which is intended cannot validate the edge either.

**Proposal:** `chart = logarithmic(reference=<quantity | None>, kind=field | power)`.

`reference=None` is load-bearing: it marks the unit as a **displacement** unit (a bare `dB`, a gain) rather than a **point** (a `dBm`, a level). That distinction is what makes 009 §4's "a literal on an affine chart is a point" correct for `dBm` and wrong for `dB` — and today's verdicts are exactly inverted:

```python
>>> Number(0.0, units.decibel_milliwatt) + Number(3.0, units.decibel)
TypeError          # the one legitimate level operation — level + gain — REFUSED
>>> Number(0.0, units.decibel_milliwatt) + Number(0.0, units.decibel_milliwatt)
<0.0 dBm>          # point + point, ill-formed — ADMITTED
```

The refusal comes from stratum 1: `decibel_milliwatt` is `Dimension(power)` while `decibel` is `Dimension(ratio)`, and `__add__` gates on dimension before anything else. So a correct log chart needs stratum 1 to admit `point + declared-displacement-unit` across dimensions — which is **3.1.0 dispatch**, not this release. This proposal ships the declaration that makes that dispatch expressible, and says so.

Fixing the `neper` edge is a **separate catalog commit** with `1 Np == 8.686 dB` pinned: it changes a shipped number, and anyone who compensated downstream inherits the inverse error.

## 4. Question 3 — what does the validator check, and when?

010: the Map-form derivation survives as a load/`extend`/merge-time validator. Specify it as:

> Derive the expected class from the edge to the fiber's canonical ratio unit — Linear → `ratio`, Affine → `interval`, Log → `logarithmic`, anything else → `transformed` — and compare against the declaration. Mismatch refuses at load.

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
| `logarithmic` | 7 | `bel`, `decibel`, `decibel_milliwatt`, `decibel_spl`, `decibel_volt`, `decibel_watt`, `neper` |
| `transformed` | 1 | `nines` (+ any `PolynomialMap` edge, #332) |

So the work is enumerating **12 units**, not 235: `ratio` is the correct default for 95% of the catalog. Also required — the TOML key, `to_toml` emission, the binary cache (another `_CACHE_SCHEMA` bump), and `Unit`'s frozen-dataclass field alongside `default_kind`.

## 7. Not here

- **Chart dispatch** — point/displacement algebra, `20 °C + 5 K`, `2 × 20 °C` refusing, the affine mean, `dBm + dB` admitting across dimensions. All 3.1.0 (ADR 009 §4, §12).
- **Angle** stays a quantity of dimension one per ADR 013; `plane_angle`/`solid_angle` are kinds, not chart classes.
- **`PolynomialMap`'s domain** is branch selection, not input validation; `DomainExceeded` belongs to the operator stratum.

## 8. Open

- Is `transformed` the right name? (`mapped`, `derived`, `opaque` were considered; `transformed` reads as "defined by its Map".)
- Is `reference` a `Number`, or a `(value, unit)` pair? `decibel_milliwatt` stores a bare `0.001` today.
- Does `field | power` belong on the chart or on the `Kind`? It is arguably a property of the measurand, which 010 says lives on `Kind` — but the *numeral scheme* is what encodes the factor of 2, which argues for the chart.

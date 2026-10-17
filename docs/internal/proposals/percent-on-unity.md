# PROPOSAL: Percent on unity — the `%` API as of 3.0.0

**Status:** Proposed API — specification by example; none of this runs today
**Date:** 2026-10-17
**Decided by:** [`../decisions/013-the-vector-is-the-only-carrier.md`](../decisions/013-the-vector-is-the-only-carrier.md) §2
(linear ratios are radix powers on unity, therefore `Scale`) and §3 (the fold rule)
**Lands:** machinery in **2.3.1** (`#307` canonical unity, `#318` fold; exact `Scale`
arithmetic); rendering table and the 10⁻⁴ member in **2.5.0**; `%` itself in **3.0.0**
with the retirement of `Dimension(ratio)`. See `ROADMAP.md`, *Where the chart defects
land* and *The UnitSafe gate*.
**Disposition on landing:** this document is the acceptance list for the 3.0.0 `%`
change; each block below becomes a test. Once shipped it is superseded by the
CHANGELOG entry and may move to `explainers/`.

---

## 1. Why `%` cannot be fixed before 3.0.0

Two things must move together: `parse_unit("%")` and `units.percent`. Flipping the
parser to scaled unity in a patch while `units.percent` stays a `Dimension(ratio)`
unit produces two disagreeing percents — `Number(5, parse_unit("%")) +
Number(5, units.percent)` goes from `<10 %>` to `TypeError`, and `==` silently
returns `False`. Moving `units.percent` off `Dimension(ratio)` changes a public
symbol's dimension, which the deprecation policy places on a major. So 2.3.1 ships
the machinery under a new spelling, 2.4.0–2.7.0 run the deprecation ladder, and
3.0.0 moves both together.

From 2.3.1 the result users want is reachable explicitly:

```python
>>> Number(50, Scale.centi * one) * Number(10, U.kilogram)
<5.0 kg>
```

That spelling is what the 2.4.0/2.5.0 deprecation warnings point at.

## 2. The one rule everything below follows

> An **anonymous** scaled unity (`centi·one`) **folds** into the magnitude when it
> meets any other factor, and **persists** — displaying as `%` — when it stands alone.
> A **named** unit of dimension one (`rad`, `request`) and a **dimensionless compound**
> (`mg/kg`) **persist** as factors.

Get this line wrong in either direction and either `mg/kg` collapses to a bare number
or `%` leaks into every product, as it does today (`10 kg × 50 % → <500.0 g·%>`,
unconvertible).

## 3. Specification by example

```python
>>> from ucon import Number, Scale, one, parse_unit, units as U

# ── What % is ────────────────────────────────────────────────────────────
>>> parse_unit("%")
<UnitProduct %>                    # Scale.centi on the canonical unity unit
>>> parse_unit("%").dimension
Dimension(none)                    # Dimension(ratio) no longer exists
>>> parse_unit("%") == Scale.centi * one == U.percent
True                               # units.percent survives as an alias; one object, three spellings
>>> parse_unit("‰"), parse_unit("ppm"), parse_unit("ppb"), parse_unit("‱")
(<UnitProduct ‰>, <UnitProduct ppm>, <UnitProduct ppb>, <UnitProduct ‱>)
>>> parse_unit("1"), parse_unit("fraction")
(<Unit 1>, <Unit 1>)               # fraction is unity; "1" resolves to it (#307)

# ── Standalone: a scaled unity PERSISTS and renders ──────────────────────
>>> eff = Number(85, U.percent)
>>> eff
<85.0 %>
>>> eff.quantity, eff.canonical_magnitude, eff.to(one)
(85.0, 0.85, <0.85>)               # all accessors agree (#318)
>>> Number(250, parse_unit("ppm")).to(U.percent)
<0.025 %>
>>> Number(0.0025, one).to(U.percent)
<0.25 %>

# ── Meeting another factor: the scaled unity FOLDS ───────────────────────
>>> Number(10, U.kilogram) * Number(50, U.percent)
<5.0 kg>                           # today: <500.0 g·%>, unconvertible
>>> Number(100, U.watt) * Number(85, U.percent)
<85.0 W>
>>> Number(2.5, parse_unit("ppm")) * Number(70, U.kilogram)
<0.000175 kg>
>>> _.to(U.milligram)
<175.0 mg>
>>> Number(5, U.milligram) / Number(2, U.kilogram)
<2.5 mg/kg>                        # a dimensionless COMPOUND persists — mg/kg is kept deliberately
>>> _ == Number(2.5, parse_unit("ppm"))
True                               # today: False, silently
>>> Number(500, parse_unit("kg·%"))
<5.0 kg>                           # the fold happens at the Number boundary; a Number never
                                   # carries a unit with canonical_scale ≠ 1

# ── Percent with percent ─────────────────────────────────────────────────
>>> Number(8, U.percent) - Number(5, U.percent)
<3.0 %>                            # percentage points — a displacement on the ratio chart
>>> Number(8, U.percent) / Number(5, U.percent)
<1.6>                              # both fold; a bare ratio
>>> _.to(U.percent)
<160.0 %>                          # the relative change, when wanted as one
>>> Number(85, U.percent) * Number(90, U.percent)
<76.5 %>                           # the right operand folds into the left's exact scale
>>> Number(1, one) + Number(5, U.percent)
<1.05>                             # left operand's unit wins — today's __add__ rule, unchanged
>>> Number(5, U.percent) + Number(1, one)
<105.0 %>
>>> Number(85, U.percent) ** 2
<7225.0 %²>
>>> _.to(one), _.to(U.percent)
(<0.7225>, <72.25 %>)              # canonical magnitude 0.7225, not 7225 (today's 10⁴ error)

# ── Exactness ────────────────────────────────────────────────────────────
>>> (Number(10, U.kilogram) * Number(50, U.percent)).quantity
5.0                                # Fraction arithmetic under the fold for exact operands
>>> Scale.centi * Scale.centi
Exponent(10, -4)                   # exact — today snaps to Scale.milli, a 10× error
>>> Number(25, parse_unit("‱")) * Number(1_000_000, U.USD)     # ≥ 2.6.0, currency as a basis component
<2500.0 USD>

# ── Uncertainty rides the fold ───────────────────────────────────────────
>>> Number(5, U.meter, uncertainty=0.1) * Number(50, U.percent)
<2.5 ± 0.05 m>                     # today: <250 ± 5.0 m>

# ── What a percent is OF — kinds on unity ────────────────────────────────
>>> a = Number(85, U.percent, kind="efficiency")
>>> b = Number(40, U.percent, kind="relative_humidity")
>>> a + b
JoinRefused: 'efficiency' and 'relative_humidity' share no join under 'dimensionless_ratio' (refuse)
>>> Number(85, U.percent) + Number(40, U.percent)
<125.0 %>                          # unkinded numbers are numbers; admitted by design
>>> Number(0.3, one, kind="mass_fraction") == Number(0.3, one, kind="volume_fraction")
False                              # equality consults kinds (2.6.0 signature/kind check)
>>> a * Number(10, U.kilowatt)
<8.5 kW [derived(efficiency·anon(power))]>     # 3.1.0 — kinds compose; in 3.0.0 strict this is
                                                #        KindMismatch, permissive drops the kind

# ── Rendering: only the named scales on unity have symbols ───────────────
>>> Number(3, Scale.kilo * one)
<3.0 ×10³>                         # SI forbids prefixes on the unit one; no symbol → power of ten
>>> Number(7, Scale.deci * one)
<7.0 ×10⁻¹>

# ── What 3.0.0 does NOT do — the chart stratum is 3.1.0 ──────────────────
>>> Number(20, U.celsius) * Number(50, U.percent)
<10.0 °C>                          # admitted in 3.0.0 (scalar × point is ill-formed); refuses in 3.1.0

# ── Migration surface ────────────────────────────────────────────────────
>>> Dimension.ratio
AttributeError                     # loud; Number[Dimension.ratio] in the pydantic guide moves to a kind
>>> from_toml("my_pkg.ucon.toml")  # a user unit declared  dimension = "ratio"
DeprecationWarning: 'ratio' is unity; declare dimension = "none" and, if the quantity has an
identity, a kind on it. Upgraded in place.
```

## 4. What remains conditional

Everything in §3 except the *kinds on unity* block is mechanical and lands with the
retirement. That block needs the dimensionless kinds in the catalog — `efficiency`,
`relative_humidity`, `mass_fraction`, `volume_fraction`, `amount_fraction`,
`bioavailability`, `strain`, and the dimensionless numbers (`reynolds`, `mach`,
`froude`) — which belong with the 2.3.0 cluster kinds. Without them `85 % + 40 %` is
admitted whatever the operands meant, and UnitSafe's dimensionless KOQ must-fails
(`bioavailability/fraction_unbound`, `strain/probability`, `reynolds/mach`,
`friction/refractive_index`, the two magnitude items) stay unprotected.

## 5. Silent value changes the 3.0.0 notes must name

| expression | today | 3.0.0 |
|---|---|---|
| `(100 W × 85 %).quantity` | 8500 | 85 |
| `(2.5 ppm × 70 kg).canonical_magnitude` | 175 (wrong) | 1.75e-4 |
| `(85 %)**2` canonical magnitude | 7225 (wrong) | 0.7225 |
| `1 mg/kg == 1 ppm` | `False` | `True` |
| `Scale.centi * Scale.centi` | `Scale.milli` (wrong) | exact 10⁻⁴ (2.3.1) |
| `units.percent.dimension` | `Dimension(ratio)` | `Dimension(none)` |

Most are wrong→right. All are silent; anyone who compensated downstream inherits the
inverse error on upgrade. Two UnitSafe problems answer `%` and `ppm` (`geo-025`,
`geo-026`) and pass today because `percent` renders `%`; the 2.5.0 rendering table
exists so they keep passing after the flip.

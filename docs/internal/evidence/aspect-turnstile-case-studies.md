# CASE STUDIES — Aspect and Turnstile as designed

**Status:** Target-state illustrations against decisions ruled 2026-09-03 → 09-09.
Nothing here is shipped. Each case marks what is **[vetted]** by prototype and
what is **[ruled]** by decision without a running implementation.

---

## Turnstile — definition

The Turnstile is the gate every arithmetic operation passes through. It runs
four checks in dependency order, each either refusing or contributing to the
coercion, then executes.

```
                          a ⊕ b
                            │
        ┌───────────────────┼───────────────────┐
        │  1  dimension     φ(a) ? φ(b)          │  category 1
        │  2  chart         admissible on chart?  │  categories 2, 3
        │  3  kind          join, ⊤_d on miss     │  categories 4, 5, 6
        │  4  aspect        componentwise join    │  categories 7, 8
        └───────────────────┼───────────────────┘
                            │  first refusal raises Refused(warrant)
                            ▼
                   factor lookup · fma · construct Number
```

**Runtime cost.** Four inline checks, no cache, no compile step. Measured
baseline `[live]`: today's `__add__` is 0.80 µs; the cache key alone costs 0.26 µs
and the checks cost 0.29 µs, so caching was removed. Target ≈ 1 µs.

**Warrants are lazy.** A refusal carries one in the exception. An admission
builds one only on request via `explain()`.

**What each stratum contributes to the coercion:**

| stratum | contributes |
|---|---|
| dimension | `result_unit` |
| chart | `left_factor`, `right_factor`, `offset`, `result_displacement` |
| kind | `result_kind` — LCA, or ⊤_d on degradation |
| aspect | `result_aspect` — per aspect family |

---

## Case 1 — Radiation dose: kind and aspect together

The canonical case. Absorbed dose (Gy) and dose equivalent (Sv) share the
dimension L²T⁻². Two dose equivalents may further differ by which standard
weighted them — a distinction below the kind layer's reach.

### Package

```toml
[package]
name = "radsafe"
namespace = "radsafe"

# --- kinds --------------------------------------------------------------
[[kinds]]
name = "dose"
dimension = "specific_energy"
join_policy = "refuse"

[[kinds]]
name = "absorbed_dose"
dimension = "specific_energy"
parent = "dose"

[[kinds]]
name = "dose_equivalent"
dimension = "specific_energy"
parent = "dose"

[[kinds]]
name = "radiation_weighting_factor"
dimension = "none"

# --- aspects: the root carries the family's rules ---------------------------
[[aspects]]
name = "weighting_standard"
applies_to = ["dose_equivalent", "radiation_weighting_factor"]
multiplication_policy = "carry"
join_policy = "refuse"

[[aspects]]
name   = "icrp60"
parent = "weighting_standard"

[[aspects]]
name   = "icrp103"
parent = "weighting_standard"

# --- formula ---------------------------------------------------------------
[[formulas]]
name = "radiation_weighting"
input_kinds = ["absorbed_dose", "radiation_weighting_factor"]
output_kind = "dose_equivalent"
```

### 1a — Kind refuses what dimension admits `[vetted]`

```python
absorbed = Number(1.5, gray,    kind="radsafe:absorbed_dose")
equiv    = Number(2.0, sievert, kind="radsafe:dose_equivalent")

absorbed + equiv
```

```
Refused: category 5 (kind, join_policy)
  1.5 Gy [absorbed_dose] + 2.0 Sv [dose_equivalent]
  siblings under 'radsafe:dose' (join_policy=refuse)
  remedy: radiation_weighting(absorbed_dose, radiation_weighting_factor) -> dose_equivalent
```

Today `[live]` this returns `<3.5 Gy>`. Stratum 1 passes (same dimension);
stratum 3 refuses. The remedy is a registry hit, not prose.

### 1b — Aspect refuses what kind admits `[vetted by prototype]`

```python
old = Number(2.0, sievert, kind="radsafe:dose_equivalent",
             aspects=["radsafe:icrp60"])
new = Number(3.0, sievert, kind="radsafe:dose_equivalent",
             aspects=["radsafe:icrp103"])

old + new
```

```
Refused: category 7 (aspect, aspect family conflict)
  2.0 Sv + 3.0 Sv — both dose_equivalent
  aspect family 'radsafe:weighting_standard': 'icrp60' and 'icrp103'
  are siblings under 'radsafe:weighting_standard' (join_policy=refuse)
```

Identical dimension, unit, and kind. Strata 1–3 pass. Only stratum 4 can see
the difference. The sum would conform to neither standard.

### 1c — The factor carries its own standard `[ruled]`

```python
w_R = Number(20, dimensionless, kind="radsafe:radiation_weighting_factor",
             aspects=["radsafe:icrp103"])

absorbed * w_R
# → 30.0 Sv [dose_equivalent] {icrp103}
```

No `produces` on the formula. `{} × {icrp103}` under `carry` yields `{icrp103}`.
The formula does kind work only; the ICRP package ships an annotated w_R table
as data. Requires `weighting_standard.applies_to` to include the factor's kind.

### 1d — Carry rule through degradation `[vetted by prototype]`

```python
t = Number(5, second)

(new * t) / t
# → 3.0 Sv [⊤_specific_energy] {weighting_standard: icrp103}
```

No formula matches `dose_equivalent × time`, so kind degrades to ⊤. The family root's
`carry` policy keeps the aspect; the warrant records it landed outside
`applies_to`. **Round trip preserves the qualification** — the alternative
(drop) destroyed it through an identity operation.

### 1e — Refusal survives degradation `[vetted by prototype]`

```python
p_old = old * t     # [⊤_specific_energy·time] {icrp60}
p_new = new * t     # [⊤_specific_energy·time] {icrp103}

p_old + p_new
```

```
Refused: category 7
  both kinds are ⊤_specific_energy·time — kind cannot distinguish them
  aspect family 'radsafe:weighting_standard': icrp60 vs icrp103
```

This is the property that makes aspects load-bearing: kind enforcement goes
blind at ⊤, and aspect enforcement does not.

### 1f — `applies_to` refuses at attachment `[ruled]`

```python
Number(1.5, gray, kind="radsafe:absorbed_dose",
       aspects=["radsafe:icrp103"])
```

```
Refused: aspect family 'radsafe:weighting_standard' does not apply to kind
  'radsafe:absorbed_dose' (applies_to = ['radsafe:dose_equivalent', ...])
```

Absorbed dose is the *input* to weighting. Claiming a weighting standard on it
asserts something false, and the error fires when the claim is made.

---

## Case 2 — Temperature: the chart stratum

The one stratum that refuses on **identical** operands.

### 2a — The shipped defect `[live]`

```python
Number(5, celsius).to(fahrenheit)     # 41.0 — correct for a temperature
```

A 5 °C *difference* is 9 °F. Today there is no way to express it.

### 2b — Displacement is derived, never declared `[vetted]`

```python
t1 = Number(20, celsius)          # point
t2 = Number(5,  celsius)          # point

d = t1 - t2                       # displacement — the only producer
d.displacement                    # True
d.to(fahrenheit)                  # 27.0  (15 × 1.8, no offset)
d.to(kelvin)                      # 15.0

t2.to(fahrenheit)                 # 41.0  (point: 5 × 1.8 + 32)
```

Mechanism `[vetted]`: `_displacement` is `init=False` on a frozen dataclass,
written by exactly one seam in `__sub__`. `Number(1, C, _displacement=True)`
raises `TypeError`; `dataclasses.replace` rejects it; `setattr` raises
`FrozenInstanceError`.

### 2c — Point + point refuses `[ruled]`

```python
t1 + t2
```

```
Refused: category 3 (chart, operation ill-formed)
  20 °C + 5 °C — two points on an interval chart do not sum
  remedy: subtract a reference to obtain a displacement, or use kelvin
```

### 2d — Scalar × point refuses `[vetted]`

```python
2 * t1
```

```
Refused: category 3
  2 × 20 °C is chart-dependent: 40 °C in celsius, 313.15 °C via kelvin
  remedy: convert to kelvin for thermodynamic scaling
```

Today `[live]` this returns `<40 °C>`.

### 2e — A rise, without a special unit `[ruled]`

```python
rise = Number(5, celsius).as_displacement()     # = 5 °C − 0 °C
t1 + rise                                        # 25 °C, point
t1 + Number(5, kelvin)                           # 25 °C — ratio chart, no ambiguity
```

`.as_displacement()` is origin subtraction. On a ratio chart it's a no-op; on
interval it drops the offset; on logarithmic it drops the reference. One
definition, every chart. No `delta_celsius`.

### 2f — Mean is forced into the correct form `[ruled]`

```python
temps = [Number(20, celsius), Number(22, celsius), Number(24, celsius)]
sum(temps)                        # REFUSE at the first point + point
```

The naive fold refuses. The correct form — `t0 + mean(tᵢ − t0)` — works
because every intermediate is a displacement or a point + displacement.

---

## Case 3 — Navigation: cyclic as a kind property

`degree` stays a ratio unit. Cyclicity is declared on the kind as a modulus and
executed by the chart stratum. `[vetted by prototype]`

### Package

```toml
[[kinds]]
name = "angle"
dimension = "angle"

[[kinds]]
name = "rotation"
dimension = "angle"
parent = "angle"

[[kinds]]
name = "bearing"
dimension = "angle"
parent = "angle"
modulus = "1 revolution"
```

### 3a — The user never says "cyclic"

```python
heading = Number(350, degree, kind="nav:bearing")
turn    = Number(20,  degree, kind="nav:rotation")

heading + turn                    # 10° [bearing]     — wraps
heading + heading                 # REFUSE: point + point
2 * heading                       # REFUSE: scalar × point
2 * turn                          # 40° [rotation]
```

### 3b — Equality and comparison

```python
Number(370, degree, kind="nav:bearing") == Number(10, degree, kind="nav:bearing")   # True  (mod 360)
Number(370, degree)                     == Number(10, degree)                        # False (angle magnitude)

heading < Number(10, degree, kind="nav:bearing")        # REFUSE: no total order on S¹
Number(350, degree) < Number(10, degree)                # False (angle magnitude, ratio)
```

### 3c — Subtraction is unambiguous once the kinds are right

```python
a = Number(359, degree, kind="nav:bearing")
b = Number(1,   degree, kind="nav:bearing")

a - b                             # −2° [rotation]   shortest arc, in (−180°, 180°]
b - a                             # +2° [rotation]
```

The "wrong for accumulation" objection dissolved: accumulation is the
`rotation` kind, which never takes this path.

### 3d — Aggregation refuses correctly

```python
circular_mean([Number(350, degree, kind="nav:bearing"),
               Number(10,  degree, kind="nav:bearing")])
# → 0° [bearing]                  (naive mean would give 180°)

circular_mean([0°, 90°, 180°, 270°])
```

```
Refused: category 3
  resultant magnitude 0.0 < ε — no mean direction exists
```

The evenly-spaced case returned 135° in the first prototype: pure noise from
`atan2(ε, ε)`. Refusing is the only honest answer.

---

## Case 4 — Package composition: merge validation

Two packages, each self-consistent, that compose into an unsound lattice.
`[vetted]`

### Package A — radiation safety

```toml
[[kinds]]
name = "specific_energy"
dimension = "specific_energy"
join_policy = "refuse"

[[kinds]]
name = "absorbed_dose"
parent = "specific_energy"

[[kinds]]
name = "dose_equivalent"
parent = "specific_energy"
```

### Package B — thermodynamics, grafting A's root under a permissive umbrella

```toml
[[kinds]]
name = "energy_per_mass"
dimension = "specific_energy"
join_policy = "lca"

[[kinds]]
name = "specific_enthalpy"
parent = "energy_per_mass"

[[kinds]]
name = "radsafe:specific_energy"
parent = "energy_per_mass"        # ← inversion: refuse under lca
```

### What happens without validation `[vetted]`

```
1 Gy + 1 Sv           → REFUSE
1 Gy + 1 J/kg + 1 Sv  → ADMITTED       ← laundered
```

Adding an unrelated third term makes the forbidden pair legal. Neither package
contains a bug.

### What happens with validation `[ruled]`

```
$ ucon install thermo.ucon.toml
Refused: InvertedPolicy
  'radsafe:specific_energy' (join_policy=refuse) would be grafted under
  'thermo:energy_per_mass' (join_policy=lca)
  A refusal cannot be overridden by a more general context.
```

The check is the invariance theorem's condition — every internal `refuse` node
has a `refuse` parent — evaluated on the *composed* forest at merge time. The
theorem `[vetted, exhaustive]` guarantees that once it passes, every operand
grouping yields the same verdict.

### Why ⊤_d matters here `[vetted]`

Without ⊤_d, two roots over one dimension crash `lca` with `ValueError`. With
it, they meet at ⊤_specific_energy (`refuse`, non-overridable) and produce a
verdict. Setting ⊤_d to `lca` reproduces the laundering exactly — which is why
non-overridability is load-bearing rather than cautious.

---

## Case 5 — Sample basis: aspects outside radiation

A distinction any analytical lab makes, invisible to every existing unit
library. `[ruled]` Same dimension, kind, and unit — a pure aspect distinction, and not a procedural one.

```toml
[[aspects]]
name = "sample_basis"
applies_to = ["mass_fraction"]
multiplication_policy = "carry"
join_policy = "refuse"

[[aspects]]
name   = "dry"
parent = "sample_basis"

[[aspects]]
name   = "wet"
parent = "sample_basis"
```

```python
protein_dry = Number(0.42, dimensionless, kind="ag:mass_fraction",
                     aspects=["ag:dry"])
protein_wet = Number(0.35, dimensionless, kind="ag:mass_fraction",
                     aspects=["ag:wet"])

(protein_dry + protein_wet) / 2
```

```
Refused: category 7
  aspect family 'ag:sample_basis': 'dry' and 'wet' are siblings under the root
  (join_policy=refuse)
  remedy: moisture_correction(mass_fraction, moisture_content) -> mass_fraction
```

Same dimension (none), same kind, same unit. The average of a dry-basis and a
wet-basis fraction is not a fraction of anything.

---

## Case 6 — `explain()`: the warrant on an admitted operation

```python
result, warrant = ucon.explain(
    Number(1500, meter) + Number(0.5, kilometer))
```

```
verdict     ADMIT
result      2000 m
strata
  dimension   length == length
  chart       ratio + ratio; no offset
  kind        None + None → None
  aspect      none
coercion
  left        ×1.0        (meter)
  right       ×1000.0     (kilometer → meter, via BaseForm)
  fma         1500·1.0 + 0.5·1000.0
path        kilometer → meter (1 edge, prefix)
```

Same four checks, run with a recorder attached. Nothing on the hot path
changes; the trail is produced only when asked for.

---

## Case 7 — Unspecified vs unrelated: `None` and ⊤_d

Two ways for a number to have no specific kind. They look alike and must
behave differently. `[vetted]` — join rule exhaustively confirmed; the
contrast is the design.

### Package

```toml
[[aspects]]
name = "coverage"
applies_to = ["*"]                # kind-independent
join_policy = "refuse"

[[aspects]]
name   = "k1"
parent = "coverage"

[[aspects]]
name   = "k2"
parent = "coverage"
```

### 7a — Unkinded, with an aspect: `None`

```python
plain  = Number(5.0, meter, uncertainty=0.1, aspects=["metrology:k2"])
height = Number(3.0, meter, uncertainty=0.1, kind="geo:height", aspects=["metrology:k2"])

plain + height           # permissive
# → 8.0 ± 0.14 m [height] {k2}
```

`plain` has no kind — the user didn't say. The kind slot is `None`, governed by
the **partial** policy. Permissive inherits `height`; the aspect carries
because both agree.

Under strict:

```
Refused: category 6 (kind, partial + strict)
  5.0 m [unspecified] + 3.0 m [height] — one operand has no declared kind
```

The refusal is for the honest reason: one side hasn't said what it is.

### 7b — Two coverages disagree

```python
Number(5.0, meter, uncertainty=0.1, aspects=["metrology:k1"]) + height
```

```
Refused: category 7 (aspect)
  aspect family 'metrology:coverage': 'k1' and 'k2' are siblings under the
  root (join_policy=refuse)
```

Neither number's kind matters. The aspect layer refuses on its own.

### 7c — ⊤_d as an operand

```python
product = Number(2.0, gray, kind="radsafe:absorbed_dose") * Number(5.0, second)
# no formula for absorbed_dose × time
# → 10.0 Gy·s [⊤_specific_energy·time]

product + Number(1.0, gray * second, kind="radsafe:some_dose_time_kind")
```

```
Refused: category 5 (kind, LCA policy)
  ⊤_specific_energy·time is the top of its fiber (join_policy=refuse,
  non-overridable)
```

**This is not a bug.** The product's ⊤ was *earned*: an operation with no
declared kind produced it, and it must not acquire a neighbor's label on the
next addition. That is the Gy/Sv laundering closed at the multiplicative
boundary.

### 7d — The contrast

| | `None` | ⊤_d |
|---|---|---|
| means | *unspecified* — nobody said | *provably not any declared kind* |
| produced by | omitting `kind` | `×` with no formula; two unrelated kinds meeting |
| `+ specific kind` | partial policy — permissive inherits, strict refuses | **refuse**, always |
| hosts kind-independent aspects | ✓ | ✗ — would render a coverage annotation un-addable |

Two rules that would have blurred this line were proposed and tested: treating
ancestor⊔descendant as partial (inherit the specific) and as ancestor-with-
policy-skipped. Across 344 sound lattices they preserved grouping invariance
in 284 and 36 cases respectively. The current rule preserves it in all 344.

---

## Case 8 — Ordinal: Mohs hardness

Order without arithmetic. Declared on the kind, executed by the chart stratum
— the mirror of cyclic. `[vetted by prototype]`

```toml
[[kinds]]
name = "mohs_hardness"
dimension = "none"
ordinal = true
```

```python
talc, quartz, diamond = (Number(n, one, kind="mineral:mohs_hardness") for n in (1, 7, 10))

talc < quartz              # True
max(talc, diamond, quartz) # 10 [mohs_hardness]
sorted([diamond, talc])    # [1, 10]

diamond - quartz
```

```
Refused: category 3 (chart, operation ill-formed)
  ordinal: − undefined. Mohs 10−9 spans ≈1100 absolute-hardness units;
  Mohs 2−1 spans ≈2. Equal steps, 550× different gaps.
```

```python
2 * talc                   # REFUSE — 10 is not twice 5
talc + quartz              # REFUSE
```

The giveaway for an ordinal: the numerals could be replaced with letters and
nothing would be lost.

**Joins with non-ordinal kinds refuse** (item 7, ruled). `mohs ⊔ vickers` does
not resolve to `hardness` — a rank and a measurement have no common ground the
lattice can vouch for. The Mohs→Vickers correlation bridge was designed and
deferred: a smooth fit would imply Mohs 7.5 means something.

---

## What the cases demonstrate, by stratum

| stratum | case | the thing no other stratum could do |
|---|---|---|
| chart | 2, 3, 8 | refuse **identical** operands (`20 °C + 5 °C`, `bearing + bearing`); refuse `−` on ranks |
| kind | 1a, 4, 7 | refuse same-dimension different-sort (`Gy + Sv`); distinguish *unspecified* from *unrelated* |
| aspect | 1b, 1e, 5, 7 | refuse same-kind different-aspect; **survive kind degradation**; attach without a kind |
| merge validator | 4 | refuse a composition neither input would refuse alone |

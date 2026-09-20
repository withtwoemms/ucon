# 012 — What "dimensionless" means

**Status:** Proposed (2026-09-20)
**Supersedes:** [`005-pseudo-dimension-tuple-values.md`](005-pseudo-dimension-tuple-values.md) on retirement
**Context:** v3.0.0 retires pseudo-dimensions. The roadmap says only that
"degree et al. become first-class", and that phrase admits two readings with
opposite consequences. Three open issues are symptoms of the gap, and
[`011-currency-kinds-and-contexts.md`](011-currency-kinds-and-contexts.md)
chose "dimensionless" for currency before those consequences were known.

## The decision required

**Does a named dimensionless unit remain a distinguishable symbol in the unit
algebra, or is it unity?**

Everything below follows from that one answer. This ADR states the evidence
and costs both readings; it does not yet pick one.

## Why the question is open

ADR 005 gave `angle`, `ratio`, `count`, and `solid_angle` the **zero vector**
so they stay multiplicatively transparent (`angle × length = length`), plus a
tag so they remain semantically distinct and `radian(1).to(percent)` refuses.
The tuple encoding exists only to stop Python's `Enum` from aliasing members
that share a value.

Retirement removes the tag. What replaces it was never specified.

## Evidence

All verified against `main` at `a26bb4a`.

**`Dimension(none)` factors are dropped at construction** — not at
multiplication, and not merely in display ([#318](https://github.com/withtwoemms/ucon/issues/318)):

```python
>>> usd = Unit(name="USD", dimension=NONE)
>>> UnitProduct({UnitFactor(usd, Scale.one): 1.0,
...              UnitFactor(hour, Scale.one): -1.0}).factors
{UnitFactor(hour, Scale.one): -1.0}          # USD absent
```

Pseudo-dimensions survive the same construction. So the two leading
candidates for "dimensionless" have **opposite algebraic behaviour**:

| `USD` declared with | product | factor kept |
|---|---|---|
| `Dimension(none)` | `<UnitProduct 1/h>` | no |
| `Dimension(ratio)` | `<UnitProduct USD/h>` | yes |

**There is no canonical unity.** `parse_unit("1")` resolves to `<Unit frac>`
at `Dimension(ratio)`, which is why the shipped `radiation_weighting`
formula cannot consume it ([#307](https://github.com/withtwoemms/ucon/issues/307)).

**Pseudo-dimensional units cannot normalize**, so comparison and additive
arithmetic refuse across them ([#313](https://github.com/withtwoemms/ucon/issues/313)):
`180 deg == π rad` was `False` before 2.2.2 and raises after. `BaseForm`
cannot express the relation — its contract admits only canonical SI base
units, and angle has no SI expansion.

## Three groups, not one

"Dimensionless" currently bundles families with incompatible needs. Today's
`Dimension(ratio)` holds members of the first and third rows simultaneously.

| group | members | relation between members | resolved by |
|---|---|---|---|
| **exact factor** | `percent`, `ppm`, `fraction`; `degree`, `radian`, `gradian`, `turn`; `steradian`, `square_degree` | exact multiplicative (π/180, 0.01, 1e-6) | a scale relation — see *Option A* |
| **no relation** | apples vs oranges; distinct things tallied | none exists | `⊤_d` at the kind stratum ([009 §5](009-turnstile.md#5-kind)) |
| **non-multiplicative** | `decibel`, `neper`, `bel` | logarithmic | the chart stratum ([010](010-chart-nomenclature.md)) |

Only the first row is this ADR's subject. The second and third already have
owners, and conflating them is what makes "dimensionless" feel intractable.

Note `dozen → each` belongs in the first row while `apples → oranges`
belongs in the second, though both would live in `Dimension(count)` — the
split is orthogonal to dimension.

## Option A — dimensionless with kinds

A dimensionless unit is **unity** in the unit algebra. Semantic distinction
moves to the kind stratum via `default_kind`. ADR 011 already names this
pattern and its example: *"`default_kind` is machinery the pseudo-dimension
retirement already specifies (`bit` with `default_kind = "information"`)."*

`Dimension(none)` becomes the only dimensionless dimension. Dropping its
factors is then **correct**, and #318 is resolved by redefinition rather
than by a fix: `rad/s` reducing to `1/s` with the kind carrying
`angular_velocity` is dimensionally honest.

**Requires the within-dimension canonical scale.** With every member at
`Dimension(none)` and no `base_form` available, nothing relates `degree` to
`radian` algebraically. The first row above needs a declared reference unit
per family (`radian`, `fraction`, `steradian`) plus a factor per member —
a new faculty, distinct from `base_form` because the reference need not be
SI-basic.

**Consequences**

- `#307` dissolves: one dimensionless dimension, one answer for `"1"`.
- `#313`'s angle third is fixed by the new faculty, not by `base_form`.
- `#318` is intended behaviour, closed as such.
- A money-rate is a **kind**, not a unit. Verified constructible today:
  `<0.12 1/(kW·h) [energy_price]>`, with `energy × energy_price → cost` as a
  `KindFormula` — the `H = D · w_R` pattern ADR 011 reserves for
  formula-shaped money operations.
- Legibility cost: a price displays as `1/(kW·h)` with the money only in the
  kind. `USD/kWh` is never a unit.

## Option B — promote to basis dimensions

`angle`, `ratio`, `count`, and `solid_angle` become real dimensions with
canonical base units. This is the more literal reading of "first-class".

**Consequences**

- `#313`'s angle third is fixed for free: `radian` becomes a canonical base
  unit and `degree` takes an ordinary `BaseForm(prefactor=π/180)`. No new
  faculty.
- `#318` becomes a genuine bug — a named dimensionless unit is a symbol
  products must preserve — and `USD/kWh` becomes expressible as a unit.
- A money-rate is a **unit**, so tariffs are unit algebra rather than
  `KindFormula`s.
- **But currency still cannot be promoted.** ADR 011 rejected
  currency-as-a-basis-dimension on two grounds that this option does not
  touch: algebraic stability (`currency²` is meaningless — the criterion
  that retired INFORMATION) and FX cycles that do not close. So currency
  remains dimensionless under Option B too, and needs #318 reversed to
  express rates.
- Reopens ADR 005's original problem for whichever members stay
  dimensionless.

## Consequences for #292

Currency's dimension is the first thing [#292](https://github.com/withtwoemms/ucon/issues/292)
must decide, and every other piece inherits it — the `currency ▸ {usd, eur}`
lattice (a kind's dimension must match its unit's), the rate contexts, and
the `default_kind` arrival rule ([#305](https://github.com/withtwoemms/ucon/issues/305)).

| | Option A | Option B |
|---|---|---|
| `USD/kWh` is a… | kind | unit |
| tariffs are… | `KindFormula`s | unit algebra |
| `#317`'s product path needed for prices | no | no |
| currency shippable in 2.x | yes, on the final shape | only on a pseudo-dimension, then migrate |

FX is unaffected either way: currency-to-currency is same-dimension, and
plain, composite, and scaled endpoints all convert today.

The third option — ship currency on a pseudo-dimension now — is available
but buys a migration, since the dimension it depends on is scheduled for
removal in the same major that would define its replacement.

## Open

- Which option.
- If A: where the canonical scale is declared (unit field, family table, or
  TOML section), and whether `⊤_d` interacts with it.
- Whether `Dimension(count)` members are first-row, second-row, or both
  (`dozen → each` is a factor; `apples → oranges` is not).
- Whether ADR 005 is superseded or merely narrowed — the tuple encoding may
  still be needed for whichever members remain dimensionless under B.

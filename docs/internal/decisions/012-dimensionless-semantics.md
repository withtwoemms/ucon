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

## Option C — resolve per family

The families do not agree on what promotion would even mean, which suggests
the retirement may not have one global answer.

**Pseudo-dimension tags do not compose today.** Both are idempotent, because
the zero vector times any exponent is still the zero vector and the tag is
carried through unchanged:

```python
>>> UnitProduct({UnitFactor(radian, Scale.one): 2.0}).dimension
Dimension(angle)                  # mathematically this is solid_angle
>>> UnitProduct({UnitFactor(each, Scale.one): 2.0}).dimension
Dimension(count)                  # nothing this could be
```

Under Option B those two need different answers. `radian²` **is** steradian,
so promoting angle requires making exponentiation compose across the
angle/solid_angle pair — real work, but with a correct target. `each²` has no
target at all, and `count²` fails the same algebraic-stability criterion that
retired INFORMATION as a basis dimension and that [011](011-currency-kinds-and-contexts.md)
used to reject currency-as-a-dimension.

So Option B may be right for `angle` and `solid_angle` and wrong for `count`
and `ratio` — promotion for the families whose exponents mean something,
Option A for the families whose exponents do not.

**Consequences**

- Neither #318 nor #313 gets a single answer; each resolves per family.
- The exact-factor faculty is still needed, but only for the families that
  stay dimensionless.
- Costs a uniform mental model, which is the main argument against.

## Money as `Dimension(count)`

Raised as a candidate for currency, and it is the strongest of the
pseudo-dimension options.

**It works today.** `count` survives product construction, so the unit that
Option A cannot express is expressible:

```python
>>> usd = Unit(name="USD", dimension=COUNT)
>>> UnitProduct({UnitFactor(usd, Scale.one): 1.0,
...              UnitFactor(watt, Scale.kilo): -1.0,
...              UnitFactor(hour, Scale.one): -1.0})
<UnitProduct USD/(kW·h)>
>>> Number(0.005, usd)
<0.005 USD>                       # no integrality constraint, so divisibility is fine
```

**It matches what 011 already says.** 011 states that *"currency-plus-tally
refuses as disjoint roots (`DisjointKinds`)"* — a **kind**-stratum refusal,
which presupposes that currency and tally are dimension-compatible. Putting
money in `count` makes that explicit rather than changing it. The
apples-to-oranges structure carries over exactly: counting dollars against
counting euros is the same shape as counting apples against oranges — one
dimension, disjoint kind roots, no conversion without a license.

**And the algebra agrees.** `currency²` and `count²` are meaningless by the
same criterion, so 011's rejection of currency-as-a-basis-dimension applies
verbatim to `count`. That is an argument for grouping them, and — under
Option C — an argument that neither should be promoted.

**What it does not do is escape this ADR.** `count` is a pseudo-dimension, so
choosing it binds currency's fate to whatever happens to `count`:

| retirement outcome for `count` | consequence for money-as-count |
|---|---|
| Option A (dimensionless with kinds) | currency collapses to `Dimension(none)` and rates become inexpressible again — the migration this choice was meant to avoid |
| Option B (promoted) | currency becomes a basis dimension by the back door, which 011 rejects on its merits |
| Option C (per family: `count` stays dimensionless) | same as Option A for currency |

So money-as-count is viable *now* and unstable *later* under every branch
except one that has not been proposed: `count` promoted while currency is
excluded from it, which would require currency to have its own dimension
after all.

The useful conclusion is narrower than a decision: money-as-count is the
right answer **if** currency ships before the retirement, and it makes the
retirement's treatment of `count` a currency-facing decision rather than an
internal one.

## Count rates, and a sequencing hazard

A countable divided by another unit should read as a rate. It does — at the
unit level — because a pseudo-dimension survives product construction:

```python
>>> each / second      -> <UnitProduct ea/s>        dim = Dimension(frequency)
>>> USD / hour         -> <UnitProduct USD/h>       dim = Dimension(frequency)
>>> USD / kWh          -> <UnitProduct USD/(kW·h)>  dim = Dimension(derived(time^2/length^2*mass))
```

**But the dimension collapses.** `ea/s` and `USD/h` both report
`Dimension(frequency)` — the same dimension as `hertz` and as `1/s`. The
countable-ness lives in the unit symbol; the dimension forgets it. So
dimensionally a throughput *is* a frequency and a burn rate *is* a frequency.

That is defensible, and the type safety belongs one stratum up:

```python
>>> Number(5, 1/s, kind=throughput) + Number(3, Hz, kind=cycle_rate)
DisjointKinds
```

Same dimension, disjoint kind roots, refused at stratum 3 — the same shape as
`absorbed_dose` against `dose_equivalent`. Wanting count-rates to refuse
*dimensionally* would require promoting `count`, which the INFORMATION
precedent forbids on the same grounds (`bit/second` is meaningful, `bit²` is
not, and it was retired anyway).

So: count-rates read cleanly, are dimensionally honest, and are discriminated
by kinds. No promotion required.

### The hazard

Today `ea/s + Hz` refuses — but for the **wrong reason**:

```python
>>> Number(5, each/second, kind=throughput) + Number(3, Hz, kind=cycle_rate)
UnitsNotNormalizable
```

That is the 2.2.2 scale check firing because `each` has no `base_form`, not a
kind-stratum verdict. The exact-factor faculty would give `each` a canonical
scale and **remove** this refusal, at which point only a populated kind
lattice keeps the operation refused.

`Dimension(count)` ships **seven** units — `each`, `flop`, `op`,
`instruction`, `cycle`, `request`, `event` — and **no** count kinds. So the
exposure is not one obscure unit but the whole throughput family: `flop/s`,
`request/s`, `event/s`, `instruction/s`, `cycle/s`.

Implementing the faculty before populating the count kind lattice converts a
refusal into a **silent admission**: `flop/s + Hz` would start returning a
number. The faculty and the kinds have to land together, and that ordering is
a consequence of this ADR rather than of either work item.

`cycle/s` is the instructive member. It arguably *is* hertz, so a reader may
well want that one to succeed while `flop/s + Hz` refuses — which is a kind
question, not a unit one, and cannot be answered by a canonical scale at all.

### What shipping money-as-count would do to the retirement

Delivering currency on `Dimension(count)` before v3.0.0 is viable and has a
real benefit — a consumer informs a design, which is the argument for not
landing infrastructure ahead of its use. But it is worth separating that
benefit from its cost, because they attach to different acts.

**The cost is constraint, not migration.** Today `count` carries seven
internal units and no kinds, so the retirement may treat it on the merits.
After currency ships it carries every currency unit, a currency kind lattice,
and — via [#282](https://github.com/withtwoemms/ucon/issues/282)'s
`[[contexts]]` packages — third-party FX rate tables with
`dimension = "count"` written into their TOML. At that point the retirement's
treatment of `count` is decided under currency-compatibility pressure rather
than on what "dimensionless" ought to mean. A general decision distorted by
one application is the failure mode this ADR exists to prevent.

**And no branch is kind to it.** Per the table above, `count` staying
dimensionless collapses currency into `Dimension(none)` and un-expresses
`USD/kWh`; `count` being promoted makes currency a basis dimension, which
011 rejected on its merits. Currency would ship in v2.4.0 and migrate in
v3.0.0 — one minor apart.

**The benefit comes from building, not releasing.** A currency prototype on
`count` supplies exactly the evidence this ADR lacks: whether rate units are
legible, whether the kind lattice carries cross-currency refusal cleanly,
whether FX contexts compose as expected. None of that requires a tag. An
in-flight consumer informs the decision; a released one constrains it.

So the recommendation is narrow: **prototype currency against `count`, use it
as evidence here, and do not release it until this ADR is resolved.**

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

- Which option, and whether it resolves globally or per family.
- If A: where the canonical scale is declared (unit field, family table, or
  TOML section), and whether `⊤_d` interacts with it.
- Whether `Dimension(count)` members are first-row, second-row, or both
  (`dozen → each` is a factor; `apples → oranges` is not).
- Whether currency ships as `Dimension(count)` before the retirement,
  accepting the migration that every branch except one implies.
- Sequencing: the exact-factor faculty must not land before the count kind
  lattice, or `ea/s + Hz` silently admits.
- Whether ADR 005 is superseded or merely narrowed — the tuple encoding may
  still be needed for whichever members remain dimensionless under B.

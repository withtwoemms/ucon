# 013 — The vector is the only carrier

**Status:** Proposed (2026-10-15); corrections from a five-perspective adversarial review incorporated 2026-10-17
**Supersedes:** [`005-pseudo-dimension-tuple-values.md`](005-pseudo-dimension-tuple-values.md) in full;
[`011-currency-kinds-and-contexts.md`](011-currency-kinds-and-contexts.md) in full (its context and
arrival machinery is re-adopted in [§5](#5-re-adopted-from-011));
[`012-dimensionless-semantics.md`](012-dimensionless-semantics.md) by resolution — it posed the question
and declined to answer it.
**Supplies:** the "3.0.0 pseudo-dimension retirement" prerequisite that
[`009-turnstile.md`](009-turnstile.md) names and leaves unspecified. 009's ⊤_d multiplication rule is
narrowed as a consequence ([§4](#4-kinds-compose)); nothing else in 009 changes.
**Context:** v3.0.0 lists *pseudo-dimension retirement* with no content behind it. ADR 012 says so
directly: *"Retirement removes the tag. What replaces it was never specified."* Every proposal since —
currency on `Dimension(count)`, tags that compose, angle promotion — has patched one symptom while
leaving the mechanism standing. This ADR names the mechanism and replaces it.

## The decision

**Dimensional identity lives in the basis vector, and nowhere else.**

A label that cannot compose under `×`, `÷`, and `**` is not a dimension. It either joins the vector as
a basis component, or it leaves the dimension stratum for the stratum whose algebra it actually has:
`Scale` for exact radix factors, the kind stratum for semantic refinement, a transform stratum for
non-multiplicative quantities.

Pseudo-dimension tags are retired by **absorption or dissolution — never by deletion to `none`**.

## 1. The criterion

ADR 011 rejected currency-as-a-dimension because `currency²` is meaningless, and called this *"the
algebraic-stability criterion that retired INFORMATION as a basis dimension."* Both halves fail
against the shipped basis.

All evidence below verified against `main` at `4d34b85`.

```python
>>> for u in (meter, second, kilogram, ampere, kelvin, candela, mole, bit):
...     UnitProduct({UnitFactor(u, Scale.one): 2.0}).dimension
Dimension(area)                                   # the only named square
Dimension(derived(time^2))
Dimension(derived(mass^2))
Dimension(derived(current^2))
Dimension(derived(temperature^2))
Dimension(derived(luminous_intensity^2))
Dimension(derived(amount_of_substance^2))
Dimension(derived(information^2))
```

Seven of eight basis components have **unnamed** squares — not meaningless ones: `kg²` is in G,
`A²` in Ω, `s²` in acceleration, `mol²` in second-order rate constants. Meaning-closure, applied as a
membership test, would leave SI with `length` and nothing else; it was never the test. ISO 80000-1
§3.6 defines a base quantity by independence, and the SI Brochure (§1.3) records the choice of base
quantities as conventional. And `information` is still an SI basis component — the retirement 011
cites as precedent did not happen.

**The criterion that does govern basis membership:**

1. **Independence** — the generator cannot be written as a product of powers of the others.
2. **A total, truthful algebra** — every product and power is a legal element. Legal is not
   instantiated: `mass²` is legal, unnamed, and carries no units. That is the normal state.

A corollary separates the two mechanisms ucon has today. Under a tag, `USD × USD` returns
`Dimension(currency)` and `rad × rad` returns `Dimension(angle)` — the algebra asserts that squared
money is money and that two radians make an angle. Both are **false**. Under a basis component the
same products return `derived(currency^2)` and `derived(angle^2)` — **unnamed, not wrong**. Unnamed
is the standard condition of most of the basis. Wrong is not acceptable anywhere.

## 2. The disposition rule

Every current pseudo-dimension family is placed by four questions, asked in order.

| question | answer → destination | families |
|---|---|---|
| Is it an independent generator whose protection must not depend on configuration? | **basis component** | `currency`, `information` (already there) |
| Is it a power of a small radix on unity? | **`Scale`** | `fraction`, `percent`, `permille`, `basis_point`, `ppm`, `ppb` |
| Is it non-multiplicative? | **transform stratum** (unbuilt) | `bel`, `decibel`, `neper`, `nines`; `celsius` is the same shape |
| Is it a family of quantities of dimension one with special-name units? | **kinds on unity** — exact factors on ordinary graph edges | `plane_angle`, `solid_angle`; `count` (`each`, `request`, … as units on unity with `default_kind`) |

### Angle stays dimensionless — SI is right

A radian is *defined* as arc length over radius: `θ = s/r`, both lengths. Angle is derivable from
length and therefore **fails independence**. It is not a basis component, and the behaviours a
promotion was supposed to fix are correct physics:

```python
>>> radn = Unit(name="radn", dimension=NONE)
>>> UnitProduct({UnitFactor(meter, one): 1.0, UnitFactor(radn, one): 1.0})
<UnitProduct m>                        Dimension(length)      # arc length IS a length
>>> UnitProduct({UnitFactor(radn, one): 1.0, UnitFactor(second, one): -1.0})
<UnitProduct 1/s>                      Dimension(frequency)   # angular velocity IS T⁻¹
```

The dimensions are right; only the **symbol** is lost — that is [#318](https://github.com/withtwoemms/ucon/issues/318),
not a dimension question. The one genuine defect today is the tag lying: `rad² → Dimension(angle)`,
which is neither `solid_angle` nor dimensionless. Angular-velocity-versus-frequency is a **kind**
distinction, by construction.

The family needs an identity carrier once the tag is gone — something that refuses `rad → sr` and
`rad → %`. That carrier is a **kind**, not a dimension (ISO 80000-3 3-5/3-6; VIM 1.2 Note 2:
quantities of the same dimension are not necessarily of the same kind): `plane_angle` and
`solid_angle` on unity, every angle unit declaring `default_kind`, `degree → radian` an ordinary
graph edge. No separate exact-factor faculty is needed.

The cost of angle-dimensionless *without* symbol retention and kinds is already live in the catalog:
`lumen.base_form` dropped `sr` because it was transparent, so `1 lm → 1 cd` converts,
`cd·sr → lm` refuses, and `1 cd/m² + 1 lx` admits — four ISO 80000-7 quantities collapsed to two.
All eight angle units have `base_form = None` today.

### Count and currency are both independent; the ground for treating them differently is pragmatic

`5 requests` and `$5.37` are equally independent of L, M, T — neither is derivable from the others,
so the independence test does not separate them. The SI places number of entities at dimension one
**by convention** (SI Brochure §2.3.3; VIM 1.7 Note 3), not by derivation. The reason this ADR
treats them differently is where each family's protection has to live: a price's whole use is in
products (`USD/MWh`), and it must be guarded with no kind lattice installed, so currency takes a
basis component. A count's symbols are kept via `default_kind` on units on unity; its rates are
guarded by the normalizability check (count units have no `base_form`) until kinds compose (§4),
and by derived kinds after. So `count` is a kind on unity. Promotion was considered and declined
(§7).

### `ratio` is three families, not one

```python
>>> Number(1.0, percent).to(fraction)      # 10⁻²      LINEAR  — radix powers
<0.01 frac>
>>> Number(1.0, ppb).to(fraction)          # 10⁻⁹
<1e-09 frac>
>>> Number(10.0, decibel).to(fraction)     # 10^(x/10) LOGARITHMIC
<10.0 frac>
>>> Number(10.0, neper).to(fraction)       # eˣ
<22026.465794806703 frac>
>>> Number(3.0, nines).to(fraction)        # 1 − 10⁻ⁿ  TRANSFORMED
<0.999 frac>
```

`Scale` is already multi-radix — 21 members, 6 at base 2 and 15 at base 10, shaped `base^exponent`.
The linear ratios are `Scale` values that were filed as units (`basis_point` is 10⁻⁴; `Scale` runs
−15…15 and skips −4, so one member is added). The cost of the misfiling is not
cosmetic:

```python
>>> Number(10.0, kg) * Number(50.0, percent)
<500.0 g·%>
>>> _.to(gram)
ConversionNotFound: Base-form signatures differ        # 5 kg is unrecoverable
```

`Dimension(ratio)` is not retired by collapse or promotion. It is **emptied**.

## 3. Retirement, defined

Retirement is a change to where identity lives, not a deletion.

**Absorption** — a family that passes independence becomes a basis component. The mechanism exists
and is declarable today with no schema change: `[bases.X]`, `[transforms.A_TO_B]`, and
`[dimensions.X]` are existing TOML constructs, and a package declaring a nine-component `SI9` with an
8×9 identity embedding loads with `strict=True`.

```python
>>> embed = BasisTransform(SI, SI9, <8×9 identity, currency column zero>)
>>> divide_via(Vector(SI9, currency=1), Vector(SI, energy), graph=g)
Vector(SI9, time=2, length=-2, mass=-1, currency=1)     # existing SI8 vectors unchanged
>>> proj(Vector(SI9, currency=1))                       # SI9 → SI, currency non-zero
LossyProjection: component 'currency' has no representation
>>> proj(Vector(SI9, length=1))                         # SI9 → SI, currency zero
Vector(SI, length=1)                                    # clean; the reverse is safe
>>> resolve(Vector(SI9, (-2,2,1,0,0,0,0,0,1)))
Dimension(derived(length^2*mass*currency/time^2))      # no registry work
```

Full suite with the embedding installed additively: **3356 passed, 3 skipped — identical to
baseline.** **Both** transforms are declared. `LossyProjection` fires only when the dropped component
is non-zero, so the reverse is safe — and necessary: with only the forward transform, anything that
cancels currency is stranded in the extended basis (`(USD/EUR)·m → derived(length) ≠ length`, so
`+ 1 m` refuses at stratum 1 with a false category-1 warrant). Dimension equality must be invariant
under the embedding: `resolve()` returns the canonical `NONE` for any zero vector regardless of
basis, and the standard dimensions are registered under their embedded vectors so lookup returns
the standard object. Sanctioned activation is `dataclasses.replace(system, basis_graph=…)` under
`use()`; a loaded package's basis graph must also reach dimension arithmetic through
`using_conversion_graph` and `UnitSystem.extend`
([#323](https://github.com/withtwoemms/ucon/issues/323)).

**Dissolution** — a family that fails independence leaves the dimension stratum: radix factors to
`Scale`, non-multiplicative quantities to the transform stratum, exact non-radix factors to the
kinds on unity (exact factors on graph edges). These depend on unity being a real unit, which it is not today:

```python
>>> none.name, parse_unit("1")
('', <Unit frac>)                      # unity is unnamed; "1" parses to a DIFFERENT unit on ratio
>>> Number(1.0, percent).to(none)
DimensionMismatch                      # likewise radian, each, bit
>>> u = UnitProduct({UnitFactor(none, Scale.centi): 1.0})
>>> u, u.canonical_scale
(<UnitProduct 1>, 0.01)                # factors=0; the scale is KEPT on canonical_scale …
>>> x = Number(10.0, kg) * Number(50.0, u)
>>> x.quantity, x.canonical_magnitude, x.to(gram)
(500.0, 5.0, <500000.0 g>)             # … and consumed inconsistently: three accessors, two answers
>>> x == Number(5.0, kg), x + Number(5.0, kg)
(True, <505.0 kg>)                     # equal to 5 kg and adds as 500 kg
```

[#318](https://github.com/withtwoemms/ucon/issues/318) is therefore an **inconsistency between
accessors**, not symbol loss: `UnitProduct` already absorbs the scale (Step 2 of construction);
`Number.__mul__` ignores it, `_canonical_magnitude` and the scale-only `.to()` read it, and
`UnitProduct.__eq__` ignores it. The fix is an invariant — *a `Number` never holds a unit with
`canonical_scale ≠ 1`* — folded at the `Number` boundary, with `canonical_scale` entering
`UnitProduct` identity. Together with [#307](https://github.com/withtwoemms/ucon/issues/307) it
gates every dissolution. Reachability today is two catalog units (`none` and
`radiation_weighting_factor`); the mechanism is wrong regardless.

**The fold rule.** An *anonymous* scaled unity (`centi·one`) folds into the magnitude when it meets
any other factor and persists — rendering as `%` — when alone. A *named* unit of dimension one
(`rad`, `request`) and a *dimensionless compound* (`mg/kg`) persist as factors with zero vector
contribution; this is the SI's own safety mechanism for dimension-one units (symbol retention,
SI Brochure §2.3.4), and it is what lets a compound carry the kinds its factors declare (§4). The
persisting scaled factor carries an exact `Exponent`, not a `Scale` member — `Scale.__mul__`
snaps to the nearest member today (`centi × centi → milli`).

**Why tags cannot be kept and made to compose.** Transparency and erasure are the same line:

```python
# ucon/dimension.py — Dimension.__mul__ / __truediv__
elif self.is_pseudo:
    result = other                                   # ANGLE * MASS = MASS   (also: USD*kW = kW)
elif self.is_pseudo:
    result = resolve(divide_via(self.vector, ...))   # zero vector in: tag never reaches the result
```

```python
>>> for u in (radian, each, steradian):
...     UnitProduct({UnitFactor(u, one): 1.0, UnitFactor(second, one): -1.0}).dimension
Dimension(frequency)   Dimension(frequency)   Dimension(frequency)     # erased in mixed products
>>> UnitProduct({UnitFactor(radian, one): 2.0}).dimension
Dimension(angle)                                                       # idempotent under **
```

A tag is a dimension that has identity and no algebra. [#321](https://github.com/withtwoemms/ucon/issues/321)
asks for the algebra to be added; this ADR removes the tag instead. 321 closes without a fix.

### The discriminating case

```
                     tag `currency`                   basis component
USD/J  vs  1/J       same dimension                   distinct
refusal of their sum UnitsNotNormalizable (2.2.2)     TypeError (stratum 1)
```

Under a tag, every cross-family refusal a price enjoys today comes from the 2.2.2 scale check
firing on a missing `base_form` — an accident of the chart stratum doing stratum 1's job. The
inventory of refusals currently owed to that accident splits in two. Three must be **re-owned**
before the accident is removed: `flop/s + Hz` (kinds; a compound carries its factors' declared
kinds), `100 USD + 50 EUR` and `USD/MWh + EUR/MWh` (the chart stratum, category 2 of ADR 009 §9 —
no conversion path between distinct canonical units; made structural by comparing expanded
base-form *signatures* before rescaling), `USD·kW + W` (dimension, once currency is a component).
Two are **corrected to admits**: `kg·% + kg → 6 kg` and `m·rad + m → 4 m` — arc length plus length
is a length. The normalizability check is retained until each has its owner; anything resting on it
meanwhile is a half measure by construction.

## 4. Kinds compose

A kind is *"a refinement within a dimensional equivalence class"* (`ucon/kinds/types.py`). The
dimension pin is the definition, and it is enforced: a `Kind` declared on `Dimension(currency)` cannot
attach to `USD/MWh`, and there is no wildcard.

```python
>>> Number(100.0, USD, kind=usd)
<100.0 USD [usd]>
>>> Number(48.0, USD_per_MWh, kind=usd)
KindDimensionMismatch
>>> Number(48.0, USD_per_MWh, kind=Kind("k", dimension=None))
KindDimensionMismatch
```

Today, `×` on two kinded operands consults the `FormulaRegistry` through four tiers (EXACT,
COMMUTATIVE, GENERALIZED, DIMENSIONAL); no match is `FormulaNotFound`. One formula ships
(`radiation_weighting`). Every rate shape therefore needs a hand-declared kind *and* a hand-declared
formula per direction:

```python
>>> Number(500.0, MWh, kind=energy) * Number(48.0, USD_per_MWh, kind=usd_per_energy)
<24000.0 USD [usd]>                                   # the one declared formula, both orders
>>> Number(24000.0, USD, kind=usd) / Number(500.0, MWh, kind=energy)
FormulaNotFound                                       # the reverse is not declared
>>> Number(500.0, MWh) * Number(48.0, USD_per_MWh, kind=usd_per_energy)
KindMismatch                                          # unkinded operand, strict
>>> Number(48.0, USD_per_MWh, kind=usd_per_energy) + Number(45.0, EUR_per_MWh, kind=eur_per_energy)
UnitsNotNormalizable                                  # the lattice's JoinRefused is never reached
```

That last line is the finding: even with every declaration made, the kind stratum contributes
nothing to protecting a price. This is the stratum-3 copy of the stratum-1 defect — **identity
without algebra**. Aspects fail the same way (`FormulaNotFound` on `×`). Only the vector composes.

**Decision: kinds compose the way dimensions do.** `Dimension.__mul__` ends in `resolve(vector)`:
return the registered name if there is one, else `derived(…)`. The kind stratum mirrors it.

1. **`DerivedKind`** — a factor-multiset over registered kinds, dimension equal to the product
   dimension (so it passes the attachment check), canonical name (`derived(usd/energy)`), equality by
   structure. Not a member of any lattice, as `derived(…)` dimensions are not in `all_dimensions()`.
2. **A normal form, not a fifth tier.** A formula is a rewrite rule, not a name; applied only to the
   immediate operand pair it is not confluent — `(D × w_R) × t → derived(dose_equivalent·time)` but
   `D × (w_R × t) → derived(absorbed_dose·w_R·time)`, structurally unequal, violating ADR 009 §6/C3.
   The carrier of a derived kind is therefore the fully expanded multiset — every formula output
   replaced by its inputs, to fixpoint; equality is equality of normal forms; the display name is the
   shortest registered abbreviation. That is the true mirror of `resolve()`: the vector is the
   carrier, the name is cosmetic. Load-time validation: output→inputs edges form a DAG
   (termination) and no kind is the output of two formulas with unequal normal forms (confluence).
   `FormulaRegistry.register` must refuse input-tuple collisions rather than keep the first writer.
3. **Cancellation** — when the multiset collapses to one registered kind, return it:
   `derived(usd/energy) × energy → usd`; a factor may cancel an ancestor of opposite sign via
   `is_descendant`. The empty multiset (`E/E`) normalizes to the **identity** `anon(none)` — never
   to ⊤, which would break associativity (`usd × (E/E)` must equal `(usd/E) × E`).
4. **Structural refusal** in `_resolve_add_kind` — derived kinds with different factors refuse
   without consulting the lattice.
5. **An unkinded operand under `×` and `÷` contributes an anonymous factor**, `anon(d)` for its
   dimension `d`: `kinded × unkinded(d) → derived(k · anon(d))`. Treating it as the identity is
   well-typed only when `d` is `none` — `height × 2 s` with result kind `height` fails the attachment
   check, since the kind's dimension no longer matches the unit's. `anon(none)` *is* the identity, so
   `h × 50 %` and `h × 2` keep `height`. `+` keeps strict `KindMismatch` for
   kinds the caller asserted; a kind attached by the unit's `default_kind` is
   a *default* and joins `None` by inheriting it (and is dropped under `×`)
   with no warning (#325) — else `default_kind` on `hertz` would refuse
   `1 Hz + 1 (1/s)`.

**Relation to ADR 009's ⊤_d.** 009 rules: *"`×` with no formula → ⊤_d of the product dimension,
refuse, non-overridable."* Its motivating case is laundering — `dose_rate × time`, unkinded,
inheriting `equivalent_dose` on the next addition. A derived `dose_rate·time` does not launder
either: it is structurally `≠ equivalent_dose` and refuses to join it. Derived kinds meet 009's goal
and keep the information ⊤_d discards. ⊤_d is the **anonymous kind of its fiber**, `anon(d)`: it refuses
against every specific kind under `+` (009's requirement) and is *not* absorbing under `×` (013's).
The two are one mechanism. ⊤_d is currently implemented only for aspects; for kinds this narrowing precedes
any implementation.

**Consequence for `count`.** With derived kinds, `request · time⁻¹` needs no declaration, and the
user-level test passes today with hand-declared kinds on unity:

```python
>>> Number(5.0, none, kind=request) + Number(3.0, none, kind=event)
JoinRefused                                           # apples and oranges, at stratum 3
```

One hole must be closed for this to hold on the common path. `default_kind` is a per-unit
annotation and `UnitProduct` sets it only for a lone surviving factor — "compounds declare nothing" —
so a count-rate built from a *unit expression* (`parse_unit("flop/s")`) carries no kind, and
`Number(5, flop/s) + 3 Hz` would admit once the tag is gone. With the fold rule (§3) the named factor
`flop` persists, so the compound has what it needs; the rule becomes: **a compound's kind is derived
from its factors' declared kinds, with `anon(d)` for undeclared factors** —
`flop/s → derived(flop · anon(time⁻¹))`, `USD/MWh → derived(usd · anon(energy⁻¹))`. No new field;
the identity is already in the factors. Until it lands, the normalizability check guards count rates
(count units have no `base_form`) and is retained through 3.0.0.

So `count` is a kind on unity. Promotion to a basis component was considered after this hole was
found and declined (§7): the compound-kind rule closes it, and a 26-kind lattice is active by
default, so stratum-3 protection is the baseline experience, not an opt-in.

## 5. Re-adopted from 011

Superseding 011 retires its dimension choice, not its machinery. The following stand on their own
and are adopted here by reference to their shipped implementations:

- **Contingent contexts** — `ConversionContext.contingent`; at most one contingent *context* per
  derivation; two dated tables refuse to chain
  ([#320](https://github.com/withtwoemms/ucon/pull/320)).
- **The arrival rule** — `.to()` re-kinds at a `default_kind` unit unless the declared kind is
  already an ancestor of the current kind ([#322](https://github.com/withtwoemms/ucon/pull/322)) —
  **with a refusing clause**: both kinds set, neither an ancestor of the other, and the edge not
  licensed by a contingent context → refuse. As shipped the rule relabels:
  `Number(1, gray, kind=absorbed_dose).to(sievert) → <1.0 Sv [dose_equivalent]>`, a label nothing
  earned. Currency's `usd → eur` under a dated FX table is the licensed case and still re-kinds.
- **Sub-units are `Scale`** — cents are centi-dollars. This is the same move §2 makes for the linear
  ratios. It requires a self-referential `base_form` on every currency unit (the kilogram pattern;
  today `cUSD + USD` refuses because `USD` has none) and the `BaseForm` invariant amended to
  "canonical base units of the unit's own basis" — and, because that removes the accident that
  refuses `USD/MWh + EUR/MWh` today, it ships together with the chart-stratum signature check (§3).
- **Rate tables are contexts, not units** — FX and tariffs remain `ContextEdge`s, now between
  currency-dimensioned endpoints.

The star topology (one contingent table, several edges) and the date-as-aspect discipline for
settlements carry over unchanged.

## 6. Consequences

### Currency

Ships as a basis component (`[bases.SI9]` + `[transforms.SI_TO_SI9]` + `[dimensions.currency]`),
non-breaking, before v3. Every price shape is expressible with an honest dimension and closes
correctly:

```python
USD/MWh  derived(time^2*currency/length^2*mass)      USD/kg   derived(currency/mass)
USD/hour derived(currency/time)                      USD/m²   derived(currency/length^2)
USD/EUR  derived(dimensionless)                      # an fx rate is a pure number; symbol survives
>>> Number(500.0, MWh) * Number(48.0, USD_per_MWh) + Number(1200.0, USD)
<25200.0 USD>
>>> Number(1200.0, USD_per_yr) / Number(20000.0, USD)
<0.06 1/yr>                             Dimension(frequency)   # a yield, with currency cancelled —
                                                               # `+ 3 Hz` would admit; the fx package
                                                               # declares `rate_of_return` under a
                                                               # `frequency(refuse)` root
>>> Number(48.0, USD_per_MWh) + Number(2.0, USD_per_kg)
TypeError                                                      # stratum 1, new
```

`100 USD + 50 EUR` and `USD/MWh + EUR/MWh` are **chart refusals by design** — ADR 009 §9 category 2,
no conversion path between distinct canonical units; FX is a context edge and `+` never consults a
graph. Today they refuse only because `USD` lacks a `base_form`; the structural form is the
signature check (§3), which ships with the currency `base_form`s. Kinds carry same-signature
distinctions only (`revenue` vs `expense`, both `usd`). `USD/each` is dimensionally `USD` until the
compound-kind rule (§4) lands; the per-item/total distinction is then `derived(usd/each)`.

### Issues

| | disposition |
|---|---|
| [#318](https://github.com/withtwoemms/ucon/issues/318) | re-rated: accessor inconsistency — `canonical_scale` kept by `UnitProduct`, consumed by some `Number` paths and not others; fold at the `Number` boundary; first in line with #307 |
| [#307](https://github.com/withtwoemms/ucon/issues/307) | resolved by construction once unity is canonical and parseable as `"1"` |
| [#321](https://github.com/withtwoemms/ucon/issues/321) | closed without fix — tags are retired, not taught to compose |
| [#292](https://github.com/withtwoemms/ucon/issues/292) | re-scoped to currency-as-basis-component; `Dimension(count)` abandoned |
| [#323](https://github.com/withtwoemms/ucon/issues/323) | loaded package basis graph not consulted by dimension arithmetic; `UnitSystem.extend` equally inert |
| new | division dispatches kinds through the *multiplication* formula index — `Gy / w_R → dose_equivalent` in strict mode |
| new | `**` drops the kind and launders — `h[height]**2 + 1 m²` admits |
| new | `lumen.base_form` dropped `sr` — `1 lm → 1 cd` converts; `cd/m² + lx` admits |
| new | `Np ↔ dB` off by 2 against SI Brochure Table 8 (field/power never declared) |
| new | `contingent` has no TOML key — two dated tables shipped as packages chain silently |
| new | `DerivedKind` / Tier 5 / cancellation / identity-under-`×` |
| new | `1 rad + 90 degree` refuses while `180 degree → radian` converts |
| new | `10 dB + 10 dB → 20 dB` is right for cascaded gain and wrong for summed power; unguarded |
| new | the accidental-refusal inventory (§3), to be retired deliberately |

### Roadmap

The v2.4.0 row is rewritten: currency as a basis component, not kinds-plus-contexts on
`Dimension(count)`, with no compatibility caveat needed. v3.0.0's "pseudo-dimension retirement" gains
this ADR as its content. §4 is a design input to v3.1.0's four-stratum dispatch; the *decision*
belongs to v3.0.0 because it decides `count`.

### Deprecations to land in 2.x

Per the deprecation policy, every v3 removal needs its `PendingDeprecationWarning` first:

- `percent`, `permille`, `basis_point`, `ppm`, `ppb`, `fraction` as units → `Scale` on unity.
- `each`, `flop`, `op`, `instruction`, `cycle`, `request`, `event` as units → kinds on unity
  (conditional on §4).
- `bel`, `decibel`, `neper`, `nines` → transform stratum.
- `Dimension.angle`, `.ratio`, `.count`, `.solid_angle` as tagged pseudo-dimensions → retired.

### Sequencing

Ordered by what the UnitSafe benchmark exercises (see `ROADMAP.md`, *The UnitSafe gate*):

1. The KOQ floor (2.3.0): the arrival rule's refusing clause and `default_kind` on every degeneracy
   cluster, including the dimensionless cluster. 27 of UnitSafe's 62 KOQ must-fails convert freely
   today; two more regress at 3.0.0 without this.
2. [#307](https://github.com/withtwoemms/ucon/issues/307) and [#318](https://github.com/withtwoemms/ucon/issues/318) (2.3.1): canonical unity and the fold rule.
3. Array parity, quantity ergonomics, the deprecation ladder (2.4.0–2.7.0).
4. Currency as a basis component (2.6.0) — zero benchmark exposure; may slip.
5. v3.0.0: retire the tags; dissolve `ratio`; `count` as a kind on unity; the normalizability check
   **kept**. v3.1.0: kinds compose; the check retires.

Nothing in 1–4 is unwound by 5.

## 7. Declined alternatives

- **Currency on `Dimension(count)`** (011, 012) — a tag; every cross-family refusal accidental; needs
  unwinding at retirement.
- **Tags that compose** (#321) — adding an algebra to a mechanism that should not exist.
- **Promoting `angle`** — fails independence; "fixes" correct physics; `m·rad ≠ m` would be a false
  physics claim. Rejected on the criterion.
- **Promoting `count`** — independent, so admissible on the criterion; declined because the
  compound-kind rule (§4) closes the only hole that motivated it, the default lattice makes
  stratum-3 protection the baseline, and a tenth slot buys protection for an opt-out configuration
  at the cost of `mg/ea`'s dimension and the fold migration.
- **Forward-only embedding** — strands cancelled results in the extended basis (§3).
- **"Unkinded operand is the kind identity"** — ill-typed unless the operand is dimensionless (§4).
- **A separate exact-factor faculty for angle** — a tag by another name; the family is a kind (§2).
- **Wildcard-dimension kinds** — a kind that refines nothing; breaks the same-dimension lattice
  invariant; fixes attachment, which was never the blocker, and leaves composition untouched.
- **`None` or a per-shape formula as the answer to kinded `×`** — the former launders, the latter is
  combinatorial; ADR 012's *"a money-rate is a kind"* is correct only once kinds compose.
- **Meaning-closure as a basis criterion** — see §1.

## Open

- Whether `fraction` survives as a unit for the bare-ratio case or is `Scale.one` on unity.
- Where the transform stratum lands — it is new capability, not a break, and `celsius` makes it
  overdue independent of this ADR.
- Whether `DerivedKind` canonical names reuse the `derived(…)` renderer.
- Whether `nines` belongs with the logarithmic family or is its own transform.

# 010 — "Chart" as the name of the scale-structure stratum

**Status:** Accepted (2026-09-10); naming unchanged, inference ban corrected and the declared field withdrawn 2026-10-18 — see [§Amendment](#amendment-2026-10-18)
**Context:** A classification of units as `ratio` | `interval` | `logarithmic`
— inert until the v3.1.0 arithmetic dispatch reads it as its second stratum (see
[`009-turnstile.md` §4](009-turnstile.md#4-chart)). The classification, its
error messages, and the stratum itself need one name.

*As written in 2026-09, this said "the v2.2.0 release adds a declared
classification field on `Unit`." No such field shipped in 2.2.0 or since —
`Unit`'s fields are `name`, `dimension`, `aliases`, `base_form`, `scalable`,
`default_kind` — and the Amendment below withdraws it. Nothing in the Decision
depends on the field existing.*

## Decision

The name is **chart**: were there a field it would be `Unit.chart`; the stratum
is the **chart stratum**; the values are **chart classes**. Error messages always
pair the term with the class ("two points on an interval chart do not sum").

*This is a naming decision. It fixes what the stratum and its values are called,
not where the classification is stored — the Amendment settles that, and the
names are unaffected by it.*

## The concept being named

How a unit's numerals map onto the underlying quantity: pure scaling with
a true zero (`ratio`), scaling with a conventional zero (`interval`), log
of a ratio to a reference (`logarithmic`). It is a property of the
*numeral scheme*, not the measurand — cyclic and ordinal structure live on
`Kind` (`modulus`, `ordinal`), per 009.

## Why "chart"

A unit is a coordinate chart on the quantity manifold; conversions are the
transition maps between charts; a `Map`'s algebraic form (Linear / Affine /
Log) *is* the chart classification relative to the canonical ratio chart.
The name buys four things:

1. **It names the mechanism, not just the classification.** Every behavior
   the stratum exhibits is a theorem about coordinate charts:
   many-numerals-one-state; `2 × 20 °C` computing different physical states
   in different charts (hence refusal — the result is an artifact of
   coordinates, not a fact about the quantity); the chart stratum being the
   only one that refuses *identical* operands.
2. **It keeps the ordinal/cyclic split legible.** Stevens' taxonomy mixes
   numeral-scheme categories (ratio, interval) with measurand-space
   categories (ordinal). "Chart" claims only the former; `Kind` owns the
   latter. A Stevens-derived name would promise `ordinal` as a field value
   and then refuse it — a permanent FAQ.
3. **Zero collisions.** `Dimension`, `Basis`, `Scale`, `Kind`, `Aspect`,
   `Map`, `chart` — seven distinct nouns. In particular `Scale` (SI prefix
   magnitude — a linear rescaling *within* ratio charts, i.e. a chart
   automorphism) is already taken for the adjacent knob.
4. **Error messages teach the theory.** "Interval chart" in a refusal
   points at the offset-zero mechanism, not at a taxonomy label.

## Alternatives considered

| Name | Why declined |
|---|---|
| `scale_type` | The measurement-theory term (Stevens; also M-Layer's "scale") — but collides with ucon's `Scale`, and imports the ordinal promise (see #2 above). Strongest rival. |
| `level` / `measurement_level` | Fatally overloaded: ISO 80000 uses *level* specifically for logarithmic quantities (dB **is** "a level"). Naming the umbrella after one member. |
| `scheme` / `numeral_scheme` | Honest but inert — carries no mechanism, teaches nothing. |
| `structure`, `arithmetic` | Too generic. |

Precedent for a naming decision carrying an ADR:
[`004-unit-algebra-naming.md`](004-unit-algebra-naming.md).

## Mitigations for unfamiliarity

- Wherever the stratum is first introduced in user-facing docs, open with the
  bridge sentence: chart class corresponds to Stevens' ratio/interval scale types, extended
  with logarithmic; ucon says "chart" because a unit fixes a coordinate
  chart on the quantity space, and because Stevens' measurand-describing
  categories (ordinal, cyclic-like) live on `Kind`.
- Refusal text always uses the paired form ("logarithmic chart"), so the
  value teaches the term.

## Consequences

- `chart` is **never** inferred from `base_form` (which conflates unrelated
  `None` causes; see the `BaseForm` contract docstring) and **never** from an
  arbitrary edge to a sibling unit (log units relate linearly to their
  siblings). Both bans stand. It *is* read from the **declared edge
  vocabulary**, direction included — see the Amendment below, which replaces
  this bullet's original "from the declared field only … the reference-edge Map
  derivation survives solely as a load/`extend`/merge-time validator."
- The taxonomy is deliberately open (the evidence record lists "chart
  class taxonomy is closed" as unvetted). A fourth class needs no migration
  either way: derivation adds a new edge-map form, a field adds a new value.

## Amendment (2026-10-18)

**The Decision is unchanged.** The field name, the stratum name, the class
names, and the paired error form all stand. What changes is one Consequences
bullet, which contradicted this ADR's own rationale.

### What this ADR already said

"Why chart" states: *"a `Map`'s algebraic form (Linear / Affine / Log) **is**
the chart classification relative to the canonical ratio chart."* The original
Consequences bullet then forbade using that, admitting it only as a validator
against a separately declared field. The document asserted the derivation and
banned it in the same breath.

### Why the ban's two supporting cases fail

[`009-turnstile.md` §4](009-turnstile.md#4-chart) named two `[live]`
misclassifications that "force the declared field over inference". Both were
re-tested against `main`:

- **`dyne`** — "has no direct edge to read" is true (no `_unit_edges` entry; its
  `LinearMap` to `newton` is a cross-basis composition). "Its `base_form is
  None`" is **false**: it is populated, `prefactor=1e-05`, `m·kg·s⁻²`. So both
  `base_form` and any map reading classify `dyne` as `ratio`, correctly. What
  refuses `20 dyn + 1 N` is stratum 1 (`Dimension(cgs_force)` ≠
  `Dimension(force)`), and the operation 009 actually names, `2 × 20 dyn`, does
  not refuse at all (see #340).
- **`decibel`** — "its direct edge is a `LinearMap` to `bel`" is true, and
  reading *that* edge does misclassify it. But `decibel` also carries a declared
  `exp` edge to `fraction`. Reading the **log-bearing edge with its direction**
  classifies it correctly. The case refutes undirected sibling-edge reading, not
  edge reading.

### What the declared edge vocabulary is

Across all 207 declared edges the catalog uses exactly three shapes: bare
`factor` (196, pure scaling), `factor` + `offset` (2, conventional zero — both
`celsius`-sourced), and `map` (9, log/exp/composed). Two computations recover
the classification:

- **coordinate** — a unit's numerals are a logarithm iff it is the source of an
  `exp` edge or the target of a `log` edge. Both conventions ship
  (`decibel → fraction` is `exp`; `fraction → neper` is `log`), and both name
  the log-side unit.
- **origin** — components under pure-scaling edges only. `Dimension(temperature)`
  splits into `{kelvin, rankine}`, `{celsius, reaumur}`, `{fahrenheit}`.

With one exogenous fact — thermodynamic temperature has an absolute zero,
realised by `kelvin` — this classifies all 234 catalog units with zero
disagreements: 222 `ratio`, 3 `interval`, 9 `logarithmic`.

This is not inference from derived structure. It reads the key names the catalog
author wrote, in the place the author already declares. A separate field would
be a second copy of the same information, and the two could disagree — the
failure mode this ADR's `base_form` ban exists to prevent.

### The one thing not derivable, and why it does not need a field

Whether a unit's origin is true or conventional is **undecidable** from
conversion maps. `reaumur ↔ celsius` is strictly linear with both `interval`
(shared freezing zero); `kelvin ↔ rankine` is strictly linear with both `ratio`.
Same observation, different classes — because the pure-scaling group is the
stabilizer of 0 *inside* the affine group, so a linear map lies in both. Rotating
the reference unit through `Dimension(temperature)` flips the derived answers;
only `kelvin` and `rankine` as reference reproduce the census, i.e. exactly the
two units already known to have a true zero.

So each fiber holding a non-ratio unit needs **one** declared fact: which unit
realises the true zero. That is a per-fiber datum (metrology), not a per-unit
field. Today only `Dimension(temperature)` holds such units and `kelvin` supplies
it — harmless by accident of the catalog rather than by construction, which is
why a fiber acquiring a non-ratio unit must declare its origin.

`interval` and `logarithmic` are **relational** classes: an offset from what, a
logarithm of what. Both are meaningless without an edge. A unit with no edges is
necessarily `ratio` — 009 §4 already concedes this ("units with no such edge
default to ratio and are re-validated when an edge arrives"), and the catalog
agrees: 16 units carry no declared edge and none is non-ratio, while all 12
non-ratio units carry at least one. So the declared field has no residual job,
including at `extend` time.

### Still open

Nothing in this ADR. The chart *dispatch* remains 3.1.0 per 009 §4 and §12; the
three bugs the work exposed are #339, #340 and #341; the record of the
withdrawal is
[`../proposals/declared-unit-chart.md`](../proposals/declared-unit-chart.md).

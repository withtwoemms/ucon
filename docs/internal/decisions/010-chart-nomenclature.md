# 010 — "Chart" as the name of the scale-structure stratum

**Status:** Accepted (2026-09-10)
**Context:** The v2.2.0 release adds a declared classification field on
`Unit` (`ratio` | `interval` | `logarithmic`) — inert until the v3.1.0
arithmetic dispatch reads it as its second stratum (see
[`009-turnstile.md` §4](009-turnstile.md#4-chart)). The field, its TOML key, its
error messages, and the stratum itself need one name.

## Decision

The field is **`Unit.chart`**; the stratum is the **chart stratum**; the
values are **chart classes**. Error messages always pair the term with the
class ("two points on an interval chart do not sum").

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

- The field's docstring and 2.2.0 docs open with the bridge sentence:
  chart class corresponds to Stevens' ratio/interval scale types, extended
  with logarithmic; ucon says "chart" because a unit fixes a coordinate
  chart on the quantity space, and because Stevens' measurand-describing
  categories (ordinal, cyclic-like) live on `Kind`.
- Refusal text always uses the paired form ("logarithmic chart"), so the
  value teaches the term.

## Consequences

- `chart` is read from the declared field only — never inferred from
  `base_form` (which conflates unrelated `None` causes; see the `BaseForm`
  contract docstring) and never from an edge to a sibling unit (log units
  relate linearly to their siblings). The reference-edge Map derivation
  survives solely as a load/`extend`/merge-time validator.
- The taxonomy is deliberately open (the evidence record lists "chart
  class taxonomy is closed" as unvetted); a declared field admits a fourth
  class without migration.

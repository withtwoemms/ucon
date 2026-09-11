# 011 — Currency via kinds and rate contexts

**Status:** Accepted (2026-09-10) — implementation tracked in #292
**Context:** Currency support has been wanted since the sovereign-potential
demo used `mass` as a stand-in ("working but semantically dishonest" —
`../ISSUE_REPORT_ucon-extend-basis-design-note.md`). Currency is the
canonical stress test for a units system: units interconvertible only
through dated, revisable tables; sums meaningful only within one currency;
comparisons that silently lie across inflation bases. The ecosystem
default (pint's FAQ) is to decline currency outright because "rates
fluctuate."

## Decision

**Kinds govern combination; contexts license conversion.**

- Currency amounts are **dimensionless numbers carrying kinds**:
  a `currency` root with `join_policy = refuse`, children `usd`, `eur`, …
  Cross-currency addition refuses at the kind stratum; currency-plus-tally
  refuses as disjoint roots (`DisjointKinds`, 2.1.5).
- `USD`, `EUR`, … are dimensionless **units with `default_kind`**
  (`"fx:usd"`, …) so `Number(100, USD)` reads naturally and auto-attaches
  its kind. **No graph edges between currency units** — they are not
  timelessly interconvertible, and the absence is load-bearing.
- **FX rates are `ConversionContext`s** — dated, named, session-scoped.
  `.to(EUR)` works inside `using_context(fx_2026_09_10)` and raises
  `ConversionNotFound` outside any: correct epistemics, since only a dated
  table's truth exists. Rate tables ship as `[[contexts]]` TOML packages
  (#282).
- **Star topology convention:** rate packages quote every currency against
  one base. No cycles → `CyclicInconsistency` never applies (triangular
  arbitrage / holonomy never becomes a graph problem), and BFS composes
  cross-rates through the base automatically.
- **Kind transport — the one new mechanism:** `.to()` preserves kind, which
  is correct for physics (J → kWh is still `energy`) and wrong for
  exchange (converted euros must not stay kinded `usd`). Rule: **arrival
  at a `default_kind` unit re-kinds the result.** `default_kind` is
  machinery the pseudo-dimension retirement already specifies (`bit` with
  `default_kind = "information"`); currency pulls it forward.
- Sub-units are `Scale` (`centi * USD`); derived quantities are formulas
  (`usd / time → usd_burn_rate`); inflation basis (nominal vs
  `real_2020`) is an **aspect family** once the aspect stratum
  ([`008-aspect-stratum.md`](008-aspect-stratum.md)) lands.

## Evidence

Exercised live against a running ucon MCP server (2026-09-10): the
`currency(refuse) ▸ {usd, eur}` lattice and dimensionless units register
today; conversion without a rate correctly refuses (`no_conversion_path`);
with a session rate edge, `convert(100, USD → EUR, kind="usd")` returned
`{quantity: 92.14, unit: "EUR", kind: "usd"}` — **92.14 euros still
kinded `usd`**, demonstrating the kind-transport gap on the wire and
confirming re-kind-on-arrival as the missing rule.

## Alternatives considered

**Currency as an extended-basis dimension** (the design note's Phase 2).
Buys stratum-1 refusals and context-free `.to()`. Declined as the shipped
design:

1. The algebraic-stability criterion that retired INFORMATION as a basis
   dimension applies verbatim — `currency²` is meaningless, and currency's
   only equations are the universal rate/intensity patterns.
2. Static graph edges collide with FX's defining property: conversion
   cycles that do not close. The basis route forces an "open cycle" graph
   mode; the contexts route never creates cycles at all.

`extend_basis` remains available as a user-chosen escape hatch — which is
what a user extension is for.

**FX rates as formulas** (rate as a kinded factor, mirroring the
radiation-weighting pattern). Sound but strictly dominated by contexts: it
loses `.to()` ergonomics and automatic cross-rate composition, both of
which contexts restore. Retained as the pattern for genuinely
formula-shaped money operations (weighted conversions, fee schedules).

## Consequences

- The division of labor matches the strata: dimension (stratum 1) catches
  money-vs-physical mixes, kind (stratum 3) catches cross-currency
  arithmetic, aspect (stratum 4) catches inflation-basis mixes, and
  conversion legality is scoped to explicitly loaded, dated tables.
- Provenance becomes structural: every conversion names the context that
  licensed it — the foundation for on-demand rate tooling (session
  contexts fetched from trusted sources) in the MCP surfaces.
- Uncertainty machinery applies to money: a bid/ask spread is a
  `rel_uncertainty` on a context edge, and converted amounts propagate it.

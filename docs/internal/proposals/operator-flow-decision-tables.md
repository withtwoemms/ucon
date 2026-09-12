> **SUPERSESSION NOTE (2026-09-10).** Partially superseded by
> [`../decisions/009-turnstile.md`](../decisions/009-turnstile.md): the
> role/menu machinery (T6–T9, §G1) is replaced by the four-stratum dispatch
> with derived point/displacement and the affine-algebra admissibility rule;
> the mixed-signature governance question (G1) is thereby moot. The map
> algebra, T1–T5, the T3 rewrite system, the closure theorem, and the
> ratified T5 branch-inverse declaration (B5d) remain current and feed the
> v2.2.0 `PolynomialMap` and `Unit.chart` work.

# DESIGN: Operator Flow — The Decision Tables

**Status:** Draft for review
**Date:** 2026-07-17
**Target:** v2.3+ (lands after the v2.2.0 aspect work; see Amendment G5)
**Provenance:** Base text is the decision-tables v2 draft (external working note,
2026-07-17), incorporated verbatim in §V–Appendix C. New in this repo copy:
the prior-art survey (§P), the amendments (§G) closing the seven gaps
identified in review, and Appendix D (lessons from prototype v2).

**Cross-reference key.** The base text carries labels from its v1 lineage that
do not resolve in this repository. They are anchored here:
- **⟨D6⟩** — decision: the selection rule (T9) is property-tested rather than
  case-tested (generate role pairs × ops, assert count ∈ {0, 1, >1} maps to
  {refuse-hint, execute, refuse-enumerate}).
- **⟨D7⟩** — decision: displacement charts are *derived*, minted by the
  `(−, point, point)` and `(−, level, level)` menu entries, not declared.
- **Eval INST.1.5** — instrumentation-domain eval case: thermocouple
  calibration-range enforcement (the class-C domain-check requirement).

---

## §P. Prior art — which fragments exist elsewhere

No existing library derives operation legality from chart structure. Several
have shipped fragments, each as a special case:

| library | fragment | relation to this design |
|---|---|---|
| **mp-units** (C++) | `quantity_point` vs `quantity` — point/displacement split with distinct origins | The T-add torsor, hand-instantiated; no T-mult, no class C, no menu/refusal machinery |
| **au** (C++) | `QuantityPoint` with offset handling | Same fragment as mp-units |
| **Boost.Units** | `absolute<>` wrapper for affine temperature | T-add only, opt-in per unit |
| **std::chrono** | `time_point` vs `duration` | The single most battle-tested T-add torsor in production; domain-specific |
| **pint** | delta units (`delta_degC`); refuses ambiguous offset-unit arithmetic | Appendix A derives pint's delta behavior as the affine row of the general transport law. pint's `interval × interval` precedent is cited at T8b |
| **astropy** | function units (`dB`, `mag`) with `physical_unit` | The T-mult fragment: log charts carry their codomain. No level/ratio role split — `dBm + dBm` silently adds numerals |
| **GUM / metrology practice** | sensitivity-coefficient uncertainty transport | T11 is GUM first-order; the k = 2 pushforward = quadrature identification (T4, class P) appears to be novel packaging |

What is unprecedented is the *unification*: structure classes computed from
chart signatures, roles computed from kind relations, legality decided by a
single counting rule (T9), refusals carrying machine-applicable spellings
(T10), and transport as one functorial law covering displacements and
uncertainty alike (Appendix A). Each fragment above is a row or cell of these
tables; none of the libraries has the tables.

---

## §V. Vocabulary

The design terms form a ladder; each names exactly one rung.

| term | meaning | example |
|---|---|---|
| **quantity space** | the physical magnitude domain, with its intrinsic structure | temperature; power; resistance–conductance |
| **quantity** | a point or displacement in that space; chart-independent | the temperature of this coffee |
| **chart** | a numeral-assignment scheme (coordinate system) on the space, with structural character | °C (affine); dBm (log); a Type K curve (class C) |
| **unit** | a reference quantity for ratio comparison; every unit generates a *linear* chart, but not every chart reduces to a unit | the kelvin; the meter |
| **numeral** | the number a chart assigns to a quantity | 283.15 (K-chart), 10 (°C-chart) — one quantity |
| **quantity value** | numeral + chart (+ uncertainty, kind): what a `Number` is | `10 °C ± 0.2` |
| **kind** | which *sort* of quantity (lattice-resident; chart-invariant) | absorbed_dose; power_level |
| **role** | which geometric object of the space a kind occupies: POINT, DISPLACEMENT, LEVEL, RATIO, FRAME — computed from `displacement_of` / `additive_frame` links, never stored | temperature_interval → DISPLACEMENT |
| **map** | the transition function between charts | °F→°C; Ω→S |
| **transport** | the induced action of a chart change on a numeral (Appendix A) | 10 °C → 283.15 K |

Slogans: *units measure, charts represent*; *the space determines what
operations exist, the chart determines which are computable as numeral
arithmetic, the kind says which operation the operands have selected*; the
original bug in one line: *a numeral operation wearing a quantity operation's
clothes*.

Naming note: `Number.quantity` holds the **numeral** — VIM-faithful renaming
(`numeral` or `value`) is desirable but cannot ride a minor release; see
Amendment G6.

---

## 0. The organizing claim

Operation legality in ucon is decided by consulting a fixed sequence of small
tables. Every table is one of two sorts:

- **⚙ Static** — fixed by mathematics. Ships in the library, versioned with code.
  Wrong entries are bugs, not modeling choices.
- **📄 Declared** — chosen by the model. Serialized in `.ucon.toml`, versioned with
  the graph artifact. Wrong entries are modeling errors, caught (where possible)
  by validation against the static tables.

The layers, bottom to top: **dimension → chart → graph → kind → dispatch →
refusal/uncertainty.** Each layer either short-circuits with a structured refusal
or narrows the decision for the next.

---

## Layer 1 — Dimension

### T1. Pseudo-dimension absorption 📄 (with ⚙ default)

Governs products of dimension components. The default base carries SI-style
entries; extended bases declare their own.

| left · right | product | example |
|---|---|---|
| angle · angle | angle | rad × rad → rad² (dim: angle) |
| solid_angle · luminous_intensity | luminous_intensity | cd·sr, lm both → luminous_intensity |
| (default) d · d | d² (vector add) | m × m → area |

*Consulted:* dimension gate (pipeline step 1) and product-dimension computation.
*Note:* whether `sr = rad²` is an identity is a **declared** stance (ucon: no;
astropy: yes) — this table is where that stance lives.

## Layer 2 — Chart (map)

### T2. Chart typing ⚙ — the four hom-families

Objects: **A** = (ℝ, +), **M** = (ℝ⁺, ×). Endpoint translations (offset on A,
reference scale on M) permitted and tracked.

| family | type | form | closed parametrization |
|---|---|---|---|
| linear | A → A | a·x | LinearMap |
| affine | A → A + translation | a·x + b | AffineMap |
| log | M → A (+ endpoint translations) | s·log_b(x/r) + o | LogMap |
| exp | A → M (+ endpoint translations) | r·b^(s·x+o) | ExpMap |
| power | M → M | c·x^k | PowerMap (k = −1: ReciprocalMap) |
| *(untypeable)* | — | e.g. Σaᵢxⁱ deg ≥ 2; log∘(inner-offset affine) | PolynomialMap, opaque composites |

### T3. Composition & normalization ⚙ — the closure/rewrite table

| f ∘ g | normalizes to | note |
|---|---|---|
| linear ∘ linear | linear | factors multiply |
| affine ∘ affine | affine | offsets fold |
| power_j ∘ power_k | power_{j·k} | recip∘recip = power₁ = linear (verified) |
| log ∘ exp | linear | A → A round trip |
| exp ∘ log | **power** | verified: constant doubling-ratio 2^(S·s) |
| log ∘ power_k | log (k folds into s) | b·log(a) = log(a^b) |
| exp/log ∘ affine (inner offset ≠ 0) | **untypeable → C** | Stevens: no log of interval scale |
| poly ∘ anything, anything ∘ poly | untypeable → C | |
| conjugation identity | pow_k = exp ∘ lin_k ∘ log | makes M the log-conjugate of A |

*Consulted:* at `ComposedMap` construction (eager) and path resolution (step 2).
Loop residuals in coherence checking are classified through this same table —
a residual normalizing to linear(1.02) is a factor error; surviving offset =
reference-point error; surviving power = exponent error.

### T4. Structure classification ⚙ — normalized type → class & capabilities

| normalized type | class | torsor (displacement lives in) | pushforward | scalar-mult law |
|---|---|---|---|---|
| linear | **H** | degenerate | — | direct |
| affine | **T-add** | A (intervals) | — | via menu (T8) |
| log | **T-mult** + P | M-image (ratios; dimension-shifting) | power-sum | via menu |
| exp | **T-mult** mirror + P | chart quotients | mirror sum | via menu |
| power_k (k ≠ 1) | **P** | none (theorem) | generalized-mean sum; k = 2 is GUM quadrature | degree-k: f(cx) = c^k f(x) |
| untypeable | **C** | none | branch-inverse only, if declared | none |

Classification is applied to each operand's **chart→canonical signature**
(the normal form of its resolved path to the space's canonical frame), not
to the pairwise transition between operands. This is what makes `K + K`
route to H while `degC + degC` stays T-add even though the pairwise
transition is the identity in both cases. See Amendments G1–G2.

### T5. Chart domain 📄

Per map: valid interval, behavior at boundary (refuse / warn), branch selection
for inverses. Mandatory for C-class (calibration ranges — Eval INST.1.5);
implicit today for log (x > 0), made explicit.

## Layer 3 — Graph

### T6. Coherence policy 📄 (semantics ⚙)

| policy | on incoherent declaration | implicit coercion | loop residuals |
|---|---|---|---|
| require | refuse (`EdgeIncoherent`) | allowed on H paths | must close within uncertainty budget (k-coverage; exact for defined conversions) |
| warn | accept, mark pairs | refuses on marked pairs | reported |
| open | accept | disabled graph-wide | queryable (holonomy as signal: currency) |

*Consulted:* edge declaration time; step 2 legitimacy of "the" resolved path.

## Layer 4 — Kind

### T7. Join policies 📄 (existing)

Per parent kind: `refuse | permit` — the sort gate. `specific_energy: refuse`
kills Gy + Sv at step 4 regardless of chart structure. Unchanged by this work.

### T8a. Torsor & frame links 📄 (new relations on existing kinds)

| relation | example entries |
|---|---|
| `displacement_of(K_point) = K_interval` | temperature_interval ↔ temperature_point |
| `displacement_of(K_level) = K_ratio` | power_ratio ↔ power_level (dimension-shifting) |
| `additive_frame(K) = chart` | series_resistance → Ω; parallel_conductance → S |

*Distinct from the join lattice; consulted at role lookup (step 5), never at
sort-join (step 4). Conflating the two relations corrupts both.*

## Layer 5 — Dispatch

### T8b. Operation menus ⚙ — one small table per structure class

Keyed `(op, role_a, role_b) → (execution rule, result kind, result chart)`.
The complete T-add menu:

| op | roles | result | rule |
|---|---|---|---|
| − | point, point | **interval** | canonical-frame difference |
| + | point, interval | point | torsor action |
| + | interval, interval | interval | vector add (coerce H-wise) |
| + | point, point | ∅ | (no entry → refusal enumerates the two spellings) |
| k· | interval | interval | scale |
| k· | point | ∅ | (two readings: chart-naive / canonical) |
| × | interval, interval | interval² | pint precedent, verified |
| × | point, * | ∅ | pint precedent, verified |

T-mult menu adds: `(−, level, level) → ratio` (dimension-shifting);
`(+, level, ratio) → level`; `(+, ratio, ratio) → ratio` (= underlying ×);
`(k·, ratio) → ratio` (= exponentiation/cascade); `(k·, level) → level`
(unique legal reading: underlying scaling); `(⊕, level, level) → level`
(power-sum). H menu: everything direct. P menu: named sums only.
C menu: **empty** (only `.to()`, domain-checked, exists).

Menu lookup canonicalizes commutative operand order — see Amendment G4.

### T9. The selection rule ⚙ — one law, not a table

> Count matching menu entries for the operands' roles:
> **1 → execute silently. 0 → refuse, hinting nearest legal spellings.
> >1 (incl. unknown roles on T charts) → refuse, enumerating all spellings.**

This single rule replaces per-case judgment everywhere: it is why unkinded
`dB + dB` refuses with three spellings while `2 ⊗ 30 dBm` resolves.

## Layer 6 — Refusal & uncertainty

### T10. Refusal taxonomy ⚙

| failure point | error type | payload must include |
|---|---|---|
| step 1 | DimensionMismatch | dims, compatible-unit hint (existing) |
| step 2 | ConversionNotFound / NonHomogeneousCoercion | base-form signatures / offending normalized class |
| step 2 (graph) | EdgeIncoherent | violated cycle, residual **and its T3 class**, budget |
| step 3 | ChartConversionOnly / DomainExceeded | valid range, `.to()` spelling |
| step 4 | JoinRefused | kinds, LCA, policy (existing) |
| step 5/6 | AmbiguousChartOperation | **the enumerated legal spellings** (T9's >1 branch) |

### T11. Uncertainty transport ⚙

| op | rule |
|---|---|
| `.to()` / coercion | transport δ by sensitivity \|f′(x)\| (positional for C-class) |
| +/− (post-coercion) | RSS in the common frame |
| ⊕ (pushforward) | transport to underlying frame, RSS there, return — RSS itself is the k = 2 instance |
| ×, k· | relative-uncertainty composition per existing GUM rules |

---

## The pipeline, annotated

| step | consults | short-circuit |
|---|---|---|
| 1. dimension gate | T1 | DimensionMismatch |
| 2. path resolve + normalize | T3, T6, (T2) | ConversionNotFound, NonHomogeneousCoercion, EdgeIncoherent |
| 3. class C check | T4, T5 | ChartConversionOnly, DomainExceeded |
| 4. kind sort-join | T7 | JoinRefused |
| 5. role lookup | T8a | — (unknown roles flow to T9 as multi-match) |
| 6. menu + selection | T8b, T9 | AmbiguousChartOperation |
| 7. execute | T11 | — |

The v2.2.0 aspect gate sits as a peer of step 4 and reads nothing from these
tables — see Amendment G5.

## Closing observations

1. **Six static tables carry the entire theory** (T2, T3, T4, T8b, T9, T10, T11 —
   with T9 a single sentence). They are enumerable, testable in isolation, and
   the natural spine for both the test suite and the Metrologia exposition.
2. **Four declared tables carry the entire model** (T1, T5, T6, T7+T8a) — all
   serializable, which means a `.ucon.toml` package now declares not just units
   and edges but *absorption stances, domains, coherence posture, and torsor
   structure*: the marketplace artifact becomes a complete "way of seeing."
3. **Validation is the static tables checking the declared ones**: T3 classifies
   T6's loop residuals; T4 demands T5 domains for C-class charts; T8a links are
   type-checked against T4's torsor capabilities (declaring `displacement_of` on
   a power chart is rejected — the theorem says no torsor exists). Two further
   validations added by amendment: canonical-frame zero (G2) and derived-chart
   topology (G3).

---

## §G. Amendments — gaps closed in review

The base text left seven points implicit or unresolved. Each is closed here;
where an amendment touches a table above, the table carries a pointer.

### G1. Mixed-signature menu selection

When the two operands' chart→canonical signatures classify differently
(`K` is H, `degC` is T-add), **the most structured class of the pair governs
menu selection**, under the partial order:

```
H  <  T-add
H  <  T-mult  <  P (where pushforward applies)
everything  <  C        (already enforced at step 3)
```

Rationale: a structured chart's readings do not collapse merely because the
other operand's chart is linear. `K⟨point⟩ + degC⟨point⟩` consults the T-add
menu → `(+, point, point)` → ∅ → refusal with two spellings. Only when *both*
signatures are H do point readings degenerate and the H menu ("everything
direct") apply — this is the ratio-scale privilege, and it is now a
consequence of G1 + G2 rather than a special case. T-add and T-mult never
meet at step 6: their operands differ dimensionally (step 1) or are separated
by the absence of a declared pushforward.

### G2. Canonical-frame zero invariant 📄-validation

The ratio-scale privilege (H-classified point operands may be summed
directly) is sound only because a `linear` chart→canonical signature (`a·x`)
shares the canonical frame's zero, and that zero is physically absolute.
This makes canonical-frame choice load-bearing, so it is validated:

> **A quantity space whose canonical frame lacks a true zero must not present
> any point-role chart with a `linear` signature.**

Concretely: temperature's canonical frame must be K (not °C). A basis
declaring an offset canonical frame fails graph validation with
`EdgeIncoherent`-class diagnostics, or — where the space genuinely has no
absolute zero (e.g. calendar time) — every chart in the space is registered
affine and the H menu is unreachable for points, which is the correct
semantics. This joins closing-observation 3's validation list.

### G3. Derived displacement charts are topologically separate

`ChartRole` is computed from kinds and never stored, which leaves a hole for
*unkinded* numerals on displacement charts: nothing at the kind layer stops
`5 ddegC → K` from converting a displacement into a point. The resolution is
topological, per ⟨D7⟩:

> **Derived displacement charts form their own conversion component. No edge
> connects a derived displacement chart to any point chart of its space.**

`to(5 ddegC, K)` is then `ConversionNotFound` by construction — no role
lookup required. Displacement↔displacement conversions (ddegC ↔ dK, dB ↔ Np)
live inside the component and transport by derivative (Appendix A). The
family-vs-frame confusion found in prototype v2 (Appendix D, B4) cannot be
reproduced: family membership never spans the point/displacement divide at
the graph layer.

### G4. Commutation stance for menu keys

Menus list each unordered role pair once (the base text's T-add menu lists
`(+, point, interval)` only). **For commutative ops (+, ×, ⊕), lookup
canonicalizes operand order before consulting the menu; the execution rule
receives the operands tagged by role, not by position.** Non-commutative ops
(−, ÷) key on ordered pairs, and missing orders refuse via T9's count-0
branch (e.g. `(−, interval, point)` has no entry and never will).

This kills the prototype's residual asymmetry class (Appendix D, B1) by
construction: an executor cannot assume "a is the point" because it is handed
`{point: …, interval: …}` bindings, not `(a, b)`.

### G5. Aspect-gate placement and orthogonality

The v2.2.0 aspect work adds a refusal gate that reads only the two operands'
aspect sets and the operation — nothing from T1–T11, and nothing here reads
aspects (Law 0, orthogonality to Kind, extends to charts and roles). The
aspect gate runs as a **peer of step 4**: after the structural gates
(steps 1–3) so that aspect refusals are never reported for operations that
were structurally illegal anyway, and independent of steps 5–6 so that menu
counting is aspect-blind. Neither workstream's refusal taxonomy references
the other's error types.

### G6. The `numeral` rename rides v3.0, not v2.2

§V's naming observation (`Number.quantity` holds a numeral) is correct, but
the repo's deprecation policy (CLAUDE.md) forbids breaking renames in minor
releases: `PendingDeprecationWarning` → `DeprecationWarning` → removal at the
next major. Schedule: introduce `Number.numeral` as an alias whenever
convenient; begin the warning ladder no earlier than the release that ships
this design; remove `Number.quantity` at v3.0.

### G7. Cross-references anchored

`⟨D6⟩`, `⟨D7⟩`, and `Eval INST.1.5` are defined in the cross-reference key at
the head of this document. Future revisions cite those anchors, not the v1
draft.

---

## Appendix A. The transport law

Transport = recomputing the numeral of the *same* quantity under a chart
change. Different geometric objects induce different laws, functorially:

| object | transports through | note |
|---|---|---|
| point / level | the map: x′ = f(x) | offset included — position is origin-relative |
| displacement / ratio | the derivative: d′ = f′·d | **exact** (not linearized) for in-family transitions: f(x+d) − f(x) = a·d, offsets cancel identically |
| uncertainty δ | \|f′\| | δ *is* a small displacement — T11's sensitivity rule and this row are one law |
| kind | does not transport | chart-invariant by construction |
| closed cycle | residual ≠ id ⇒ holonomy | T6's subject matter |

Closure theorem: displacement transport is base-independent **iff** the chart
transition has constant derivative (is affine in chart coordinates) — torsor
structure exists exactly where permissible transformations are affine
(Stevens' hierarchy, derived). Transitions into class-C charts fail this:
transport the point pair and re-difference, or refuse.

pint's delta-unit conversion behavior is the affine row of this table,
special-cased; here it is derived.

## Appendix B. Type lifecycle — where each type lives

| phase | types constructed / consulted | persistence |
|---|---|---|
| **authoring** | PowerMap, PolynomialMap, Domain, CoherencePolicy, Kind + displacement_of / additive_frame links, pushforward registrations | `.ucon.toml` (declared tables T1, T5, T6, T7/T8a) |
| **graph build / validation** | LoopResidual (per closed cycle, classified via T3); link type-checks (T4 rejects torsor links on power charts); canonical-zero check (G2); displacement-component check (G3) | validation report / coherence certificate |
| **call time** | ChartSignature (normal form of resolved path), StructureClass, ChartRole (computed from kinds; never stored), MenuEntry via T9 count | ephemeral, per operation |
| **result / refusal** | Number (kind/unit-family may shift, e.g. level − level → ratio in the derived displacement chart), or T10 exceptions carrying Spelling[] / LoopResidual | caller / MCP envelope |

Reference trace (`30 dBm − 27 dBm`): signature log(M→A) → T_MULT; sort-join
passes; roles (LEVEL, LEVEL); menu key `(−, LEVEL, LEVEL)` → one entry → T9
count = 1 → `Number(3, dB, kind=power_ratio)`, δs transported by derivative.
Unkinded variant diverges only at role lookup: count = 3 →
`AmbiguousChartOperation` with three Spellings. The `Number` itself stays lean:
numeral, chart handle, uncertainty, kind — everything else computed at use.

## Appendix C. Class inventory → tables implemented

| new type | implements | notes |
|---|---|---|
| `PowerMap(k)` | T2, T3, T4 | ReciprocalMap = alias k = −1; degree-k scalar law; k = 2 pushforward = GUM quadrature |
| `PolynomialMap` | T2 (untypeable row), T5 | coefficients + mandatory Domain; official ITS-90 sets at implementation |
| `Domain` | T5 | interval, boundary behavior, branch selection |
| `ChartSignature` | T3 output; T4 input | reified normal form: source object, core family, endpoint translations |
| `StructureClass` enum | T4 | {H, T_ADD, T_MULT, P, C} |
| `ChartRole` enum | T8a → T8b key | {POINT, DISPLACEMENT, LEVEL, RATIO, FRAME}; computed, never stored |
| `displacement_of`, `additive_frame` relations | T8a | on existing Kind objects; distinct from join |
| `MenuEntry` / `OperationMenu` | T8b | shipped data, testable in isolation; role-tagged operand bindings per G4 |
| selection rule | T9 | one law; property-tested (⟨D6⟩) |
| `Spelling` | T10 payload | structured alternative (op + role annotations + template); machine-applicable by MCP consumers |
| error types (NonHomogeneousCoercion, ChartConversionOnly, DomainExceeded, AmbiguousChartOperation, EdgeIncoherent) | T10 | EdgeIncoherent carries residual **and its T3 class** |
| `CoherencePolicy` enum, `LoopResidual` | T6 | residual = classified composite |
| derived displacement charts | ⟨D7⟩, G3 | minted by `(−, point, point)` / `(−, level, level)` entries; own conversion component |

User-facing surface: kinds, edges, three small relation declarations, and the
named-sum API. Everything else is computed machinery.

## Appendix D. Lessons from prototype v2

Two throwaway prototypes (dispatch-only, self-contained) preceded this
design. The second fixed the first's headline flaw (asymmetric dispatch) and
demonstrated symmetric reading enumeration, a closed map algebra, codomain
checking, construction gating, and GUM transport. Its residual defects are
recorded here because each one hardened a table or amendment above:

| id | prototype defect | design consequence |
|---|---|---|
| B1 | Reading enumeration was symmetric but the executor `pd_add` still assumed operand order — `disp + point` produced a displacement-charted, displacement-kinded "point" | G4: executors receive role-tagged bindings, never positional operands |
| B2 | `level − level` and `level + ratio` executors skipped chart transitions, so `30 dBm − 1000 mW⟨level⟩` computed `30 − 1000` | Appendix A: transport is one law applied by the pipeline before any rule executes, not re-implemented per executor |
| B3 | Three of five executors dropped uncertainty | T11 is total over the op inventory; the δ-is-a-displacement identification makes omission structurally visible |
| B4 | Family-based codomain check let unkinded `5 ddegC → 5 K` and `3 dB → 3 mW` convert silently; kinded cases were caught by the wrong layer with a misleading error | G3: derived displacement charts are graph-disconnected from point charts — the conversion cannot be expressed |
| B5a | The degeneracy-collapse condition contained a dead branch duplicating a later one | T9's counting rule leaves nowhere for per-case conditions to accumulate |
| B5b | Unkinded `degC − degC` silently *inferred* `temperature_interval` on the result | Resolved by T9: unknown roles on T charts are multi-match → refusal with spellings. The system refuses or preserves; it never invents information |
| B5c | Ratio-scale privilege was implemented as "both charts linear" with the canonical-zero assumption unstated | G2 states and validates the invariant |
| B5d | `Poly` inversion refused unconditionally, blocking reverse thermocouple lookup (`K → mV_typeK`) | T5 branch-inverse declaration: C-class charts may declare an inverse (NIST publishes inverse polynomials); absent a declaration, the refusal stands |

The prototypes are not part of the deliverable and are superseded by this
document.

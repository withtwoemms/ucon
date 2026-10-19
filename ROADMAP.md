# ucon Roadmap

> *Major milestones from foundation through v2. `CHANGELOG.md` is the source of truth for incremental updates.*

---

## Vision

ucon is a dimensional analysis library for engineers building systems where unit handling is infrastructure, not just convenience.

**Target users:**

- Library authors embedding unit handling without global state
- Domain specialists defining dimensions that match their field
- Modern stack developers wanting first-class Pydantic, Polars, MCP support

---

## How This Document Relates to CHANGELOG

This roadmap tracks **major milestones** on the path to v2. For incremental updates — every patch and minor release, including bug fixes, new units, parser refinements, and small API additions — see `CHANGELOG.md`. The CHANGELOG is the source of truth; this roadmap exists only to surface the structural waypoints that connect releases into a coherent trajectory.

---

## Milestone Timeline

| Version | Milestone | Status |
|---------|-----------|--------|
| v0.x | Algebraic foundation: Unit/Scale separation, `UnitProduct`, `ConversionGraph`, dimension/basis abstraction, uncertainty propagation, MCP integration | Complete |
| v1.0.0 | API stability: semantic-versioning commitment, 2+ year LTS, ~215 units across 67+ dimensions, cross-dimensional contexts (spectroscopy, Boltzmann) | Complete |
| v1.2.0 | TOML round-trip `ConversionGraph` serialization | Complete |
| v1.3.0 | Graph-independent arithmetic via `BaseForm` decomposition | Complete |
| v1.4.0 | Basis isomorphisms: Atomic and Planck units as first-class bases | Complete |
| v1.5.0 | Conversion factor uncertainty (GUM propagation) | Complete |
| **v1.6.0** | **TOML takeover** — TOML as single source of truth (~1,250 lines of hand-written Python collapsed to a ~150-line loader) | Complete |
| v1.6.x | Cross-basis arithmetic completion: base-form conversion fallback, `@enforce_dimensions` coercion, transform-graph-aware `Vector` arithmetic | Complete |
| v1.7.0 | Basis subpackage layout: `types`/`vector` extraction, deferred-import reduction | Complete |
| **v1.8.0** | **`UnitSystem` value type, `ucon.basis.ops`, basis cycle break.** Introduces `ucon.system.UnitSystem` as a frozen value owning units, dimensions, conversions, basis, basis-graph, base-units, contexts, constants, and a per-instance `AlgebraCache`; renames the v1.7 `UnitSystem` to `BaseUnits` (PEP-562 alias retained with `PendingDeprecationWarning`); makes `Vector` strictly same-basis with explicit cross-basis helpers in `ucon.basis.ops` (`unify`, `multiply_via`, `divide_via`); routes `Dimension` algebra through the active system's `AlgebraCache`; threads an optional `system=` kwarg onto `Number.to`, `parse`, `parse_unit`, `parse_dimension`, `enforce_dimensions`, and the compound-unit parser. Resolves the `vector → graph → transforms → vector` load-time cycle as a side effect. | Complete |
| **v1.9.0** | **Kind-of-Quantity (KOQ) preview surface.** Introduces `ucon.kinds` (sortal lattice with `Kind`, `KindLattice`, `JoinPolicy`) and `ucon.formulas` (`KindFormula`, `FormulaRegistry`, `AspectRule`) as opt-in data models for quantities that share a dimension but differ semantically (kinetic vs. potential energy; absorbed vs. equivalent dose). TOML loaders in `ucon.parsing` (`load_kinds_file`, `load_formulas_file`) make lattices and registries authorable from the same format that defines units. Not wired to `Number` — preview surface only. | Complete |
| v1.9.1 | **Aspect propagation.** Activates the `aspect_rules` field on `KindFormula`. Adds `ucon.aspects` subpackage with `AspectSet`, `AspectJoinPolicy`, and `join_aspects(a, b, policy)`. Adds `KindFormula.project_aspects` and `FormulaRegistry.apply(inputs)` returning `(formula, output_kind, output_aspects)`. Still callable-side; still not wired to `Number`. | Complete |
| v1.9.2 | **Lookup completeness.** Makes the registry consult declared structure that v1.9.0 indexes but does not act on: full `n!` permutation for commutative formulas with `n > 2`, ancestor-walk matching for formulas declared with `generalizes=True`, and opt-in dimension-only fallback. Adds `LookupResult` with `MatchKind` (EXACT/COMMUTATIVE/GENERALIZED/DIMENSIONAL) for diagnostic inspection. No new concepts — completeness pass on existing declarations. | Complete |
| v1.10.0 | **`Number.to()` routed through the active `UnitSystem`.** First step in retiring module-level global state: `UnitSystem` becomes the authority for unit resolution and graph lookup. Adds `UnitSystem.resolve_unit(name)` and top-level `active()` / `use()` exports. All v1.9.x call sites continue to work unchanged. | Complete |
| v1.11.0 | **Eager system initialization.** `ucon/__init__.py` pushes a `UnitSystem` onto the `_active` ContextVar at import time, so the active-system tier in `get_default_graph()` is always hit. The module-level `_default_graph` singleton becomes dead code; `set_default_graph`, `reset_default_graph`, and `UnitSystem.from_globals` are deprecated. | Complete |
| v1.12.0 | **Cycle-break completion — structural rather than runtime.** The `_active` ContextVar relocates to a true Layer-0 leaf (`ucon._active`) with zero intra-ucon imports; `AlgebraCache` moves to `ucon._algebra_cache`; the transitional `_resolve_unit_impl` dependency-injection scaffold and the `constants._constants_cache` cross-module attribute assignment both retire. A static AST audit (`test_no_cross_module_injection.py`) guards against future regressions. No public API change. | Complete |
| **v2.0.0** | **`UnitSystem` algebra, global retirement, and `Number.kind` wiring.** Closes the value-type loop: pure-function operations `extend` / `restrict` / `merge` / `with_*`, first-class relations `subsystem_of` / `compatible_with` / `diff` / `shared_units` / `shared_dimensions`, explicit cross-system value movement (`system.adopt`, `Bridge(A, B)` with `rename` + `basis_transform`), and retirement of the module-global registries (`_REGISTRY`, `_DIMENSION_ATTRS`, default `ConversionGraph`) in favour of the default `UnitSystem` value. Promotes the v1.9.x KOQ surface to first-class: `Number` accepts `kind=`, arithmetic dispatches through the active `FormulaRegistry`, and the `ActiveContext` substrate (single ContextVar payload bundling `system + formulas + kinds + strict`, extended `use(...)` with field-wise inheritance) makes scope explicit. `strict=True` by default raises `UnitDefinitionMismatch` on identity-mismatched source units. Removes the deprecated `UnitSystem` alias for `BaseUnits` and the `_DIM_*_CACHE` shims. Marshal-based graph cache (~15-25x import speedup). | Complete |
| v2.1.x | **Correctness train** — six per-issue patch releases (2.1.2–2.1.7) closing the 2026-09 audit: exact customary prefactors derived from statutory seeds, constant symbols in package edge factors, path resolution through composite edge endpoints, typed `DisjointKinds` refusals, idempotent kind re-add, exact SI `base_form`s for mechanical CGS units. Per-issue detail in [`CHANGELOG.md`](CHANGELOG.md). | Complete |
| **v2.2.0** | **Aspect stratum** — per [decisions/008](docs/internal/decisions/008-aspect-stratum.md): one `Aspect` type (peer of `Kind`), flat additive `Number.aspects`, family-wise resolution, carry rule, D3 namespacing; the never-exported flat `AspectSet` model is removed outright; pseudo-dimension deprecations begin (`PendingDeprecationWarning`). | Complete |
| v2.2.x | **Scale correctness train** — a second per-issue patch train, symmetrical with v2.1.x, closing the ψ (scale) defects [ADR 009](docs/internal/decisions/009-turnstile.md) predicted: additive operands converted before combining (2.2.1, #309), unnormalizable pairs refused rather than combined unscaled (2.2.2, #313). Interim by construction — see *Where the chart defects land*. | Complete |
| v2.3.0 | **Stratum wiring and invariant enforcement** — the three routes by which the kind stratum can be bypassed, closed; the invariants that were allowlists, enforced. Shipped: `[[contexts]]` (#316 ✓), `default_kind` (#306 ✓), `contingent` + its TOML key (#320 ✓), the arrival rule **with its refusing clause** (#322 ✓), unit-declared kinds join `None` permissively (#326 ✓), `PolynomialMap` with domain-restricted branch inverses (#332 ✓), six degeneracy-cluster `default_kind`s (#328 ✓), `rankine`'s `base_form` (#339 ✓), `var` completing the W/VA/var cluster (#345 ✓). Owed: scalar `*`/`/` gated on level-vs-gain, `BaseForm` validated to its own documented invariants, `_set_base_form` guarded so the 2.2.2 proxy is sound by construction rather than by a four-name list (#340); `==` consults the kind stratum, so `gray(1) == sievert(1)` stops answering `True` where `.to()` and `+` refuse (#352); the comparison protocol completed — ordering, and `__hash__`, absent as a side effect of defining `__eq__` (#353); formula-collision behaviour established, and refused if arbitrary (#347). **Re-scoped 2026-10-18:** the declared `Unit.chart` field is withdrawn ([decisions/010 §Amendment](docs/internal/decisions/010-chart-nomenclature.md#amendment-2026-10-18)) and the *catalog* half of the KOQ floor splits across v2.4.0 and v3.1.0 by whether it needs the dimensionless fiber before or after 3.0.0 reshapes it. Everything retained here is independent of that fiber. *UnitSafe: low directly; it closes the bypass routes the floor's refusals rely on.* | In progress |
| v2.3.1 | **Unity and the dimensionless fold** — canonical `one` resolving from `"1"` (#307); `UnitProduct` keeps named dimension-one factors and folds only an anonymous scaled unity into the magnitude at the `Number` boundary (#318: today `10 kg × 50 (centi·1)` answers 5 kg, 500 kg, or 500 000 g depending on the accessor); `canonical_scale` enters `UnitProduct` identity; exact `Exponent` arithmetic in `Scale` (`centi × centi` is 10⁻⁴, not `milli`); `Fraction` exponents; division dispatches kinds through its own table, not multiplication's (`Gy / w_R` is not a dose equivalent); `**` never yields an unkinded result. **Not** the `%`/`ppm` parser flip — that rides v3.0.0 with the unit retirement; the intended `%` API is specified by example in [proposals/percent-on-unity](docs/internal/proposals/percent-on-unity.md). Ships with ucon-tools switching its `compute` placeholder from `ea` to `one`. *UnitSafe: high — the `ea` residue sits on every multiply step.* | Planned |
| v2.4.0 | **The pre-retirement KOQ floor** — the clusters 3.0.0 *regresses without*. `xdom-018` (`rad → sr`), `xdom-020` (`rad/s → Hz`) and `pr-028` (`W/m² → W/sr`) refuse today **only because the pseudo-dimension tags differ**; the retirement removes the tags, so `plane_angle`, `solid_angle` and `angular_velocity` must be declared kinds first, and `radian`/`steradian` must carry them (#344, #348). `rad/s` and `W/sr` are `UnitProduct`s, so this needs `default_kind` on product-unit **signatures** — the same mechanism the torque/energy and pressure clusters require, carrying the fiber's **generic** kind so linear work passes and moments refuse (#342, #343 — 14 further must-fails, the largest single lever). Plus the first rung of the v3 deprecation ladder (`PendingDeprecationWarning`). *UnitSafe: high — and it is the difference between the retirement holding the line and dropping three must-fails.* | Planned |
| v2.5.0 | **Deprecation rung two and `Scale` members** — `DeprecationWarning` on the linear-ratio units (→ `Scale` on unity), the logarithmic ratio units (→ the logarithmic chart), `fraction`, and the pseudo-dimension tags; mechanism is `Number.__post_init__` plus module `__getattr__` (precedent: `constants.py`). `Scale` gains 10⁻⁴ (`‱`) and `atto`; rendering table for scales on unity. *UnitSafe: low — two problems answer `%`/`ppm`.* | Planned |
| v2.6.0 | **Native currency as a basis component** (#292) — **a 3.0.0 prerequisite, not a feature queued in front of it:** no `currency` dimension or unit exists today and the SI basis still carries `information` in slot 8, so 3.0.0's "`currency` folds into slot 9 … and the shim transform retires" has nothing to fold until this lands. `[bases.SI-currency]` with both embedding transforms, `resolve()` returning canonical `NONE` for any zero vector, #323 (a loaded package's basis graph reaches dimension arithmetic; `extend` included; append-only embeddings registered ambiently), self-referential `base_form` on currency units and the denomination signature check at the chart stratum (so cents work *and* `USD/MWh + EUR/MWh` still refuses), `ContingentCollision`, star-topology validation, a loadable `fx` package, acceptance re-measured with the lattice active. Supersedes the kinds-plus-contexts route; this **is** the v3 design, only the encoding folds at v3.0.0. *UnitSafe: none — zero currency problems; may slip without touching the gate.* | Planned |
| v2.7.0 | **Last 2.x minor** — `DeprecationWarning` for anything that entered the ladder at v2.5.0; nothing new. | Planned |
| v3.0.0 | **Lean structural major** — the pseudo-dimension retirement per [decisions/013](docs/internal/decisions/013-the-vector-is-the-only-carrier.md): tags absorbed or dissolved, never deleted to `none`; `currency` folds into slot 9 of the renamed system basis (it has not been SI since `information`) and the shim transform retires; `ratio` empties into `Scale`; `count` is a kind on unity; `angle`/`solid_angle` are kinds on unity. The `%`/`ppm`/`bp` parser flip lands here with the unit retirement ([proposals/percent-on-unity](docs/internal/proposals/percent-on-unity.md)). `from_toml` upgrades 8-component packages in place; migration script; `FORMAT_VERSION` 2.0. The 2.2.2 normalizability check is **kept** until v3.1.0. **Gated on v2.3.0's refusing clause and angle/frequency `default_kind`s** — without them `xdom-020` and the `angle/solid_angle` must-fail, which refuse today only by the tag, regress. Plus `Number` frozen, `Unit`/`UnitProduct` identity unification, deprecation removals. | Planned |
| v3.1.0 | **The post-retirement KOQ floor** — the half that needs the merged fiber and could not be done sooner. `lumen.base_form = cd·sr`, unwritable while `steradian` is pseudo-dimensional because `BaseForm.factors` may reference only canonical base units and the BFS oracle skips pseudo-dimensional units (#346); the two log edges that target a quantity other than the one they chart — `nines` hiding `x ↦ 1 − x`, and `pH` as a level on `Dimension(concentration)` where ISO 80000-9 item 9-37 makes it dimension one (#341); the ten dimensionless kinds beyond the angle set, now that `Dimension(none)` and `Dimension(ratio)` are one fiber rather than two (#344); `sr = rad²` made representable, which needs both the tags gone and composing kinds (#348). *UnitSafe: moderate — catalog correctness more than score.* | Planned |
| v3.2.0 | **The Turnstile and the kind algebra** — per [decisions/009](docs/internal/decisions/009-turnstile.md): four-stratum arithmetic dispatch, derived point/displacement, cyclic/ordinal kind flags, lazy warrants via `explain()`. Plus [decisions/013](docs/internal/decisions/013-the-vector-is-the-only-carrier.md) §4: kinds compose — a normal-form `DerivedKind` (formula outputs expanded to their inputs; equality of normal forms; shortest registered name for display), anonymous factors for unkinded operands, cancellation to registered kinds, a `**` dispatch row, ⊤_d as the anonymous kind of its fiber; load-time confluence validation. Logarithmic-chart dispatch (`dBm + dB` admits, `dBm + dBm` refuses). Retires the normalizability check — which requires the arithmetic to route through the conversion graph, since `_canonical_magnitude` is contracted not to; dropping the check alone would corrupt magnitudes rather than free them. *UnitSafe: none as harnessed — `compute` does not run ucon arithmetic.* | Planned |
| *unsequenced* | **Array parity and quantity ergonomics** — `NumberArray` receives the kind and aspect strata (#297, #298) and routes `sum`/`mean`/`std` through them (barycenter mean on interval charts; `sum` of points refuses); `kelvin` declared as `celsius`'s displacement unit so `20 °C + 5 K → 25 °C`; `Number.__neg__`, `__abs__`, `__round__`/`quantize`, `Decimal` operands; opt-in `as_of` provenance aspect stamped by contingent contexts. The **only** row checked against 3.0.0 and found not to be a prerequisite: the benchmark's `compute` is a float path, so the array strata are unexercised either way. Left unsequenced rather than renumbered — where it lands is a product call. *UnitSafe: low.* | Unsequenced |

---

## Where the chart defects land

`Number.__add__` gates on dimension and never consults scale.
[ADR 009](docs/internal/decisions/009-turnstile.md) §2 diagnosed this before it
was reported from outside, recording the shipped behavior as
`1 rad + 180 deg → <181 rad>` and `1 Gy + 1 Sv → <2 Gy>`.

The Turnstile is the fix, and it rides after the 3.0.0 breaks. That is several
releases out, so the v2.2.x train converted silence into either a correct answer
or a loud refusal in the meantime. **The interim work is a waypoint, not the
destination** — some of what 2.2.2 refuses, 3.2.0 is meant to compute. Earlier
drafts of this table also described some of its refusals as *accidental*, to be
removed by re-keying the check. That is withdrawn: the refusals are correct and
the message is what misleads, so they are cleared by supplying the missing
`base_form`s, not by relaxing the gate. The two rows below record it.

| Step | Release | What changes |
|---|---|---|
| Ratio-chart operands converted before combining | 2.2.1 | `1 V - 1000 mV` returns `0 V`, not `-999 V` (#309) |
| Unnormalizable pairs refused, not combined unscaled | 2.2.2 | `1 K == 1 °C` raises instead of reporting `True` (#313) |
| Same-dimension KOQ pairs refuse in `.to()` | 2.3.0 → 2.4.0 → 3.1.0 | `1 Gy[absorbed_dose] → Sv` **refuses** instead of relabeling to `dose_equivalent`; likewise `N·m → J`, `W → VA`, `Bq → Hz`, `Pa → J/m³`, `rad → sr`. The arrival rule gains its refusing clause and every degeneracy cluster ships `default_kind`. 27 of UnitSafe's 62 KOQ must-fails convert freely today. |
| Refusal keys on a principled marker | **withdrawn** | The plan was for the `base_form is None` proxy to give way to a declared `Unit.chart`. It cannot: `_canonical_magnitude` is contracted not to consult any graph and falls back to the raw quantity, so admitting `50 % + 1 fraction` yields `51 %` where the answer is `150 %`, and `20 °R + 5 K` yields `25` where it is `16.111 K`. `base_form` is load-bearing for the *arithmetic*, not only for the meaningfulness check. The two predicates are independent and both stay: chart answers "is this meaningful?", `base_form` answers "is this computable without the graph?" |
| Unity folds; named dimensionless units persist | 2.3.1 | `10 kg × 50 % → 5 kg` (today `<500 g·%>`, unconvertible); `rad/s` and `request/s` keep their symbols; the `ea` residue on every multiply step disappears once the placeholder is `one` (#307, #318; [proposals/percent-on-unity](docs/internal/proposals/percent-on-unity.md)) |
| Angle stays a quantity of dimension one | 3.0.0 | SI Brochure §2.3.4 is right: `m·rad = m`, `rad/s` is T⁻¹. `plane_angle` and `solid_angle` are **kinds** on unity; `degree → radian` is an ordinary edge. The earlier plan to promote angle is withdrawn — it fails the independence test and would have made arc length a cross-dimension error. |
| Over-refusals given base_forms, not relaxed gates | 3.0.0 | **62** same-fiber pairs over **34** units refuse today only because a `base_form` is missing — not five, as earlier drafts said. They are *correct* refusals with a misleading message (see *Refusal keys on a principled marker*), so the fix is to supply the `base_form`, never to relax the gate: 27 units are non-SI-basis (#283), 21 pseudo-dimensional (ADR 013's retirement, 3.0.0), 1 is `rankine` (#339), 1 is the unnamed unity unit, and 12 are genuinely non-ratio and must keep refusing. Three refusals are re-owned deliberately instead — `flop/s + Hz` (kinds, 2.3.0), `100 USD + 50 EUR` and `USD/MWh + EUR/MWh` (denomination signature, 2.6.0) — and two become admits: `kg·% + kg → 6 kg` and `m·rad + m → 4 m` (2.3.1). |
| Chart-crossing arithmetic returns a value | 3.2.0 | the chart stratum supplies factors and offsets, so `1 rad + 180 deg` converts rather than refusing; `20 °C + 5 °C` refuses as `point + point`; `20 °C + 5 K` admits |

Two consequences worth stating plainly. `BaseForm.factors` is contracted to
reference only canonical base units of its basis, so giving angle units a
`base_form` to shortcut this would violate the type rather than fix it — the
BFS oracle skips them for that reason — via `dim.is_pseudo`, which covers the
angle, ratio and count families (21 units); its separate empty-`base_expansion`
branch catches exactly one more, the unnamed unity unit. The angle family's
exact factors live on graph edges and its identity on kinds. And the open Turnstile
prerequisites are now #322's refusing clause and the retirement itself (#282
closed as #316) — declared `Unit.chart` is no longer among them, per
[010 §Amendment](docs/internal/decisions/010-chart-nomenclature.md#amendment-2026-10-18) — so v2.3.0 no longer carries the
chart stratum at all.

**Dependency audit, 2026-10-18.** Thirteen issues (#339–#348, #352–#354) reduce
to four root causes, the largest being the pseudo-dimension tags: eight open
issues are their consequences (#307, #318, #321, #336, #341, #344, #346, #348).
The retirement therefore unblocks the most — but it cannot simply move earlier,
because checking its prerequisites showed two of them were mis-read as features
queued in front of it:

- **#292 currency is a prerequisite.** No `currency` dimension or unit exists
  today and the SI basis still carries `information` in slot 8, so 3.0.0's
  "`currency` folds into slot 9 … and the shim transform retires" has nothing to
  fold until v2.6.0 lands.
- **Part of the KOQ floor is a prerequisite.** `xdom-018`, `xdom-020` and
  `pr-028` refuse today *only* because the pseudo-dimension tags differ; the
  retirement removes the tags, so the angle kinds and the product-signature
  `default_kind` mechanism must precede it or three must-fails regress. That half
  is now v2.4.0; the half that genuinely needs the merged fiber is v3.1.0.

Array parity (#297, #298) was the only row checked and found *not* to be a
prerequisite, so it is the only one unsequenced. The retirement is late because
it is genuinely gated, not because it was queued badly.

## The UnitSafe gate

ucon's downstream goal is the [UnitSafe](https://github.com/withtwoemms/ucon-tools/tree/main/benchmarks/unitsafe)
benchmark: 500 problems scored on numerical, unit-string, and kind-of-quantity
accuracy, with 124 must-fail items — 62 dimension mismatches and 62 pairs that
**share a dimension and differ in kind**. The treatment is a language model
driving [ucon-tools](https://github.com/withtwoemms/ucon-tools); its `compute`
tool multiplies floats and tracks kinds as metadata, so the benchmark exercises
ucon's catalog, `.to()`, and unit rendering — not its arithmetic dispatch.

What that makes gate-critical in this repository, in order:

1. **The KOQ floor** (mechanism v2.3.0 ✓, angle clusters v2.4.0, remainder
   v3.1.0) — the arrival rule's refusing clause shipped in #322 and six clusters
   declare `default_kind`; the rest split by whether they precede or follow the
   retirement. Measured end to end through
   ucon-tools against the shipped catalog: the legitimate weighted
   conversion `0.5 Gy × 20 Sv/Gy` is **refused** when its factor is kinded
   (the lattice join is consulted, the `radiation_weighting` formula is not)
   and **mislabeled** `10 Sv [absorbed_dose]` when it is not; the must-fail
   direct `2 Gy → Sv` returns the same label. The tool cannot tell them
   apart. The fix is split across both repositories and ships together.
2. **Unity** (v2.3.1) — `one` as a real, parseable identity, and named
   dimension-one units that survive products. The `ea` placeholder leaking
   into every multiply-by-scalar result is the single largest unit-string
   failure class.
3. **Catalog correctness** — `lumen.base_form` (today `1 lm → 1 cd`
   converts), `Np ↔ dB` (off by 2 against SI Brochure Table 8, #336),
   `rankine`'s suppressed `base_form` (#339), and the two log edges that target
   a quantity other than the one they chart (#341: `nines` hides `x ↦ 1 − x`;
   `pH` is a level on `Dimension(concentration)`, where ISO 80000-9 item 9-37
   makes it dimension one).

What is **not** on the gate: currency (zero problems), the logarithmic chart
(zero), count placement (no count-vs-count items), and the kind algebra of
3.2.0 (unexercised by a float-path `compute`). Those remain library
correctness work and are sequenced accordingly. The larger lever for the score
is on the ucon-tools side — see its roadmap's v0.14.0 and v0.15.0.
## v1.9.x — Kind-of-Quantity Preview Line

**Theme:** Land the kind subsystem as a complete, standalone data model before binding it to arithmetic.

**Motivation:**
A dimension answers *what kind of measurement is this* at the level of physics (length, energy, time). A kind answers it at the level of physical interpretation: kinetic energy and thermal energy share `Dimension.energy` but are not interchangeable in every context; absorbed dose and equivalent dose share `Dimension.absorbed_dose` (J/kg) but only the latter accounts for radiation weighting. Type systems handle the dimensional level; the conceptual level needs its own structure.

The v1.9.x line introduces that structure incrementally, in three releases of decreasing scope:

- **v1.9.0 — Structure.** The data model: `Kind`, `KindLattice`, `KindFormula`, `FormulaRegistry`, TOML loaders. Equality on name, refinement via partial order, formula lookup by input-kind tuple. Indexed but inert fields (`commutative` beyond arity 2, `generalizes`, `aspect_rules`) reserve declarative space for later releases without forcing premature semantics. Shipped as opt-in preview — no top-level `ucon` namespace export, no `Number` integration.
- **v1.9.1 — Propagation.** Aspects (covariant tags carried on quantities) become real. `FormulaRegistry.apply(inputs)` returns the joined aspect set alongside the output kind. Aspect behavior under LCA join is pinned (intersect-on-join). Still caller-side; the library does not yet store kinds on `Number`.
- **v1.9.2 — Lookup completeness.** The registry consults the lattice during lookup. `commutative=True` honors all permutations, not just pairwise swap. `generalizes=True` matches via ancestor walk. Opt-in dimension fallback covers the long tail. Diagnostic surface (`LookupResult`, `MatchKind`) exposes which match tier resolved a call.

**Why three releases and not one:**
Each release establishes a property the next depends on. 1.9.0 fixes the vocabulary and storage shape. 1.9.1 fixes the data flow through application. 1.9.2 fixes the lookup completeness. Shipping these as one release would conflate three different categories of design risk: data model (rare changes, high cost), application semantics (frequent feedback during real use), and matching policy (intricate but mechanical). Separating them lets users adopt 1.9.0 against the eventual stable model while 1.9.1 and 1.9.2 evolve under real workloads.

**Why preview, not wired:**
Wiring kinds to `Number` is a v2.0-shaped change — it modifies arithmetic dispatch, introduces context managers for the active lattice/registry, and forces decisions about how kinds interact with `enforce_dimensions`, `UnitSystem`, conversion, and serialization. v1.9.x deliberately defers all of that. The preview surface lets the data model harden against real usage patterns before the integration that locks it in.

**Status:** Complete. All three releases shipped; full integration landed in v2.0.0.

---

## v2.0 — `UnitSystem` as a Value Type

**Theme:** Make a "system of units" something you *hold*, not something the module *is*. The universe of units becomes a first-class value with semantics, algebra, and lifetime.

**Motivation:**
Three structural threads in v1.x share a root cause and resolve together:

1. The name `UnitSystem` (`ucon/core.py:670`) currently labels a small record — `name + Dict[Dimension, Unit]` — while the responsibilities the name implies (the universe of known units, dimension singletons, conversion topology, parser context, algebra caches) live in module-level globals: `_REGISTRY`, `_DIMENSION_ATTRS`, `_DIM_*_CACHE`, the default `ConversionGraph`, the default `BasisGraph`, and basis-related ContextVars. The class is anemic; the module is the real aggregate. This split makes isolation hard, composition impossible, and invalidation a debugging exercise rather than a structural property. It is also the root cause of the v1.7.0 dimension-cache id-reuse bug.

2. The `ucon.basis` subpackage carries a type-level cycle (`vector → graph → transforms → vector`) that originated with the 1.6.6 implicit cross-basis arithmetic feature: `Vector.__mul__` / `__truediv__` consult the active `BasisGraph` at runtime. The 1.7.x refactors mitigated symptoms (deferred imports, lazy default-graph construction) but the underlying triangle remains.

3. The v1.9.x kind subsystem ships as a preview because wiring it to `Number` requires the same scope decisions v2.0 must make for `UnitSystem`: where does the active lattice/registry live, how do context managers compose with the active system, how do kinds survive conversion and serialization. Promoting KOQ to first-class is a v2.0-shaped problem precisely because it touches the same ambient-state surface.

All three are forms of *ambient state in the arithmetic path*. Eliminating one without eliminating the others leaves the principle violated. Adopting the value-type principle therefore implies the basis cycle break and the KOQ promotion, and each implies the others. They are one piece of work.

**API changes (breaking):**

*Universe of units becomes a value:*

- Today's `UnitSystem` is renamed `BaseUnits` (a mapping from dimension to chosen base unit).
- A new `UnitSystem` is introduced as a frozen value owning:
  - `units`, `dimensions`, `conversion_graph` (formerly `_REGISTRY`, `_DIMENSION_ATTRS`, the default `ConversionGraph`),
  - `basis`, `basis_graph`, `base_units`,
  - per-instance algebra caches (replacing the module-level `_DIM_*_CACHE`).
- Operations on `UnitSystem` are pure functions returning new systems: `extend`, `restrict`, `overlay`, `merge`.
- Relations between systems are first-class queries: `subsystem_of`, `compatible_with`, `diff`.
- Cross-system value movement is explicit: `system.adopt(number)` and `Bridge(A, B)` for translation.
- The default global system is retained as a convenience but is now *one* `UnitSystem` value among many, not the only universe.
- One `ContextVar` (`ucon.system.active._active`) replaces the family of basis-related ContextVars and module globals.

*Kind-of-Quantity becomes first-class:*

- `Number` accepts an optional `kind=` argument; the field is preserved through arithmetic and conversion.
- Arithmetic dispatches through the active `FormulaRegistry`: `a * b` consults the registry, applies the matching `KindFormula`, propagates aspects per `AspectRule`, and stamps the result kind.
- Scope is made explicit via the **`ActiveContext` substrate**: a frozen dataclass bundling `system + formulas + kinds + strict`, carried by a single `ucon._active` ContextVar. The `use(system, *, formulas=None, kinds=None, strict=None)` context manager overrides any subset of fields; unset fields inherit from the enclosing context. Typed read paths are `active()`, `active_system()`, `active_formulas()`, `active_kinds()`, `active_strict()`. This supersedes the earlier sketch of parallel `using_kind_lattice` / `using_formula_registry` context managers — collapsing all four ambient fields into one payload preserves the "one ContextVar" promise above without forcing callers to nest three separate `with` blocks.
- Conversion preserves kind by default (`Number.to(unit)` does not change kind); cross-kind movement is explicit.
- Pydantic and TOML serialization round-trip `kind` alongside `unit` and `quantity`.
- `@enforce_dimensions` gains an optional `kind=` constraint that complements the dimensional check.

*Basis arithmetic becomes explicit:*

- `Vector.__mul__` / `__truediv__` raise on different bases instead of consulting `BasisGraph`. `Vector` becomes strictly same-basis. This breaks the type-level cycle at its source: `Vector` no longer references `BasisGraph` or `BasisTransform`.
- Cross-basis arithmetic moves to explicit helpers in `ucon.basis.ops`:
  - `ops.unify(a, b) -> tuple[Vector, Vector]`
  - `ops.multiply_via(a, b, graph=None) -> Vector`
  - `ops.divide_via(a, b, graph=None) -> Vector`
  - The `graph` parameter defaults to `active().basis_graph`. Passing `system=` is also accepted.
- Migration: callers relying on implicit cross-basis arithmetic call the explicit `ops.*` helper.

**Module layout consequences:**

With ambient state retired, the basis subpackage falls into a clean DAG as a side effect — no separate file-reorganization workstream is needed. `Vector` no longer references `BasisGraph`, so deferred imports disappear; `_default_basis_graph` retires because `system.basis_graph` owns it; the `ucon.basis.active` ContextVars consolidate into one in `ucon.system.active`.

```
ucon/basis/
├── types.py        — Basis, BasisComponent, exceptions
├── builtin.py      — SI, CGS, NATURAL, ATOMIC, PLANCK, …
├── vector.py       — Vector with strict same-basis arithmetic (no BasisGraph reference)
├── transforms.py   — BasisTransform, ConstantBinding, ConstantBoundBasisTransform
├── graph.py        — BasisGraph (pure registry + path-finding)
└── ops.py          — explicit cross-basis helpers
```

Dependency order in `basis/`: `types → {builtin, vector} → transforms → graph → ops`. Every import lives at the top of its file. No `global`, no lazy factory, no deferred imports. The active-state plumbing that previously lived in `basis/active.py` and `basis/standard.py` moves to `ucon/system/` and `ucon/system/default.py` respectively, since "what is the current basis graph" is now equivalent to "what is the current system."

**Outcomes:**

- **Value semantics for the universe of units.** Two `UnitSystem`s coexist, can be compared, combined, and discarded without affecting each other.
- **Invalidation collapses into construction.** Caches are per-instance; "stale" cannot mean "across systems," and id-reuse hazards (the v1.7.0 cache-keying class of bug) are structurally impossible.
- **Closure under composition.** `extend` / `restrict` / `overlay` give `UnitSystem` an algebra with associativity and identity laws callers can rely on.
- **Zero hidden global state in arithmetic operators.** No basis graph consulted implicitly, no unit registry mutated implicitly, no dimension cache shared across logical scopes.
- **Zero deferred imports in `ucon.basis`.** The cycle is broken at the API level, not papered over with import tricks.
- **Cross-basis intent visible at the call site.** `ops.multiply_via(a, b)` instead of `a * b` doing something subtle.
- **Concurrency- and multi-tenant-ready.** Independent systems on independent threads/tasks/tenants without shared mutable state or locks.
- **Test isolation by default.** Tests construct the system they need; nothing leaks across imports.
- **Honest naming.** `UnitSystem` denotes a system; `BaseUnits` denotes a base-unit mapping; each name matches its contract.

**Status:** Complete. Released as v2.0.0 on 2026-06-07.

---

## Guiding Principle

> "If it can be measured, it can be represented.
> If it can be represented, it can be validated.
> If it can be validated, it can be trusted."

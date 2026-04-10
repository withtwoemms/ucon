# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.5.0] - 2026-04-10

### Added

- **Conversion factor uncertainty propagation.** When a conversion factor
  derives from a measured physical constant (e.g., Hartree energy, Planck
  mass), its CODATA 2022 relative uncertainty can now propagate into the
  converted result via GUM quadrature:
  `(δy/y)² = (δx/x)² + (δa/a)²`.

- **`rel_uncertainty` field on `Map` subclasses** — optional
  `rel_uncertainty: float = 0.0` on `LinearMap`, `AffineMap`, and
  `ReciprocalMap`. Composition rules:
  - `@` (composition): quadrature `sqrt(r₁² + r₂²)`
  - `inverse()`: preserved unchanged
  - `**n` (power): `|n| * r`
  - `ComposedMap`: computed property via quadrature of `outer` and `inner`
  - Default `0.0` means exact conversions carry zero overhead.

- **`Number.to(target, propagate_factor_uncertainty=False)`** — opt-in
  parameter. When `True`, combines measurement uncertainty and conversion
  factor uncertainty via GUM quadrature. When `False` (default), behavior
  is unchanged from prior versions.

- **8 new physical constants** in `ucon.constants` with CODATA 2022
  uncertainties:
  - Atomic-scale: `hartree_energy` (Eₕ), `rydberg_energy` (Ry),
    `bohr_radius` (a₀), `atomic_unit_of_time` (ℏ/Eₕ)
  - Planck-scale: `planck_mass` (m_P), `planck_length` (l_P),
    `planck_time` (t_P), `planck_temperature` (T_P)
  - All carry `category="measured"` and are accessible via
    `get_constant_by_symbol()` with both Unicode and ASCII aliases.

- **15 default graph edges with `rel_uncertainty`** from measured constants:
  - Atomic: kg↔electron_mass, J↔hartree, eV↔hartree, J↔rydberg,
    m↔bohr_radius, s↔atomic_time, electron_mass→hartree,
    bohr_radius→atomic_time
  - Planck: kg↔planck_mass, J↔planck_energy, eV↔planck_energy,
    m↔planck_length, s↔planck_time, K↔planck_temperature,
    planck_energy↔hartree

- **`EdgeDef.rel_uncertainty`** field in `ucon.packages` — `.ucon.toml`
  packages can now declare conversion factor uncertainty on `[[edges]]`
  entries.

- **TOML serialization of `rel_uncertainty`.** `_edge_dict()` emits
  `rel_uncertainty` when non-zero; `_build_edge_map()` reads it back.
  Backward-compatible: existing TOML files without the field deserialize
  with `rel_uncertainty=0.0`.

- **`to_toml()` dimension collection from unit registry.** Dimensions
  referenced by registered units (e.g., area, velocity, force) are now
  included in the output even when they have no dedicated edge partition.
  Required for self-contained TOML files that don't rely on a runtime
  dimension registry — preparatory for the TOML-as-source-of-truth
  transition.

- **`scripts/generate_comprehensive_toml.py`** — generation script that
  produces `examples/units/comprehensive.ucon.toml` from the default graph
  via `to_toml()`, with cosmetic array collapsing for readability.

- **`make toml`** — Makefile target that runs the TOML generation script.

- `tests/ucon/test_factor_uncertainty.py` — 32 new tests across 8 classes
  covering map construction, composition rules (quadrature, inverse,
  power), `Number.to()` backward compatibility, factor uncertainty
  propagation, multi-hop accumulation, and serialization round-trips.

- `tests/ucon/conversion/test_map.py::TestRelUncertaintyComposition` —
  6 new tests for `rel_uncertainty` composition, inverse, and power on
  `LinearMap` and `AffineMap`.

### Changed

- **`comprehensive.ucon.toml` is now machine-generated** from the default
  graph rather than hand-maintained. Contains 7 bases, 71 dimensions,
  15 transforms, 227 units, 148 edges, 17 product edges, and 42
  cross-basis edges (15 with `rel_uncertainty`).

- **`ucon.constants` used as single source for conversion factors in
  `ucon.graph`.** The default graph's `_build_standard_edges()` now loads
  full `Constant` objects and extracts both `.value` and `.uncertainty`,
  rather than using hard-coded numeric literals. This ensures conversion
  factor values and their uncertainties stay in sync with the constants
  module.

### Notes

- **Backward compatibility.** `propagate_factor_uncertainty` defaults to
  `False`. All existing code produces identical results. The
  `rel_uncertainty` field defaults to `0.0` and is omitted from TOML
  output when exact, so serialized files remain unchanged for exact
  conversions.

- **GUM model.** The implementation uses relative uncertainty because it
  composes cleanly under multiplication and is preserved under inversion.
  For affine maps (temperature), `rel_uncertainty` refers to the slope
  `a` only; the offset `b` is exact by definition.

## [1.4.0] - 2026-04-09

### Added

- **Planck basis** — 1-component energy basis (`E`) where ℏ = c = G = k_B = 1.
  - `PLANCK` basis in `ucon.basis.builtin`
  - `SI_TO_PLANCK` / `PLANCK_TO_SI` transforms via `ConstantBoundBasisTransform`
    with constant bindings for ℏ, c, G, k_B
  - `PLANCK_ENERGY` (E¹) and `PLANCK_LENGTH` (E⁻¹) dimensions
  - 5 Planck units: `planck_energy` (`E_P`), `planck_mass` (`m_P`),
    `planck_length` (`l_P`), `planck_time` (`t_P`),
    `planck_temperature` (`T_P`) — all with CODATA 2018 values
  - Mass and energy share `PLANCK_ENERGY` (E¹); length and time share
    `PLANCK_LENGTH` (E⁻¹). This is physically correct: when c = 1,
    mass ≡ energy and length ≡ time.

- **Atomic basis** — 1-component energy basis (`E`) where ℏ = e = mₑ = 4πε₀ = 1.
  - `ATOMIC` basis in `ucon.basis.builtin`
  - `SI_TO_ATOMIC` / `ATOMIC_TO_SI` transforms with constant bindings
    for a₀, ℏ, mₑc², e/ℏ
  - `ATOMIC_ENERGY` (E¹) and `ATOMIC_LENGTH` (E⁻¹) dimensions
  - 3 new atomic units: `bohr_radius` (`a_0`, `a0`), `atomic_time` (`t_au`),
    `electron_mass` (`m_e`)
  - Differs from Natural/Planck in that electric current is representable
    (I → E¹) but temperature is not (k_B ≠ 1)

- **Inter-basis isomorphisms** — 6 bidirectional 1×1 identity transforms
  connecting NATURAL, PLANCK, and ATOMIC bases:
  - `NATURAL_TO_PLANCK` / `PLANCK_TO_NATURAL` (mediated by G)
  - `NATURAL_TO_ATOMIC` / `ATOMIC_TO_NATURAL` (mediated by e, mₑ, 4πε₀)
  - `PLANCK_TO_ATOMIC` / `ATOMIC_TO_PLANCK` (mediated by G, e, mₑ, 4πε₀)
  - Cross-basis conversion edges: `eV ↔ planck_energy`,
    `eV ↔ hartree`, `planck_energy ↔ hartree`
  - Inter-basis edge factors are computed from shared SI bridge constants
    (e.g., `_eV_J / _EP_J`) rather than independently rounded, ensuring
    exact algebraic cancellation on round-trips.

- **CGS-EMU basis promotion** — `CGS_EMU` promoted from 3-component
  (`L, M, T`) to 4-component (`L, M, T, Φ`) basis to support the
  ESU↔EMU bridge:
  - `SI_TO_CGS_EMU` is now an 8×4 transform with `I → Φ¹` mapping
  - `CGS_ESU_TO_CGS_EMU` and `CGS_EMU_TO_CGS_ESU` bridge transforms
    (4×4) connecting the two electromagnetic subsystems
  - 15 ESU/EMU dimension vectors redefined with integer exponents on
    the expanded bases
  - ESU↔EMU conversion edges via the speed of light c:
    `statcoulomb ↔ abcoulomb`, `statvolt ↔ abvolt`,
    `statampere ↔ biot`, `statohm ↔ abohm`,
    `statfarad ↔ abfarad`, `stathenry ↔ abhenry`
  - Fulfills the v1.3.1 deferral: "ESU↔EMU cross-family conversion
    deferred to v1.4.0"

- 33+ new tests across `test_cross_basis.py`:
  `TestPlanckDimensionIsolation` (5), `TestPlanckConversions` (6),
  `TestAtomicDimensionIsolation` (7), `TestAtomicConversions` (6),
  `TestInterBasisIsomorphisms` (6 including full J→E_P→eV→Eₕ→J
  round-trip at `places=10`), plus ESU↔EMU bridge tests.

### Changed

- **`hartree` and `rydberg` moved from NATURAL to ATOMIC basis.**
  These units physically belong to the atomic system (ℏ = e = mₑ =
  4πε₀ = 1), not the particle-physics natural system. Their dimension
  changes from `NATURAL_ENERGY` to `ATOMIC_ENERGY`; numeric conversion
  values to SI are unchanged. Cross-basis edges from SI
  (`joule → hartree`, `joule → rydberg`) now route through
  `SI_TO_ATOMIC` instead of `SI_TO_NATURAL`.

- BasisGraph standard graph now registers 15 transforms (was 6):
  SI↔CGS, SI↔CGS_ESU, SI↔CGS_EMU, CGS_ESU↔CGS_EMU, SI↔NATURAL,
  SI↔PLANCK, SI↔ATOMIC, NATURAL↔PLANCK, NATURAL↔ATOMIC, PLANCK↔ATOMIC.

### Notes

- **Round-trip precision.** The full cross-basis round-trip
  `joule → planck_energy → electron_volt → hartree → joule` returns
  exactly 1.0 (verified at `places=10`). This is achieved by defining
  physical constants once and computing inter-basis factors from those
  shared values, avoiding independently-rounded intermediate constants.

- **Dimension sharing on reduced bases.** On any 1-component energy
  basis, units mapping to E¹ (energy, mass, temperature) share one
  `Dimension` object, and units mapping to E⁻¹ (length, time) share
  another. This is not a collision — it encodes the physics of
  c = ℏ = 1. Consequently, `planck_mass(1).to(planck_energy)` → 1
  and `planck_length(1).to(planck_time)` → 1 are both valid
  conversions.

## [1.3.1] - 2026-04-09

### Added

- **Photometric luminance units** — 4 new SI-basis ILLUMINANCE units:
  - `nit` (`nt`) — 1 cd/m², the SI-coherent luminance unit
  - `stilb` (`sb`) — 1 cd/cm² = 10,000 cd/m²
  - `lambert` (`La`) — (1/π) cd/cm² ≈ 3183.1 cd/m²
  - `apostilb` (`asb`) — (1/π) cd/m² ≈ 0.3183 cd/m²

  All four carry `base_form` with `prefactor` relative to `cd·m⁻²` and
  same-basis conversion edges (`nit→lux`, `stilb→nit`, `lambert→nit`,
  `apostilb→nit`). No cross-basis edges needed — these are SI-basis
  units because their dimensional formula involves `candela`, which
  belongs exclusively to the SI basis (CGS has no luminous intensity
  component).

- `TestPhotometricConversions` — 6 new tests covering `stilb↔nit`,
  `lambert→nit`, `apostilb→nit`, `stilb→lux` (multi-hop), and
  `phot→stilb` (cross-validation).

- Disposition comment on `phot` in `ucon/units.py` explaining why it
  uses SI-basis ILLUMINANCE despite being conventionally called "CGS".

- Deferral comment on ESU↔EMU cross-family conversion in `ucon/graph.py`,
  noting that the bridge requires promoting `CGS_EMU` to a 4-component
  basis and is scheduled for v1.4.0 (basis isomorphisms release). See
  `docs/internal/IMPLEMENTATION_basis_isomorphisms.md`.

### Notes

- **Cross-basis edge audit (24/24 CGS→SI, 7/7 SI→CGS).** All atomic
  CGS-family units were verified to have correct bidirectional edges in
  the default graph. No missing edges found.

- **ESU↔EMU cross-family conversion deferred to v1.4.0.** Requires
  promoting `CGS_EMU` to a 4-component basis (`L, M, T, Φ`),
  redefining ~15 dimension vectors, and adding a quantity-dependent
  `CGS_ESU_TO_CGS_EMU` 4×4 transform. This is a refactoring-scale
  change best done while the drift detector is still active as a safety
  net.

## [1.3.0] - 2026-04-08

### Added

- **`BaseForm`** — a new dataclass at `ucon.core.BaseForm` (re-exported from
  `ucon`) representing a unit's definitional decomposition into the canonical
  base units of its basis:

        1 U  ≡  prefactor × b₁^e₁ × b₂^e₂ × ... × bₙ^eₙ

  `BaseForm` is immutable, dimensionally consistent with its parent `Unit`,
  and references only base units of that unit's own basis.

- **`Unit.base_form`** — new public attribute on `Unit`, set at construction
  and never overwritten thereafter. Carried by 137 atomic units in
  `ucon/units.py`: **129** via constructor literal plus **8** via a
  one-shot `Unit._set_base_form` bootstrap (one per unit) for the
  self-referential SI base units (`kilogram`, `meter`, `second`, `ampere`,
  `kelvin`, `candela`, `mole`, `bit`), whose `base_form` cannot be expressed
  as a constructor literal because each references itself. The 4 affine
  non-base temperature units (`celsius`, `fahrenheit`, `rankine`, `reaumur`)
  carry `base_form = None` because `y = a·x + b` cannot be represented as a
  single `(prefactor, factors)` pair.

- **`Number.to_base()`** — new public method that returns a new `Number`
  expressed in the basis's coherent base units (e.g., SI: `kg, m, s, A, K,
  cd, mol`). It decomposes each factor of `self.unit` through its
  `base_form` and folds scale prefixes, without consulting any
  `ConversionGraph`. Units that lack a `base_form` (affine temperature,
  logarithmic, or graph-only units) are preserved as-is. Uncertainty is
  scaled by the same multiplier as the quantity. Examples:
  `kilometer(5).to_base()` → `<5000.0 m>`;
  `(kilometer(90) / hour(1)).to_base()` → `<25.0 m/s>`;
  `joule(1).to_base()` → `<1.0 m²·kg/s²>`.

- **`Number.canonical_magnitude`** — new public property that returns
  `self._canonical_magnitude` as a plain float. Useful at interop
  boundaries where a raw SI-coherent magnitude is needed (formula
  constants, JSON payloads, plotting libraries). The identity
  `n.to_base().quantity == n.canonical_magnitude` holds for every
  `Number n`. Prefer `to_base()` for unit-safe composition.

- `tests/ucon/test_quantity.py::TestNumberCanonicalBaseForm` — 19 new
  tests covering scaled units, compound units, derived units with
  multi-factor `base_form`, self-referential coherent bases, units with
  `base_form = None`, zero-quantity uncertainty propagation, and the
  `to_base().quantity == canonical_magnitude` identity.

- **`Unit._set_base_form(bf)`** — the single sanctioned post-construction
  mutation point for `base_form`. Guards against re-assignment
  (`ValueError`) and non-`BaseForm` inputs (`TypeError`). Used by the SI
  bootstrap in `ucon/units.py` and by the TOML deserializer in
  `ucon/serialization.py`; no other caller mutates `base_form`.

- **TOML serialization of `base_form`.** `to_toml` now emits each unit's
  `base_form` as an inline dict on the `[[units]]` entry:

        base_form = { prefactor = 1.0, factors = [ [ "meter", 1.0 ], [ "kilogram", 1.0 ], [ "second", -2.0 ] ] }

  `from_toml` resolves the factor references in a second pass after all
  units are registered, so forward references between units in the same
  document are supported. Affine and logarithmic units whose `base_form`
  is `None` omit the key. `examples/units/comprehensive.ucon.toml` ships
  with 134 `base_form` entries, round-trip verified.

- **`TestRoundTrip::test_base_form_roundtrip`** — asserts that every
  non-`RebasedUnit`'s `base_form` (both the `None` case and the populated
  case) survives TOML export/import bit-for-bit. Necessary because
  `Unit.__eq__` ignores `base_form` (`compare=False`), so
  `test_graph_equality` alone cannot detect a dropped or corrupted
  `base_form`.

- **Graph-independent quantity arithmetic.** `Number` equality, comparison,
  and arithmetic now route through `Number._canonical_magnitude`, a pure
  function of `(quantity, unit)` that reads `base_form` directly and never
  consults a `ConversionGraph`. Importing `ucon.units` and evaluating
  `gram(1000) == kilogram(1)`, dimensional ratios, and similar expressions
  no longer requires the default graph to be built. This is enforced by
  `tests/ucon/test_base_form.py::TestNoGraphInit::test_cold_start_subprocess`,
  which runs a subprocess-isolated smoke test against a fresh interpreter.

- **`scripts/generate_base_forms.py`** — a drift detector that compares the
  hand-written `base_form` literals in `ucon/units.py` against an internal
  BFS oracle computed over the standard conversion graph. Modes: `--check`
  (CI gate), `--report` (human-readable diff), `--emit` (regenerate
  literals). *(Scheduled to be superseded in v1.4.0 by a `ucon.toml`
  catalog validator. The drift dimension changes — from "hand-written
  literal vs. graph oracle" to "catalog TOML parseability, structural
  validity, and round-trip integrity" — but the pre-release CI gate
  remains: no malformed catalog reaches a tag.)*

- **`make base-forms-check`** — Makefile target wiring the drift detector
  into CI.

- **`base_forms` CI job** (`.github/workflows/tests.yaml`) — single-version
  GitHub Actions job (Python 3.12) that runs `make base-forms-check` on
  every push to `main` and every pull request, and is included in the
  aggregating `ci` job's `needs:` list so branch-protected merges are
  blocked on drift. This closes a gap in the pytest-based suite:
  `Unit.__eq__` uses `compare=False` for `base_form`, so neither
  `test_graph_equality` nor `test_base_form_roundtrip` can detect a
  hand-edited literal in `ucon/units.py` whose prefactor has silently
  drifted from what the graph would compute; only the BFS oracle
  can. In v1.4.0 this job will be replaced (not removed) by a
  `ucon.toml` catalog-validation job that asserts the shipped catalog
  parses, resolves all references, and round-trips cleanly through
  `to_toml`/`from_toml`. The release-blocking invariant — "no malformed
  catalog reaches a tag" — persists across the transition; only the
  oracle changes.

- **`tests/ucon/test_base_form.py`** — 34 tests covering the `BaseForm`
  contract, the graph-independence invariant, affine-unit `None` handling,
  and the cold-start subprocess smoke test.

- **`Unit.base_signature` / `UnitProduct.base_signature` /
  `Number.base_signature`** — new public properties returning a hashable,
  sorted tuple of `(base_unit_name, exponent)` pairs that fingerprint the
  unit's base-form decomposition. The prefactor is intentionally dropped:
  `base_signature` identifies the *shape* of a quantity (which base units
  participate, and with what exponents), not its scale. Useful as a
  dispatch key for grouping formula inputs by kind. The identity
  `n.base_signature == n.to_base().base_signature` holds for every
  `Number n`. Examples:
  `units.meter.base_signature → (("meter", 1.0),)`;
  `units.joule.base_signature → (("kilogram", 1.0), ("meter", 2.0), ("second", -2.0))`.
  Units with `base_form = None` (affine temperature, logarithmic) report
  themselves as a self-leaf so the API is total.

- **`Number.in_base_form`** — new public property; a fast predicate for
  "is this Number already what `to_base()` would return?" Returns `True`
  when every factor is at `Scale.one`, every underlying `Unit` is a leaf
  (either `base_form is None` or a self-referential coherent base), and
  any residual scale factor on a `UnitProduct` is `1.0`. Useful as a
  hot-path guard against redundant `to_base()` calls and as an invariant
  assertion at formula boundaries.

- **`Number.same_dimension_as(other)`** — new public method that returns
  `True` if `self` and `other` share a `Dimension`. Accepts a `Number`,
  `Unit`, or `UnitProduct`; raises `TypeError` for any other type. A
  lightweight, graph-free compatibility check for the common
  "can these be added / compared / fed into the same formula slot?"
  question, distinct from `Unit.is_compatible` which is unit-to-unit
  and basis-graph-aware.

- `tests/ucon/test_quantity.py::TestBaseSignature`,
  `TestNumberInBaseForm`, and `TestNumberSameDimensionAs` — 24 new tests
  covering coherent base units, derived units, prefactor independence,
  composition under arithmetic, the `to_base()` invariance identity,
  scaled-vs-unscaled distinctions, leaf-detection for `base_form = None`
  units, residual-scale-factor handling on `UnitProduct`, and the
  `TypeError` contract on `same_dimension_as`.

- **`ConversionGraph.add_edge` documented as public API.** The keyword-only
  signature (`src`, `dst`, `map`, `basis_transform`) was already in use
  but unmarked; v1.3.0 promotes it to a public, semver-stable surface
  with an expanded docstring covering the most common usage patterns
  (linear edges, affine temperature edges, composite-unit edges) and a
  cross-reference to `ConversionGraph.connect_systems` for bulk
  cross-basis registration. No behavioral change.

### Changed

- **`FORMAT_VERSION`** bumped from `"1.2"` to `"1.3"` in `ucon.serialization`
  to mark the addition of the optional `base_form` field on `[[units]]`
  entries. Older `1.2` files continue to load without warning (no
  `base_form` data to drop). Newer `1.3` files loaded by an older `1.2`
  library keep the same major version, so `_check_format_version` does
  not raise; it emits a `UserWarning` that the file is newer than
  supported, and any `base_form` entries are silently dropped by the
  older deserializer. Downstream consumers who serialize their own
  `.ucon.toml` files should bump their `format_version` when they begin
  emitting `base_form`.

### Notes

- `Number.to(target)` continues to route through `ConversionGraph.convert()`
  in both its fast path (plain `Unit → Unit`) and its general path
  (`UnitProduct → UnitProduct`). The graph remains load-bearing for
  everything `BaseForm` structurally cannot represent: affine temperature
  conversions, logarithmic and other non-linear conversions, cross-basis
  conversions (SI ↔ CGS ↔ natural via `RebasedUnit` edges), user-registered
  custom edges, and uncertainty propagation via `Map.derivative()`. This
  release decouples *arithmetic* from the graph; explicit conversion via
  `.to()` still uses it.

## [1.2.0] - 2026-04-06

### Added

- Full round-trip `ConversionGraph` serialization to TOML (`to_toml()` / `from_toml()`)
  - Bases, dimensions, and transforms (including `ConstantBoundBasisTransform` with fraction-exact matrices)
  - Unit edges with shorthand (`factor`, `factor`+`offset`) and explicit `map` for all 6 map types
  - Product edges for composite unit conversions (e.g., kWh → joule)
  - Cross-basis edges via `RebasedUnit` provenance (e.g., dyne → newton across CGS/SI)
  - Physical constants with full metadata (symbol, name, value, unit, uncertainty, source, category)
  - `ConversionContext` persistence via `[contexts.*]` TOML sections
  - `graph == restored` equality guaranteed for all graph types after round-trip
- `GraphLoadError` exception for structured error reporting during TOML import
- Strict parsing mode on `from_toml()` (default `strict=True`)
  - Raises `GraphLoadError` on unresolvable unit references in edges, product edges, and cross-basis edges
  - `strict=False` warns and skips unresolvable edges for forward-compatible loading
- Format version validation in `from_toml()`
  - Major version mismatch raises `GraphLoadError`
  - Newer minor version emits `UserWarning`
  - Missing `format_version` or `[package]` table accepted for backward compatibility
- Product expression grammar with `/` division support
  - Parser: `meter/second`, `mg/kg/day`, `kg*m/s^2` all parse correctly
  - Left-to-right arithmetic precedence (`*` and `/` are left-associative)
  - Invalid exponents raise `GraphLoadError` (previously returned `None`)
  - Emitter: uses `/` notation when there are both positive and negative exponents
- Implicit `Map` subclass discovery for TOML deserialization
  - Any imported `Map` subclass with a `_map_type` class attribute is automatically deserializable
  - `_build_map()` recursively resolves nested map specs (dicts with `"type"` keys)
  - Custom `Map` subclasses need only define `_map_type` and be imported before `from_toml()`
- `Map.to_dict()` base implementation with recursive serialization
  - Introspects dataclass fields, skips `_`-prefixed attributes
  - Recursively serializes `Map`-valued fields and lists containing `Map` instances
  - Subclasses may override to omit default values (e.g., `LogMap`, `ExpMap`)
- `_map_type` class attribute on all concrete `Map` subclasses: `LinearMap` (`"linear"`),
  `AffineMap` (`"affine"`), `LogMap` (`"log"`), `ExpMap` (`"exp"`),
  `ReciprocalMap` (`"reciprocal"`), `ComposedMap` (`"composed"`)
- `ConversionGraph.register_context()` for attaching named `ConversionContext` objects to a graph
- `ConversionGraph.__eq__` with comprehensive field comparison
  - Symmetric unit-edge comparison across all dimension partitions
  - Product-edge comparison by key set and map evaluation
  - Cross-basis edge comparison via `_cross_basis_edge_signature()`
  - Constants comparison across all metadata fields plus unit dimension
  - Loaded packages, basis graph topology, and context equality
- Serialization format reference documentation (`docs/reference/serialization-format.md`)
- `ucon[serialization]` optional dependency (`tomli-w`) for TOML export
- Arithmetic expression factors in `from_toml()` via `_parse_factor()`
  - `_build_edge_map()` now accepts string factor expressions (e.g., `"1/3"`, `"1852/3600"`)
  - Parity with `load_package()`, which already supported expression factors
- Production-ready `examples/units/comprehensive.ucon.toml`
  - Complete default conversion graph: 4 bases, 43 dimensions, 214 units, 139 edges, 18 product edges, 26 cross-basis edges, 1 context
  - Exact ratio factors where applicable (e.g., `"1/3"` for foot→yard, `"1/7"` for day→week)
  - Deduplicated cross-basis edges and cleaned empty unit entry from machine-generated export

### Changed

- `ConversionGraph._rebased` changed from `dict[Unit, list[RebasedUnit]]` to `dict[Unit, set[RebasedUnit]]`
  - Prevents duplicate `RebasedUnit` accumulation when multiple cross-basis edges share the same source unit and transform (e.g., joule → electron_volt/hartree/rydberg)
  - Eliminates cubic amplification of `[[cross_basis_edges]]` on repeated round-trips
  - `list_rebased_units()` return type unchanged (`dict[Unit, list[RebasedUnit]]`)
- Product expression parsing (`_parse_product_expression`) uses `get_unit_by_name()` as primary resolver
  - Scale-prefixed names (e.g., `kwatt`) now decompose correctly into `UnitFactor` with proper `Scale`
  - Falls back to `_resolve_unit()` when the full resolver is unavailable
- Map deserialization uses implicit subclass discovery instead of an explicit registry
  - `_build_map()` walks `Map.__subclasses__()` to find the class matching the `"type"` key
  - No registry to manage; defining `_map_type` on a subclass is sufficient
- Updated `docs/external/ucon-tools` submodule from 0.2.1 to 0.3.2

## [1.1.2] - 2026-04-03

### Added

- Binary scale prefixes: `tebi` (Ti, 2^40), `pebi` (Pi, 2^50), `exbi` (Ei, 2^60)
  - Enables parsing of `TiB`, `PiB`, `EiB` and other tebi/pebi/exbi-scaled units
  - Greedy prefix matching ensures `TB`/`PB` still resolve as tera/peta (decimal)
- Spelled-out scale aliases for common unit names via `register_priority_scaled_alias`
  - Length: `kilometer`, `centimeter`, `millimeter`, `micrometer`, `nanometer`, `picometer`
  - Mass: `milligram`, `microgram`
  - Time: `millisecond`, `microsecond`, `nanosecond`, `picosecond`
  - Frequency: `kilohertz`, `megahertz`, `gigahertz`
  - Volume: `milliliter`, `microliter`
  - Power: `kilowatt`, `megawatt`, `gigawatt`, `milliwatt`
  - Energy: `kilojoule`, `megajoule`
  - Pressure: `kilopascal`, `megapascal`, `hectopascal`
  - Voltage: `millivolt`, `kilovolt`
  - Current: `milliampere`, `microampere`
  - Information (decimal): `kilobyte`, `megabyte`, `gigabyte`, `terabyte`, `petabyte`,
    `kilobit`, `megabit`, `gigabit`
  - Information (binary): `kibibyte`, `mebibyte`, `gibibyte`, `tebibyte`, `pebibyte`, `exbibyte`

## [1.1.1] - 2026-04-02

### Fixed

- Cross-basis conversions for composite unit strings (e.g., `poise → Pa·s`, `reyn → Pa·s`)
  - Composite strings like `"Pa·s"`, `"m²/s"`, `"J/m²"` were parsed as multi-factor
    `UnitProduct`s rather than resolving to registered atomic unit aliases, causing
    cross-system (CGS↔SI) and same-dimension conversions to fail with spurious
    dimension mismatch or factor structure errors
  - `_convert_products()` now resolves products to atomic `Unit` equivalents via
    `as_unit()` and the graph's name registry before dimension comparison and
    factorwise decomposition
  - Affected units: poise, stokes, galileo, reyn, kayser, langley, oersted

### Added

- `UnitProduct.as_unit()` method to extract the underlying `Unit` from trivial
  single-factor products (one factor, exponent 1, `Scale.one`)

## [1.1.0] - 2026-04-01

### Added

- `[package]` table in `.ucon.toml` format for structured package metadata
  - `name`, `version`, `description`, `requires` fields
  - Legacy top-level keys still supported with deprecation warning
- `shorthand` field on `UnitDef` for explicit display symbols (e.g., `shorthand = "nmi"`)
- `requires` field on `UnitPackage` for declaring package dependencies
  - Validated during `with_package()` — raises `PackageLoadError` if dependencies not loaded
- `[[constants]]` section in `.ucon.toml` for domain-specific physical constants
  - `ConstantDef` dataclass with `symbol`, `name`, `value`, `unit`, `uncertainty`, `source`, `category`
  - Constants materialized onto graph during `with_package()`
  - Accessible via `graph.package_constants` property
- Explicit `map` type on `[[edges]]` for non-linear conversion maps
  - Supported types: `linear`, `affine`, `log`, `exp`, `reciprocal`
  - `map_spec` field on `EdgeDef` with `_build_map()` dispatch
  - `map` takes precedence over `factor`/`offset` shorthand when both present
- `ExpMap` added to package format map type registry
- Verified composite unit expressions (e.g., `"watt*hour"`, `"kg*m/s^2"`) resolve
  correctly as `src`/`dst` in `EdgeDef.materialize()` — product edges work without
  format changes
- `ConstantDef` exported from `ucon` top-level package

## [1.0.0] - 2026-03-31

### Added

- `ReciprocalMap(a)` conversion map for inversely proportional relationships (`y = a / x`)
  - Self-inverse: `ReciprocalMap(a).inverse()` returns `ReciprocalMap(a)`
  - Used for spectroscopy conversions (e.g., frequency = c / wavelength)
- EXPOSURE dimension (`I·T/M`) and roentgen unit (`R_exp`) for radiation exposure
  - `coulomb_per_kilogram` bridge unit with `C/kg` alias
  - 1 R = 2.58e-4 C/kg conversion edge
- CGS-EMU electromagnetic unit system
  - `SI_TO_CGS_EMU` basis transform mapping SI current to `L^(1/2)·M^(1/2)·T^(-1)` in CGS
  - 6 CGS-EMU dimensions: `CGS_EMU_CURRENT`, `CGS_EMU_CHARGE`, `CGS_EMU_VOLTAGE`, `CGS_EMU_RESISTANCE`, `CGS_EMU_CAPACITANCE`, `CGS_EMU_INDUCTANCE`
  - 7 CGS-EMU units: `biot` (abampere), `abcoulomb`, `abvolt`, `abohm`, `abfarad`, `abhenry`, `gilbert`
  - Cross-basis edges: ampere↔biot, coulomb↔abcoulomb, volt↔abvolt, ohm↔abohm, farad↔abfarad, henry↔abhenry
- `ConversionContext` for scoped cross-dimensional conversions (`ucon/contexts.py`)
  - `ContextEdge` dataclass for cross-dimensional edge specifications
  - `using_context()` context manager that copies the graph, injects context edges, and scopes via `using_graph()`
  - Built-in `spectroscopy` context: wavelength/frequency/energy via c and h
  - Built-in `boltzmann` context: temperature/energy via k_B
  - Cross-dimensional BFS fallback in `ConversionGraph._bfs_convert_cross_dimensional()`
- Réaumur temperature scale (`reaumur`, aliases: `°Ré`, `degRe`)
  - 1 °Ré = 1.25 °C conversion edge
- Historical electrical units
  - `international_ampere` (`A_int`): 1 A_int = 1.000022 A
  - `international_volt` (`V_int`): 1 V_int = 1.00034 V
  - `international_ohm` (`ohm_int`): 1 Ω_int = 1.00049 Ω
- `CyclicInconsistency`, `spectroscopy`, `boltzmann`, `register_unit` exported from top-level package
- `__all__` declarations for `ucon.maps` and `ucon.graph`
- `SECURITY.md` vulnerability disclosure policy
- `SUPPORT.md` semantic versioning, LTS, and backward-compatibility policy

### Changed

- `ConversionGraph._rebased` changed from `dict[Unit, RebasedUnit]` to `dict[Unit, list[RebasedUnit]]`
  - Fixes collision when multiple basis transforms register rebased entries for the same source unit (e.g., CGS-ESU and CGS-EMU both rebasing `ampere`)
  - `list_rebased_units()` now returns `dict[Unit, list[RebasedUnit]]`
- Scalar conversion performance: 5–50x faster than v0.11.0 across all benchmarks
  - Fast paths in `UnitProduct.__init__` for single-factor and two-factor cases
  - Cached `UnitProduct.from_unit()` results
  - Plain-Unit fast path in `Number.to()` bypassing UnitProduct wrapping
  - Hash caching on `Vector`, `Dimension`, `Unit`, `UnitFactor`
  - Dimension algebra caching (`__mul__`, `__truediv__`, `__pow__`)
  - `Vector` components use `int` instead of `Fraction` for common cases
- Removed `_Quantifiable` and `_none` from `ucon.quantity.__all__`

## [0.11.0] - 2026-03-28

### Changed

- `ucon.basis` is now a subpackage (`ucon/basis/`) with four modules:
  - `ucon.basis` (`__init__.py`) — core types: `Basis`, `BasisComponent`, `Vector`, `LossyProjection`, `NoTransformPath`
  - `ucon.basis.builtin` — shipped basis instances: `SI`, `CGS`, `CGS_ESU`, `NATURAL`
  - `ucon.basis.transforms` — transform types and instances: `BasisTransform`, `ConstantBoundBasisTransform`, `ConstantBinding`, `SI_TO_CGS`, `CGS_TO_SI`, `SI_TO_CGS_ESU`, `SI_TO_NATURAL`, `NATURAL_TO_SI`
  - `ucon.basis.graph` — registry and context scoping: `BasisGraph`, `get_default_basis()`, `get_basis_graph()`, `using_basis()`, `using_basis_graph()`
  - All symbols remain importable from `ucon.basis` and `ucon` via re-exports
- Integration modules moved to `ucon.integrations` subpackage:
  - `ucon.numpy` → `ucon.integrations.numpy`
  - `ucon.pandas` → `ucon.integrations.pandas`
  - `ucon.polars` → `ucon.integrations.polars`
  - `ucon.pydantic` → `ucon.integrations.pydantic`
- Package discovery changed from explicit list to `setuptools.packages.find`

### Removed

- `ucon.bases` module (contents split into `ucon.basis.builtin` and `ucon.basis.transforms`)
- `ucon.quantity` module (backward-compatibility shim; import `Number`, `Ratio` from `ucon.core` or `ucon`)

## [0.10.1] - 2026-03-25

### Added

- Affine conversion support in `EdgeDef` (#215)
  - `EdgeDef` gains `offset: float = 0.0` field for affine conversions (e.g., temperature scales)
  - `materialize()` uses `AffineMap(factor, offset)` when offset is non-zero, `LinearMap(factor)` otherwise
  - `load_package()` reads optional `offset` field from TOML `[[edges]]` definitions
  - Backward compatible: existing packages and edge definitions are unaffected
- Domain-Specific Bases documentation (`docs/guides/domain-bases/`)
  - Explains how to resolve SI dimensional degeneracies with extended bases
  - Radiation Dosimetry: Gy vs Sv vs Gy(RBE) vs effective dose
  - Pharmacology: drug potency, IU variations, morphine equivalents
  - Clinical Chemistry: molarity vs osmolarity, Bq vs Hz, mEq vs mmol
  - Classical Mechanics: torque vs energy, surface tension vs spring constant
  - Thermodynamics: heat capacity vs entropy

## [0.10.0] - 2026-03-01

### Added

- NumPy array support via `NumberArray` class
  - Vectorized arithmetic with unit tracking and uncertainty propagation
  - Vectorized conversion: `heights.to(units.foot)`
  - Reduction operations: `sum()`, `mean()`, `std()`, `min()`, `max()`
  - Comparison operators returning boolean arrays for filtering
  - N-D array support with broadcasting
  - Callable syntax: `units.meter([1, 2, 3])` returns `NumberArray`
- Pandas integration via `NumberSeries` and `UconSeriesAccessor`
  - `df['height'].ucon.with_unit(units.meter).to(units.foot)`
  - Arithmetic preserves unit semantics
- Polars integration via `NumberColumn`
  - Wraps `pl.Series` with unit metadata
  - `.to()` conversion with unit tracking
- Map array support for vectorized operations
  - `LinearMap`, `AffineMap`, `LogMap`, `ExpMap` work with numpy arrays
  - `_log()` and `_exp()` helpers for scalar/array compatibility
- Optional dependencies: `ucon[numpy]`, `ucon[pandas]`, `ucon[polars]`
- Performance caching for repeated operations
  - Conversion path caching in `ConversionGraph`
  - Scale factor caching for scale-only conversions
  - Unit multiplication/division caching
  - `fold_scale()` result caching on `UnitProduct`
- Performance benchmarks: `make benchmark`, `make benchmark-pint`
- Documentation: `docs/guides/numpy-arrays.md`, `docs/guides/pandas-integration.md`, `docs/guides/polars-integration.md`
- Example notebook: `examples/scientific_computing.ipynb`

### Changed

- `Unit.__call__` and `UnitProduct.__call__` return `NumberArray` when given list or ndarray input

## [0.9.4] - 2026-02-28

### Changed

- MCP subpackage extracted to [ucon-tools](https://github.com/withtwoemms/ucon-tools) (#212)
  - Install MCP server via `pip install ucon-tools[mcp]`
  - Core ucon package no longer has MCP dependencies
  - Namespace package support via `pkgutil.extend_path()` enables coexistence

### Removed

- `ucon.mcp` subpackage (moved to ucon-tools)
- `ucon-mcp` CLI entry point (now in ucon-tools)
- `mcp` optional dependency
- MCP documentation (moved to ucon-tools, sourced via submodule)

## [0.9.3] - 2026-02-26

### Added

- Natural units support with `ConstantBoundBasisTransform` (#206)
  - `NATURAL` basis where c = ℏ = k_B = 1 (all quantities reduce to powers of energy)
  - `SI_TO_NATURAL` transform maps SI dimensions to natural units (e.g., velocity → dimensionless)
  - `NATURAL_TO_SI` inverse transform with constant bindings for reconstruction
  - `ConstantBinding` records relationships between dimensions via physical constants
  - `LossyProjection` exception for dimensions without natural unit representation (e.g., current)
  - `allow_projection=True` option to drop unrepresentable dimensions
- Example demos for alternative unit systems (`examples/basis/`)
  - `natural_units_demo.py` — particle physics natural units
  - `geometrized_units_demo.py` — general relativity units (c = G = 1)
  - `elemental_units_demo.py` — custom "elemental" basis
- Natural units guide in `docs/guides/natural-units.md`
- Natural units section in API reference `docs/reference/api.md`
- Custom constants documentation in README and API reference
- Comprehensive test suite for natural units (`tests/ucon/test_natural_units.py`)

### Fixed

- MCP session state persistence across tool calls (#209)
  - Custom units defined via `define_unit()` are now resolvable in subsequent `define_conversion()` calls
  - Replaced `ContextVar`-based isolation (per-task) with lifespan context (per-session)
  - Added `SessionState` protocol and `DefaultSessionState` for injectable session management
  - All session-dependent tools now use FastMCP `Context` injection
- MCP session unit safety and visibility improvements (#209)
  - `define_unit()` now rejects duplicate unit names (prevents silent edge destruction)
  - `define_unit()` now rejects alias collisions (prevents silent overwrites and cross-dimension corruption)
  - `check_dimensions()` now sees session-defined units
  - `list_units()` now includes session-defined units
  - `compute()` correctly resolves session-defined units in denominators with numeric prefixes

## [0.9.2] - 2026-02-25

### Added

- MCP tools for physical constants (#204)
  - `list_constants(category)` lists available constants filtered by category
    - Categories: `"exact"` (7), `"derived"` (3), `"measured"` (7), `"session"`, `"all"`
  - `define_constant(symbol, name, value, unit, uncertainty, source)` creates session constants
  - Session constants persist until `reset_session()` is called
- `all_constants()` function to enumerate built-in constants
- `get_constant_by_symbol()` function for constant lookup by symbol or alias
- `Constant.category` field classifying constants as `"exact"`, `"derived"`, `"measured"`, or `"session"`
- MCP tools reference documentation for constants in `docs/reference/mcp-tools.md`
- Physical constants section in API reference `docs/reference/api.md`

### Changed

- `reset_session()` now clears session constants in addition to custom units and conversions

## [0.9.1] - 2026-02-25

### Added

- pH unit with concentration dimension for mol/L ↔ pH conversions (#204)
  - `(units.mole / units.liter)(1e-7).to(units.pH)` returns `<7.0 pH>`
  - `units.pH(7.0).to(units.mole / units.liter)` returns `<1e-07 mol/L>`
  - Follows established pattern: pH has concentration dimension (like dBm has POWER)
- Logarithmic units documentation in `docs/reference/units-and-dimensions.md`
- `examples/units/logarithmic.py` demonstration module

## [0.9.0] - 2026-02-25

### Added

- `Constant` class for physical constants with CODATA uncertainties
- SI defining constants (exact): `c`, `h`, `e`, `k_B`, `N_A`, `K_cd`, `ΔνCs`
- Derived constants (exact): `ℏ` (hbar), `R` (molar gas), `σ` (Stefan-Boltzmann)
- Measured constants: `G`, `α`, `m_e`, `m_p`, `m_n`, `ε₀`, `μ₀`
- Unicode aliases: `c`, `h`, `ℏ`, `k_B`, `N_A`, `G`, `α`, `ε₀`, `μ₀`, `mₑ`, `mₚ`, `mₙ`
- ASCII aliases: `hbar`, `alpha`, `epsilon_0`, `mu_0`, `m_e`, `m_p`, `m_n`
- `Constant` arithmetic returns `Number` with uncertainty propagation
- `constants` module exported from `ucon`

## [0.8.5] - 2026-02-25

### Added

- `parse()` function for parsing human-readable quantity strings into `Number` objects
  - Basic quantities: `parse("60 mi/h")` returns `Number(60, mile/hour)`
  - Scientific notation: `parse("1.5e3 m")` returns `Number(1500, meter)`
  - Uncertainty with `±`: `parse("1.234 ± 0.005 m")` returns `Number` with uncertainty
  - Uncertainty with `+/-`: `parse("1.234 +/- 0.005 m")` (ASCII alternative)
  - Parenthetical uncertainty: `parse("1.234(5) m")` means `1.234 ± 0.005`
  - Pure numbers: `parse("100")` returns dimensionless `Number`

### Removed

- `setup.py` (redundant; `pyproject.toml` is the single source of truth)

## [0.8.4] - 2026-02-25

### Added

- `using_basis()` context manager for thread-safe scoped basis override
- `using_basis_graph()` context manager for thread-safe scoped BasisGraph override
- `get_default_basis()` accessor returning context-local basis or SI fallback
- `get_basis_graph()` accessor returning context-local or standard BasisGraph
- `set_default_basis_graph()` for module-level BasisGraph replacement
- `reset_default_basis_graph()` to restore standard BasisGraph on next access
- `Dimension.from_components()` and `Dimension.pseudo()` now respect context basis

## [0.8.3] - 2026-02-25

### Added

- Auto-generated `dimension.pyi` stubs for IDE code completion (`make stubs`)
- `Unit.is_compatible(other, basis_graph)` method for checking conversion compatibility
- `Unit.basis` property exposing the unit's dimensional basis
- `convert()` validates dimensional compatibility via `BasisGraph`
- `ConversionGraph.connect_systems()` for bulk cross-basis edge registration
- `ConversionGraph.list_rebased_units()` for introspection
- Dual-Graph Architecture documentation (`docs/architecture/dual-graph-architecture.md`)
- Cross-basis conversion guide in Custom Units & Graphs
- Basis System section in API reference
- CI: merge gate job, concurrency control, dependency caching, docs build check
- CI: CHANGELOG entry required for all PRs
- CHANGELOG with full version history
- Automated GitHub Releases from CHANGELOG on tag push
- Tests for Pydantic dimension constraints and constrained_number factory

### Changed

- `RebasedUnit` now uses `ucon.basis.BasisTransform` (unified implementation)
- Removed old `BasisTransform` from `ucon/core.py`
- Removed `NewBasisTransform` alias from exports
- Updated ConversionGraph internals documentation with BasisGraph integration
- Updated API reference with cross-basis conversion methods

## [0.8.2] - 2026-02-24

### Added

- Basis-aware Dimensions (#193)

## [0.8.1] - 2026-02-24

### Added

- BasisGraph and standard bases (#191)

## [0.8.0] - 2026-02-23

### Added

- Basis abstraction (#189)

## [0.7.7] - 2026-02-23

### Added

- MCP server documentation (#188)
- Incompatible Python versions skip MCP tests (#186)
- MCP formula tools (#185)
- Architecture docs (#182)

## [0.7.6] - 2026-02-20

### Added

- Public-facing documentation site (#168)
- Getting Started guides (#175)
- Reference docs and styling (#180)
- Units extensions support for MCP (#167)

### Fixed

- Residual scale factor bug (#178)

## [0.7.5] - 2026-02-13

### Added

- True generic support for Pydantic integration (#166)

## [0.7.4] - 2026-02-12

### Added

- UnitPackage for unit organization (#164)

## [0.7.3] - 2026-02-12

### Added

- Graph-local name resolution (#163)
- MCP "compute" tool (#158)

## [0.7.2] - 2026-02-10

### Added

- Dimension.count for counting dimensions (#157)

## [0.7.1] - 2026-02-10

### Added

- MCP error infrastructure for multi-step chains (#154)

## [0.7.0] - 2026-02-09

### Added

- MCP error suggestions (#152)

## [0.6.11] - 2026-02-08

### Added

- Dimension enforcement decorator (#150)

## [0.6.10] - 2026-02-08

### Added

- Type-safe generics (#149)

## [0.6.9] - 2026-02-08

### Changed

- Improved repr for derived Dimensions (#148)

## [0.6.8] - 2026-02-04

### Added

- Parser revamp (#144)

## [0.6.7] - 2026-02-04

### Changed

- Factor structure normalization (#143)

## [0.6.6] - 2026-02-04

### Added

- New chemical engineering units (#142)

## [0.6.5] - 2026-02-04

### Fixed

- Same unit ratio information loss (#138)

## [0.6.4] - 2026-02-04

### Fixed

- Cubic centimeter (cc) support (#136)

## [0.6.3] - 2026-02-04

### Fixed

- Microgram (mcg) recognition (#134)

## [0.6.2] - 2026-02-04

### Fixed

- Milli-inch disambiguation (#133)

## [0.6.1] - 2026-02-03

### Added

- Nines notation support (#127)

## [0.6.0] - 2026-02-03

### Added

- MCP server (#121)
- Pydantic integration (#117)

### Changed

- uv replaces nox for task running (#120)

## [0.5.2] - 2026-02-02

### Added

- Basis transforms and unit systems (#108, #109, #110, #111, #112, #113)

## [0.5.1] - 2026-02-01

### Added

- Uncertainty propagation (#106)

## [0.5.0] - 2026-02-01

### Added

- Dimensionless units (#104)

## [0.4.2] - 2026-01-30

### Added

- Number simplification (#95)

## [0.4.1] - 2026-01-30

### Added

- Information dimension (#96)

## [0.4.0] - 2026-01-30

### Added

- ConversionGraph and Maps (#90)
- Ergonomic unit conversion with `Number.to()` (#92)

## [0.3.5] - 2026-01-27

### Added

- UnitFactor and UnitProduct exports from main package (#88)

### Changed

- Unit and UnitProduct are now siblings (no inheritance) (#87)
- Unit combination refactor (#85)
- New license and copyright statements (#84)

## [0.3.4] - 2025-11-29

### Added

- Derived dimensions and composite units (#81)
- Scale multiplies Unit (#78)
- Unit provides Scale (#77)
- New package structure (#76)
- Dimension exponentiation (#73)
- Support for derived dimensions (#72)
- ucon.algebra module (#69)

## [0.3.3] - 2025-10-27

### Changed

- Number refactor (#61)

## [0.3.2] - 2025-10-24

### Added

- Scale refactor (#54)
- Mermaid diagram for architecture (#49)

### Changed

- CI simplification (#59, #57, #55)

## [0.3.1] - 2025-10-24

### Added

- Exponent refactor (#45)
- ROADMAP.md (#42)

### Changed

- Formalized Python version support (#39)
- CI workflow sequencing (#37)

## [0.3.0] - 2025-10-18

### Added

- Dimension abstraction (#32)
- Coverage report badge (#30)

### Changed

- File structure for multiple modules (#31)
- CI pipeline upgrades (#34)

## [0.2.2] - 2021-12-08

### Changed

- Maintenance release

## [0.2.1] - 2020-09-07

### Changed

- Maintenance release

## [0.2.0] - 2020-09-07

### Added

- Initial public API

## [0.1.1] - 2020-09-07

### Fixed

- Initial bug fixes

## [0.1.0] - 2020-09-07

### Added

- Initial alpha release

## [0.0.1] - 2020-09-05

### Added

- Project scaffolding

## [0.0.0] - 2020-08-08

### Added

- Initial commit

<!-- Links -->
[Unreleased]: https://github.com/withtwoemms/ucon/compare/1.5.0...HEAD
[1.5.0]: https://github.com/withtwoemms/ucon/compare/1.4.0...1.5.0
[1.4.0]: https://github.com/withtwoemms/ucon/compare/1.3.1...1.4.0
[1.3.1]: https://github.com/withtwoemms/ucon/compare/1.3.0...1.3.1
[1.3.0]: https://github.com/withtwoemms/ucon/compare/1.2.0...1.3.0
[1.2.0]: https://github.com/withtwoemms/ucon/compare/1.1.2...1.2.0
[1.1.2]: https://github.com/withtwoemms/ucon/compare/1.1.1...1.1.2
[1.1.1]: https://github.com/withtwoemms/ucon/compare/1.1.0...1.1.1
[1.1.0]: https://github.com/withtwoemms/ucon/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/withtwoemms/ucon/compare/0.11.0...1.0.0
[0.11.0]: https://github.com/withtwoemms/ucon/compare/0.10.1...0.11.0
[0.10.1]: https://github.com/withtwoemms/ucon/compare/0.10.0...0.10.1
[0.10.0]: https://github.com/withtwoemms/ucon/compare/0.9.4...0.10.0
[0.9.4]: https://github.com/withtwoemms/ucon/compare/0.9.3...0.9.4
[0.9.3]: https://github.com/withtwoemms/ucon/compare/0.9.2...0.9.3
[0.9.2]: https://github.com/withtwoemms/ucon/compare/0.9.1...0.9.2
[0.9.1]: https://github.com/withtwoemms/ucon/compare/0.9.0...0.9.1
[0.9.0]: https://github.com/withtwoemms/ucon/compare/0.8.5...0.9.0
[0.8.5]: https://github.com/withtwoemms/ucon/compare/0.8.4...0.8.5
[0.8.4]: https://github.com/withtwoemms/ucon/compare/0.8.3...0.8.4
[0.8.3]: https://github.com/withtwoemms/ucon/compare/0.8.2...0.8.3
[0.8.2]: https://github.com/withtwoemms/ucon/compare/0.8.1...0.8.2
[0.8.1]: https://github.com/withtwoemms/ucon/compare/0.8.0...0.8.1
[0.8.0]: https://github.com/withtwoemms/ucon/compare/0.7.7...0.8.0
[0.7.7]: https://github.com/withtwoemms/ucon/compare/0.7.6...0.7.7
[0.7.6]: https://github.com/withtwoemms/ucon/compare/0.7.5...0.7.6
[0.7.5]: https://github.com/withtwoemms/ucon/compare/0.7.4...0.7.5
[0.7.4]: https://github.com/withtwoemms/ucon/compare/0.7.3...0.7.4
[0.7.3]: https://github.com/withtwoemms/ucon/compare/0.7.2...0.7.3
[0.7.2]: https://github.com/withtwoemms/ucon/compare/0.7.1...0.7.2
[0.7.1]: https://github.com/withtwoemms/ucon/compare/0.7.0...0.7.1
[0.7.0]: https://github.com/withtwoemms/ucon/compare/0.6.11...0.7.0
[0.6.11]: https://github.com/withtwoemms/ucon/compare/0.6.10...0.6.11
[0.6.10]: https://github.com/withtwoemms/ucon/compare/0.6.9...0.6.10
[0.6.9]: https://github.com/withtwoemms/ucon/compare/0.6.8...0.6.9
[0.6.8]: https://github.com/withtwoemms/ucon/compare/0.6.7...0.6.8
[0.6.7]: https://github.com/withtwoemms/ucon/compare/0.6.6...0.6.7
[0.6.6]: https://github.com/withtwoemms/ucon/compare/0.6.5...0.6.6
[0.6.5]: https://github.com/withtwoemms/ucon/compare/0.6.4...0.6.5
[0.6.4]: https://github.com/withtwoemms/ucon/compare/0.6.3...0.6.4
[0.6.3]: https://github.com/withtwoemms/ucon/compare/0.6.2...0.6.3
[0.6.2]: https://github.com/withtwoemms/ucon/compare/0.6.1...0.6.2
[0.6.1]: https://github.com/withtwoemms/ucon/compare/0.6.0...0.6.1
[0.6.0]: https://github.com/withtwoemms/ucon/compare/0.5.2...0.6.0
[0.5.2]: https://github.com/withtwoemms/ucon/compare/0.5.1...0.5.2
[0.5.1]: https://github.com/withtwoemms/ucon/compare/0.5.0...0.5.1
[0.5.0]: https://github.com/withtwoemms/ucon/compare/0.4.2...0.5.0
[0.4.2]: https://github.com/withtwoemms/ucon/compare/0.4.1...0.4.2
[0.4.1]: https://github.com/withtwoemms/ucon/compare/0.4.0...0.4.1
[0.4.0]: https://github.com/withtwoemms/ucon/compare/0.3.5...0.4.0
[0.3.5]: https://github.com/withtwoemms/ucon/compare/0.3.4...0.3.5
[0.3.4]: https://github.com/withtwoemms/ucon/compare/0.3.3...0.3.4
[0.3.3]: https://github.com/withtwoemms/ucon/compare/0.3.2...0.3.3
[0.3.2]: https://github.com/withtwoemms/ucon/compare/0.3.1...0.3.2
[0.3.1]: https://github.com/withtwoemms/ucon/compare/0.3.0...0.3.1
[0.3.0]: https://github.com/withtwoemms/ucon/compare/0.2.2...0.3.0
[0.2.2]: https://github.com/withtwoemms/ucon/compare/0.2.1...0.2.2
[0.2.1]: https://github.com/withtwoemms/ucon/compare/0.2.0...0.2.1
[0.2.0]: https://github.com/withtwoemms/ucon/compare/0.1.1...0.2.0
[0.1.1]: https://github.com/withtwoemms/ucon/compare/0.1.0...0.1.1
[0.1.0]: https://github.com/withtwoemms/ucon/compare/0.0.1...0.1.0
[0.0.1]: https://github.com/withtwoemms/ucon/compare/0.0.0...0.0.1
[0.0.0]: https://github.com/withtwoemms/ucon/releases/tag/0.0.0

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-06-07

### Added

- `UnitSystem.extend`, `restrict`, `merge`, and `with_unit` /
  `with_conversion` / `with_basis` / `with_basis_graph` incremental
  constructors.
- `UnitSystem.subsystem_of`, `compatible_with`, `diff`, `shared_units`,
  `shared_dimensions` relation methods.
- `ConflictPolicy` enum (`RAISE`, `PREFER_SELF`, `PREFER_OTHER`),
  `ExtendConflict`, `RegistryDiff`, `SystemDiff` — exported from
  `ucon.system` and re-exported from `ucon`.
- `UnitSystem.adopt(n)` cross-system value rebinding and `Bridge`
  dataclass (`src`, `dst`, `rename`, `basis_transform`) with `apply`,
  `inverse`, `__matmul__`; synonym-only `rename` validated at
  construction via `InvalidRename`.
- **`ActiveContext` substrate (v2.0 §3.4)** — frozen dataclass that
  bundles the active `UnitSystem` with a `FormulaRegistry` (kind-aware
  arithmetic dispatch table), a `KindLattice` (kind taxonomy), and a
  `strict` flag. This is the payload now carried by the
  `ucon._active` ContextVar. Keeping `formulas` and `kinds` off
  `UnitSystem` is deliberate: a system does not own its formulas, and
  the substrate lets callers swap the dispatch table without
  rebuilding the system. Single-ContextVar discipline is preserved —
  the bundle ships as one payload rather than spawning sibling
  ContextVars for each field.
- Typed accessors `active_system`, `active_formulas`, `active_kinds`,
  `active_strict` — the only sanctioned read paths for the bundled
  fields. Exported from `ucon.system` and re-exported from `ucon`.
- `ActiveContext`, `FormulaRegistry`, `Kind`, `KindLattice` re-exported
  from the top-level `ucon` package.
- Tests under `tests/ucon/system/`: `test_algebra.py`,
  `test_algebra_laws.py`, `test_relations.py`, `test_adopt.py`,
  `test_bridge.py`, `test_active_context.py`.
- **`UnitDefinitionMismatch`** — new public exception raised by
  `Number.to` and `NumberArray.to` under `strict=True` when the source
  unit is not in the active conversion graph by object identity.
  Carries the offending `unit` and the `graph` that did not contain it.
  Exported from `ucon.core` and re-exported from `ucon`.
- `ConversionGraph.contains_unit_by_identity(unit)` — new public method
  that performs `is`-comparison against every node in `_unit_edges`,
  descending into `UnitProduct` factors. This is the lookup semantics
  required by strict source-unit resolution; it is intentionally
  distinct from value-based `__contains__` and `resolve_unit`.
- **`Number.kind` field (v2.0 §3.4)** — optional `Kind | None = None`
  slot on `Number`, validated against the unit's dimension at
  construction (raises `KindDimensionMismatch` on mismatch) and
  preserved through every `Number.to(...)` conversion path (fast,
  scale-only, general). Backward-compatible: existing `Number(...)`
  constructions without `kind=` are unaffected, and equality is
  unchanged in this slice — `kind` is carried as metadata alongside
  `uncertainty` and does not participate in `__eq__`. Kind-aware
  equality and arithmetic dispatch are reserved for the follow-on
  §3.4 slices.
- **`KindDimensionMismatch`** — new public exception raised at
  `Number.__post_init__` when a supplied `kind`'s dimension does not
  match the unit's dimension. Carries the offending `kind` and `unit`.
  Exported from `ucon.core` and re-exported from `ucon`.
- **`KindMismatch`** — new public exception raised when kinded and
  unkinded `Number`s are added or subtracted under `strict=True`.
  Carries the `kinded` kind and the `unkinded_side` (`"left"` or
  `"right"`). Exported from `ucon.core` and re-exported from `ucon`.
- **`KindConstraint`** — annotation marker parallel to
  `DimensionConstraint`. Enables `Number[kind]` and
  `Number[Dimension.X, kind]` subscript syntax for kind-constrained
  parameters. Exported from `ucon.core` and re-exported from `ucon`.
- **Named dimensions `MOLAR_ENERGY`, `MOLAR_ENTROPY`, `SPECIFIC_ENERGY`.**
  Three new derived dimensions added to `ucon.dimension` for KOQ
  degeneracy clusters: molar energy (M·L²·T⁻²·N⁻¹), molar entropy
  (M·L²·T⁻²·Θ⁻¹·N⁻¹), and specific energy (L²·T⁻² — the shared
  dimension of Gy, Sv, and J/kg).
- **Built-in `KindLattice` (25 kinds, 8 clusters).** The
  `comprehensive.ucon.toml` now ships `[[kinds]]` sections covering
  the fundamental KOQ degeneracy clusters identified from the UnitSafe
  benchmark: energy/torque, frequency/activity, absorbed dose/dose
  equivalent, voltage/EMF, molar energy thermodynamic potentials,
  molar entropy/heat capacity, real/apparent/reactive power, and
  pressure/stress. The lattice loads at import time and is accessible
  via `active_kinds()`.
- **`load_package()` / `with_package()` support for `[[kinds]]`.**
  `UnitPackage` gains an optional `kinds: KindLattice | None` field.
  `load_package()` parses `[[kinds]]` sections via `parse_kinds_payload()`.
  `Graph.with_package()` merges the package lattice into
  `graph._kind_lattice`, with package definitions taking precedence on
  name collision. Packages without `[[kinds]]` continue to work unchanged.
- **`ucon._cache` — marshal-based binary graph cache.** The conversion
  graph is serialized to a `.ucon.cache` file using `marshal` (primitives
  only — no code execution on deserialization). Subsequent imports load
  from cache when fresh, providing ~15-25x speedup over TOML parsing.
  Invalidation uses mtime comparison, magic header, format version,
  Python version, and cache schema version; any mismatch silently falls
  through to TOML. Disable with `UCON_NO_CACHE=1`.
- `make cache` / `make cache-check` targets — generate and validate the
  binary graph cache respectively. `cache-check` is suitable as a CI
  guard.
- Cold-start import benchmark in `benchmarks/array_operations.py`
  profiling cache-hit vs cache-miss vs TOML-only paths.
- **`UnitSystem.extend_many(*others)`** — bulk composition that merges
  multiple systems in a single graph copy. Equivalent to chained
  `.extend()` calls but O(1) in copy overhead regardless of how many
  systems are combined.
- **`KindLattice.copy()`** — returns an independent copy sharing the
  same frozen `Kind` objects but with separate index dicts. Mutations
  via `register()` on the copy do not affect the original.
- **`use()` now sets `_parsing_graph`** — unit name resolution inside a
  `use(system)` block now resolves against `system.conversion_graph`,
  eliminating the need for the dual-context-manager pattern
  (`use()` + `using_conversion_graph()`) in downstream platforms.

### Fixed

- **`Graph.copy()` no longer shares `_kind_lattice` by reference.**
  Previously, `Graph.copy()` aliased the lattice object, meaning
  `define_quantity_kind` in one session could mutate another session's
  graph in multi-tenant deployments. `copy()` now calls
  `KindLattice.copy()` to produce an independent index.
- **`UnitSystem.extend` with `ConflictPolicy.PREFER_OTHER` now correctly
  installs the RHS conversion edge.** Previously, the fall-through in
  `_merge_conversion_graphs` called `Graph.add_edge` to overwrite the LHS
  edge, but `add_edge` enforced cyclic consistency against the existing
  reverse edge and raised `CyclicInconsistency`. `Graph.add_edge` now
  accepts `overwrite=True`, which removes the prior forward+inverse edges
  before insertion so the cyclic check sees clean state.
- **`Graph.with_package()` now resolves constant `kind=` references against
  the package's merged kind lattice**, not just the ambient context.
  Packages defining both novel kinds and constants referencing those kinds
  now load correctly. `ConstantDef.materialize()` accepts an optional
  `kind_lattice` parameter for local resolution.
- **`Graph.contains_unit_by_identity` no longer scans every dimension on
  every call.** The check is on the hot path of `Number.to` / `NumberArray.to`
  under `strict=True` (the v2.0 default); the previous implementation
  iterated `_unit_edges` across all dimensions, then iterated
  `_name_registry_cs`, before returning. The lookup is now scoped to
  `_unit_edges[unit.dimension]` for the per-dimension scan and a single
  `_name_registry_cs.get(unit.name)` identity check for the
  product-only-unit fallback. Behavior is unchanged; the new
  `tests/ucon/conversion/test_graph.py::TestContainsUnitByIdentity`
  pins the identity-vs-name semantics and the dimension-scoped
  invariant. Restores most of the per-conversion overhead introduced
  in #259, with the largest improvement on temperature (affine)
  conversion.
- **`Dimension.__eq__` performance regression addressed.** Identity
  short-circuit (`self is other`) and `__hash__` fast-path avoid the
  full vector comparison for repeated algebra on the same dimension
  objects. Restores Unit algebra throughput after the dimension-cache
  removal.

### Changed

- **`ucon.units` loads from cache first.** `units.py` attempts
  `_cache.load_cached_graph()` before falling back to TOML parsing.
  The cache path is transparent — the resulting `Graph` is identical
  regardless of source.
- **Lazy numpy import in `ucon.core._types` and `ucon.maps`.** The
  top-level `import numpy` is replaced with a `_get_numpy()` accessor
  that defers the import to first use. This eliminates numpy from the
  critical import path for pure-scalar workloads and reduces cold-start
  time when numpy is installed but unused.
- **Context-global getters replaced with active-UnitSystem substrate.**
  `get_default_graph()`, `get_basis_graph()`, and all resolution paths
  now delegate to the `ActiveContext` carried by the `_active` ContextVar
  rather than consulting independent module-level sentinels. This
  eliminates the class of bugs where context managers disagreed about
  which graph was current.
- **Basis/graph resolution centralized into `ucon._active`.**
  `get_default_basis()` and `get_basis_graph()` resolve exclusively
  via `active().system.basis` and `active().system.basis_graph`
  respectively, making the active `UnitSystem` the single source of
  truth for all resolution paths.
- **Basis context globals retired.** `get_default_basis`,
  `get_basis_graph`, `using_basis`, and `using_basis_graph` are removed.
  All four were deprecated in v1.x; their functionality is subsumed by
  `use(system)` and `active_system().basis` / `.basis_graph`.
- **TOML becomes authoritative for Dimensions.** Dimension definitions
  (including symbols) are now loaded from `comprehensive.ucon.toml`
  rather than being hard-coded in `ucon/dimension.py`. The generated
  `dimension.pyi` stub reflects the TOML-declared catalog. This
  completes the TOML-takeover trajectory for all three registries
  (units, constants, dimensions).
- **Module-level mutable dimension caches deleted.** The dimension
  algebra caches (`_DIM_MUL_CACHE`, `_DIM_DIV_CACHE`, `_DIM_POW_CACHE`)
  that formerly lived as module globals on `ucon.dimension` are removed.
  All dimension algebra routes through the per-`UnitSystem` `AlgebraCache`
  accessible via the active context. This eliminates the last category
  of module-level mutable state.
- **Removed `_DEFAULT_ALGEBRA_CACHE` module-level global.** `_get_active_cache()`
  now returns a fresh `AlgebraCache()` when no active context exists (bootstrap
  only). Dimension algebra during import runs uncached; post-init behavior
  is unchanged.
- **Pydantic kind integration (v2.0 §3.4).** The `ucon.pydantic` adapter
  now supports `Kind` constraints alongside `Dimension` constraints.
  `Number[kind]`, `Number[Dimension.X, kind]`, and `Number[kind, Dimension.X]`
  subscripts work as Pydantic field types. Kind survives JSON round-trip
  via a new `"kind"` key in the wire format (`null` when absent).
  Kind-constrained fields validate kind identity with lattice descendancy.
  JSON schema generation includes the `kind` property and describes kind
  constraints in the `description` field. Unknown kind strings raise
  `ValueError` during deserialization.
- **TOML kind round-trip on `Constant` (v2.0 §3.4).** The `Constant`
  dataclass gains an optional `kind: Kind | None = None` field.
  `Constant.as_number()` now passes `kind` through to `Number`.
  `_serialize_constant()` writes `kind = "<canonical>"` when set
  (omitted when `None` for backward compatibility). `from_toml()`
  reads the optional `kind` key from constant specs and resolves it
  via `active_kinds()`; unknown kind names raise `GraphLoadError`.
  `ConstantDef` in `ucon.packages` gains a parallel `kind: str | None`
  field, and `load_package()` parses the `kind` key from TOML constant
  definitions. Existing TOML files without `kind` keys are unaffected.
- **`[[kinds]]` TOML serialization (v2.0 §3.4).** `to_toml()` accepts an
  optional `kinds: KindLattice` keyword argument and emits `[[kinds]]`
  sections (name, dimension, parent, join_policy, aliases). `from_toml()`
  parses `[[kinds]]` via `parse_kinds_payload()` and stores the result on
  `graph._kind_lattice`. Constant kind resolution prefers the locally-parsed
  lattice, falling back to `active_kinds()`. TOML files without `[[kinds]]`
  load with `_kind_lattice = None` (backward compatible).
- **`@enforce_dimensions` extended with kind validation (v2.0 §3.4).**
  Parameters annotated as `Number[kind]` are validated for kind identity
  (or lattice descendancy via the active `KindLattice`). Joint
  annotations `Number[Dimension.X, kind]` check both dimension and kind.
  `Number.__class_getitem__` now accepts `Kind`, `(Dimension, Kind)`, and
  `(Kind, Dimension)` subscripts — order-insensitive. Descendancy
  semantics: `Number[energy]` accepts `kinetic_energy` when it is a child
  of `energy` in the active lattice.
- **Kind-aware arithmetic dispatch (v2.0 §4.3, §4.4, §4.9).**
  `Number.__mul__` and `Number.__truediv__` consult the active
  `FormulaRegistry` when both operands carry a `kind`; the matched
  `KindFormula`'s `output_kind` stamps the result. `Number.__add__`
  and `Number.__sub__` consult the active `KindLattice`: same-kind
  preserves, different-kind joins at LCA or raises `JoinRefused`.
  Scalar operations preserve kind (S1); same-kind division yields
  `kind=None` (S2). Strict mode refuses kinded + unkinded addition
  (`KindMismatch`); permissive mode warns and inherits the present
  kind. Fast path: when both operands have `kind=None`, no registry
  or lattice is consulted.

- **Internal rename: `UnitProduct._residual_scale_factor` →
  `UnitProduct.canonical_scale`.** Same semantics, same default (`1.0`),
  same propagation algebra. The field is becoming a contract-bearing
  piece of the canonical form rather than a defensively-accessed
  implementation cache. Affects downstream code that reads
  `getattr(unit_product, '_residual_scale_factor', 1.0)`; the field
  starts with no underscore and the default behavior is preserved.

- **`UnitProduct.__init__` canonical-form contract codified
  (per-UnitFactor grain).** The constructor now (1) accepts an optional
  second positional argument, `canonical_scale: float = 1.0`, which is
  composed into the final `canonical_scale` of the constructed product;
  (2) accesses `key.canonical_scale` directly on flattened nested
  products instead of going through `getattr(..., 1.0)`; and (3)
  **absorbs** the scale of any dimensionless (NONE-dim) factor into
  `canonical_scale` before dropping the factor, where previously such
  factors' scales were silently discarded. Single-argument call sites
  are unaffected (default `1.0` for the new parameter, default `1.0`
  absorption when no NONE-dim factors are present). The new parameter
  enables the idempotence guarantee: `UnitProduct(u.factors,
  u.canonical_scale)` is structurally equal to `u`.

  The canonical form is per-UnitFactor grain: cross-scale variants of
  the same base unit (e.g. `mg` and `kg`) are distinct UnitFactors and
  both survive, preserving downstream composition (`mg/kg * kg == mg`)
  and display fidelity (shorthand `"mg/kg"`). Same-scale duplicates
  collapse normally. Property tests live in
  `tests/ucon/core/test_unitproduct_canonical.py`.

- **Parsing layer composes `canonical_scale` unconditionally.**
  `_multiply` and `_divide` in `ucon/parsing/units.py` now access
  `canonical_scale` directly and compose it unconditionally, replacing
  the defensive `getattr(..., 1.0)` fallbacks and conditional guards
  that existed before the field was contract-bearing.

- **`Number.__repr__` extended for `kind`.** A bound `kind` now renders
  as a bracketed tag after the unit shorthand:
  `<500 J [kinetic_energy]>` (or `<500 ± 0.5 J [kinetic_energy]>` with
  uncertainty). Existing `kind`-less reprs are byte-identical to the
  prior release. The repr is now assembled from an optional-parts list
  so the forthcoming aspects channel can append `#aspect` tokens
  without restructuring the existing channels.

- **BREAKING: `ucon.active()` now returns `ActiveContext`** rather
  than `UnitSystem`. Migration: call `active_system()` where the
  previous code wanted the `UnitSystem`, or access `active().system`
  explicitly. The renaming is mechanical at call sites; the type
  change is the breaking surface. This BREAKING change is
  v2.0-gated and consistent with the `[Unreleased]` lineup.
- **`use(system, *, formulas=None, kinds=None, strict=None)`** —
  the context-manager now accepts optional overrides for each
  `ActiveContext` field. Unset fields inherit from the enclosing
  context, so nested `use(...)` blocks compose without forcing
  callers to re-specify untouched fields. Outermost-block inheritance
  defaults are `FormulaRegistry()`, `KindLattice()`, `strict=True`.
- **Eager init in `ucon/__init__.py`** now constructs an
  `ActiveContext(system=..., formulas=FormulaRegistry(),
  kinds=KindLattice(), strict=True)` and pushes it onto
  `ucon._active` at import time. The active-system tier in
  `get_default_graph()` and `get_basis_graph()` is therefore always
  hit, and the legacy module-level fallback path is dead code.
- Internal sites that previously read `_active.get()` directly and
  treated the payload as a `UnitSystem` (`Number.to`, `NumberArray.to`,
  `BasisGraph` accessor, `ConversionGraph` accessor,
  `_get_active_cache`) now extract `.system` from the `ActiveContext`
  payload. The cascade is invisible to public callers; existing
  user code that only goes through public entry points is unaffected.
- `UnitSystem.from_globals(...)` deprecation message updated to point
  at `active_system()` instead of the (now-breaking) `active()`.
- **BREAKING (v2.0 §3.4): `Number.to` and `NumberArray.to` enforce
  identity-based source-unit resolution under `strict=True` (the v2.0
  default).** A `Number` whose `unit` is not in the active conversion
  graph by object identity now raises `ucon.UnitDefinitionMismatch`
  instead of being silently re-resolved by name. Remediation:
  `system.adopt(n)` when systems share unit names, or
  `Bridge(src, dst, ...).apply(n)` when names or bases diverge.
  Per-scope opt-out: `with use(system, strict=False): ...` preserves
  v1.x name-based ergonomics. The common case (a single active
  `UnitSystem`, or systems derived via `extend` / `restrict` / `with_*`
  that share `Unit` objects by reference) is unaffected. This makes
  `Bridge` structurally load-bearing at the `Number` layer, mirroring
  what §3.5 already did at the `Vector` layer with `BasisMismatch`.

### Removed

- **`_none` sentinel retired.** The module-level `_none = Unit()` in
  `ucon.core._types` is deleted. All sites that returned or defaulted
  to `_none` now use `UnitProduct({})` — the multiplicative identity
  whose contract was established in Phase 2. External code that
  imported `_none` from `ucon.core` or `ucon.quantity` should migrate
  to structural checks: `unit == UnitProduct({})` or
  `unit.factors == {}`.
- **All v1.x deprecated symbols removed (Phase 5 breaking removals).**
  The following public API symbols, deprecated during the v1.x series,
  are deleted:
  - `get_unit_by_name()` — use `parse_unit()` instead.
  - `using_graph()` — use `using_conversion_graph()` instead.
  - `set_default_graph()` / `reset_default_graph()` — graph ownership
    moved to `UnitSystem`; use `use(system)` for scoping.
  - `set_default_basis_graph()` / `reset_default_basis_graph()` — same;
    use `using_basis_graph()` or `use(system)`.
  - `UnitSystem.conversions` property — use `conversion_graph` instead.
  - `UnitSystem(conversions=...)` kwarg — use `conversion_graph=`.
  - `UnitSystem.from_globals()` — use `active_system()` instead.
  - `units.have(name)` — use `parse_unit(name)` with a try/except.
  - `_DIM_MUL_CACHE` / `_DIM_DIV_CACHE` / `_DIM_POW_CACHE` PEP-562
    shims on `ucon.dimension` — algebra caches are now per-`UnitSystem`
    via `AlgebraCache`.
  - Module-level `_default_graph` and `_default_basis_graph` globals —
    `get_default_graph()` and `get_basis_graph()` now resolve
    exclusively via `ContextVar` and active `UnitSystem`.
  - `get_default_basis()` / `get_basis_graph()` / `using_basis()` /
    `using_basis_graph()` — basis resolution is now exclusively via
    `active_system().basis` and `active_system().basis_graph`.

## [1.12.0] - 2026-05-23

Finishes the cycle-break work begun on the
`refactor-avoiding-most-cycles` branch **structurally** rather than at
runtime. The transitional `_resolve_unit_impl` module-level
dependency-injection scaffold and the `constants._constants_cache`
cross-module attribute assignment are both retired. A static AST audit
guards against future regressions.

No public API is added, removed, renamed, or repositioned. No
deprecated APIs are removed (those land in v2.0 per
[`docs/internal/ucon-roadmap-after-v04x.md`]).

### Changed

- **`_active` ContextVar relocated to `ucon._active`** — the canonical
  location of the active-system ContextVar moves from
  `ucon.system._active` to the package root `ucon._active`. This is a
  true Layer-0 leaf with zero intra-ucon imports, allowing
  `ucon.core._types` to consult the active system without forcing
  `ucon.system/__init__.py` to execute mid-init of `ucon.core`. The
  earlier shim at `ucon.system._active` was deleted (it had no
  out-of-tree callers).

- **`UnitSystem.resolve_unit()` restored as an orthodox method** —
  previously implemented via a module-level `_resolve_unit_impl = None`
  sentinel that `ucon/__init__.py` populated by attribute assignment
  after all modules loaded. With the `_active` relocation removing the
  underlying cycle, `ucon.system/__init__.py` now imports
  `parse_unit` at the top of the file and the method body calls it
  directly. The sentinel, its `RuntimeError` guard, and the injection
  block in `ucon/__init__.py` are all deleted.

- **`AlgebraCache` relocated to `ucon._algebra_cache`** — for the same
  parent-package-init reason as `_active`. Public access via
  `from ucon.system import AlgebraCache` is unchanged; the
  `ucon.system` re-export is preserved.

- **`constants` cache population is now orthodox** — the previous
  `ucon/__init__.py` block that did
  `constants._constants_cache = _descriptive_constants` (cross-module
  attribute assignment) is replaced by two helpers exposed by
  `ucon.constants`: `_build_symbol_lookup(package_constants)` produces
  the dict consumed by `UnitSystem(constants=...)`, and
  `_populate_cache(package_constants)` populates the module-internal
  cache used by `ucon.constants` PEP-562 attribute access.
  `ucon/__init__.py` now calls those helpers and never reaches into a
  sibling module's namespace.

### Added

- **`tests/ucon/test_no_cross_module_injection.py`** — static AST audit
  that scans every file under `ucon/` and fails if any top-level
  attribute assignment targets a `ucon.*` module imported by the
  current file. Complements the existing
  `tests/ucon/test_import_dag.py` deferred-import audit by closing the
  loophole where a cycle break manifests as cross-module mutation
  rather than as a function-body deferred import.

- **`KNOWN_DEFERRED` annotations** — each of the three remaining
  deferred imports (`from_toml`, `to_toml`, `with_package` in
  `ucon.conversion`) now carries an inline comment confirming "v2.0
  removal — deprecated method". The audit count stays at 3.

### Notes for downstream integrators

v1.12.0 makes no change to the public API surface, but the cumulative
internals churn since v1.10.x retires several private symbols that
some downstream packages (notably `ucon-tools`) had reached into. If
you import from a module path beginning with an underscore, expect to
migrate. Known impacts:

- **`ucon._loader` is gone** (removed during the TOML-takeover work
  that landed in earlier 1.x releases; surfaced now as ucon-tools'
  test suite goes red against v1.12.0). The previous
  `from ucon._loader import get_units, get_constants` entry points
  no longer exist.

  Recommended replacements use the active :class:`UnitSystem`:

  ```python
  from ucon import active
  sys = active()
  units = sys.units            # Mapping[str, Unit]
  constants = sys.constants    # Mapping[str, Constant]
  ```

  Or, for the raw module-level dicts (private, but stable through
  v1.x): ``ucon.units._units`` and ``ucon.constants.all_constants()``.

- **`ucon.system._active` is gone** — the active-system ContextVar
  moved to the package root at `ucon._active`. Direct importers of
  the old path must update to `from ucon._active import _active`, or
  preferably use the public `ucon.system.active()` / `ucon.use()`.

- **`UnitSystem._resolve_unit_impl` is gone** — the v1.10/1.11
  module-level injection sentinel is deleted. Callers should use
  `UnitSystem.resolve_unit()` directly; the underscore-prefixed
  sentinel was never public.

A `v1.12.0a1` alpha is published ahead of the final tag so downstream
packages can land their patches against a real artifact before
`v1.12.0` is promoted.

[`docs/internal/ucon-roadmap-after-v04x.md`]: docs/internal/ucon-roadmap-after-v04x.md

## [1.11.0] - 2026-05-23

Eagerly initializes the active [`UnitSystem`] at import time, completing
the globals-retirement effort begun in v1.10.0. The module-level
`_default_graph` singleton is now dead code — all graph resolution flows
through the active system. [`set_default_graph()`],
[`reset_default_graph()`], and [`UnitSystem.from_globals()`] are
deprecated.

### Added

- **Eager system initialization** — `ucon.__init__` now calls
  `_active.set(UnitSystem.from_globals())` at import time, ensuring the
  active-system tier in [`get_default_graph()`] is always hit. Code that
  relied on the lazy module-level `_default_graph` singleton continues to
  work; the active system's `conversion_graph` is functionally identical.

- **Deprecation tests for [`set_default_graph()`] / [`reset_default_graph()`]**
  — added `TestConversionGraphGlobalsDeprecated` to
  `tests/ucon/test_deprecation.py`.

### Changed

- **[`Number.to()`] uses [`get_default_graph()`] for graph resolution** —
  when no explicit `graph=` is provided, `Number.to()` now calls
  `get_default_graph()` (which respects the 3-tier priority:
  context-local → active system → module default) instead of reading
  `system.conversion_graph` directly. This ensures [`using_context()`]
  and [`using_conversion_graph()`] overrides remain effective under eager
  initialization.

- **[`set_default_graph()`] emits `DeprecationWarning`** — the
  module-level default graph is masked by the active system; mutations
  via this function are invisible to [`get_default_graph()`]. Use
  [`using_conversion_graph()`] for scoped overrides or [`use()`] to
  switch the active system. Scheduled for removal in v2.0.

- **[`reset_default_graph()`] emits `DeprecationWarning`** — same
  rationale as `set_default_graph()`. Leave the `use(system)` block
  instead of resetting a global. Scheduled for removal in v2.0.

- **[`UnitSystem.from_globals()`] emits `DeprecationWarning`** — with
  eager initialization, the active system is always available via
  [`active()`]. Call `active()` instead of snapshotting module-level
  registries. Scheduled for removal in v2.0.

- **Test suite modernized** — removed 11 `reset_default_graph()` setUp
  calls from `test_default_graph_conversions.py`; rewrote
  `TestDefaultGraphManagement` in `conversion/test_graph.py` to verify
  active-system-takes-precedence behavior; updated dimension cache
  routing tests to use `active()._algebra_cache` instead of
  `_DEFAULT_ALGEBRA_CACHE`; suppressed deprecation warnings in remaining
  call sites.

[`Number.to()`]: https://github.com/withtwoemms/ucon/blob/1.11.0/ucon/core.py
[`UnitSystem`]: https://github.com/withtwoemms/ucon/blob/1.11.0/ucon/system/__init__.py
[`get_default_graph()`]: https://github.com/withtwoemms/ucon/blob/1.11.0/ucon/graph.py
[`set_default_graph()`]: https://github.com/withtwoemms/ucon/blob/1.11.0/ucon/graph.py
[`reset_default_graph()`]: https://github.com/withtwoemms/ucon/blob/1.11.0/ucon/graph.py
[`using_context()`]: https://github.com/withtwoemms/ucon/blob/1.11.0/ucon/contexts.py
[`using_conversion_graph()`]: https://github.com/withtwoemms/ucon/blob/1.11.0/ucon/graph.py
[`UnitSystem.from_globals()`]: https://github.com/withtwoemms/ucon/blob/1.11.0/ucon/system/__init__.py
[`active()`]: https://github.com/withtwoemms/ucon/blob/1.11.0/ucon/system/__init__.py
[`use()`]: https://github.com/withtwoemms/ucon/blob/1.11.0/ucon/system/__init__.py

## [1.10.0] - 2026-05-22

Routes [`Number.to()`] through the active [`UnitSystem`], establishing
`UnitSystem` as the authority for unit resolution and graph lookup. This
is the first step toward retiring module-level global state; all existing
call sites continue to work without changes.

### Added

- **[`UnitSystem.resolve_unit(name)`]** — resolves a unit name, alias,
  scale-prefixed name, or composite expression string to a `Unit` or
  `UnitProduct`, drawing from the system's unit registry. Delegates to
  [`parse_unit()`] with `system=self`.

- **Top-level exports: [`active()`], [`use()`]** — the active-system
  accessor and context-manager scoping function are now importable
  directly from `ucon`. `active()` returns the currently active
  `UnitSystem`, falling back to `UnitSystem.from_globals()` when none
  has been set.

- **[`get_default_graph()`] checks active system** — resolution priority
  is now: context-local graph (from `using_conversion_graph`) →
  active `UnitSystem`'s `conversion_graph` → module-level default
  (legacy fallback).

- **`tests/ucon/test_deprecation.py`** — parametrized test coverage for
  all deprecated symbols emitting `DeprecationWarning`.

### Changed

- **[`Number.to()`] routes through `active()`** — when neither `system=`
  nor `graph=` is provided, `Number.to()` obtains both the conversion
  graph and unit resolver from the active `UnitSystem` instead of
  importing `get_default_graph` and `parse_unit` directly. Callers see
  no behavioral change; the method signature is unchanged.

- **Deprecation warnings upgraded to `DeprecationWarning`** — the
  following symbols previously emitted `PendingDeprecationWarning`
  (introduced in v1.8) and now emit `DeprecationWarning`, the standard
  signal that removal is forthcoming in v2.0:
  - [`UnitSystem.conversions`] property (use `conversion_graph`)
  - `UnitSystem(conversions=...)` constructor kwarg (use `conversion_graph=`)
  - [`using_graph()`] (use [`using_conversion_graph()`])
  - [`set_default_basis_graph()`] (use `with use(system): ...`)
  - [`reset_default_basis_graph()`] (use `with use(system): ...`)

### Notes

- **`UnitSystem` is not yet exported as the real class from `ucon`.** The
  PEP-562 alias `ucon.UnitSystem → BaseUnits` remains active with a
  `DeprecationWarning`. The alias will be retired and `UnitSystem`
  exported directly in v2.0.

- **Module-level globals are still functional.** This release wires
  `UnitSystem` as the routing authority but does not deprecate
  `set_default_graph()`, `reset_default_graph()`, or `from_globals()`.
  Those deprecations land in a subsequent v1.x release once test
  infrastructure has migrated to `use()` scoping.

[`UnitSystem.resolve_unit(name)`]: https://github.com/withtwoemms/ucon/blob/1.10.0/ucon/system/__init__.py
[`UnitSystem.conversions`]: https://github.com/withtwoemms/ucon/blob/1.10.0/ucon/system/__init__.py
[`parse_unit()`]: https://github.com/withtwoemms/ucon/blob/1.10.0/ucon/resolver.py
[`active()`]: https://github.com/withtwoemms/ucon/blob/1.10.0/ucon/system/__init__.py
[`using_graph()`]: https://github.com/withtwoemms/ucon/blob/1.10.0/ucon/graph.py
[`set_default_basis_graph()`]: https://github.com/withtwoemms/ucon/blob/1.10.0/ucon/basis/graph.py
[`reset_default_basis_graph()`]: https://github.com/withtwoemms/ucon/blob/1.10.0/ucon/basis/graph.py

## [1.9.2] - 2026-05-22

Lookup completeness for `FormulaRegistry`. The `resolve()` method
implements tiered formula resolution — commutative matching at any arity,
ancestor-walk generalization via the kind lattice, and opt-in
dimension-only fallback — completing the lookup surface deferred from
v1.9.0.

### Added

- **`FormulaRegistry.resolve(*kinds, lattice=, dimension_fallback=)`** —
  tiered formula resolution returning `LookupResult` with `MatchKind`
  discriminator. Tiers checked in priority order:
  1. **EXACT** — exact input-kind tuple match.
  2. **COMMUTATIVE** — canonical sorted-key match for any arity
     (replaces the arity-2 special case).
  3. **GENERALIZED** — ancestor-walk via `KindLattice` at increasing L1
     distance; requires `lattice=` and `generalizes=True` on the formula.
  4. **DIMENSIONAL** — dimension-tuple match ignoring kind identity;
     requires `dimension_fallback=True`.

- **`MatchKind`** enum (`EXACT`, `COMMUTATIVE`, `GENERALIZED`,
  `DIMENSIONAL`) — discriminator indicating which resolution tier matched.

- **`LookupResult`** frozen dataclass — wraps the matched `KindFormula`,
  the `MatchKind` tier, and the L1 `distance` (meaningful only for
  `GENERALIZED`).

- **`AmbiguousFormula`** exception — raised when two or more formulas
  match at the same L1 distance during ancestor-walk. Carries
  `candidates` and `distance`.

### Changed

- **`FormulaRegistry.apply()`** — now accepts keyword arguments
  `lattice: KindLattice | None = None` and
  `dimension_fallback: bool = False`, and returns a 4-tuple
  `(formula, output_kind, output_aspects, match_kind)`. The fourth
  element is the `MatchKind` tier that resolved the formula. Callers
  destructuring three values will get a clear unpacking error.

## [1.9.1] - 2026-05-22

Activates the `aspect_rules` field on `KindFormula` that shipped as opaque
data in v1.9.0. Aspects are covariant tags (strings) that travel with
quantities through formula application and lattice join, describing
provenance or processing state rather than physical identity. The new
machinery is still preview surface — not wired to `Number`; callers
interact with aspects through `FormulaRegistry.apply` and `join_aspects`.

### Added

- **`ucon.aspects` subpackage** — new sibling to `ucon.kinds` and
  `ucon.formulas`, housing aspect data types and the pure join operation.

  - **`AspectSet`** — `frozenset` subclass with a variadic constructor
    (`AspectSet("calibrated", "ICRP103")`). Fully interchangeable with
    plain `frozenset[str]` at every internal surface. Single string
    arguments are treated as one aspect (not iterated as characters).

  - **`AspectJoinPolicy`** enum (`INTERSECT`, `UNION`) — controls how
    aspect sets combine when kinds join at the lattice. `INTERSECT`
    (the default) keeps only aspects present on both sides; `UNION`
    keeps every aspect from either side.

  - **`join_aspects(a, b, policy=INTERSECT)`** — pure function combining
    two aspect sets under the given policy. Does not consult a lattice;
    callers compose with `KindLattice.join` explicitly.

- **`KindFormula.project_aspects(inputs)`** — pure method projecting
  input aspect sets through the formula's `aspect_rules`. For each
  binding: `CARRY` (or absent — the default) unions the binding's
  aspects into the output; `CONSUME` drops them.

- **`FormulaRegistry.apply(inputs)`** — single entry point that resolves
  a formula by input kinds *and* projects aspects through it. Returns
  `(formula, output_kind, output_aspects)`. Raises `FormulaNotFound` if
  no formula matches.

### Changed

- **`AspectRule` canonical location.** `AspectRule` now lives in
  `ucon.aspects.types`; the canonical import is
  `from ucon.aspects import AspectRule`. The v1.9.0 import path
  (`from ucon.formulas import AspectRule`) continues to work via
  re-export and is not deprecated.

### Notes

- **`aspect_rules` keys are binding names.** Keys in `aspect_rules` are
  operand binding names drawn from `[formulas.inputs]`, not aspect
  strings. A `CONSUME` rule drops every aspect on its binding's
  operand; a `CARRY` rule unions them into the output. Bindings
  omitted from `aspect_rules` default to `CARRY`. Per-facet rule
  semantics (selective propagation by aspect string) are a v2.0
  question; the schema may be extended at that time to accept a richer
  entry shape. v1.9.1 binding-keyed rules will continue to be honored
  as a syntactic subset of any future schema.

## [1.9.0] - 2026-05-20

Introduces *kinds* as a first-class concept: dimensional refinements that
let callers distinguish kinetic energy from potential energy, active power
from reactive power, or apples from tablets, even though each pair shares
a dimension. v1.9.0 lands the storage and structural-reasoning surface —
the `Kind` dataclass, `KindLattice` with lowest-common-ancestor (LCA)
computation, the `KindFormula` dataclass, the `FormulaRegistry`, and the
TOML loaders that build both from declarative files. None of it is wired
to `Number` yet; the lattice is opt-in, queried explicitly, and lives
alongside the existing arithmetic without changing its semantics.

Until now, two quantities with the same dimension were interchangeable
under arithmetic, full stop. That is correct for raw dimensional algebra
but wrong for physics: `5 J` of kinetic energy plus `5 J` of potential
energy yields `10 J` of *mechanical energy* — a different sortal — and
`5 m` of "elastic deformation" plus `5 m` of "wavelength" yields
nonsense. v1.9.0 publishes the vocabulary for that distinction (`Kind`,
parent edges, `join_policy`) and the lookup machinery (`KindLattice.lca`,
`KindLattice.join`) without yet enforcing it on `Number`. Users can build
lattices, query them, validate them at load time, and prepare formula
declarations against them in isolation.

The roadmap from there forward: v1.9.1 wires aspect machinery (the
opaque `aspect_rules` field gains semantics); v1.9.2 wires
formula-lookup generalization (`generalizes` and `commutative` become
load-bearing); v2.0.0 folds the lattice and registry into `UnitSystem`
and wires them into `Number`.

### Added

- **`ucon.kinds` subpackage** — new public surface for the sortal lattice.

  - **`Kind(name, dimension, parent=None, join_policy=JoinPolicy.LCA,
    aliases=())`** — frozen dataclass representing a kind node. A kind
    refines a `Dimension`: every kind in a lattice partition has the same
    dimension as its parent, and parent edges form rooted trees within
    each dimension. Equality and hashing key off `name` only, so two
    references to the same name compare equal even when one is a
    placeholder constructed during parsing.

  - **`JoinPolicy`** enum (`LCA`, `REFUSE`) — declared per kind, consulted
    at the lowest common ancestor. `LCA` lifts the result to the ancestor
    (the default); `REFUSE` raises `JoinRefused`, signalling that the two
    kinds must be combined via a named formula rather than via addition.

  - **`KindLattice([kinds...])`** — owns the canonical `Kind` instances,
    indexes them by name and alias, and runs load-time validation in a
    fixed order: name/alias collisions, then orphan parents, then
    cross-dimension parent edges, then cycles. The public surface:
    `get(name_or_alias)`, `names()`, `ancestors(kind)`,
    `is_descendant(child, ancestor)`, `lca(a, b)`, `join(a, b)`,
    `register(kind)` for additive extension, `__contains__`, `__len__`,
    `__iter__`.

  - **`lca(a, b, *, lattice)`** — module-level convenience that
    delegates to `KindLattice.lca`. There is no implicit global; the
    lattice is always explicit in v1.9.x. (v2.0.0 will host it on
    `UnitSystem`.)

  - Exception family: **`KindError`** (base), **`KindCycle`**,
    **`OrphanParent`**, **`CrossDimensionParent`**, **`NameCollision`**,
    **`AliasCollision`**, **`KindNotFound`**, **`JoinRefused`**. Each
    carries diagnostic attributes (`OrphanParent.missing_parent`,
    `JoinRefused.left/right/parent`, etc.) so callers can format
    error messages without re-parsing the message text.

  Minimal usage:
  ```python
  from ucon.dimension import LENGTH, MASS, TIME
  from ucon.kinds import Kind, KindLattice

  ENERGY = (LENGTH ** 2) * MASS / (TIME ** 2)
  energy = Kind("energy", dimension=ENERGY)
  ke = Kind("kinetic_energy", dimension=ENERGY, parent=energy)
  pe = Kind("potential_energy", dimension=ENERGY, parent=energy)
  lat = KindLattice([energy, ke, pe])

  ancestor, policy = lat.lca(ke, pe)  # (energy, JoinPolicy.LCA)
  ```

- **`ucon.formulas` subpackage** — new public surface for the formula
  registry.

  - **`KindFormula(name, expression, input_kinds, output_kind,
    aspect_rules={}, generalizes=False, commutative=True, notes="")`** —
    frozen dataclass declaring a relationship between kinds. Formulas
    serve three purposes: documentation of the physical relationship,
    kind assignment for multiplication/division (the lattice handles
    addition), and a named computation surface. Equality and hashing key
    off `name` only, matching `Kind`.

  - **`AspectRule`** enum (`CONSUME`, `CARRY`) — declared per facet in
    `KindFormula.aspect_rules`. The field is opaque in v1.9.0; semantics
    activate in v1.9.1 alongside the `Aspect` type.

  - **`FormulaRegistry([formulas...])`** — indexes formulas by name and
    by input-kind tuple. `register(formula)` refuses duplicate names
    (`DuplicateFormula`); `get(name)` and `lookup(*input_kinds)` resolve
    by name and by exact input-kind tuple respectively
    (`FormulaNotFound` on miss). When a formula declares `commutative=True`
    and has exactly two inputs, the registry also indexes the reversed
    ordering, so `voltage × current` and `current × voltage` both
    resolve to the same formula. Higher-arity permutations and subkind
    climbing (`generalizes`) land with v1.9.2's lookup work.

  - Exception family: **`FormulaError`** (base), **`FormulaNotFound`**,
    **`DuplicateFormula`**.

- **TOML loaders in `ucon.parsing`.**

  - **`parse_kinds_payload(payload)`** and **`load_kinds_file(path)`**
    build a `KindLattice` from a TOML payload. Schema:
    ```toml
    [[kinds]]
    name = "kinetic_energy"
    dimension = "L^2·M/T^2"
    parent = "energy"           # optional
    join_policy = "lca"         # optional, default "lca"
    aliases = ["KE"]            # optional
    ```
    The `dimension` field is parsed via the existing
    `ucon.parsing.parse_dimension`. Parent references are resolved in a
    second pass, so out-of-order and forward-reference declarations are
    supported. Load-time validation surfaces as the corresponding
    `KindError` subclass.

  - **`parse_formulas_payload(payload, *, lattice)`** and
    **`load_formulas_file(path, *, lattice)`** build a `FormulaRegistry`
    against a supplied lattice. Schema:
    ```toml
    [[formulas]]
    name = "radiation_weighting"
    expression = "D * w_R"
    output_kind = "equivalent_dose"
    notes = "w_R per ICRP 103; caller selects."
    commutative = true              # optional, default true
    generalizes = false             # optional, default false
      [formulas.inputs]
      D   = { kind = "absorbed_dose" }
      w_R = { kind = "radiation_weighting_factor" }
      [formulas.aspect_rules]       # optional; keys are binding names
      w_R = "consume"
    ```
    Kind references resolve through `lattice.get`, so unknown names
    surface as `KindNotFound`. Both loaders are exported lazily from
    `ucon.parsing` via the same PEP 562 mechanism as `parse_dimension`.

### Notes

- **Not wired to `Number`.** v1.9.0 does not change arithmetic on
  `Number`. Two numbers with the same dimension still combine without
  consulting any lattice; the kind machinery is queried explicitly by
  callers who opt in. Wiring lands at v2.0.0, when `UnitSystem` becomes
  the home for the active lattice and formula registry.

- **No module-level default lattice or registry.** Every API that needs
  one takes it as an explicit argument (`lattice=...`). There is no
  hidden global state in v1.9.x; users compose their own lattice and
  pass it where it is needed. This mirrors the shape `UnitSystem` will
  take in v2.0.0, so v1.9.x code carries forward without an
  import-site rewrite.

- **No top-level re-export.** `Kind`, `KindLattice`, `KindFormula`, and
  the parsers are not exposed on `ucon` directly. Callers opt in via
  `from ucon.kinds import ...` and `from ucon.formulas import ...`.
  This signals that the surface is preview-ish and discourages
  inadvertent dependency before v2.0.0 settles the wiring.

- **`aspect_rules`, `generalizes`, and `commutative` are stored but
  partially inert.** The fields exist on `KindFormula` so v1.9.0 TOML
  files do not need to be rewritten when v1.9.1 and v1.9.2 land. Only
  the two-input commutative case is honored by `FormulaRegistry.lookup`
  in v1.9.0; everything else is data carried through the registry for
  future passes to consult.

- **Parser diagnostic quirk.** `[[kinds]]` with two entries sharing the
  same `name` surfaces as `AliasCollision` rather than `NameCollision`
  because the parser's second pass deduplicates by name before handing
  the lattice a `Kind` instance. The lattice's direct-construction path
  raises the canonical `NameCollision` (covered in
  `tests/ucon/kinds/test_validation.py`); the parser-level diagnostic
  is a minor message-quality issue tracked for v1.9.0.1.

## [1.8.3] - 2026-05-15

Lifts unit prefix-scalability from consumer-side policy into a first-class
`Unit` property, with resolver enforcement, TOML round-trip, a dedicated
`NonScalableError` diagnostic, and a computing-event vocabulary in the
catalog.

Prior to this release, every consumer that wanted to reject nonsensical
prefix decompositions (e.g. `meach` for "milli-each", `kdB` for "kilo-decibel")
had to maintain its own allowlist of scalable units. The ucon-tools MCP
server in particular hardcoded `SCALABLE_UNITS = {"meter", "gram", ...}`
and tagged every other unit as non-scalable by fiat, which both duplicated
catalog knowledge and made it impossible for callers to define new
scalable units via `define_unit`. With `Unit.scalable` as a first-class
field on the catalog entry, the policy lives where the data lives.

### Added

- **`Unit.scalable: bool = True`** — new field on the `Unit` frozen
  dataclass that marks whether the unit accepts SI/binary prefix
  decomposition. The field defaults to `True` so existing catalog entries
  and user-defined units continue to work unchanged. It is declared with
  `compare=False, hash=False` so it does not participate in unit
  identity: two `Unit` instances with the same `name`, `dimension`,
  `aliases`, and `base_form` remain equal regardless of the scalability
  flag. This preserves the established invariant that two catalogs with
  the same vocabulary describe the same algebra.

  Example:
  ```python
  from ucon import Unit, Dimension

  each = Unit("each", Dimension.none, scalable=False)
  meter = Unit("meter", Dimension.length)  # scalable=True by default
  ```

- **`NonScalableError`** — new exception (subclass of `UnknownUnitError`)
  raised by the prefix-decomposition resolver when a prefix is applied
  to a base unit that has opted out of scalability. The exception carries
  `.attempted` (the failing token, e.g. `"meach"`), `.base` (the
  resolved base `Unit`, e.g. `each`), and `.prefix` (the parsed prefix
  descriptor) so callers can format domain-specific diagnostics instead
  of the generic "unknown unit" message.

  Because `NonScalableError` is a subclass of `UnknownUnitError`,
  existing `except UnknownUnitError:` handlers continue to catch the
  new exception — code that does not care about the distinction is
  unaffected.

- **TOML round-trip for `scalable`.** `_serialize_unit()` emits
  `scalable = false` only when the field diverges from its default
  (`True`), keeping catalog TOML compact and preserving backward
  compatibility with packages produced before the field existed.
  `from_toml` reads `scalable = bool(unit_spec.get("scalable", True))`
  so packages serialized by earlier ucon versions load cleanly. The
  field is also plumbed through `UnitDef.scalable` and `materialize()`
  for the package layer.

- **Computing-event family in `comprehensive.ucon.toml`** — six new
  units under the `count` dimension: `flop`, `op`, `instruction`,
  `cycle`, `request`, `event`. All are scalable by default, so common
  HPC and observability vocabulary (`Gflop`, `Mop`, `kreq`, `Mevent`)
  parses out of the box. Future sortal-lattice support on `Number`
  will be the venue for distinguishing these kinds; for now they live
  alongside `each` under `count` and are dimensionally
  interchangeable.

### Changed

- **Prefix-decomposition resolver guards on `Unit.scalable`.** When the
  resolver finds a candidate base for an unknown token via prefix
  decomposition, it now checks `base.scalable` before accepting the
  match. If the base is non-scalable, the resolver raises
  `NonScalableError` instead of returning a `(prefix, base)` pair.
  Shorter-prefix scalable bases continue to win over longer-prefix
  non-scalable bases on the same token, so disambiguation is
  deterministic.

- **Catalog opt-outs in `comprehensive.ucon.toml`.** The following units
  are marked `scalable = false`, since prefix decomposition of them
  produces nonsensical reads:

  - `each` — a counting marker, not a prefixable quantity.
  - `decibel`, `decibel_spl`, `decibel_volt` — logarithmic units whose
    SI prefix on the *outer* symbol would mean "prefix of the logarithm"
    rather than "prefix of the underlying ratio".

  This is a behaviour change for any caller that was relying on
  `meach`, `kdB`, etc. parsing successfully; such tokens now raise
  `NonScalableError`. The failure mode is intentional — the previous
  parse was almost certainly a typo or a model hallucination.

## [1.8.2] - 2026-05-14

Adds a thin convenience for constructing the canonical "append-only" basis
embedding so callers that extend a parent basis with additional components
(e.g. `SI` extended with a `currency` slot) can register the lift in the
active `BasisGraph` and have `unify` succeed across the two bases.

### Added

- **`BasisTransform.append_components_embedding(parent, extended)`** —
  classmethod that returns the zero-pad embedding `parent -> extended`.
  Each parent component is routed by name to the same-named slot in
  `extended`; components present only in `extended` receive a zero
  column. The reverse projection is available via the resulting
  transform's `.embedding()` and raises `LossyProjection` if a non-zero
  added component is asked to drop — the correct behavior for
  unification.

  This is the canonical primitive for an append-only basis extension:
  with the forward transform registered in the active
  `BasisGraph`, `ucon.basis.ops.unify` (and therefore the algebraic
  path through `multiply_via` / `divide_via`) lifts parent-basis
  vectors into the extended basis when composing with extended units.

  Example:
  ```python
  from ucon.basis import Basis, BasisComponent, BasisTransform
  from ucon.basis.builtin import SI
  from ucon.basis.graph import get_basis_graph

  fin = Basis("fin", list(SI) + [BasisComponent("currency", "C")])
  forward = BasisTransform.append_components_embedding(SI, fin)

  graph = get_basis_graph()
  graph.add_transform(forward)
  graph.add_transform(forward.embedding())  # reverse projection
  ```

### Fixed

- **#247 — cross-basis arithmetic with append-extended bases.** Provides
  the missing primitive so downstream callers (notably the ucon-tools
  MCP `extend_basis` tool) can register a parent ↔ extended transform
  pair at basis-creation time. Without an edge in the basis graph,
  `unify` raises `BasisMismatch` when composing a parent-basis vector
  (e.g. `s` on SI) with an extended-basis vector (e.g. `USD` on a
  financial basis); ucon's algebraic surface had no built-in helper for
  the trivial zero-pad case, forcing callers to hand-roll the matrix.
  Registration remains the caller's responsibility — `Basis` and
  `BasisTransform` continue to be value types — but the matrix
  construction is now a one-liner.

## [1.8.1] - 2026-05-12

API correction on the freshly-introduced `UnitSystem` value type.

### Changed

- **`UnitSystem.conversion_graph`** — the `conversions` field on the v1.8.0
  `UnitSystem` value type is renamed to `conversion_graph` for symmetry
  with the sibling `basis_graph` field. The old name remains accepted in
  both directions during the v1.8.x window:

  - `UnitSystem(conversions=...)` constructor kwarg continues to work and
    emits `PendingDeprecationWarning`.
  - `system.conversions` attribute access continues to return
    `system.conversion_graph` and emits `PendingDeprecationWarning`.
  - Passing both `conversion_graph=` and `conversions=` raises `TypeError`.

  The alias is scheduled for removal in v2.0 alongside the other
  `PendingDeprecationWarning` items listed in the v1.8 implementation
  plan.

## [1.8.0] - 2026-05-12

v1.8 introduces a frozen `UnitSystem` value type and routes the algebraic,
parsing, and conversion surfaces through it via an optional `system=` kwarg.
Every change is paired with a PEP-562 alias, a kwarg default, or a
`DeprecationWarning`-emitting delegate, so v1.7 code runs unchanged. Outside
a `with use(sys): ...` block, behaviour is byte-for-byte identical to v1.7.
Deprecated surfaces are scheduled for removal in v2.0.

### Added

- **`ucon.system` subpackage** — new home for system-level value types.
  Exposes `BaseUnits` (the renamed v1.7 `UnitSystem`, a small named
  `Mapping[Dimension, Unit]`), `UnitSystem` (a frozen-dataclass value type
  owning `basis`, `units`, `dimensions`, `base_units`, `conversion_graph`,
  `basis_graph`, `contexts`, `constants`, and a per-instance
  `AlgebraCache`), `AlgebraCache`, plus the activation helpers
  `use(system)` (contextmanager) and `active()` (queries the active
  system, snapshotting from globals if none is set). Construct a
  `UnitSystem` directly or via `UnitSystem.from_globals()`.

- **`system=` kwarg on user-facing entry points.** Optional; ignored when
  omitted. Accepted on:
  - `Number.to(target, *, graph=None, system=None)`
  - `ucon.parsing.units.parse(s, *, system=None)`
  - `ucon.resolver.parse_unit(name, *, system=None)`
  - `ucon.parsing.dimensions.parse_dimension(spec, basis=None, *, system=None)`
  - `ucon.checking.enforce_dimensions(*, system=None)` (factory form;
    bare `@enforce_dimensions` unchanged)

  The compound-unit parser threads `system=` into every internal helper,
  so factor-level lookups inside `"USD/year"` or `"widget*kg/s"` consult
  `system.units` before module globals. Resolution priority when multiple
  sources supply a graph: `graph= > system.basis_graph > active() > module
  default`. Inside `with use(sys): ...` whose `basis_graph` embeds two
  domain bases into a combined basis, `Number(100, USD) * Number(1,
  second)` resolves through `sys.basis_graph` instead of raising
  `BasisMismatch`.

- **`ucon.basis.ops` module — explicit cross-basis arithmetic.** Three
  helpers — `unify(a, b, *, system=None, graph=None)`, `multiply_via`,
  `divide_via` — bring two `Vector`s into a common basis via the active
  or supplied `BasisGraph`. `unify` performs 3-way unification: if no
  direct transform connects the operands' bases, the graph is searched
  for a common target reachable from both.

- **`BasisMismatch(ValueError)`** in `ucon.basis.types` (re-exported from
  `ucon.basis`). Carries `left`, `right`, and `op` attributes. Replaces
  the bare `ValueError("Cannot multiply dimensions from different bases:
  …")` raised by `Vector.__mul__` / `__truediv__` in v1.6.x / v1.7.x.
  Subclasses `ValueError` so existing `except ValueError` and
  `pytest.raises(ValueError, match=...)` callsites continue to catch;
  message format is unchanged.

### Changed

- **`UnitSystem` renamed to `BaseUnits`.** The v1.7 `UnitSystem` was a
  small `@dataclass(frozen=True)` mapping `name + bases:
  Mapping[Dimension, Unit]`. It has been renamed `BaseUnits` to free the
  `UnitSystem` name for the new richer value type. Class shape,
  validation rules, and methods (`base_for`, `covers`, `dimensions`,
  `__hash__`) are unchanged. The pre-defined `ucon.units.si` and
  `ucon.units.imperial` are now `BaseUnits` instances. `from ucon import
  UnitSystem` is retained as a PEP-562 alias (see *Deprecated*).

- **`Vector` arithmetic is now strict same-basis.** `Vector.__mul__` and
  `Vector.__truediv__` raise `BasisMismatch` immediately when operands
  live in different bases. The 1.6.6 implicit consultation of the active
  `BasisGraph` (via the removed `Vector._unify_basis`) has moved to
  explicit `ucon.basis.ops.multiply_via` / `divide_via`. Same-basis
  behaviour is byte-identical. `Dimension.__mul__` and
  `Dimension.__truediv__` now route through `ops.multiply_via` /
  `divide_via`, so dimension-level cross-basis algebra continues to work
  via the active graph without code change.

- **`Dimension` algebra routes through `UnitSystem._algebra_cache`.**
  `Dimension.__mul__`, `__truediv__`, and `__pow__` consult the active
  `UnitSystem`'s per-instance `AlgebraCache` (with `mul` / `div` / `pow`
  sub-dicts) instead of three module-level dicts. Outside a `use(...)`
  block, the new `_DEFAULT_ALGEBRA_CACHE` in `ucon.system` is the stable
  fallback. Cache keys remain structural `(Dimension, Dimension)` /
  `(Dimension, exponent)` tuples, so the v1.7 regression fix against
  `id()`-keyed collisions is preserved.

- **`ucon.basis` subpackage is now a clean DAG.** The load-time cycle
  `vector → graph → transforms → vector` documented in v1.7.0 is fully
  resolved. `ucon/basis/vector.py` depends only on `ucon.basis.types`;
  the two function-body deferred imports in `BasisGraph.get_transform()`
  and `_build_standard_basis_graph()` are now top-of-file. Load order is
  uniform: `types ← vector ← transforms ← graph ← ops`.

- **Deferred imports in `ucon.checking._coerce_via_graph` hoisted.**
  `from ucon.graph import get_default_graph, ConversionNotFound` and
  `from ucon.core import RebasedUnit` are now module-level. Tests that
  patched `ucon.graph.get_default_graph` were updated to patch
  `ucon.checking.get_default_graph` (the binding the function actually
  reads). No production behaviour change.

### Deprecated

- **`from ucon import UnitSystem`** is a PEP-562 alias resolving to
  `BaseUnits` and emits a `PendingDeprecationWarning`. Migration: replace
  with `from ucon import BaseUnits` (or `from ucon.system import
  BaseUnits`). Scheduled for removal in v2.0.

- **`ucon.using_graph`** is retained as a `PendingDeprecationWarning`
  alias to `ucon.using_conversion_graph`, renamed for symmetry with
  `using_basis_graph`. Migration: replace `with using_graph(g):` with
  `with using_conversion_graph(g):`. Scheduled for removal in v2.0.

- **`ucon.dimension._DIM_MUL_CACHE` / `_DIM_DIV_CACHE` /
  `_DIM_POW_CACHE`** are PEP-562 module-level aliases that emit a
  `PendingDeprecationWarning` on read and return the live `mul` / `div` /
  `pow` dict of the active `UnitSystem._algebra_cache`. Migration: read
  via `ucon.system.active()._algebra_cache.{mul,div,pow}`. Scheduled for
  removal in v2.0.

- **`ucon.units.have(name)`** emits a `DeprecationWarning` and delegates
  to `parse_unit()`. The legacy Python-variable-name fallback is dropped;
  `have()` resolves only canonical `Unit.name` and registered aliases.
  Migration: call `parse_unit(name)` and catch `UnknownUnitError`.
  Scheduled for removal in v2.0.

### Removed

- **`ucon.units.pint_volume` / `ucon.units.point_typo`.** Two pre-TOML
  Python-identifier aliases (carried since v0.x to avoid variable-name
  collisions in the hand-built module). The canonical units remain
  accessible as `units.pint` and `units.point`, with TOML-registered
  aliases `pt` / `pints` and `pt_typo`. They were never reachable through
  the resolver. Migration: replace `units.pint_volume` with `units.pint`
  and `units.point_typo` with `units.point`.

## [1.7.0] - 2026-05-09

### Changed

- **`ucon.basis` subpackage internal layout.** The 404-line
  `ucon/basis/__init__.py` has been split along the lines its docstring
  already advertised. `Basis`, `BasisComponent`, `LossyProjection`, and
  `NoTransformPath` move to a new leaf module `ucon/basis/types.py`.
  `Vector` moves to a new module `ucon/basis/vector.py`. `__init__.py`
  is now a thin re-export shim. The public API is unchanged: every
  symbol previously importable from `ucon.basis` (or `ucon`) continues
  to import from the same path. Downstream code that imported via the
  documented entry points needs no modification. Code that reached
  into the package via `from ucon.basis.__init__ import …` or relied
  on these symbols' module-of-definition (`Vector.__module__ ==
  "ucon.basis"`) will need to update — `Vector.__module__` is now
  `"ucon.basis.vector"`, etc.

- **`ucon/basis/graph.py` reorganised** to host the standard-graph
  factory and active-state accessors alongside `BasisGraph` itself.
  The eager top-of-file imports of every standard `*_TO_*` transform
  instance are now deferred inside `_build_standard_basis_graph()`,
  and `BasisTransform.identity` is deferred inside
  `BasisGraph.get_transform()`. These two function-body imports are
  the explicit, documented workaround for the load-time cycle
  `vector → graph → transforms → vector` introduced when `Vector`
  moved out of `__init__.py`. Behaviour is identical: the standard
  graph is still built lazily on first call to `get_basis_graph()`,
  context scoping via `using_basis_graph` / `using_basis` is
  unchanged, and `set_default_basis_graph` /
  `reset_default_basis_graph` retain their semantics.

- **`ucon.parsing` promoted from single-file module to subpackage.**
  The previous `ucon/parsing.py` is now `ucon/parsing/` with three
  leaf modules: `lexer.py` (the shared `_Tokenizer`, `_Token`,
  `_TokenType`, `ParseError`), `units.py` (the unit-expression grammar
  and the quantity-string `parse()` entry point), and `dimensions.py`
  (the dimension-expression grammar and `parse_dimension()`). The
  public surface is unchanged — `from ucon.parsing import parse,
  parse_dimension, parse_unit_expression, ParseError` continues to
  work via re-exports in `ucon/parsing/__init__.py`, as do private
  imports of `_Tokenizer`/`_Token`/`_TokenType`. Modules-of-definition
  shift: e.g., `ParseError.__module__ == "ucon.parsing.lexer"` now
  rather than `"ucon.parsing"`. The dimensions submodule is loaded
  lazily via PEP 562 module `__getattr__` to avoid a load-time cycle
  through `ucon.units → ucon.resolver → ucon.parsing`.

- **`parse_dimension` definition moved out of `ucon/dimension.py`**
  into `ucon/parsing/dimensions.py`. Its public import path is
  `from ucon import parse_dimension` (or `from ucon.parsing import
  parse_dimension`) — both unchanged. `from ucon.dimension import
  parse_dimension` no longer works; nothing in the public docs
  ever advertised that path.

### Added

- **`parse_unit(name)` and `parse_dimension(spec, basis=None)` public
  parsers** as the canonical string-to-object entry points.
  `parse_unit` is the new name for the existing `get_unit_by_name`
  behaviour and is exposed at the top level (`from ucon import
  parse_unit`). `parse_dimension` is a new function: it accepts (a)
  bare component symbols of the active basis (`"M"`, `"L"`, `"T"`,
  `"I"`, `"Θ"`, `"J"`, `"N"`, `"B"`), (b) bare dimension or component
  names (`"mass"`, `"velocity"`, `"force"`, `"energy"`, `"frequency"`,
  …), and (c) algebraic expressions over those atoms with `*`, `·`,
  `⋅`, `/`, `^`, Unicode superscripts, parentheses, and a `1`
  numerator (`"M*L/T^2"`, `"M·L/T²"`, `"L/T"`, `"1/T"`,
  `"M/(L*T^2)"`). Both functions are exported from `ucon`. The unit
  and dimension grammars share a single tokenizer
  (`ucon.parsing.lexer._Tokenizer`).

- **v2.0 design proposal in `ROADMAP.md`** capturing a clean-DAG
  restructure of `ucon.basis` that eliminates the residual cycle by
  changing the API rather than the file layout. The proposal makes
  `Vector.__mul__` / `__truediv__` strictly same-basis and moves
  cross-basis arithmetic (the 1.6.6 implicit-`BasisGraph`
  consultation) to explicit helpers in a new `ucon.basis.ops` module
  (`ops.unify`, `ops.multiply_via`, `ops.divide_via`). Documented as
  proposed; deferred until a major-version window.

### Deprecated

- **`ucon.resolver.get_unit_by_name`** is now a soft-deprecated alias
  for `parse_unit`. It continues to work and returns the same value
  but emits a `DeprecationWarning` on every call. Removal is
  scheduled for v2.0. All internal callers within `ucon/` have been
  migrated to `parse_unit` so the deprecation warning is only
  triggered by external code.

### Fixed

- **`Dimension` algebra caches re-keyed by value instead of by `id()`.**
  The mul/div/pow caches in `ucon/dimension.py` were previously keyed
  on `(id(self), id(other))` (or `(id(self), power)`). Because `id()`
  is only unique among simultaneously-living objects, transient
  `Dimension` instances created during expression parsing
  (`_DimensionParser._resolve_atom` constructs fresh instances per
  symbol) could be garbage-collected and have their ids reassigned to
  later transients of *different* base dimensions. The cache would
  then return a stale entry whose key happened to share an id with
  the new operand. The failure manifested on Python 3.13 in
  `parse_dimension` test sequences: parsing `"L^2"` populated the pow
  cache with `(id(transient_L), 2) → AREA`, and a subsequent parse of
  `"M*L/T^2"` whose transient `T` landed at the freed id of
  `transient_L` returned `AREA` for `T**2`, turning `M·L/T²` into
  `M·L/L² = linear_density`. The caches are now keyed by the
  `Dimension` instances themselves, which use structural hash and
  equality on `(vector, tag)`. Distinct instances with identical
  content collapse to the same key, and id reuse is no longer a
  failure mode. Performance is preserved (the pre-existing `1.2×`
  speedup over `pint` on the Unit-algebra microbenchmark holds) and
  no public API changes. Regression coverage in
  `tests/ucon/test_dimension.py::TestDimensionAlgebraCacheKeying`.

### Notes

- The basis-package split is a structural refactor with no behavioural
  change. The `parse_unit` / `parse_dimension` additions are
  additive-only; the soft-deprecation of `get_unit_by_name` preserves
  call-site compatibility under the v1.x LTS commitment, with
  hard-removal scheduled for v2.0. The `Dimension` cache-keying fix
  is a correctness fix with no API impact. Test suite is green at
  2312 passed, 2 skipped.

## [1.6.6] - 2026-05-06

### Fixed

- **Cross-basis arithmetic in `Vector` now consults the active
  `BasisGraph`.** `Vector.__mul__` and `Vector.__truediv__` previously
  raised `ValueError` on any pair of operands whose bases were not
  equal by identity. They now attempt to unify operands through a
  *clean* (non-lossy) transform path resolved against the active
  basis graph (set via `using_basis_graph` or the module default)
  before raising. Both projection directions are tried; the first
  clean projection wins. A path is "clean" when no non-zero source
  exponent would be discarded — i.e., embeddings such as SI into an
  extended basis (the shape produced by `extend_basis`) compose
  transparently, while genuine dimensional incompatibility (no path,
  or only a lossy path) continues to raise the same `ValueError` as
  before. The redundant basis-equality guard at the `Dimension` layer
  (`Dimension.__mul__`, `Dimension.__truediv__`) has been removed so
  the unification logic lives in exactly one place.

  This unblocks expressions like `USD * year` or `USD / year` when
  `economic` is registered via `extend_basis(name="economic",
  base="SI", additional_components=[currency])`: SI operands promote
  into the extended basis, the currency exponent passes through
  untouched, and the result lives in `economic`. Closes the
  cross-basis blocker in the ucon-tools sovereign-potential demo
  (issue 2.5 in the ucon-tools feedback registry). Regression coverage
  added in `tests/ucon/test_basis.py::TestVectorCrossBasisArithmetic`
  exercising extension-basis multiplication (USD·year), extension-basis
  division (USD/year), left-operand symmetry, no-transform-path
  rejection, and lossy-only-path rejection.

## [1.6.5] - 2026-05-05

### Added

- **Whole-token alias resolution for parenthesised labels.** Aliases
  containing parentheses are now resolved as a single token before the
  composite parser tokenises the input. The resolver maintains an
  internal `_VERBATIM_ALIASES` registry populated automatically when a
  unit's alias contains `(` or `)`; this is consulted at the top of
  `get_unit_by_name()` ahead of composite detection. Aliases that contain
  only multiplication or division operators (e.g. `m/s²`, `J/K`) continue
  to flow through the existing composite parser unchanged. Case-sensitive
  only — convention-bearing labels carry their canonical casing.

- **`Gy(RBE)` alias on `gray`** and **`Sv(RBE)` alias on `sievert`.**
  Used in radiation oncology (proton and heavy-ion therapy) to label
  radiobiological-equivalent dose. At the unit-resolution layer these
  resolve to the canonical SI dose units; the semantic distinction
  between RBE-weighted and unweighted quantities is a Kind-of-Quantity
  concern handled at higher layers.

## [1.6.4] - 2026-05-04

### Added

- **`solar_mass` unit** (dimension `mass`) with aliases `M☉` and
  `solar_masses`. Base-form prefactor `1.98892e+30` against `kilogram`,
  enabling `convert(1, "solar_mass", "kg")` and astrophysics-domain
  expressions of stellar and planetary masses.

- **Plural aliases on common SI and derived units** in
  `comprehensive.ucon.toml`: `amperes`/`amps`, `arcminutes`, `arcseconds`,
  `grams`, `hours`, `joules`, `liters`/`litres` (and singular `litre`),
  `lumens`, `meters`/`metres` (and singular `metre`), `newtons`, `ohms`,
  `pascals`, `radians`, `seconds`, `volts`, `watts`. Inputs like `5 meters`
  or `100 watts` now parse without requiring abbreviation.

- **Spelled-out scaled aliases not covered by prefix decomposition** in
  `ucon/units.py`. The prefix-decomposition machinery handles compact
  forms like `km`, `µs`, `mW`; this release adds the spelled-out and
  plural variants as priority-scaled aliases:
  - Length: `kilometers`, `centimeters`, `millimeters`, `micrometers`,
    `nanometers`, `picometers`.
  - Mass: `milligrams`, `micrograms`.
  - Time: `milliseconds`, `microseconds`, `nanoseconds`.
  - Volume: `milliliters`, `microliters`.
  - Power: `kilowatts`, `megawatts`, `milliwatts`.
  - Energy: `kilojoules`, `megajoules`.
  - Pressure: `kilopascals`, `megapascals`, `hectopascals`.
  - Angle: `microradian`/`microradians`, `milliradian`/`milliradians`.
  - Luminous intensity: `millilumen`/`millilumens`.

- **`dimensionless`/`unitless` aliases on `fraction`.** The existing
  `fraction` unit (dimension `ratio`) now also resolves from the words
  `dimensionless` and `unitless`, which models commonly emit for ratios
  in benchmark prompts.

- **`M` alias on `molar`** plus priority scaled aliases for `mM`, `µM`,
  `uM`, `nM`, and `pM`. `M` is the canonical chemistry symbol for molar
  concentration and now resolves to `units.molar` directly. Prefixed
  forms used in lab/clinical contexts resolve via the priority-scaled
  alias machinery and bypass ambiguous prefix decomposition.

- **Plural aliases for `day` and `minute`** (`days`, `minutes`). Other
  common time units (`hours`, `seconds`, `years`) already had plural
  aliases.

- **Parser-coverage tests** in `tests/ucon/test_unit_parsing.py`
  exercising the new plural and spelled-out scaled aliases, the
  dimensionless aliases, and the molar / prefixed-molar aliases against
  `Number(...)` construction and base-form conversion.

### Changed

- **`get_unit_by_name("M")` now resolves to `units.molar` (was
  `units.meter`).** Previously, lookup case-insensitively matched the
  meter alias `m`. Capital `M` is the universal scientific symbol for
  molar concentration (and also the SI mega prefix when used as a
  prefix), so the new resolution reflects established convention.
  Lowercase `m` continues to resolve to `meter` unchanged. Code that
  intentionally relied on case-insensitive `M`→meter must use lowercase
  `m`.

### Notes

- These additions are surface-level (catalog and aliases only); no
  `Unit`/`UnitFactor`/`ConversionGraph` semantics changed. Existing TOML
  files and pickled units remain compatible.

- Motivated by failure analysis on the UnitSafe benchmark, where natural
  prompts ("convert 100 watts for 8 hours") and gold answers (`M☉`,
  `solar_masses`, `5 mM`, `dimensionless`) used spelled-out, plural, and
  domain-symbol forms the parser did not yet recognize.

## [1.6.3] - 2026-04-15

### Added

- **Cross-basis coercion in `@enforce_dimensions`.** When a CGS-basis argument
  (e.g. dyne, erg, poise) passes dimensional validation against an SI
  constraint, the decorator now automatically coerces it to the coherent SI
  equivalent before the function body runs. This eliminates "Cannot multiply
  dimensions from different bases" errors inside decorated functions.

## [1.6.2] - 2026-04-14

### Added

- **Base-form conversion fallback.** `ConversionGraph._convert_via_base_form()`
  decomposes both source and destination `UnitProduct` expressions to their SI
  base units and computes the conversion factor as the ratio of prefactors.
  This handles conversions where factor structures don't align (e.g.,
  `kg·m/s² → N`, `J/L → Pa`, `W/m² → BTU/(h·ft²)`) without requiring
  explicit product edges — the definitional identity is already encoded in
  each unit's `base_form`.

- **Cross-basis dimensional compatibility for `@enforce_dimensions`.**
  `_dimensions_compatible()` in `ucon/checking.py` normalizes both actual and
  expected dimensions to SI via `BasisGraph` before comparing. CGS units like
  poise (dimension `cgs_dynamic_viscosity`) now satisfy constraints expecting
  the SI equivalent (`dynamic_viscosity`).

- **22 new `base_form` entries** in `comprehensive.ucon.toml` for SI-basis
  units that previously lacked decompositions: acre, ampere_per_meter, barn,
  becquerel, coulomb_meter, curie, farad, gray, hectare, henry,
  joule_per_kelvin, knot, lumen, mile_per_hour, molar, rad_dose, rem,
  siemens, sievert, tesla, weber, webers_per_meter.

### Fixed

- **Liter `base_form` prefactor** corrected from `1.0` to `0.001`
  (1 L = 0.001 m³).

- **Tex `base_form` prefactor** corrected from `9.0` to `1e-6`
  (1 tex = 1 g/km = 1e-6 kg/m).

- **Denier `base_form` prefactor** corrected from `1.0` to
  `1.1111111111111111e-07` (1 denier = 1 g/9000 m).

- **23 volume unit `base_form` prefactors** corrected. All were calibrated
  relative to liter = 1.0 (wrong) instead of m³. Affected units: acre_foot,
  barrel, bushel, cubic_foot, cubic_inch, cubic_yard, cup, fluid_ounce,
  gallon, gill, imperial_cup, imperial_fluid_ounce, imperial_gallon,
  imperial_gill, imperial_pint, imperial_quart, minim, peck, pint, quart,
  stere, tablespoon, teaspoon.

- **`generate_base_forms.py` BFS oracle** no longer assumes all reference
  units are SI-coherent (prefactor = 1.0). The BFS seed prefactor is now
  read from the unit's own TOML `base_form`, making the oracle a consistency
  checker across each dimension partition rather than relying on a hardcoded
  override table.

- **`_dimensions_compatible` crash on isolated bases.** The except clause
  in `_dimensions_compatible()` did not catch `NoTransformPath` (raised by
  `BasisGraph.get_transform()` for disconnected bases), causing an unhandled
  exception instead of returning `False`.

## [1.6.1] - 2026-04-13

### Fixed

- **Unit expression parser unified to standard left-to-right associativity.**
  `_UnitParser` (the recursive-descent parser in `ucon/parsing.py`) was using a
  non-standard "slash-opens-denominator" convention where `a/b*c` was parsed as
  `a/(b·c)`. Reverted to standard order of operations: `*` and `/` have equal
  precedence and associate left-to-right, so `a/b*c` = `(a/b)·c`. Multi-term
  denominators require explicit parentheses: `m³/(kg·s²)`.

- **Gravitational constant (G), molar gas constant (R), and Stefan-Boltzmann
  constant (σ) unit strings** in `comprehensive.ucon.toml` restored to use
  explicit parentheses: `m³/(kg·s²)`, `J/(mol·K)`, `W/(m²·K⁴)`. Without
  parentheses, left-to-right parsing produced incorrect unit decompositions.

- **TOML exponent formatting.** The serializer emitted `^2.0` for integral
  exponents; now emits `^2`. The parser also now accepts float exponents
  (`^2.0`) for backward compatibility with previously-emitted TOML files.

### Removed

- `_parse_product_expression()` and `_resolve_single_factor()` from
  `ucon/serialization.py`. Product expression parsing is now handled
  exclusively by `_UnitParser` via `get_unit_by_name()`, eliminating a
  redundant regex-based parser that had diverged in associativity semantics.

## [1.6.0] - 2026-04-12

### Added

- **TOML as single source of truth.** `ucon/comprehensive.ucon.toml` is now
  the canonical declaration site for all units, conversion edges, and physical
  constants. Python modules (`ucon/units.py`, `ucon/graph.py`,
  `ucon/constants.py`) consume the TOML at import time via a central
  single-load cache (`ucon/_loader.py`). ~1,250 lines of hardcoded Python
  declarations replaced by ~150 lines of loader infrastructure.

- **`ucon/_loader.py`** — central TOML loader with caching. `get_graph()`,
  `get_units()`, `get_constants()` return the same object instances across
  all consumers. `reset()` for test isolation.

- **`ucon/expressions.py`** — AST-based safe expression evaluator for TOML
  factor fields. Evaluates symbolic expressions like `"1 / Eₕ"` and
  `"mP * c**2 / Eₕ"` where symbols resolve to physical constants. Propagates
  relative uncertainty via GUM rules (quadrature for multiply/divide,
  `|n| * rel` for power, absolute quadrature for add/subtract). Only
  `ast.Constant`, `ast.Name`, `ast.BinOp`, and `ast.UnaryOp` nodes are
  accepted — no `eval()`.

- **Symbolic expression factors in TOML.** 14 conversion edges now use
  constant expression strings instead of hardcoded numeric values:
  - `factor = "gₙ"` for kilogram_force → newton, millimeter_water → pascal
  - `factor = "1 / Eₕ"` for joule → hartree
  - `factor = "1 / Ry"` for joule → rydberg
  - `factor = "1 / e"` for joule → electron_volt
  - `factor = "1 / a₀"` for meter → bohr_radius
  - `factor = "1 / mP"`, `"1 / lP"`, `"1 / tP"`, `"1 / TP"` for
    SI → Planck unit edges
  - `factor = "e / Eₕ"`, `"e / (mP * c**2)"`, `"mP * c**2 / Eₕ"` for
    compound cross-basis edges
  - `rel_uncertainty` auto-derived from referenced constants via GUM
    quadrature — no longer hardcoded on these edges.

- **Auto-generated `.pyi` type stubs** for IDE autocomplete:
  - `ucon/units.pyi` — all unit names typed as `Unit`
  - `ucon/constants.pyi` — all constant instances and accessor functions
  - Generated by `scripts/generate_unit_stubs.py` and
    `scripts/generate_constant_stubs.py`

- **Makefile targets for stub generation:**
  - `make stubs` — generate all stubs (units, constants, dimensions)
  - `make unit-stubs`, `make constant-stubs`, `make dimension-stubs` —
    individual targets
  - `make stubs-check` — verify all stubs are current (for CI)

- **`stubs` CI job** (`.github/workflows/tests.yaml`) — verifies `.pyi`
  stubs match the current TOML on every push and PR. Wired into the
  `ci` gate job.

- `tests/ucon/test_expressions.py` — expression parser tests covering
  numeric literals, constant references, division, multiplication, power,
  compound expressions, unknown symbols, and unsupported syntax.

- `tests/ucon/test__loader.py` — loader integration tests covering graph
  construction, unit extraction, constant extraction, object identity
  guarantees, and cache behavior.

### Changed

- **`ucon/units.py` rewritten** — ~400 lines of hardcoded `Unit()`
  declarations removed, replaced by a thin loader that populates module
  globals from the TOML. `register_priority_scaled_alias()` calls,
  `UnitSystem` definitions, and `have()` preserved.

- **`ucon/graph.py` trimmed** — `_build_standard_edges()` (~557 lines of
  hardcoded `graph.add_edge()` calls) removed. `_build_standard_graph()`
  delegates to `_loader.get_graph()`.

- **`ucon/constants.py` rewritten** — `_build_constants()` (~300 lines of
  hardcoded `Constant()` instances) removed, replaced by loader delegation.
  `Constant` gains an `aliases: tuple = ()` field for TOML round-trip
  fidelity.

- **`ucon/serialization.py` enhanced** — constants materialized before edges
  (step 7, was step 10) so expression factors can resolve constant symbols.
  `_build_edge_map()` accepts string expression factors containing constant
  references. `FORMAT_VERSION` bumped to `"1.4"`. NFKC-normalized constant
  symbols registered in the lookup table for Python AST compatibility.

- **`ucon/comprehensive.ucon.toml` moved into package** — canonical copy
  now at `ucon/comprehensive.ucon.toml`, shipped as package data. Includes
  26 constants with full CODATA metadata, 14 expression-based edge factors,
  no `[contexts.*]` section (contexts stay in Python).

- **Makefile `stubs` target expanded** from dimension-only to all three
  stub types (units, constants, dimensions). Old `toml` target removed.

### Removed

- `scripts/generate_comprehensive_toml.py` — the old Python → TOML export
  script. The TOML is now hand-edited as the source of truth.

- `_build_standard_edges()` body in `ucon/graph.py` (retained as no-op
  stub for backward compatibility).

- `_build_constants()` body in `ucon/constants.py`.

- Hardcoded `Unit()` declarations in `ucon/units.py`.

- `make toml` Makefile target.

### Notes

- **Backward compatibility.** All public APIs (`from ucon.units import meter`,
  `from ucon.constants import speed_of_light`, `get_default_graph()`, etc.)
  work identically. The 2,095-test suite passes without modification.

- **Object identity guarantee.** All consumers share the same `Unit` and
  `Constant` instances from a single TOML parse via `_loader.py`. E.g.,
  `units.meter is get_default_graph()._name_registry_cs["meter"]`.

- **Import performance.** The ~4,600-line TOML is parsed once at first
  import and cached. If performance becomes a concern, a pre-compiled
  binary cache can be added in a future release.

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
  basis and is scheduled for v1.4.0 (basis isomorphisms release).

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
[2.0.0]: https://github.com/withtwoemms/ucon/compare/1.12.0...2.0.0
[1.12.0]: https://github.com/withtwoemms/ucon/compare/1.11.0...1.12.0
[1.11.0]: https://github.com/withtwoemms/ucon/compare/1.10.0...1.11.0
[1.10.0]: https://github.com/withtwoemms/ucon/compare/1.9.2...1.10.0
[1.9.2]: https://github.com/withtwoemms/ucon/compare/1.9.1...1.9.2
[1.9.1]: https://github.com/withtwoemms/ucon/compare/1.9.0...1.9.1
[1.9.0]: https://github.com/withtwoemms/ucon/compare/1.8.3...1.9.0
[1.8.3]: https://github.com/withtwoemms/ucon/compare/1.8.2...1.8.3
[1.8.2]: https://github.com/withtwoemms/ucon/compare/1.8.1...1.8.2
[1.8.1]: https://github.com/withtwoemms/ucon/compare/1.8.0...1.8.1
[1.8.0]: https://github.com/withtwoemms/ucon/compare/1.7.0...1.8.0
[1.7.0]: https://github.com/withtwoemms/ucon/compare/1.6.6...1.7.0
[1.6.6]: https://github.com/withtwoemms/ucon/compare/1.6.5...1.6.6
[1.6.5]: https://github.com/withtwoemms/ucon/compare/1.6.4...1.6.5
[1.6.4]: https://github.com/withtwoemms/ucon/compare/1.6.3...1.6.4
[1.6.3]: https://github.com/withtwoemms/ucon/compare/1.6.2...1.6.3
[1.6.2]: https://github.com/withtwoemms/ucon/compare/1.6.1...1.6.2
[1.6.1]: https://github.com/withtwoemms/ucon/compare/1.6.0...1.6.1
[1.6.0]: https://github.com/withtwoemms/ucon/compare/1.5.0...1.6.0
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

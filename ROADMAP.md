# ucon Roadmap

> *A clear path from algebraic foundation to a stable 1.0 release.*

---

## Vision

ucon is a dimensional analysis library for engineers building systems where unit handling is infrastructure, not just convenience.

**Target users:**

- Library authors embedding unit handling without global state
- Domain specialists defining dimensions that match their field
- Modern stack developers wanting first-class Pydantic, Polars, MCP support

---

## Release Timeline

| Version | Theme | Status |
|---------|-------|--------|
| v0.3.x | Dimensional Algebra | Complete |
| v0.4.x | Core Conversion + Information | Complete |
| v0.5.0 | Dimensionless Units | Complete |
| v0.5.x | Uncertainty Propagation | Complete |
| v0.5.x | BasisTransform + UnitSystem | Complete |
| v0.6.0 | Pydantic + Serialization | Complete |
| v0.6.x | MCP Server | Complete |
| v0.6.x | LogMap + Nines | Complete |
| v0.6.x | Dimensional Type Safety | Complete |
| v0.7.0 | MCP Error Suggestions | Complete |
| v0.7.1 | MCP Error Infrastructure for Multi-Step Chains | Complete |
| v0.7.2 | Compute Tool | Complete |
| v0.7.3 | Graph-Local Name Resolution | Complete |
| v0.7.4 | UnitPackage + TOML Loading | Complete |
| v0.7.5 | MCP Extension Tools | Complete |
| v0.7.6 | docs.ucon.dev | Complete |
| v0.7.7 | Schema-Level Dimension Constraints | Complete |
| v0.8.0 | Basis Abstraction Core | Complete |
| v0.8.1 | BasisGraph + Standard Bases | Complete |
| v0.8.2 | Dimension Integration | Complete |
| v0.8.3 | ConversionGraph Integration | Complete |
| v0.8.4 | Basis Context Scoping | Complete |
| v0.8.5 | String Parsing | Complete |
| v0.9.0 | Physical Constants | Complete |
| v0.9.1 | Logarithmic Units | Complete |
| v0.9.2 | MCP Constants Tools | Complete |
| v0.9.3 | Natural Units + MCP Session Fixes | Complete |
| v0.9.4 | MCP Extraction | Complete |
| v0.10.0 | Scientific Computing | Planned |
| v1.0.0 | API Stability | Planned |

---

## Current Version: **v0.9.4** (complete)

Building on v0.9.3 baseline:
- `ucon.basis` (`Basis`, `BasisComponent`, `Vector`, `BasisTransform`, `BasisGraph`, `ConstantAwareBasisTransform`)
- `ucon.bases` (standard bases: `SI`, `CGS`, `CGS_ESU`, `NATURAL`; standard transforms including `SI_TO_NATURAL`)
- `ucon.dimension` (`Dimension` as frozen dataclass backed by basis-aware `Vector`)
- `ucon.core` (`Scale`, `Unit`, `UnitFactor`, `UnitProduct`, `Number`, `Ratio`, `UnitSystem`, `RebasedUnit`, `Exponent`)
- `ucon.maps` (`Map`, `LinearMap`, `AffineMap`, `ComposedMap`, `LogMap`, `ExpMap`)
- `ucon.graph` (`ConversionGraph`, default graph, `get_default_graph()`, `using_graph()`, cross-basis conversion)
- `ucon.units` (SI + imperial + information + angle + ratio units, callable syntax, `si` and `imperial` systems, `get_unit_by_name()`)
- `ucon.pydantic` (`Number` type for Pydantic v2 models)
- Callable unit API: `meter(5)`, `(mile / hour)(60)`
- `Number.simplify()` for base-scale normalization
- Pseudo-dimensions: `ANGLE`, `SOLID_ANGLE`, `RATIO`, `COUNT` with semantic isolation
- Uncertainty propagation: `meter(1.234, uncertainty=0.005)` with quadrature arithmetic
- User-definable dimensional bases via `Basis` and `BasisGraph`
- `Dimension` now uses basis-aware `Vector` with explicit basis reference
- Pydantic v2 integration with JSON serialization
- Unit string parsing: `get_unit_by_name("kg*m/s^2")`
- Auto-generated `dimension.pyi` stubs for IDE code completion
- Basis context scoping: `using_basis()`, `using_basis_graph()`, `get_default_basis()`
- Quantity string parsing: `parse("1.234 ± 0.005 m")` → `Number` with uncertainty
- Physical constants: `Constant` class with CODATA 2022 values and uncertainty propagation
- Logarithmic units: pH with concentration dimension, dBm, dBW, dBV, dBSPL
- Natural units: `NATURAL` basis with c=ℏ=k_B=1, `ConstantAwareBasisTransform` for non-square transforms
- Namespace package support: `pkgutil.extend_path` enables coexistence with ucon-tools

---

## v0.3.x — Dimensional Algebra (Complete)

**Theme:** Algebraic foundation.

- [x] `Vector` and `Dimension` classes
- [x] Unit/Scale separation: `Unit` is atomic, `UnitFactor` pairs unit+scale
- [x] `UnitProduct` with `fold_scale()` and `_residual_scale_factor`
- [x] `Exponent` algebraic operations (`__mul__`, `__truediv__`, `to_base`)
- [x] Scale/Exponent integration for prefix arithmetic

**Outcomes:**
- All units acquire explicit dimensional semantics
- Enables composable and type-safe dimensional operations
- Establishes the mathematical foundation for future conversions
- Unified algebraic foundation for all scaling and magnitude operations
- Clean Unit/Scale separation: `Unit` is an atomic symbol, `UnitFactor` pairs it with a `Scale`
- `UnitProduct` correctly tracks residual scale from cancelled units
- Type system is ready for a `ConversionGraph` to be built on top

---

## v0.4.x — Conversion System Foundations (Complete)

**Theme:** First useful release.

- [x] `Map` hierarchy (`LinearMap`, `AffineMap`, `ComposedMap`)
- [x] `Quantity` class (callable unit constructor)
- [x] `ConversionGraph` with edge API and BFS path finding
- [x] `Number.to()` wired to graph
- [x] Default graph with SI + Imperial + conventional units
- [x] Unit registry with `get_unit_by_name()`
- [x] Graph management (`get_default_graph`, `set_default_graph`, `using_graph`)
- [x] `Dimension.information` with `bit`, `byte`
- [x] `Vector` extended to 8 components (added B for information)
- [x] Binary scale prefixes: `kibi`, `mebi`, `gibi`, `tebi`, `pebi`, `exbi`
- [x] `Number.simplify()` for base-scale normalization
- [x] Temperature, pressure, and base SI conversion tests
- [x] Exponent/Scale developer guide

**Outcomes:**
- Unified conversion taxonomy
- Reversible, dimension-checked conversions
- Scale-aware graph that leverages the `Unit`/`UnitFactor` separation from v0.3.x
- Ergonomic API: units are callable, returning `Number` instances
- Information dimension support (bit, byte) with binary prefix compatibility
- `Number.simplify()` for expressing quantities in base scale
- Forms the basis for nonlinear and domain-specific conversion families

---

## v0.5.0 — Dimensionless Units (Complete)

**Theme:** Complete the dimension model.

- [x] Pseudo-dimensions: `angle`, `solid_angle`, `ratio` (same zero vector, distinct enum identity)
- [x] Angle units: `radian`, `degree`, `gradian`, `arcminute`, `arcsecond`, `turn`
- [x] Solid angle units: `steradian`, `square_degree`
- [x] Ratio units: `percent`, `permille`, `ppm`, `ppb`, `basis_point`
- [x] Cross-pseudo-dimension conversion fails (enforced isolation)
- [x] Conversion edges for all new units

**Outcomes:**
- Semantic isolation prevents nonsensical conversions (radian → percent)
- Rich dimensionless unit coverage for geometry, optics, finance, chemistry
- Complete dimension model ready for metrology extensions

---

## v0.5.x — Uncertainty Propagation (Complete)

**Theme:** Metrology foundation.

- [x] `Number.uncertainty: float | None`
- [x] Propagation through arithmetic (uncorrelated, quadrature)
- [x] Propagation through conversion via `Map.derivative()`
- [x] Construction: `meter(1.234, uncertainty=0.005)`
- [x] Display: `1.234 ± 0.005 meter`

**Outcomes:**
- First-class uncertainty support for scientific and engineering workflows
- Correct propagation through both arithmetic and unit conversion
- Foundation for full metrology capabilities

---

## v0.5.x — BasisTransform + UnitSystem (Complete)

**Theme:** Cross-system architecture.

- [x] `Vector` with `Fraction` exponents for exact arithmetic
- [x] `UnitSystem` class (named dimension-to-unit mapping)
- [x] `BasisTransform` class (matrix-based dimensional basis transformation)
- [x] `RebasedUnit` class (provenance-preserving cross-basis unit)
- [x] `NonInvertibleTransform` exception for surjective transforms
- [x] Prebuilt systems: `units.si`, `units.imperial`
- [x] `graph.add_edge()` with `basis_transform` parameter
- [x] `graph.connect_systems()` for bulk edge creation
- [x] Cross-basis conversion via rebased paths
- [x] Introspection: `list_transforms()`, `list_rebased_units()`, `edges_for_transform()`

**Outcomes:**
- `BasisTransform` enables conversions between incompatible dimensional structures
- Matrix operations with exact `Fraction` arithmetic (no floating-point drift)
- Invertibility detection with clear error messages for surjective transforms
- Named unit systems for domain-specific workflows
- Foundation for custom dimension domains

---

## v0.6.0 — Pydantic + Serialization (Complete)

**Theme:** API and persistence integration.

- [x] Native Pydantic v2 support for `Number`
- [x] JSON serialization/deserialization
- [x] Pickle support
- [x] Unit string parsing: `get_unit_by_name()` with Unicode and ASCII notation

**Outcomes:**
- Native validation and serialization for dimensioned quantities
- Enables safe configuration in data models and APIs
- Bridges ucon's algebraic model with modern Python typing ecosystems
- Unit strings parsed in both Unicode (`m/s²`) and ASCII (`m/s^2`) notation

---

## v0.6.x — MCP Server (Complete)

**Theme:** AI agent integration.

> **Note:** MCP functionality moved to [ucon-tools](https://github.com/withtwoemms/ucon-tools) in v0.9.4.
> Install via `pip install ucon-tools[mcp]`.

- [x] MCP server exposing unit conversion tools
- [x] `convert` tool with dimensional validation
- [x] `list_units`, `list_scales`, `list_dimensions` discovery tools
- [x] `check_dimensions` compatibility tool
- [x] stdio transport for Claude Desktop, Claude Code, Cursor
- [x] `ucon-mcp` CLI entry point

**Outcomes:**
- Zero-code adoption for AI tool users
- Agents can perform unit-safe arithmetic without codebase integration
- Dimensional errors become visible and correctable in conversation

---

## v0.6.x — LogMap + Nines (Complete)

**Theme:** Logarithmic conversions.

- [x] `LogMap` class: `y = scale · log_base(x) + offset`
- [x] `ExpMap` class: `y = base^(scale · x + offset)`
- [x] Composition with existing maps via `@` operator
- [x] Derivative support for uncertainty propagation
- [x] `nines` unit for SRE availability (99.999% = 5 nines)
- [x] `fraction` unit (renamed from `ratio_one`)

**Outcomes:**
- Foundation for logarithmic unit conversions
- SRE teams can express availability in nines notation
- Uncertainty propagates correctly through nonlinear conversions
- Paves the way for decibels, pH in v0.9.0

---

## v0.6.x — Dimensional Type Safety (Complete)

**Theme:** Type-directed validation for domain formulas.

- [x] Human-readable derived dimension names (`derived(length^3/time)` not `Vector(...)`)
- [x] `Number[Dimension]` type-safe generics via `typing.Annotated`
- [x] `DimConstraint` marker class for annotation introspection
- [x] `@enforce_dimensions` decorator for runtime validation at function boundaries

**Outcomes:**
- Dimension errors caught at function boundaries with clear messages
- Domain authors declare dimensional constraints declaratively, not imperatively
- Foundation for MCP error suggestions and schema-level constraints

---

## v0.7.0 — MCP Error Suggestions (Complete)

**Theme:** AI agent self-correction.

- [x] `ConversionError` response model with `likely_fix` and `hints`
- [x] Fuzzy matching for unknown units with confidence tiers (≥0.7 for `likely_fix`)
- [x] Compatible unit suggestions from graph edges
- [x] Pseudo-dimension isolation explanation
- [x] `ucon/mcp/suggestions.py` module (independently testable)
- [x] Error handling in `convert()`, `check_dimensions()`, `list_units()`

**Outcomes:**
- MCP tools return structured errors instead of raw exceptions
- High-confidence fixes enable single-retry correction loops
- AI agents can self-correct via readable error diagnostics
- Foundation for schema-level dimension constraints

---

## v0.7.1 — MCP Error Infrastructure for Multi-Step Chains (Complete)

**Theme:** Architectural prerequisites for multi-step factor-label chains.

- [x] SI symbol coverage audit (`A` for ampere, `kat` for katal)
- [x] `catalytic_activity` dimension and `katal` unit added
- [x] `step: int | None` field in `ConversionError` for chain error localization
- [x] `resolve_unit()` helper to reduce try/except duplication
- [x] `build_parse_error` builder for malformed composite expressions
- [x] Priority alias invariant documented for contributors

**Outcomes:**
- Expressions like `V/mA`, `mA·h`, `µA/cm²`, `mkat` resolve correctly
- Error responses can localize failures to specific steps in a chain
- MCP server code is DRY and ready for compute's N-factor resolution
- `ParseError` wrapped in structured `ConversionError` like other error types

---

## v0.7.2 — Compute Tool (Complete)

**Theme:** Multi-step factor-label calculations for AI agents.

### Interrupt: Dimension.count + `each` Unit (Complete)

Prerequisite for factor-label chains with countable items (tablets, doses).

- [x] `Dimension.count` pseudo-dimension (zero vector, named identity)
- [x] `each` unit with aliases `ea`, `item`, `ct`
- [x] Pseudo-dimension isolation (count ≠ angle ≠ ratio)
- [x] `mg/ea` renders correctly with `mass` dimension
- [x] MCP tests for `list_units(dimension="count")`, fuzzy recovery

**Design decision:** Single `each` unit instead of domain-specific atomizers (dose, tablet, capsule). Atomizers are application-layer metadata, not core units.

### Compute Tool (Complete)

- [x] `compute` tool for dimensionally-validated factor-label chains
- [x] `ComputeStep` and `ComputeResult` response models
- [x] `steps` array in response showing intermediate dimensional state
- [x] Per-step error localization using `ConversionError.step`
- [x] Multi-factor cancellation tests (medical dosage, stoichiometry, 6-7 factor chains)
- [x] `watt_hour` unit with `Wh` alias for energy chain tests
- [x] Accumulator-style unit tracking (flat factor accumulation)
- [x] Residual scale factor propagation through graph conversions
- [x] `second*second` → `s²` parsing fix (explicit factor accumulation)

**Outcomes:**
- AI agents can run factor-label chains with dimensional safety at each step
- Intermediate state visible for debugging and benchmarks (SLM vs LLM comparison)
- Agents can self-correct mid-chain rather than only at the end
- Factor-label methodology preserved: `154 lb × (1 kg / 2.205 lb) × (15 mg / kg·day)` yields `mg/d` not `kg/d`
- Countable items (30 ea × 500 mg/ea = 15000 mg) work in factor-label chains

---

## v0.7.3 — Graph-Local Name Resolution (Complete)

**Theme:** Shared infrastructure for dynamic unit extension.

- [x] `ConversionGraph._name_registry` (case-insensitive) and `_name_registry_cs` (case-sensitive)
- [x] `graph.register_unit(unit)` — Register unit for name resolution within graph
- [x] `graph.resolve_unit(name)` — Lookup in graph-local registry, return None if not found
- [x] `graph.copy()` — Deep copy edges, shallow copy registries
- [x] `_parsing_graph` ContextVar for threading resolution through parsing
- [x] `using_graph()` sets both conversion and parsing context
- [x] `_lookup_factor()` checks graph-local first, falls back to global
- [x] `_build_standard_graph()` calls `register_unit()` for all standard units

**Outcomes:**
- Unit name resolution becomes graph-scoped, not global
- `using_graph(custom_graph)` automatically scopes both conversions AND name lookups
- Foundation for UnitPackage (v0.7.4) and MCP extension tools (v0.7.5)
- No global state mutation required for custom unit definitions

---

## v0.7.4 — UnitPackage + TOML Loading (Complete)

**Theme:** Config-file-based unit extension for application developers.

- [x] `UnitDef` dataclass: `{name, dimension, aliases}`
- [x] `EdgeDef` dataclass: `{src, dst, factor}`
- [x] `UnitPackage` frozen dataclass: `{name, version, units, edges, requires}`
- [x] `load_package(path)` — Parse TOML file into `UnitPackage`
- [x] `graph.with_package(pkg)` — Return new graph with package contents added
- [x] `set_default_graph(graph)` — Already implemented in v0.7.3
- [x] Example package: `examples/units/aerospace.ucon.toml`

**Outcomes:**
- Implementers define domain units in TOML config files
- Units loaded at application startup without modifying library code
- Immutable composition: `graph.with_package(a).with_package(b)`
- No global state mutation — graphs are composed, not mutated
- Foundation for ucon.dev marketplace of domain packages

---

## v0.7.5 — MCP Extension Tools (Complete)

**Theme:** Runtime unit extension for AI agents.

### Session Tools (Token Efficient)

- [x] `_session_graph` ContextVar for session-scoped custom graphs
- [x] `define_unit(name, dimension, aliases)` — Register unit in session graph
- [x] `define_conversion(src, dst, factor)` — Add edge to session graph
- [x] `reset_session()` — Clear session graph, return to default

### Inline Parameters (Recoverable)

- [x] `convert(..., custom_units=[...], custom_edges=[...])` — Self-contained conversion
- [x] `compute(..., custom_units=[...], custom_edges=[...])` — Self-contained multi-step
- [x] Graph caching by definition hash for performance

**Outcomes:**
- Agents can bring their own units without prior registration
- Session tools minimize token cost for repeated definitions
- Inline parameters enable recovery when session state is lost
- Hybrid approach: session for efficiency, inline for fault tolerance
- Exotic domain evals (aerospace, radiation, chemeng) work without core bloat

---

## v0.7.6 — docs.ucon.dev (Complete)

**Theme:** Public documentation site.

- [x] MkDocs Material site at docs.ucon.dev
- [x] Getting Started, Guides, Reference, Architecture sections
- [x] MCP Server documentation reorganized into dedicated directory
- [x] Domain walkthroughs (nursing dosage)

**Outcomes:**
- Comprehensive public documentation for library users
- Clear separation of guides, reference, and architecture content
- Foundation for community adoption

---

## v0.7.7 — Schema-Level Dimension Constraints (Complete)

**Theme:** Pre-call validation for AI agents.

- [x] `ucon/mcp/schema.py` — `extract_dimension_constraints()` introspects `@enforce_dimensions` functions
- [x] `ucon/mcp/formulas.py` — `@register_formula` decorator with `FormulaInfo` dataclass
- [x] `list_formulas` MCP tool — Returns registered formulas with parameter dimensions
- [x] `call_formula` MCP tool — Invokes formulas with dimensionally-validated inputs
- [x] `FormulaResult` and `FormulaError` response models
- [x] Error types: `unknown_formula`, `missing_parameter`, `invalid_parameter`, `dimension_mismatch`

**Outcomes:**
- MCP schemas declare expected dimensions per parameter
- Agents can discover formulas via `list_formulas()` before calling
- `call_formula()` validates dimensions at call time with structured errors
- Completes the type-directed correction loop
- Foundation for ucon.dev marketplace of domain formula packages

---

## v0.8.0 — Basis Abstraction Core (complete)

**Theme:** User-definable dimensional coordinate systems.

**Design document:** `docs/internal/IMPLEMENTATION_PLAN_basis-abstraction.md`

- [x] `BasisComponent` class: atomic generator of a dimensional basis
- [x] `Basis` class: ordered collection of components with name/symbol indexing
- [x] `Vector` class: basis-aware exponent vector with named field access (`v["L"]`, `v["mana"]`)
- [x] `BasisTransform` class: matrix-based transformation with exact `Fraction` arithmetic
- [x] `inverse()` method: Gaussian elimination for square transforms
- [x] `embedding()` method: canonical embedding for non-square projections
- [x] `LossyProjection` exception: fail-by-default when projecting to zero

**Outcomes:**
- Dimensional basis becomes user-definable, not hardcoded to SI
- Foundation for CGS, CGS-ESU, natural units (c=ℏ=1), and custom domains
- Exact matrix arithmetic prevents round-trip drift
- New types introduced alongside existing (no breaking changes)

---

## v0.8.1 — BasisGraph + Standard Bases (complete)

**Theme:** Graph-based transform composition and standard bases.

- [x] `BasisGraph` class: graph of basis transforms with path-finding
- [x] Transitive composition: SI→CGS + CGS→CGS-ESU = SI→CGS-ESU
- [x] `NoTransformPath` exception for disconnected bases
- [x] `get_transform(source, target)` with BFS and caching
- [x] `reachable_from()` and `are_connected()` introspection
- [x] `with_transform()` copy-on-extend pattern
- [x] Standard bases: `SI`, `CGS`, `CGS_ESU` in `ucon.bases`
- [x] Standard transforms: `SI_TO_CGS`, `SI_TO_CGS_ESU`, `CGS_TO_SI`

**Outcomes:**
- Register N-1 edges for N bases instead of N² explicit transforms
- Custom domains (game, finance) correctly isolated from SI
- Separation of concerns: BasisGraph (type checking) vs ConversionGraph (numeric conversion)

---

## v0.8.2 — Dimension Integration (Complete)

**Theme:** Wire new Vector into Dimension.

- [x] `Dimension.vector` uses new basis-aware `Vector`
- [x] `Dimension.basis` property delegating to `vector.basis`
- [x] `Dimension.from_components(basis, length=1, mass=2)` factory
- [x] Backward-compatible construction for SI dimensions
- [x] `Dimension` refactored from Enum to frozen dataclass
- [x] `resolve(vector)` function for dimension lookup/creation
- [x] Pseudo-dimensions via `Dimension.pseudo()` factory with tag isolation
- [x] Delete `ucon/algebra.py` (pulled forward from v0.9.0)
- [x] Move `Exponent` to `ucon/core.py` (pulled forward from v0.9.0)

**Outcomes:**
- Dimensions carry explicit basis reference
- Foundation for cross-basis dimensional comparison
- Clean module structure achieved early

---

## v0.8.3 — ConversionGraph Integration (Complete)

**Theme:** Cross-basis conversion validation and BasisTransform unification.

### Developer Experience

- [x] Auto-generated `dimension.pyi` stubs for IDE code completion (`make stubs`)

### BasisGraph Integration

- [x] `ConversionGraph` accepts `BasisGraph` as constructor parameter
- [x] `add_edge()` validates cross-basis edges via `BasisGraph`
- [x] `convert()` validates dimensional compatibility via `BasisGraph`
- [x] `Unit.basis` property: `return self.dimension.vector.basis`
- [x] `Unit.is_compatible(other)` using `BasisGraph`

### BasisTransform Cleanup

- [x] Update `RebasedUnit` to use `ucon.basis.BasisTransform`
- [x] Update `ConversionGraph` cross-basis methods to use new `BasisTransform`
- [x] Delete old `BasisTransform` from `ucon/core.py`
- [x] Remove `NewBasisTransform` alias from `ucon/__init__.py`
- [x] Export only `BasisTransform` from `ucon.basis`

**Outcomes:**
- IDE code completion works for `Dimension.length`, `Dimension.velocity`, etc.
- Cross-basis unit edges validated at registration time
- Dimensional errors caught before numeric conversion attempted
- Single unified `BasisTransform` implementation

---

## v0.8.4 — Basis Context Scoping (Complete)

**Theme:** Thread-safe basis isolation.

- [x] `_default_basis` ContextVar with SI fallback
- [x] `_basis_graph_context` ContextVar for graph scoping
- [x] `using_basis(basis)` context manager
- [x] `using_basis_graph(graph)` context manager
- [x] `get_default_basis()` accessor
- [x] `get_basis_graph()` accessor
- [x] `set_default_basis_graph()` / `reset_default_basis_graph()` for module-level control
- [x] `Dimension.from_components()` and `Dimension.pseudo()` respect context basis

**Outcomes:**
- Per-thread/task basis isolation (same pattern as `using_graph()`)
- Injectable basis graphs for testing and multi-tenant scenarios
- Dynamic cross-system conversion paths via context scoping

---

## v0.8.5 — String Parsing (Complete)

**Theme:** Ergonomic input.

- [x] `parse("60 mi/h")` → `Number` (quantity + unit parsing)
- [x] `parse("kg * m / s^2")` → `UnitProduct` (completed in v0.6.0 via `get_unit_by_name()`)
- [x] Alias resolution (`meters`, `metre`, `m` all work) (completed in v0.6.0)
- [x] Uncertainty parsing: `parse("1.234 ± 0.005 m")` with `±` and `+/-` notation
- [x] Parenthetical uncertainty: `parse("1.234(5) m")` (metrology convention)
- [x] Scientific notation: `parse("1.5e3 m")`
- [x] Dimensionless numbers: `parse("100")` returns `Number` with no unit
- [x] Example: `examples/parsing/parse_quantities.py`

**Outcomes:**
- Human-friendly unit input for interactive and configuration use cases
- Robust alias handling for international and domain-specific conventions
- Complete round-trip: parse → compute → serialize
- Uncertainty input matches common scientific notation conventions

---

## v0.9.0 — Physical Constants (Complete)

**Theme:** CODATA physical constants with uncertainty propagation.

- [x] `Constant` dataclass with symbol, name, value, unit, uncertainty, source
- [x] SI defining constants (exact): `c`, `h`, `e`, `k_B`, `N_A`, `K_cd`, `ΔνCs`
- [x] Derived constants (exact): `ℏ`, `R`, `σ`
- [x] Measured constants: `G`, `α`, `m_e`, `m_p`, `m_n`, `ε₀`, `μ₀`
- [x] Unicode and ASCII aliases
- [x] Arithmetic operators return `Number` with uncertainty propagation
- [x] `constants` module exported from `ucon`

**Outcomes:**
- Physical constants with CODATA 2022 uncertainties
- E=mc², E=hν formulas work naturally
- Measured constant uncertainty propagates through calculations

---

## v0.9.1 — Logarithmic Units (Complete)

**Theme:** Decibels, nepers, and pH scale.

- [x] `LogMap`/`ExpMap` for logarithmic conversions (completed in v0.6.x)
- [x] `decibel`, `bel`, `neper` units (completed in v0.9.0)
- [x] Reference-level infrastructure for dBm, dBV, dBW, dBSPL variants (completed in v0.9.0)
- [x] `pH` unit with concentration ↔ pH conversion
- [x] Uncertainty propagation through logarithmic conversions (via `LogMap.derivative()`)

**Outcomes:**
- Acoustics (dB), chemistry (pH), and signal processing domains enabled
- Reference-level variants (dBm = dB relative to 1 mW) supported
- pH conversion uses concentration dimension for dimensional consistency

---

## v0.9.2 — MCP Constants Tools (Complete)

**Theme:** AI agent access to physical constants.

- [x] `list_constants(category)` MCP tool
- [x] `define_constant(symbol, value, unit, uncertainty)` MCP tool
- [x] Session constants infrastructure (`_session_constants` ContextVar)
- [x] `all_constants()` function to enumerate built-in constants
- [x] `get_constant_by_symbol()` function for constant lookup
- [x] `Constant.category` field for filtering

**Outcomes:**
- AI agents can discover and use physical constants
- Custom constants for domain-specific calculations
- Session constants persist until `reset_session()` is called

---

## v0.9.3 — Natural Units + MCP Session Fixes (Complete)

**Theme:** Custom dimensional bases where c=ℏ=1, plus MCP reliability fixes.

### Natural Units

- [x] `ConstantAwareBasisTransform` with `inverse()` for non-square transforms
- [x] `ConstantBinding` dataclass for tracking which constants absorb dimensions
- [x] `NATURAL` basis with single energy dimension
- [x] SI → NATURAL transform: T→E⁻¹, L→E⁻¹, M→E, Θ→E (via ℏ, c, k_B)
- [x] NATURAL → SI inverse transform
- [x] Documentation and examples (`examples/basis/`)

### MCP Safety Improvements (Feedback Issues)

- [x] All session-dependent tools use FastMCP `Context` injection

**Outcomes:**
- Natural units leverage custom basis infrastructure
- Foundation for particle physics and quantum field theory domains
- MCP tools are more reliable for multi-call agent workflows

---

## v0.9.4 — MCP Extraction (Complete)

**Theme:** Separate MCP tooling into ucon-tools package.

- [x] Extract `ucon.mcp` subpackage to `ucon-tools` repository
- [x] Add `pkgutil.extend_path()` for namespace package coexistence
- [x] Remove MCP optional dependency and entry point from pyproject.toml
- [x] Update documentation to reference `ucon-tools[mcp]` for MCP features
- [x] MCP docs moved to ucon-tools (sourced via git submodule)

**Outcomes:**
- Core ucon package has no MCP dependencies (simpler install, broader compatibility)
- MCP tooling available via `pip install ucon-tools[mcp]`
- Namespace package allows both packages to coexist under `ucon.*`
- ucon-tools can iterate independently on AI agent features

---

## v0.10.0 — Scientific Computing

**Theme:** NumPy and DataFrame integration.

- [ ] `Number` wraps `np.ndarray` values
- [ ] Vectorized conversion and arithmetic
- [ ] Vectorized uncertainty propagation
- [ ] Polars integration: `NumberColumn` type
- [ ] Pandas integration: `NumberSeries` type
- [ ] Column-wise conversion
- [ ] Unit-aware arithmetic on columns
- [ ] Performance benchmarks

**Outcomes:**
- Seamless integration with NumPy-based scientific workflows
- Efficient batch conversions for large datasets
- First-class support for data science workflows
- Unit-safe transformations on tabular data
- Performance characteristics documented and optimized

---

## v1.0.0 — API Stability

**Theme:** Production ready.

- [ ] API freeze with semantic versioning commitment
- [ ] Comprehensive documentation
- [ ] Performance benchmarks documented
- [ ] Security review complete
- [ ] 2+ year LTS commitment

**Outcomes:**
- Stable, well-tested release
- Fully type-safe and validated core
- Production-ready for integration into scientific and engineering workflows

---

## Post-1.0 Vision

| Feature | Notes |
|---------|-------|
| Decompose Tool | SLM enablement: deterministic `decompose` → `compute` pipeline |
| Uncertainty correlation | Full covariance tracking |
| Cython optimization | Performance parity with unyt |
| Additional integrations | SQLAlchemy, msgpack, protobuf |
| Localization | Unit names in multiple languages |
| NIST/CODATA updates | Automated constant updates |
| Symbolic bridge to SymPy | Export units for symbolic manipulation |
| Visualization | Dimensional relationship graphs |

---

## Guiding Principle

> "If it can be measured, it can be represented.
> If it can be represented, it can be validated.
> If it can be validated, it can be trusted."

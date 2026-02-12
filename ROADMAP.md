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
| v0.7.3 | Graph-Local Name Resolution | Planned |
| v0.7.4 | UnitPackage + TOML Loading | Planned |
| v0.7.5 | MCP Extension Tools | Planned |
| v0.7.x | Schema-Level Dimension Constraints | Planned |
| v0.8.0 | String Parsing | Planned |
| v0.9.0 | Constants + Logarithmic Units | Planned |
| v0.10.0 | Scientific Computing | Planned |
| v1.0.0 | API Stability | Planned |

---

## Current Version: **v0.6.0** (complete)

Building on v0.5.x baseline:
- `ucon.core` (`Dimension`, `Scale`, `Unit`, `UnitFactor`, `UnitProduct`, `Number`, `Ratio`, `UnitSystem`, `BasisTransform`, `RebasedUnit`)
- `ucon.maps` (`Map`, `LinearMap`, `AffineMap`, `ComposedMap` with `derivative()`)
- `ucon.graph` (`ConversionGraph`, default graph, `get_default_graph()`, `using_graph()`, cross-basis conversion)
- `ucon.units` (SI + imperial + information + angle + ratio units, callable syntax, `si` and `imperial` systems, `get_unit_by_name()`)
- `ucon.pydantic` (`Number` type for Pydantic v2 models)
- `ucon.algebra` (`Vector` with `Fraction` exponents, `Exponent`)
- Callable unit API: `meter(5)`, `(mile / hour)(60)`
- `Number.simplify()` for base-scale normalization
- `Dimension.information` with `units.bit`, `units.byte`
- Pseudo-dimensions: `angle`, `solid_angle`, `ratio` with semantic isolation
- Uncertainty propagation: `meter(1.234, uncertainty=0.005)` with quadrature arithmetic
- `BasisTransform` for cross-system dimensional mapping with exact matrix arithmetic
- `UnitSystem` for named dimension-to-unit groupings
- Pydantic v2 integration with JSON serialization
- Unit string parsing: `get_unit_by_name("kg*m/s^2")`

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

## v0.7.3 — Graph-Local Name Resolution (Planned)

**Theme:** Shared infrastructure for dynamic unit extension.

- [ ] `ConversionGraph._name_registry` (case-insensitive) and `_name_registry_cs` (case-sensitive)
- [ ] `graph.register_unit(unit)` — Register unit for name resolution within graph
- [ ] `graph.resolve_unit(name)` — Lookup in graph-local registry, return None if not found
- [ ] `graph.copy()` — Deep copy edges, shallow copy registries
- [ ] `_parsing_graph` ContextVar for threading resolution through parsing
- [ ] `using_graph()` sets both conversion and parsing context
- [ ] `_lookup_factor()` checks graph-local first, falls back to global
- [ ] `_build_standard_graph()` calls `register_unit()` for all standard units

**Outcomes:**
- Unit name resolution becomes graph-scoped, not global
- `using_graph(custom_graph)` automatically scopes both conversions AND name lookups
- Foundation for UnitPackage (v0.7.4) and MCP extension tools (v0.7.5)
- No global state mutation required for custom unit definitions

---

## v0.7.4 — UnitPackage + TOML Loading (Planned)

**Theme:** Config-file-based unit extension for application developers.

- [ ] `UnitDef` dataclass: `{name, dimension, aliases, shorthand}`
- [ ] `EdgeDef` dataclass: `{src, dst, factor}`
- [ ] `UnitPackage` frozen dataclass: `{name, version, units, edges, requires}`
- [ ] `load_package(path)` — Parse TOML file into `UnitPackage`
- [ ] `graph.with_package(pkg)` — Return new graph with package contents added
- [ ] `set_default_graph(graph)` — Replace module-level default
- [ ] Example package: `examples/aerospace.ucon.toml`

**Outcomes:**
- Implementers define domain units in TOML config files
- Units loaded at application startup without modifying library code
- Immutable composition: `graph.with_package(a).with_package(b)`
- No global state mutation — graphs are composed, not mutated
- Foundation for ucon.dev marketplace of domain packages

---

## v0.7.5 — MCP Extension Tools (Planned)

**Theme:** Runtime unit extension for AI agents.

### Session Tools (Token Efficient)

- [ ] `_session_graph` ContextVar for session-scoped custom graphs
- [ ] `define_unit(name, dimension, aliases)` — Register unit in session graph
- [ ] `define_conversion(src, dst, factor)` — Add edge to session graph
- [ ] `reset_session()` — Clear session graph, return to default

### Inline Parameters (Recoverable)

- [ ] `convert(..., custom_units=[...], custom_edges=[...])` — Self-contained conversion
- [ ] `compute(..., custom_units=[...], custom_edges=[...])` — Self-contained multi-step
- [ ] Graph caching by definition hash for performance

**Outcomes:**
- Agents can bring their own units without prior registration
- Session tools minimize token cost for repeated definitions
- Inline parameters enable recovery when session state is lost
- Hybrid approach: session for efficiency, inline for fault tolerance
- Exotic domain evals (aerospace, radiation, chemeng) work without core bloat

---

## v0.7.x — Schema-Level Dimension Constraints (Planned)

**Theme:** Pre-call validation for AI agents.

- [ ] Expose `DimConstraint` in MCP tool schemas
- [ ] Schema generator introspects dimension constraints from `@enforce_dimensions` functions
- [ ] Formula registration/discovery mechanism for domain packages

**Outcomes:**
- MCP schemas declare expected dimensions per parameter
- LLMs can validate inputs before calling, reducing round-trips
- Completes the type-directed correction loop
- Foundation for ucon.dev marketplace of domain formula packages

---

## v0.8.0 — String Parsing

**Theme:** Ergonomic input.

- [ ] `parse("60 mph")` → `Number` (quantity + unit parsing)
- [x] `parse("kg * m / s^2")` → `UnitProduct` (completed in v0.6.0 via `get_unit_by_name()`)
- [x] Alias resolution (`meters`, `metre`, `m` all work) (completed in v0.6.0)
- [ ] Uncertainty parsing: `parse("1.234 ± 0.005 m")`
- [ ] Revisit priority alias architecture (v0.6.x uses `_PRIORITY_ALIASES` / `_PRIORITY_SCALED_ALIASES` for `min`, `mcg`; consider "exact match first" or longest-match strategy if list grows)

**Outcomes:**
- Human-friendly unit input for interactive and configuration use cases
- Robust alias handling for international and domain-specific conventions
- Complete round-trip: parse → compute → serialize

---

## v0.9.0 — Constants + Logarithmic Units

**Theme:** Physical completeness.

- [ ] Physical constants with uncertainties: `c`, `h`, `G`, `k_B`, `N_A`, etc.
- [x] `LogMap`/`ExpMap` for logarithmic conversions (completed in v0.6.x)
- [ ] Logarithmic units with reference levels: `decibel`, `bel`, `neper`
- [ ] pH scale support
- [ ] Currency dimension (with caveats about exchange rates)

**Outcomes:**
- Physical constants with CODATA uncertainties
- Enables acoustics (dB), chemistry (pH), and signal processing domains
- Reference-level infrastructure for dBm, dBV, dBSPL variants

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

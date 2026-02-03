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
| v0.7.0 | NumPy Array Support | Planned |
| v0.8.0 | String Parsing | Planned |
| v0.9.0 | Constants + Logarithmic Units | Planned |
| v0.10.0 | DataFrame Integration | Planned |
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

## v0.7.0 — NumPy Array Support

**Theme:** Scientific computing integration.

- [ ] `Number` wraps `np.ndarray` values
- [ ] Vectorized conversion
- [ ] Vectorized arithmetic with uncertainty propagation
- [ ] Performance benchmarks

**Outcomes:**
- Seamless integration with NumPy-based scientific workflows
- Efficient batch conversions for large datasets
- Performance characteristics documented and optimized

---

## v0.8.0 — String Parsing

**Theme:** Ergonomic input.

- [ ] `parse("60 mph")` → `Number` (quantity + unit parsing)
- [x] `parse("kg * m / s^2")` → `UnitProduct` (completed in v0.6.0 via `get_unit_by_name()`)
- [x] Alias resolution (`meters`, `metre`, `m` all work) (completed in v0.6.0)
- [ ] Uncertainty parsing: `parse("1.234 ± 0.005 m")`

**Outcomes:**
- Human-friendly unit input for interactive and configuration use cases
- Robust alias handling for international and domain-specific conventions
- Complete round-trip: parse → compute → serialize

---

## v0.9.0 — Constants + Logarithmic Units

**Theme:** Physical completeness.

- [ ] Physical constants with uncertainties: `c`, `h`, `G`, `k_B`, `N_A`, etc.
- [ ] `LogMap` for logarithmic conversions
- [ ] Logarithmic units: `decibel`, `bel`, `neper`
- [ ] pH scale support
- [ ] Currency dimension (with caveats about exchange rates)

**Outcomes:**
- Support for function-based (nonlinear) physical conversions
- Enables acoustics (dB), chemistry (pH), and signal processing domains
- Physical constants with CODATA uncertainties

---

## v0.10.0 — DataFrame Integration

**Theme:** Data science workflows.

- [ ] Polars integration: `NumberColumn` type
- [ ] Pandas integration: `NumberSeries` type
- [ ] Column-wise conversion
- [ ] Unit-aware arithmetic on columns

**Outcomes:**
- First-class support for data science workflows
- Unit-safe transformations on tabular data
- Interoperability with modern DataFrame ecosystems

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
| Type-safe generics | `Number[Dimension.length]` for IDE hints |
| Symbolic bridge to SymPy | Export units for symbolic manipulation |
| Visualization | Dimensional relationship graphs |

---

## Guiding Principle

> "If it can be measured, it can be represented.
> If it can be represented, it can be validated.
> If it can be validated, it can be trusted."

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.3] - 2026-02-26

### Added

- Natural units support with `ConstantAwareBasisTransform` (#206)
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
[Unreleased]: https://github.com/withtwoemms/ucon/compare/0.9.3...HEAD
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

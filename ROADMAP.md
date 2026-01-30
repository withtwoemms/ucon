# 🧭 ucon Roadmap

> *A clear path from algebraic foundation to a stable 1.0 release.*

---

## 🪜 Current Version: **v0.4.0** (in progress)

Building on v0.3.5 baseline:
- `ucon.core` (`Dimension`, `Scale`, `Unit`, `UnitFactor`, `UnitProduct`, `Number`, `Ratio`)
- `ucon.maps` (`Map`, `LinearMap`, `AffineMap`, `ComposedMap`)
- `ucon.graph` (`ConversionGraph`, default graph, `get_default_graph()`, `using_graph()`)
- `ucon.units` (SI + imperial + information units, callable syntax)
- Callable unit API: `meter(5)`, `(mile / hour)(60)`
- `Number.simplify()` for base-scale normalization
- `Dimension.information` with `units.bit`, `units.byte`

---

## ✅ v0.3.x — Dimensional Algebra (Complete)

### 🔹 Summary
> Introduces dimensional algebra and establishes the Unit/Scale separation
> that underpins all downstream work.

### ✅ Goals
- [x] Implement `Vector` and `Dimension` classes
- [x] Integrate dimensions into `Unit`
- [x] Refactor `ucon.units` to use dimensional definitions
- [x] Publish documentation for dimensional operations
- [x] Verify uniqueness and hashing correctness across all Dimensions
- [x] Redesign `Exponent` to support algebraic operations (`__mul__`, `__truediv__`, `to_base`, etc.)
- [x] Remove redundant evaluated caching in favor of property-based computation
- [x] Integrate `Scale` with Exponent for consistent prefix arithmetic
- [x] Add regression tests for prefix math (`kilo / milli → mega`, `2¹⁰ / 10³ → 1.024×`)
- [x] Separate `scale` from `Unit`; delegate to `UnitFactor(unit, scale)`
- [x] Introduce `UnitProduct` with `fold_scale()` and `_residual_scale_factor`
- [x] `Number.value` returns as-expressed magnitude; `_canonical_magnitude` folds scale internally
- [x] Remove dead code and unify naming (`UnitFactor`, `UnitProduct`) across all docstrings and repr

### 🧩 Outcomes
- All units acquire explicit dimensional semantics
- Enables composable and type-safe dimensional operations
- Establishes the mathematical foundation for future conversions
- Unified algebraic foundation for all scaling and magnitude operations
- Clean Unit/Scale separation: `Unit` is an atomic symbol, `UnitFactor` pairs it with a `Scale`
- `UnitProduct` correctly tracks residual scale from cancelled units
- Type system is ready for a `ConversionGraph` to be built on top

---

## ⚙️ v0.4.x — Conversion System Foundations (In Progress)

### 🔹 Summary
> Implements unified conversion engine for standard, linear, and affine conversions.
> Introduces callable unit API for ergonomic quantity construction.

### ✅ Goals
- [x] Introduce `ConversionGraph` registry keyed by `Dimension`
- [x] Add support for `standard`, `linear`, and `affine` conversion types
- [x] Implement `Number.to(target_unit)` conversion API
- [x] Scale-only conversions short-circuit without graph lookup
- [x] Composite-to-composite conversion via per-component decomposition
- [x] Round-trip validation for reversible conversions (inverse maps)
- [x] Callable unit syntax: `meter(5)`, `(mile / hour)(60)`
- [x] Default graph with common SI and imperial conversions
- [x] Imperial units: `foot`, `mile`, `yard`, `inch`, `pound`, `ounce`, `fahrenheit`, `gallon`
- [x] `Number.simplify()` — Express in base scale
- [x] `Dimension.information` with `units.bit` and `units.byte`
- [x] `Vector` extended to 8 components (added B for information)
- [x] Information unit conversions in default graph (byte ↔ bit)
- [x] Extend tests to include temperature, pressure, and base SI conversions
- [x] Document Exponent/Scale relationship in developer guide

### 🧩 Outcomes
- Unified conversion taxonomy
- Reversible, dimension-checked conversions
- Scale-aware graph that leverages the `Unit`/`UnitFactor` separation from v0.3.x
- Ergonomic API: units are callable, returning `Number` instances
- Information dimension support (bit, byte) with binary prefix compatibility
- `Number.simplify()` for expressing quantities in base scale
- Forms the basis for nonlinear and domain-specific conversion families

---

## 🧱 v0.5.x — Unit Systems & Registries

### 🔹 Summary
> Introduces an extensible registry system for custom units and aliases.

### ✅ Goals
- [x] Implement `have(name)` membership check
- [ ] Add `UnitSystem` abstraction
- [ ] Support `registry.add(unit)` and dynamic system registration
- [ ] Validate alias uniqueness and collision prevention
- [ ] Include examples for user-defined unit extensions

### 🧩 Outcomes
- Registry-based extensibility for domain-specific systems
- Dynamic unit registration and discovery
- Groundwork for plugin-style system extensions

---

## 🧪 v0.6.x — Nonlinear & Specialized Conversions

### 🔹 Summary
> Adds support for logarithmic, fractional, and other specialized dimensionless conversions.

### ✅ Goals
- [ ] Extend conversion registry schema with `"nonlinear"` family
- [ ] Add `to_base` / `from_base` lambdas for function-based mappings
- [ ] Define sample nonlinear conversions (`decibel`, `bel`, `pH`)
- [ ] Add tolerance-aware tests for nonlinear conversions
- [ ] Introduce structured dimensionless unit family (`radian`, `percent`, `ppm`, `count`, etc.)
- [ ] Define canonical dimensionless subtypes for angular, fractional, and count semantics
- [ ] Ensure automatic collapse of equivalent units (`m/m → none`, `J/J → none`) via Ratio

### 🧩 Outcomes
- Support for function-based (nonlinear) physical conversions
- Unified algebraic framework across all conversion types
- Rich, semantically meaningful representation of dimensionless quantities
- Enables acoustics (dB), geometry (rad, sr), statistics (probability), and fractional scales (%, ppm)

---

## 🧰 v0.7.x — Testing, Developer Experience, & API Polish

### 🔹 Summary
> Strengthens tests, developer ergonomics, and runtime feedback.

### ✅ Goals
- [ ] Reach 95%+ test coverage
- [ ] Add property-based tests for dimensional invariants
- [ ] Improve error reporting, `__repr__`, and exception messaging
- [ ] Validate public API imports and maintain consistent naming
- [ ] Add CI coverage reports and build badges

### 🧩 Outcomes
- Reliable, developer-friendly foundation
- Consistent runtime behavior and output clarity
- Prepares API for public documentation and 1.0 freeze

---

## 🧩 v0.8.x — Pydantic Integration

### 🔹 Summary
> Introduces seamless integration with **Pydantic v2**, enabling validation, serialization, and typed dimensional models.

### ✅ Goals
- [ ] Define Pydantic-compatible field types (`UnitType`, `NumberType`)
- [ ] Implement `__get_pydantic_core_schema__` for Units and Numbers
- [ ] Support automatic conversion/validation for user-defined models
- [ ] Add YAML / JSON encoding for quantities (`Number(unit="meter", quantity=5)`)
- [ ] Add Pydantic-based examples (API config, simulation parameters)

### 🧩 Outcomes
- Native validation and serialization for dimensioned quantities
- Enables safe configuration in data models and APIs
- Bridges `ucon`'s algebraic model with modern Python typing ecosystems

---

## 📘 v0.9.x — Documentation & RC Phase

### 🔹 Summary
> Completes documentation, finalizes examples, and preps release candidates.

### ✅ Goals
- [ ] Write comprehensive README and developer guide
- [ ] Publish API reference docs (Sphinx / MkDocs)
- [ ] Add SymPy / Pint comparison appendix
- [ ] Freeze and document all public APIs
- [ ] Publish one or more release candidates (RC1, RC2)

### 🧩 Outcomes
- Complete public-facing documentation
- API frozen and versioned for stability
- Ready for final testing and validation before 1.0

---

## 🏁 v1.0.0 — Stable, Introspective Core

### 🔹 Summary
> First major release: a unified algebra for composable, type-safe, and semantically clear unit conversion.

### ✅ Goals
- [ ] Tag and release to PyPI
- [ ] Validate packaging and dependency metadata
- [ ] Include examples and tutorials in docs
- [ ] Announce 1.0 on GitHub and PyPI

### 🧩 Outcomes
- Stable, well-tested release
- Fully type-safe and validated core
- Production-ready for integration into scientific and engineering workflows

---

## 🧠 Post-1.0 Vision

| Future Direction | Description |
|------------------|-------------|
| **Graph-based conversion paths** | Automatically discover multi-hop conversions between compatible units |
| **Type-safe generics** | `Number[Dimension.length]` support for type checking and IDE hints |
| **Symbolic bridge to SymPy** | Export units and expressions for symbolic manipulation |
| **Visualization** | Dimensional relationship graphs and dependency trees |
| **Plugin architecture** | Load conversions and systems dynamically (YAML/JSON plugins) |

---

## 🗓️ Milestone Summary

| Version | Theme | Key Focus | Status |
|----------|--------|------------|---------|
| **0.3.5** | Dimensional Algebra | Unit/Scale separation, `UnitFactor`, `UnitProduct` | ✅ Complete |
| **0.4.0** | Conversion Engine | `ConversionGraph`, `Number.to()`, callable units | 🚧 In Progress |
| **0.5.0** | Unit Systems & Registries | Extensible registry system | ⏳ Planned |
| **0.6.0** | Nonlinear Conversions | Logarithmic / exponential families | ⏳ Planned |
| **0.7.0** | Testing & API Polish | Coverage, ergonomics, stability | ⏳ Planned |
| **0.8.0** | Pydantic Integration | Typed validation, serialization | ⏳ Planned |
| **0.9.x** | Documentation & RC | Freeze API, publish docs, RCs | ⏳ Planned |
| **1.0.0** | Stable Release | Publish production-ready core | 🔮 Future |

---

### ✨ Guiding Principle

> "If it can be measured, it can be represented.
> If it can be represented, it can be validated.
> If it can be validated, it can be trusted."

---

### 💡 Why Pydantic Integration Matters

- Enables **runtime validation** of dimensional correctness:
  ```python
  class Config(BaseModel):
      length: NumberType[Dimension.length]
      time: NumberType[Dimension.time]
  ```

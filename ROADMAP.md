# 🧭 ucon Roadmap

> *A clear path from algebraic foundation to a stable 1.0 release.*

---

## 🪜 Current Version: **v0.3.0**

Stable baseline for:
- `ucon.core` (`Number`, `Scale`, `Ratio`)
- `ucon.unit` (basic unit representation and composition)
- `ucon.units` (canonical SI definitions)
- Initial CI, testing, and packaging

---

## 🚀 v0.3.x — Dimensional Algebra (In Progress)

### 🔹 Summary
> Introduces `ucon.dimension` as the foundation for algebraic reasoning.

### ✅ Goals
- [x] Implement `Vector` and `Dimension` classes  
- [x] Integrate dimensions into `Unit`  
- [x] Refactor `ucon.units` to use dimensional definitions  
- [ ] Publish documentation for dimensional operations  
- [x] Verify uniqueness and hashing correctness across all Dimensions  
- [ ] Redesign `Exponent` to support algebraic operations (`__mul__`, `__truediv__`, `to_base`, etc.)  
- [ ] Remove redundant evaluated caching in favor of property-based computation  
- [ ] Integrate `Scale` with Exponent for consistent prefix arithmetic  
- [ ] Update `Number` and `Ratio` to use Exponent-driven scaling  
- [ ] Add regression tests for prefix math (`kilo / milli → mega`, `2¹⁰ / 10³ → 1.024×`)  
- [ ] Document Exponent/Scale relationship in developer guide 

### 🧩 Outcomes
- All units acquire explicit dimensional semantics  
- Enables composable and type-safe dimensional operations  
- Establishes the mathematical foundation for future conversions  
- Unified algebraic foundation for all scaling and magnitude operations  
- Precise, reversible cross-base math (`2ⁿ ↔ 10ᵐ`)  
- Simplified, consistent `Scale` and `Number` behavior  
- Ready for integration into the conversion engine (`ucon.conversions`)

---

## ⚙️ v0.4.x — Conversion System Foundations

### 🔹 Summary
> Implements unified conversion engine for standard, linear, and affine conversions.

### ✅ Goals
- [ ] Introduce `ucon.conversions` registry keyed by `Dimension`  
- [ ] Add support for `standard`, `linear`, and `affine` conversion types  
- [ ] Implement `.to(target_unit)` for `Number`  
- [ ] Round-trip validation for reversible conversions  
- [ ] Extend tests to include temperature, pressure, and base SI conversions  

### 🧩 Outcomes
- Unified conversion taxonomy  
- Reversible, dimension-checked conversions  
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
- Bridges `ucon`’s algebraic model with modern Python typing ecosystems  

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

| Version | Theme | Key Focus | Target | Status |
|----------|--------|------------|---------|---------|
| **0.3.0** | Dimensional Algebra | Introduce `ucon.dimension` | **Nov 2025** | 🚧 In Progress |
| **0.4.0** | Conversion Engine | Standard, linear, affine conversions | **Jan 2026** | ⏳ Planned |
| **0.5.0** | Unit Systems & Registries | Extensible registry system | **Mar 2026** | ⏳ Planned |
| **0.6.0** | Nonlinear Conversions | Logarithmic / exponential families | **May 2026** | ⏳ Planned |
| **0.7.0** | Testing & API Polish | Coverage, ergonomics, stability | **Jul 2026** | ⏳ Planned |
| **0.8.0** | 🧩 **Pydantic Integration** | Typed validation, serialization | **Sep 2026** | 🧭 Newly Added |
| **0.9.x** | Documentation & RC | Freeze API, publish docs, RCs | **Nov 2026** | ⏳ Planned |
| **1.0.0** | Stable Release | Publish production-ready core | **Jan 2027** | 🔮 Future |

---

### ✨ Guiding Principle

> “If it can be measured, it can be represented.  
> If it can be represented, it can be validated.  
> If it can be validated, it can be trusted.”

---

### 💡 Why Pydantic Integration Matters

- Enables **runtime validation** of dimensional correctness:
  ```python
  class Config(BaseModel):
      length: NumberType[Dimension.length]
      time: NumberType[Dimension.time]

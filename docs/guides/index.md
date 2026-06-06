# Guides

Task-oriented guides for common use cases.

## Integration Guides

- **[Pydantic Integration](pydantic-integration.md)** - Type-safe dimensional fields in Pydantic models
- **[Config Safety](dimensional-safety-config.md)** - Dimensional safety for configuration files

## Calculation Guides

- **[Dimensional Analysis](dimensional-analysis.md)** - Step-by-step factor-label calculations
- **[Custom Units & Graphs](custom-units-and-graphs.md)** - Define domain-specific units
- **[Isolated UnitSystems](building-isolated-unitsystems.md)** - Thread-safe isolated computation worlds
- **[Conversion Contexts](conversion-contexts.md)** - Cross-dimensional conversions (spectroscopy, Boltzmann)
- **[Natural Units](natural-units.md)** - Particle physics natural units (c = h_bar = k_B = 1)

## Scientific Computing

- **[NumPy Arrays](numpy-arrays.md)** - Vectorized operations with `NumberArray`
- **[Pandas Integration](pandas-integration.md)** - Unit-aware DataFrames with `NumberSeries`
- **[Polars Integration](polars-integration.md)** - Unit-aware Polars with `NumberColumn`

## MCP Server

- **[Overview](../external/ucon-tools/docs/guides/mcp-server/index.md)** - Setup and available tools
- **[Custom Units](../external/ucon-tools/docs/guides/mcp-server/custom-units.md)** - Define domain-specific units at runtime
- **[Registering Formulas](../external/ucon-tools/docs/guides/mcp-server/registering-formulas.md)** - Expose dimensionally-typed calculations to agents

## Domain Walkthroughs

- **[Nursing Dosage](domain-walkthroughs/nursing-dosage.md)** - Weight-based dosing calculations
- **[Chemical Engineering](domain-walkthroughs/chemical-engineering.md)** - Process engineering calculations
- **[Aerospace](domain-walkthroughs/aerospace.md)** - Aerospace unit conversions
- **[Finance](domain-walkthroughs/finance.md)** - Financial calculations with units
- **[Electrical Engineering](domain-walkthroughs/electrical-engineering.md)** - Electrical engineering units
- **[Particle Physics](domain-walkthroughs/particle-physics.md)** - Natural units and cross-basis transforms

## Domain-Specific Bases

- **[Radiation Dosimetry](domain-bases/radiation-dosimetry.md)** - Gy vs Sv disambiguation
- **[Pharmacology](domain-bases/pharmacology.md)** - Drug dosing dimensions
- **[Clinical Chemistry](domain-bases/clinical-chemistry.md)** - Lab result units
- **[Classical Mechanics](domain-bases/classical-mechanics.md)** - Torque vs energy disambiguation
- **[Thermodynamics](domain-bases/thermodynamics.md)** - Heat, work, and entropy

## Migration

- **[Migrating to v2.0](migrating-to-v2.md)** - Migration guide from v1.x to v2.0

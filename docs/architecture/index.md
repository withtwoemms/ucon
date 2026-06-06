# Architecture

Understand the design decisions behind ucon.

- **[Design Principles](design-principles.md)** - Core philosophy and tradeoffs
- **[Kind-of-Quantity Problem](kind-of-quantity.md)** - Dimensional ambiguity and ucon's three solutions
- **[ConversionGraph](conversion-graph.md)** - Graph topology and BFS path finding
- **[Dual-Graph Architecture](dual-graph-architecture.md)** - How BasisGraph and ConversionGraph work together
- **[UnitSystem Value Type](unitsystem-value-type.md)** - Frozen value type bundling all registries
- **[Suggestions & Recovery](suggestions-and-recovery.md)** - Fuzzy matching and error recovery
- **[Comparison with Pint](comparison-with-pint.md)** - When to use ucon vs Pint

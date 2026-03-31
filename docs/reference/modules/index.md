# Module Reference

Auto-generated API reference for all public ucon modules.

For a curated overview with examples, see the [API Reference](../api.md).

## Core

- **[ucon.core](core.md)** --- Unit, Number, Scale, UnitProduct, UnitFactor, Ratio
- **[ucon.dimension](dimension.md)** --- Dimension algebra and enumeration
- **[ucon.graph](graph.md)** --- ConversionGraph, context scoping, exceptions
- **[ucon.maps](maps.md)** --- Map hierarchy (LinearMap, AffineMap, LogMap, ExpMap)
- **[ucon.parsing](parsing.md)** --- String parsing to Number objects
- **[ucon.units](units.md)** --- Canonical unit definitions
- **[ucon.constants](constants.md)** --- Physical constants (CODATA 2022)
- **[ucon.checking](checking.md)** --- Dimension enforcement decorator
- **[ucon.packages](packages.md)** --- Unit package loading from TOML
- **[ucon.contexts](contexts.md)** --- Cross-dimensional conversion contexts (spectroscopy, boltzmann)

## Integrations

- **[ucon.integrations.numpy](integrations-numpy.md)** --- NumPy array support (NumberArray)
- **[ucon.integrations.pandas](integrations-pandas.md)** --- Pandas integration (NumberSeries)
- **[ucon.integrations.polars](integrations-polars.md)** --- Polars integration (NumberColumn)
- **[ucon.integrations.pydantic](integrations-pydantic.md)** --- Pydantic v2 integration

## Basis

- **[ucon.basis](basis.md)** --- Basis, BasisComponent, Vector
- **[ucon.basis.builtin](basis-builtin.md)** --- Standard bases (SI, CGS, CGS_ESU, NATURAL)
- **[ucon.basis.transforms](basis-transforms.md)** --- BasisTransform, standard transforms
- **[ucon.basis.graph](basis-graph.md)** --- BasisGraph, context scoping

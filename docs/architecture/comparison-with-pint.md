# Comparison with Pint

When to use ucon vs Pint, and the architectural differences between them.

---

## Overview

Both ucon and [Pint](https://pint.readthedocs.io/) solve unit conversion in Python. They make different tradeoffs:

| Aspect | Pint | ucon |
|--------|------|------|
| **Architecture** | Mutable `UnitRegistry` singleton | Injectable `ConversionGraph` (copy-on-extend) |
| **Type Safety** | Runtime checks only | `Number[Dimension.X]` generics + `@enforce_dimensions` |
| **Conversion Model** | Implicit registry lookup | Explicit `Map` hierarchy (`LinearMap`, `AffineMap`, `LogMap`) |
| **State Isolation** | Manual (separate registries, which are incompatible) | Built-in (`ContextVar` + `using_graph()`) |
| **Logarithmic Units** | Beta (`dB`, `dBm`) | `LogMap` / `ExpMap` with configurable base, scale, reference |
| **Uncertainty** | Via third-party `uncertainties` package | Built-in propagation through arithmetic and conversion |
| **NumPy** | First-class (ufunc wrapping) | `NumberArray` with unit-aware reductions |
| **Pandas** | Via `pint-pandas` extension | `NumberSeries` + `.ucon` accessor |
| **Polars** | None | `NumberColumn` |
| **Pydantic v2** | Via third-party `pydantic-pint` | Native (`Number[Dimension.X]` with JSON schema) |
| **AI Integration** | None | MCP server (ucon-tools) |
| **Domain Extensions** | Text definition files | TOML packages (`UnitPackage`, `load_package()`) |
| **Physical Constants** | None built-in | 17 CODATA 2022 constants with uncertainty |
| **Basis Systems** | None | SI, CGS, CGS-ESU, Natural + custom bases via `BasisGraph` |

!!! note "Community Interest in Parameterized Types"
    The Pint community has expressed interest in parameterized type support similar to ucon's `Number[Dimension.X]` generics. See discussions in [pint#778](https://github.com/hgrecco/pint/issues/778) and [pint#1166](https://github.com/hgrecco/pint/issues/1166). Workarounds for Pydantic integration exist but remain unmerged ([pydantic#4929](https://github.com/pydantic/pydantic/discussions/4929)). ucon's type-safe dimensional constraints address this gap natively.

---

## Architectural Difference: Registry vs Graph

### Pint: Global UnitRegistry

Pint uses a singleton registry pattern:

```python
from pint import UnitRegistry

ureg = UnitRegistry()  # Global state

distance = 5 * ureg.meter
speed = distance / (2 * ureg.second)
```

**Pros:**

- Simple, familiar pattern
- Convenient for scripts and notebooks

**Cons:**

- Tests can't run in parallel without isolation
- Libraries embedding Pint may conflict
- Custom units pollute global state

### ucon: Injectable ConversionGraph

ucon uses dependency injection via context managers:

```python
from ucon import units
from ucon.graph import using_graph, get_default_graph

# Default graph used implicitly
distance = units.meter(5)
speed = distance / units.second(2)

# Custom graph for isolation
custom = get_default_graph().copy()
custom.add_edge(src=my_unit, dst=units.meter, map=LinearMap(1.5))

with using_graph(custom):
    # Operations use custom graph
    value.to(my_unit)
```

**Pros:**

- Thread-safe, async-safe
- Libraries maintain isolated graphs
- Tests run in parallel

**Cons:**

- Slightly more verbose for simple scripts

---

## Thread Safety & State Isolation

The registry vs graph distinction has significant implications for concurrent, multi-tenant, and multi-domain scenarios.

### Key Findings

#### Cross-Registry Quantity Incompatibility

Pint quantities carry a reference to their parent registry. Quantities from different registries cannot interact:

```python
ureg1 = pint.UnitRegistry()
ureg2 = pint.UnitRegistry()

q1 = ureg1.Quantity(50, "meter")
q2 = ureg2.Quantity(50, "meter")

q1 + q2  # ValueError: Cannot operate with Quantity of different registries
```

**ucon:** Conversion graphs produce plain numeric results via `Map` objects. There is no registry-bound `Quantity` type, so cross-graph incompatibility doesn't exist.

#### Application Registry Singleton

Pint's `set_application_registry()` switches the process-global default. Any code using `pint.Quantity` is affected:

```python
ureg1 = pint.UnitRegistry()
ureg1.define("smoot = 1.7018 * meter")
pint.set_application_registry(ureg1)

pint.Quantity(1, "smoot")  # works

ureg2 = pint.UnitRegistry()
pint.set_application_registry(ureg2)

pint.Quantity(1, "smoot")  # UndefinedUnitError — smoot no longer exists
```

**ucon:** `set_default_graph()` only affects contexts that haven't explicitly called `using_graph()`. An explicit context is immune to default changes.

#### Silent Redefinition

Pint's `define()` silently overwrites previous definitions. The internal `_units` dictionary updates, but the conversion cache may retain stale values:

```python
ureg = pint.UnitRegistry()
ureg.define("widget = 100 * gram")
ureg.Quantity(1, "widget").to("gram")  # 100 gram (cached)

ureg.define("widget = 200 * gram")
ureg.Quantity(1, "widget").to("gram")  # 100 gram (stale cache!)
```

**ucon:** `with_package()` returns a new graph. The original is never mutated. There is no redefinition — only "a different graph with a different definition."

### Scenario Analysis

| Scenario | Pint Hazard | ucon Solution |
|----------|-------------|---------------|
| **MCP Server** | Concurrent agents race on shared registry, or separate registries block interoperability | `with_package()` per agent config, `using_graph()` per request |
| **pytest-xdist** | Parallel tests with `define()` produce intermittent failures | `using_graph()` isolates each test |
| **Long-running Pipeline** | Recalibration via `define()` corrupts in-flight data | Immutable graphs preserve calibration epochs |

### Architectural Summary

| Property | Pint | ucon |
|----------|------|------|
| State container | `UnitRegistry` (mutable) | `ConversionGraph` (copy-on-extend) |
| Global singleton | `application_registry` (process-wide) | None (ContextVar-scoped default) |
| Extension mechanism | `define()` (mutates in place) | `with_package()` (returns new graph) |
| Context scoping | None (manual registry passing) | `using_graph()` via ContextVar |
| Thread isolation | Requires separate registries | Built-in via ContextVar |
| Cross-context interop | Blocked (different-registry error) | Native (results are plain numbers) |
| Redefinition behavior | Silent overwrite + stale cache | Not possible (immutable extension) |

!!! info "Test Suites"
    These findings are backed by executable test suites in [`tests/ucon/comparison/`](https://github.com/withtwoemms/ucon/tree/main/tests/ucon/comparison):

    - [`test_pint_registry_isolation.py`](https://github.com/withtwoemms/ucon/blob/main/tests/ucon/comparison/test_pint_registry_isolation.py) — 14 tests demonstrating Pint's isolation failures
    - [`test_ucon_graph_isolation.py`](https://github.com/withtwoemms/ucon/blob/main/tests/ucon/comparison/test_ucon_graph_isolation.py) — 16 tests demonstrating ucon's correct isolation

    Run locally: `pytest tests/ucon/comparison/ -v` (requires `pint` installed)

---

## Dimensional Type Safety

### Pint: Runtime Checks

Pint validates dimensions at runtime but doesn't integrate with type checkers:

```python
# Pint
distance = 5 * ureg.meter
time = 2 * ureg.second

speed = distance / time  # Works
wrong = distance + time  # Raises DimensionalityError at runtime
```

Type checkers (mypy, pyright) can't catch the error before execution.

### ucon: `Number[Dimension.X]` Generics

ucon provides type-level dimensional constraints:

```python
from ucon import Number, Dimension, enforce_dimensions, units

@enforce_dimensions
def speed(
    distance: Number[Dimension.length],
    time: Number[Dimension.time],
) -> Number[Dimension.velocity]:
    return distance / time

# Runtime validation
speed(units.meter(100), units.second(10))   # <10.0 m/s>
speed(units.second(100), units.second(10))  # ValueError at call boundary

# Type introspection
from typing import get_origin, get_args, Annotated
hint = Number[Dimension.length]
assert get_origin(hint) is Annotated
```

This enables:

- IDE autocomplete for dimensioned parameters
- Framework-level validation (Pydantic, FastAPI)
- Documentation generation from type hints

---

## MCP Integration

### Pint: None

Pint has no built-in AI agent integration. Using Pint with LLMs requires custom tool definitions.

### ucon: Native MCP Server

ucon ships with an MCP server:

```bash
pip install ucon[mcp]
```

Configure in Claude Desktop:

```json
{
  "mcpServers": {
    "ucon": {
      "command": "uvx",
      "args": ["--from", "ucon[mcp]", "ucon-mcp"]
    }
  }
}
```

Available tools:

- `convert` — Unit conversion with dimensional validation
- `compute` — Multi-step factor-label calculations
- `define_unit` / `define_conversion` — Runtime extension
- `list_units`, `list_scales`, `list_dimensions` — Discovery

Structured error responses with `likely_fix` enable AI self-correction:

```python
convert(1, "kilgoram", "kg")
# → {"error": "Unknown unit: 'kilgoram'", "likely_fix": "kilogram (kg)"}
```

---

## Unit String Parsing

### Pint

```python
ureg = UnitRegistry()
q = ureg("5 km/h")  # Parses "5 km/h" → Quantity
```

### ucon

```python
from ucon import get_unit_by_name

unit = get_unit_by_name("km/h")  # → UnitProduct
number = unit(5)  # → Number
```

Both support composite unit parsing. ucon's `get_unit_by_name()` returns a typed `UnitProduct` that can be reused.

---

## Scientific Computing

### NumPy

Both libraries support NumPy arrays with unit tracking.

=== "Pint"

    ```python
    import numpy as np
    from pint import UnitRegistry

    ureg = UnitRegistry()
    arr = np.array([1, 2, 3]) * ureg.meter
    result = arr.to(ureg.foot)  # Vectorized conversion
    ```

    Pint wraps NumPy ufuncs — `arr` is a `Quantity` that delegates to `ndarray` internals. This is mature and covers most NumPy operations.

=== "ucon"

    ```python
    import numpy as np
    from ucon import units
    from ucon.integrations.numpy import NumberArray

    arr = NumberArray.from_numbers([units.meter(1), units.meter(2), units.meter(3)])
    result = arr.to(units.foot)  # Vectorized conversion

    arr.mean()   # → Number with unit preserved
    arr.std()    # → Number with unit preserved
    arr + arr    # → NumberArray with dimensional validation
    ```

    `NumberArray` uses composition (wraps an `ndarray`) rather than subclassing. This preserves uncertainty tracking through reductions and conversions.

**Architectural difference:** Pint's approach exposes the full NumPy API surface implicitly. ucon's approach exposes a curated API that guarantees dimensional correctness and uncertainty propagation at every operation, but doesn't cover every NumPy function. If your workflow needs `np.fft` or `scipy.linalg` on unit-aware arrays, Pint has broader coverage.

### Pandas

=== "Pint"

    ```python
    import pandas as pd
    import pint_pandas  # Third-party

    pa = pint_pandas.PintArray.from_1darray_quantity(arr)
    s = pd.Series(pa)
    ```

=== "ucon"

    ```python
    import pandas as pd
    from ucon.integrations.pandas import NumberSeries

    ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=units.meter)
    ns.to(units.foot)        # Vectorized conversion
    ns.mean()                # → Number
    ns.to_frame()            # DataFrame with unit in column name
    ```

### Polars

Pint has no Polars integration. ucon provides `NumberColumn`:

```python
import polars as pl
from ucon.integrations.polars import NumberColumn

nc = NumberColumn(pl.Series([1.0, 2.0, 3.0]), unit=units.meter)
nc.to(units.foot)
nc.mean()  # → Number
```

### Uncertainty Propagation

Pint delegates uncertainty to the third-party `uncertainties` package. ucon tracks uncertainty natively:

```python
from ucon import units

# Uncertainty through arithmetic
length = units.meter(5.0, uncertainty=0.1)
width = units.meter(3.0, uncertainty=0.05)
area = length * width  # uncertainty propagated via quadrature

# Uncertainty through conversion
from ucon.maps import LogMap
# LogMap.derivative() computes dB/dx for uncertainty in log space
```

Uncertainty propagates through `Number` arithmetic, `NumberArray` reductions, and `Map.derivative()` for nonlinear conversions.

---

## Conversion Model

Pint treats conversion as an opaque registry lookup. ucon makes the conversion morphism a first-class object.

### Pint: Implicit Conversion

```python
ureg = UnitRegistry()
q = ureg.Quantity(100, "celsius")
q.to("fahrenheit")  # Conversion logic is internal to the registry
```

The transformation applied (linear? affine? logarithmic?) is not inspectable or composable by user code.

### ucon: Explicit Map Hierarchy

```python
from ucon.maps import LinearMap, AffineMap, LogMap

# Each conversion is a typed, inspectable object
km_to_m = LinearMap(1000)
c_to_k = AffineMap(1, 273.15)
w_to_dbm = LogMap(scale=10, base=10, reference=0.001)

# Composition via @ operator
chain = c_to_k @ km_to_m  # Produces a ComposedMap

# Inspection
chain.inverse()       # Returns the reverse map
chain.derivative(x)   # For uncertainty propagation
chain.is_identity()   # Algebraic identity check
```

This matters for:

- **Auditability** — you can inspect exactly what transformation is applied between any two units
- **Nonlinear conversions** — `LogMap` handles dB, dBm, pH, neper with configurable base, scale, and reference level
- **Uncertainty** — `Map.derivative()` enables analytic uncertainty propagation through nonlinear conversions, not just linear scaling

### Physical Constants

Pint has no built-in physical constants. ucon ships 17 CODATA 2022 constants:

```python
from ucon import constants

c = constants.speed_of_light       # exact: 299792458 m/s
G = constants.gravitational_constant  # measured: 6.67430e-11 ± 1.5e-15 m³/(kg·s²)

# Constants participate in arithmetic with uncertainty propagation
energy = G.as_number() * units.kilogram(1.0) * units.kilogram(1.0) / units.meter(1.0)
```

---

## Performance

Pint's [own documentation](https://pint.readthedocs.io/en/develop/advanced/performance.html) reports 38x overhead for simple arithmetic vs raw magnitudes, and up to 250x for iterative operations. Pint's `@ureg.wraps` decorator reduces this to ~8x.

ucon's overhead profile is different:

- **Single conversion**: BFS path lookup + `Map.__call__`. Path caching amortizes the BFS cost after the first lookup.
- **Batch conversion** (`NumberArray`): Map applied once to the underlying `ndarray` — overhead is per-batch, not per-element.
- **`@enforce_dimensions`**: ~1 dict lookup per constrained parameter at call time (pre-computed at decoration time).

ucon does not use C extensions. For tight inner loops on millions of scalar conversions, Pint or raw arithmetic will be faster. For batch operations on arrays, the per-element overhead difference is negligible.

Published benchmarks are available via `make benchmark` (see [Performance Benchmarks](../reference/index.md)).

---

## Broader Landscape

Pint is not the only alternative. Two other libraries are worth understanding.

### unyt (yt-project)

[unyt](https://github.com/yt-project/unyt) subclasses `numpy.ndarray` directly — quantities *are* arrays. This gives near-zero overhead on large arrays and full NumPy API coverage. Uses SymPy for symbolic unit simplification.

**Where unyt wins:** Raw array performance. If your workload is "convert a million-element array and run `np.fft` on it," unyt has the least friction.

**Where ucon differs:** unyt has no Pydantic integration, no Pandas/Polars extensions, no logarithmic units beyond basic dB/Np, no uncertainty propagation, no type-safe dimensional constraints, and no state isolation mechanism. It requires NumPy + SymPy as mandatory dependencies; ucon's core has zero mandatory dependencies.

### astropy.units

[astropy.units](https://docs.astropy.org/en/stable/units/index.html) has the most mature logarithmic unit system (`Magnitude`, `Dex`, `Decibel` classes) and a powerful `Equivalencies` mechanism for physics-specific conversions (wavelength ↔ frequency, temperature ↔ energy). It has institutional backing from STScI and ESA.

**Where astropy wins:** Logarithmic unit breadth, domain-specific equivalencies, and the sheer volume of astronomy-relevant units.

**Where ucon differs:** astropy.units is part of the full astropy package — a heavy dependency for non-astronomers. It has no Pydantic integration, no Polars support, no TOML-based extension packages, no state isolation, and its `Quantity[unit]` type annotations are metadata-only (no runtime enforcement). Equivalencies are powerful but domain-specific; ucon's `BasisGraph` is a general-purpose basis transform system.

### Comparison Matrix

| Capability | Pint | unyt | astropy.units | ucon |
|---|---|---|---|---|
| **Mandatory deps** | None | NumPy + SymPy | Large (compiled C) | None |
| **State model** | Mutable singleton | Global registry | Global registry | ContextVar-scoped, copy-on-extend |
| **Type safety** | Runtime only | Runtime only | Annotations (no enforcement) | `@enforce_dimensions` at call boundary |
| **Pydantic v2** | Third-party | None | None | Native |
| **Pandas** | Third-party (`pint-pandas`) | None | None | `NumberSeries` |
| **Polars** | None | None | None | `NumberColumn` |
| **Logarithmic units** | Beta | Basic (dB, Np) | Best (mag, dex, dB) | `LogMap` / `ExpMap` |
| **Uncertainty** | Third-party (`uncertainties`) | None | None | Built-in |
| **Physical constants** | None | None | Yes (astronomy-focused) | 17 CODATA 2022 |
| **Custom unit packages** | Text definition files | Programmatic | Programmatic | TOML packages |
| **Basis systems** | None | None | Equivalencies (domain-specific) | General-purpose `BasisGraph` |
| **AI integration (MCP)** | None | None | None | ucon-tools |

---

## When to Use Pint

Choose Pint when:

- Your project is a **script or notebook** where a global registry is fine
- You want the **widest ecosystem** of third-party integrations (xarray, Dask, Matplotlib)
- You need a **battle-tested** library with 10+ years of production use
- **Scalar conversion throughput** in tight loops is critical and you've profiled

---

## When to Use ucon

Choose ucon when:

- You're building a **library or service** that embeds unit handling (injectable, isolated graphs)
- You need **type-safe dimensional constraints** at API boundaries (`Number[Dimension.X]`)
- You need **Pydantic v2** or **Polars** integration
- You want **uncertainty propagation** through conversions and arithmetic
- You're working with **logarithmic units** (dB, dBm, pH) or **nonlinear conversions**
- You need **domain-specific unit packages** loaded from TOML
- You need **AI agent integration** via MCP
- You want **auditable conversions** — inspectable, composable `Map` objects

---

## Migration Path

If you're using Pint and considering ucon:

### Basic Quantities

```python
# Pint
distance = 5 * ureg.meter

# ucon
distance = units.meter(5)
```

### Conversion

```python
# Pint
distance.to(ureg.foot)

# ucon
distance.to(units.foot)
```

### Arithmetic

```python
# Both work similarly
speed = distance / time
```

### Custom Units

=== "Pint"

    ```python
    ureg.define("smoot = 1.7018 * meter")
    ```

    Mutates the registry in place. Affects all code using this registry.

=== "ucon (programmatic)"

    ```python
    from ucon import Unit, Dimension, units
    from ucon.maps import LinearMap
    from ucon.graph import get_default_graph

    smoot = Unit(name="smoot", dimension=Dimension.length, aliases=("smoot",))
    graph = get_default_graph().copy()
    graph.register_unit(smoot)
    graph.add_edge(src=smoot, dst=units.meter, map=LinearMap(1.7018))
    ```

    Returns a new graph. Original is unmodified.

=== "ucon (TOML package)"

    ```toml
    # custom.ucon.toml
    [units.smoot]
    dimension = "length"
    aliases = ["smoot"]

    [edges.smoot_to_meter]
    src = "smoot"
    dst = "meter"
    factor = 1.7018
    ```

    ```python
    from ucon.packages import load_package
    from ucon.graph import get_default_graph

    pkg = load_package("custom.ucon.toml")
    graph = get_default_graph().with_package(pkg)
    ```

---

## Summary

| Need | Recommendation |
|------|----------------|
| Type-safe APIs / Pydantic | ucon |
| Library / service embedding | ucon |
| AI agents / MCP | ucon |
| Uncertainty propagation | ucon |
| Logarithmic conversions (dB, pH) | ucon |
| Domain unit packages (TOML) | ucon |
| Polars integration | ucon |
| NumPy arrays with full ufunc coverage | Pint or unyt |
| Astronomy-specific units | astropy.units |
| Widest third-party ecosystem | Pint |
| Simple scripts | Either |
| Maximum scalar throughput | Raw arithmetic (or Pint with `@ureg.wraps`) |

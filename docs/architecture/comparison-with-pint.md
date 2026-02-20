# Comparison with Pint

When to use ucon vs Pint, and the architectural differences between them.

---

## Overview

Both ucon and [Pint](https://pint.readthedocs.io/) solve unit conversion in Python. They make different tradeoffs:

| Aspect | Pint | ucon |
|--------|------|------|
| **Maturity** | 10+ years, widely adopted | Newer, evolving API |
| **Registry** | Global `UnitRegistry` | Injectable `ConversionGraph` |
| **Type Safety** | Runtime checks | `Number[Dimension.X]` generics |
| **AI Integration** | None | MCP server built-in |
| **NumPy** | First-class support | Planned (v0.10.x) |

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

## NumPy Integration

### Pint

First-class NumPy support:

```python
import numpy as np
from pint import UnitRegistry

ureg = UnitRegistry()
arr = np.array([1, 2, 3]) * ureg.meter
result = arr.to(ureg.foot)  # Vectorized conversion
```

### ucon

Planned for v0.10.x:

```python
# Future API (not yet implemented)
from ucon import units
import numpy as np

arr = units.meter(np.array([1, 2, 3]))
result = arr.to(units.foot)  # Vectorized
```

**If you need NumPy today, use Pint.**

---

## Performance

Pint is generally faster for simple conversions due to:

- Mature optimization
- C extensions in some paths
- Path caching in the registry

ucon prioritizes correctness and dimensional safety. Performance optimization is planned post-1.0.

For most applications, the difference is negligible. Profile your specific workload if performance matters.

---

## When to Use Pint

Choose Pint when:

- You need **NumPy/SciPy integration today**
- Your project is a **script or notebook** (global registry is fine)
- You want **mature, battle-tested** library
- **Performance** is critical and you've profiled

---

## When to Use ucon

Choose ucon when:

- You're building a **library** that embeds unit handling (injectable graph)
- You need **AI agent integration** (MCP server)
- You want **type-safe dimensional constraints** (`Number[Dimension.X]`)
- You need **Pydantic v2 integration** for APIs
- You're working in a domain that needs **custom unit systems** (TOML packages)
- You want **structured error responses** for programmatic handling

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

```python
# Pint
ureg.define("smoot = 1.7018 * meter")

# ucon
graph = get_default_graph().copy()
smoot = Unit(name="smoot", dimension=Dimension.length, aliases=("smoot",))
graph.register_unit(smoot)
graph.add_edge(src=smoot, dst=units.meter, map=LinearMap(1.7018))
```

---

## Summary

| Need | Recommendation |
|------|----------------|
| NumPy arrays | Pint (until ucon v0.10.x) |
| AI agents / MCP | ucon |
| Type-safe APIs | ucon |
| Library embedding | ucon |
| Simple scripts | Either |
| Maximum performance | Pint (or raw numbers after validation) |
| Pydantic models | ucon |
| Domain unit packages | ucon |

Both libraries solve unit conversion well. Choose based on your integration needs.

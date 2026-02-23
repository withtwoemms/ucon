# Design Principles

Core philosophy and architectural tradeoffs behind ucon.

---

## Correctness Over Performance

ucon prioritizes correctness over raw speed. Every operation validates dimensional consistency before executing.

```python
# Dimension check happens before arithmetic
length + time  # raises immediately, not after computation
```

**Tradeoff:** This adds overhead to every operation. For hot paths with millions of conversions, consider batch operations (planned for v0.10.x) or extracting raw values after validation.

**Rationale:** Unit errors in scientific and engineering contexts can have severe consequences. A 10x slower library that catches errors is more valuable than a fast library that silently propagates mistakes.

---

## Injectable Over Global

ucon avoids global mutable state. The `ConversionGraph` is injectable via context managers rather than a singleton.

```python
from ucon.graph import using_graph, ConversionGraph

# Default graph used implicitly
distance.to(units.mile)

# Custom graph injected explicitly
custom = ConversionGraph()
custom.add_edge(src=my_unit, dst=units.meter, map=LinearMap(1.5))

with using_graph(custom):
    # All operations use custom graph
    value.to(my_unit)
```

**Implementation:** `ContextVar` provides thread-safe, async-safe scoping:

```python
_graph_context: ContextVar[ConversionGraph | None] = ContextVar("graph", default=None)
_parsing_graph: ContextVar[ConversionGraph | None] = ContextVar("parsing_graph", default=None)
```

**Tradeoff:** Slightly more verbose than a global registry. Users must pass graphs explicitly or use context managers.

**Rationale:**
- Libraries embedding ucon can maintain isolated graphs
- Tests run in parallel without interference
- No hidden action-at-a-distance from global state mutation

---

## Explicit Dimensional Algebra

Dimensions are algebraic objects, not string labels. Operations produce new dimensions following physical laws.

```python
Dimension.length / Dimension.time      # → Dimension.velocity
Dimension.mass * Dimension.acceleration  # → Dimension.force
Dimension.energy ** 0.5                # → derived dimension
```

**Implementation:** Each dimension has a `Vector` of 8 exponents (T, L, M, I, Θ, J, N, B). Arithmetic operates on vectors:

```python
class Dimension(Enum):
    length = Vector(0, 1, 0, 0, 0, 0, 0, 0)
    time = Vector(1, 0, 0, 0, 0, 0, 0, 0)
    velocity = Vector(-1, 1, 0, 0, 0, 0, 0, 0)  # T⁻¹L¹
```

**Rationale:** This enables ucon to verify that `length / time` produces something compatible with `velocity`, catching errors that string-based systems miss.

---

## Parse, Don't Validate

Unit strings are parsed into structured types immediately, not validated later during computation.

```python
# Parsing happens once, at the boundary
unit = get_unit_by_name("kg*m/s^2")  # Returns UnitProduct

# All subsequent operations work with typed objects
number = unit(10)
result = number.to(units.newton)
```

**Tradeoff:** Parsing errors surface early, which may feel strict. But this prevents silent failures deep in computation chains.

**Rationale:** Borrowed from [Parse, don't validate](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/). Structured types carry invariants that eliminate whole classes of bugs.

---

## Composable Unit Systems

Custom unit systems compose without modifying the core library.

```python
from ucon.packages import load_package

# Load domain-specific units from TOML
aerospace = load_package("aerospace.ucon.toml")
medical = load_package("medical.ucon.toml")

# Compose into a new graph
graph = get_default_graph().with_package(aerospace).with_package(medical)
```

**Implementation:** `ConversionGraph.with_package()` returns a new graph, leaving the original unchanged:

```python
def with_package(self, package: UnitPackage) -> ConversionGraph:
    new = self.copy()
    for unit_def in package.units:
        new.register_unit(unit_def.materialize())
    for edge_def in package.edges:
        edge_def.materialize(new)
    return new
```

**Rationale:**
- Domain experts define units in config files, not Python code
- Composition is explicit and traceable
- No global mutation means packages can't conflict

---

## Pseudo-Dimension Isolation

Angles, ratios, solid angles, and counts share a zero-dimensional vector but are semantically distinct. ucon prevents cross-family conversions.

```python
# These all have dimension vector = (0,0,0,0,0,0,0,0)
units.radian(1)    # angle
units.percent(50)  # ratio
units.steradian(1) # solid_angle
units.each(10)     # count

# But cross-conversion is blocked
units.radian(1).to(units.percent)  # raises ConversionNotFound
```

**Implementation:** Pseudo-dimensions use tuple values to prevent Python's Enum from aliasing them:

```python
class Dimension(Enum):
    none = Vector()
    angle = (Vector(), "angle")       # tuple prevents aliasing
    ratio = (Vector(), "ratio")
    solid_angle = (Vector(), "solid_angle")
    count = (Vector(), "count")
```

**Rationale:** Mathematically, these are all dimensionless. But converting radians to percent is nonsensical. Semantic isolation catches this class of error.

---

## Map Composition

Conversion functions are first-class objects that compose via `@` (matrix-style composition).

```python
from ucon.maps import LinearMap, AffineMap, LogMap

# Linear: y = a * x
meter_to_foot = LinearMap(3.28084)

# Affine: y = a * x + b (for temperature)
celsius_to_kelvin = AffineMap(1, 273.15)

# Logarithmic: y = scale * log_base(x) + offset
fraction_to_nines = LogMap(scale=-1) @ AffineMap(a=-1, b=1)

# Composition
path = meter_to_foot @ foot_to_inch  # meter → inch
```

**Implementation:** Each `Map` implements `__call__`, `inverse()`, and `__matmul__`:

```python
class LinearMap:
    def __call__(self, x): return self.a * x
    def inverse(self): return LinearMap(1 / self.a)
    def __matmul__(self, other): return ComposedMap(self, other)
```

**Rationale:** Conversion paths are composed at graph-traversal time, not hardcoded. This enables:
- Multi-hop conversions (meter → foot → inch)
- Uncertainty propagation via `derivative()`
- Nonlinear conversions (temperature, logarithmic scales)

---

## Structured Errors for AI Agents

MCP tools return structured `ConversionError` objects with `likely_fix` for mechanical corrections and `hints` for exploratory suggestions.

```python
ConversionError(
    error="Unknown unit: 'kilgoram'",
    error_type="unknown_unit",
    likely_fix="kilogram (kg)",  # High confidence → apply directly
    hints=["Similar: gram (g)"],  # Lower confidence → reason about
)
```

**Implementation:** Fuzzy matching with confidence tiers:

```python
def _suggest_units(bad_name: str) -> tuple[str | None, list[str]]:
    matches = get_close_matches(bad_name, corpus, cutoff=0.6)
    top_score = similarity(bad_name, matches[0])

    # High confidence (≥0.7) with clear gap → likely_fix
    if top_score >= 0.7 and gap_to_second >= 0.1:
        return format_unit(matches[0]), []

    # Otherwise → hints only
    return None, [format_unit(m) for m in matches]
```

**Rationale:** AI agents can self-correct typos without escalating to users, while ambiguous cases require human judgment.

---

## Summary

| Principle | Tradeoff | Benefit |
|-----------|----------|---------|
| Correctness over performance | Slower operations | Catches errors early |
| Injectable over global | More verbose | Thread-safe, testable |
| Explicit dimensional algebra | Learning curve | Physics-correct operations |
| Parse, don't validate | Strict boundaries | No silent failures |
| Composable unit systems | Config files needed | Domain isolation |
| Pseudo-dimension isolation | Can't convert rad→% | Semantic correctness |
| Map composition | More abstractions | Flexible conversions |
| Structured errors | More response fields | AI self-correction |

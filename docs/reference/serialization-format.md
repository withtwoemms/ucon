# Serialization Format

TOML schema for persisting a `ConversionGraph` to disk.

Format version: **1.3**

---

## Overview

A `.ucon.toml` file encodes a complete `ConversionGraph` — bases, dimensions,
units, conversion edges, physical constants, and cross-dimensional contexts.
Files are produced by `graph.to_toml()` and loaded by
`ConversionGraph.from_toml()`.

```python
from ucon.graph import ConversionGraph, get_default_graph

# Export
graph = get_default_graph()
graph.to_toml("my-graph.ucon.toml")

# Import
restored = ConversionGraph.from_toml("my-graph.ucon.toml")
assert graph == restored
```

Sections appear in this order:

| Section | TOML type | Required | Purpose |
|---------|-----------|----------|---------|
| `[package]` | table | yes | Name and format version |
| `[bases.*]` | table per basis | yes | Dimensional bases (SI, CGS, ...) |
| `[dimensions.*]` | table per dimension | yes | Dimension vectors |
| `[transforms.*]` | table per transform | if cross-basis edges exist | Basis-to-basis matrix mappings |
| `[[units]]` | array of tables | yes | Unit definitions |
| `[[edges]]` | array of tables | no | Same-basis conversion edges |
| `[[product_edges]]` | array of tables | no | Composite-unit conversion edges |
| `[[cross_basis_edges]]` | array of tables | no | Cross-basis conversion edges |
| `[[constants]]` | array of tables | no | Physical constants |
| `[contexts.*]` | table per context | no | Cross-dimensional conversion contexts |

---

## `[package]`

File metadata.

```toml
[package]
name = "my-graph"
format_version = "1.3"
loaded_packages = ["si", "cgs"]   # optional
```

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `name` | string | yes | Package name (defaults to filename stem on export) |
| `format_version` | string | yes | Schema version; current is `"1.2"` |
| `loaded_packages` | array of strings | no | Names of packages baked into this graph |

---

## `[bases.*]`

Each key under `[bases]` defines a dimensional basis.

```toml
[bases.SI]
components = [
    { name = "time", symbol = "T" },
    { name = "length", symbol = "L" },
    { name = "mass", symbol = "M" },
    { name = "current", symbol = "I" },
    { name = "temperature", symbol = "Θ" },
    { name = "luminous_intensity", symbol = "J" },
    { name = "amount_of_substance", symbol = "N" },
    { name = "information", symbol = "B" },
]

[bases.CGS]
components = [
    { name = "length", symbol = "L" },
    { name = "mass", symbol = "M" },
    { name = "time", symbol = "T" },
]
```

Each component has:

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `name` | string | yes | Component name (e.g. `"length"`) |
| `symbol` | string | no | Short symbol (e.g. `"L"`); defaults to `name` |

Component order matters — it defines the index positions used by dimension
vectors and transform matrices.

---

## `[dimensions.*]`

Each key under `[dimensions]` defines a dimension as a vector over a basis.

```toml
[dimensions.force]
basis = "SI"
vector = [  -2, 1, 1, 0, 0, 0, 0, 0 ]
#           T   L  M  I  Θ  J  N  B

[dimensions.angle]
basis = "SI"
vector = [  0, 0, 0, 0, 0, 0, 0, 0 ]
tag = "angle"
```

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `basis` | string | yes | Name of the basis (must exist in `[bases.*]`) |
| `vector` | array of int | yes | Exponents over basis components, in order |
| `tag` | string | no | Disambiguation tag for dimensionless quantities (e.g. `"angle"`, `"ratio"`, `"solid_angle"`) |

---

## `[transforms.*]`

Basis-to-basis linear transforms, used by cross-basis edges.

### Standard transform

```toml
[transforms.CGS_TO_SI]
source = "CGS"
target = "SI"
matrix = [
    [0, 1, 0, 0, 0, 0, 0, 0],    # CGS length  → SI components
    [0, 0, 1, 0, 0, 0, 0, 0],    # CGS mass    → SI components
    [1, 0, 0, 0, 0, 0, 0, 0],    # CGS time    → SI components
]
```

Matrix values may be integers or fraction strings for exact representation:

```toml
[transforms.SI_TO_CGS-ESU]
source = "SI"
target = "CGS-ESU"
matrix = [
    [0, 1, 0, 0],                   # SI time   → CGS-ESU
    [0, 0, 1, 0],                   # SI length → CGS-ESU
    [1, 0, 0, 0],                   # SI mass   → CGS-ESU
    ["3/2", "1/2", "-2", 0],        # SI current → CGS-ESU (fractional)
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
]
```

### Constant-bound transform

When a transform involves physical constants (e.g. natural units),
`bindings` specifies how each source component maps via a constant.

```toml
[transforms.SI_TO_natural]
source = "SI"
target = "natural"
matrix = [
    [-1],    # SI time        → natural energy^-1
    [-1],    # SI length      → natural energy^-1
    [1],     # SI mass        → natural energy^1
    [0],     # SI current     → (unused)
    [1],     # SI temperature → natural energy^1
    [0],
    [0],
    [0],
]

[[transforms.SI_TO_natural.bindings]]
source_component = "length"
constant_symbol = "ℏc"
target_expression = [-1]

[[transforms.SI_TO_natural.bindings]]
source_component = "time"
constant_symbol = "ℏ"
target_expression = [-1]

[[transforms.SI_TO_natural.bindings]]
source_component = "mass"
constant_symbol = "c"
exponent = "-2"
target_expression = [1]

[[transforms.SI_TO_natural.bindings]]
source_component = "temperature"
constant_symbol = "k_B"
exponent = "-1"
target_expression = [1]
```

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `source` | string | yes | Source basis name |
| `target` | string | yes | Target basis name |
| `matrix` | array of arrays | yes | Rows = source components, columns = target components |
| `bindings` | array of tables | no | Present for constant-bound transforms |

Each binding entry:

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `source_component` | string | yes | Source basis component name |
| `constant_symbol` | string | yes | Physical constant symbol (e.g. `"c"`, `"ℏ"`, `"k_B"`) |
| `exponent` | string or int | no | Power of the constant; defaults to `1` |
| `target_expression` | array of int | yes | Vector in target basis |

---

## `[[units]]`

Flat array of unit definitions. Every unit referenced by an edge must appear here.

```toml
[[units]]
name = "meter"
dimension = "length"
aliases = ["m", "meters", "metre"]

[[units]]
name = "foot"
dimension = "length"
aliases = ["ft", "feet"]
```

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `name` | string | yes | Canonical unit name |
| `dimension` | string | yes | Dimension name (must exist in `[dimensions.*]`) |
| `aliases` | array of strings | no | Alternative names for parsing |

---

## `[[edges]]`

Same-basis conversion edges. Only the forward direction is stored; the inverse
is reconstructed on import.

### Linear edge (most common)

```toml
[[edges]]
src = "meter"
dst = "foot"
factor = 3.28084
```

`dst_value = src_value * factor`

### Affine edge (temperature scales)

```toml
[[edges]]
src = "celsius"
dst = "fahrenheit"
factor = 1.8
offset = 32.0
```

`dst_value = src_value * factor + offset`

### Edge with factor uncertainty

For factors derived from measured constants, `rel_uncertainty` records the
relative standard uncertainty:

```toml
[[edges]]
src = "joule"
dst = "hartree"
factor = 2.2937122783963248e+17
rel_uncertainty = 1.1e-12
```

This is used by `Number.to(target, propagate_factor_uncertainty=True)` to
include factor uncertainty in the converted result.

### Map edge (non-linear)

For conversions that aren't linear or affine, a `map` table replaces
`factor`/`offset`:

```toml
[[edges]]
src = "bel"
dst = "fraction"
map = { type = "exp", scale = 1.0, base = 10 }
```

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `src` | string | yes | Source unit name |
| `dst` | string | yes | Destination unit name |
| `factor` | float | no | Linear scale factor (shorthand for `LinearMap`) |
| `offset` | float | no | Additive offset (with `factor`, shorthand for `AffineMap`) |
| `rel_uncertainty` | float | no | Relative uncertainty of `factor` (default `0.0`, omitted when exact) |
| `map` | table | no | Explicit map specification (see [Map Types](#map-types)) |

Exactly one of `factor` or `map` should be present.

`rel_uncertainty` is used for edges derived from measured physical constants
(e.g., Hartree energy, Planck mass). It is omitted on export when `0.0` for
backward compatibility with format version 1.2 readers.

---

## `[[product_edges]]`

Edges between composite (product) units and simple units.
Source and destination are expressed as `unit*unit^exp` strings.

```toml
[[product_edges]]
src = "hour*kwatt"
dst = "joule"
factor = 3600000.0
product = true

[[product_edges]]
src = "liter^-1*mole"
dst = "pH"
product = true
map = { type = "log", scale = -1, base = 10 }
```

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `src` | string | yes | Source unit expression (e.g. `"meter*second^-1"`) |
| `dst` | string | yes | Destination unit expression |
| `factor` | float | no | Linear scale factor |
| `map` | table | no | Explicit map specification |
| `product` | boolean | yes | Always `true` |

Unit expressions use `*` for multiplication and `^` for exponents.
Scale prefixes are baked into names (e.g. `kwatt` for kilowatt).

---

## `[[cross_basis_edges]]`

Edges that bridge different dimensional bases (e.g. CGS to SI).

```toml
[[cross_basis_edges]]
src = "dyne"
dst = "newton"
factor = 1e-05
transform = "CGS_TO_SI"

[[cross_basis_edges]]
src = "joule"
dst = "electron_volt"
factor = 6.241509074460763e+18
transform = "SI_TO_natural"

[[cross_basis_edges]]
src = "joule"
dst = "hartree"
factor = 2.2937122783963248e+17
rel_uncertainty = 1.1e-12
transform = "SI_TO_atomic"
```

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `src` | string | yes | Source unit name (in source basis) |
| `dst` | string | yes | Destination unit name (in target basis) |
| `factor` | float | no | Linear scale factor |
| `rel_uncertainty` | float | no | Relative uncertainty of `factor` (default `0.0`) |
| `map` | table | no | Explicit map specification |
| `transform` | string | yes | Transform name (must exist in `[transforms.*]`) |

---

## `[[constants]]`

Physical constants associated with the graph.

```toml
[[constants]]
symbol = "c"
name = "speed of light"
value = 299792458.0
unit = "meter*second^-1"
category = "exact"
source = "CODATA 2018"
uncertainty = 0.0
```

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `symbol` | string | yes | Short symbol (e.g. `"c"`, `"h"`, `"k_B"`) |
| `name` | string | yes | Descriptive name |
| `value` | float | yes | Numeric value in the given units |
| `unit` | string | yes | Unit expression |
| `category` | string | no | Classification (e.g. `"exact"`, `"measured"`, `"derived"`) |
| `source` | string | no | Data source reference |
| `uncertainty` | float | no | Standard uncertainty |

---

## `[contexts.*]`

Named cross-dimensional conversion contexts. A context bundles edges that
connect dimensions which are normally incommensurable (e.g. wavelength to
frequency via the speed of light).

```toml
[contexts.spectroscopy]
description = "Spectroscopy: wavelength/frequency/energy via c and h."
edges = [
    { src = "meter", dst = "hertz", map = { type = "reciprocal", a = 299792458.0 } },
    { src = "hertz", dst = "joule", factor = 6.62607015e-34 },
    { src = "meter", dst = "joule", map = { type = "reciprocal", a = 1.9864458571489286e-25 } },
    { src = "joule", dst = "reciprocal_meter", factor = 5.03411656754271e+24 },
]
```

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `description` | string | no | Human-readable description |
| `edges` | array of tables | yes | Context edges (same format as `[[edges]]`) |

After import, activate a context with `using_context()`:

```python
graph = ConversionGraph.from_toml("my-graph.ucon.toml")
ctx = graph._contexts["spectroscopy"]

with using_graph(graph), using_context(ctx):
    wavelength = Number(500e-9, units.meter)   # 500 nm
    frequency = wavelength.to(units.hertz)     # ~5.996e14 Hz
```

---

## Map Types

The `map` field in edges specifies a conversion function. All map types
support lossless round-trip serialization.

### `linear`

`y = a * x`

```toml
map = { type = "linear", a = 0.3048 }
map = { type = "linear", a = 2.2937e17, rel_uncertainty = 1.1e-12 }
```

`rel_uncertainty` is omitted when `0.0` (exact).

!!! note
    Linear maps are normally written with the `factor` shorthand
    instead of an explicit `map` table.

### `affine`

`y = a * x + b`

```toml
map = { type = "affine", a = 1.8, b = 32.0 }
map = { type = "affine", a = 1.8, b = 32.0, rel_uncertainty = 1e-6 }
```

`rel_uncertainty` refers to the slope `a` only (offsets are exact).

!!! note
    Affine maps are normally written with `factor` + `offset` shorthand.

### `reciprocal`

`y = a / x`

```toml
map = { type = "reciprocal", a = 299792458.0 }
map = { type = "reciprocal", a = 1.5e-10, rel_uncertainty = 3e-5 }
```

`rel_uncertainty` is omitted when `0.0` (exact).

### `log`

`y = scale * log_base(x / reference) + offset`

```toml
map = { type = "log", scale = -1, base = 10 }
map = { type = "log", scale = 1.0, base = 10, reference = 1e-12, offset = 0.0 }
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `scale` | float | `1.0` | Multiplier on the log result |
| `base` | float | `10.0` | Logarithm base |
| `reference` | float | `1.0` | Reference value (divisor inside log) |
| `offset` | float | `0.0` | Additive offset on the result |

Fields at their default value are omitted on export.

### `exp`

`y = reference * base^((x - offset) / scale)`

Inverse of `log`.

```toml
map = { type = "exp", scale = 1.0, base = 10 }
```

Same fields as `log`.

### `composed`

Chain of two maps: `y = outer(inner(x))`.

```toml
map = { type = "composed", outer = { type = "log", scale = -1, base = 10 }, inner = { type = "affine", a = -1, b = 1 } }
```

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `outer` | map table | yes | Applied second |
| `inner` | map table | yes | Applied first |

---

## Strict Mode

By default, `from_toml()` raises `GraphLoadError` if any unit referenced by
an edge cannot be resolved. Pass `strict=False` to silently skip unresolvable
edges instead:

```python
# Raises on unknown units (default)
graph = ConversionGraph.from_toml("graph.ucon.toml")

# Skips edges with unknown units
graph = ConversionGraph.from_toml("graph.ucon.toml", strict=False)
```

---

## Minimal Example

A small self-contained graph with two units and one edge:

```toml
[package]
name = "minimal"
format_version = "1.3"

[bases.SI]
components = [
    { name = "length", symbol = "L" },
]

[dimensions.length]
basis = "SI"
vector = [1]

[[units]]
name = "meter"
dimension = "length"
aliases = ["m"]

[[units]]
name = "foot"
dimension = "length"
aliases = ["ft"]

[[edges]]
src = "foot"
dst = "meter"
factor = 0.3048
```

```python
from ucon.graph import ConversionGraph, using_graph
from ucon import Number

graph = ConversionGraph.from_toml("minimal.ucon.toml")
m = graph._name_registry_cs["meter"]
ft = graph._name_registry_cs["foot"]

with using_graph(graph):
    print(Number(1, m).to(ft))   # <3.28084 foot>
```

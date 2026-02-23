# MCP Tools Reference

Complete schema and response format documentation for ucon MCP server tools.

---

## convert

Convert a numeric value from one unit to another.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `value` | float | Yes | The numeric quantity to convert |
| `from_unit` | string | Yes | Source unit string |
| `to_unit` | string | Yes | Target unit string |
| `custom_units` | list[dict] | No | Inline unit definitions |
| `custom_edges` | list[dict] | No | Inline conversion edges |

### Response Schema

**Success: `ConversionResult`**

```json
{
  "quantity": 3.107,
  "unit": "mi",
  "dimension": "length",
  "uncertainty": null
}
```

**Error: `ConversionError`**

```json
{
  "error": "Dimension mismatch: mass is not length",
  "error_type": "dimension_mismatch",
  "parameter": "to_unit",
  "likely_fix": "Use a mass unit like 'lb' or 'g'"
}
```

### Examples

```python
# Simple conversion
convert(value=5, from_unit="km", to_unit="mi")
# → {"quantity": 3.107, "unit": "mi", "dimension": "length"}

# Composite units
convert(value=10, from_unit="m/s", to_unit="km/h")
# → {"quantity": 36.0, "unit": "km/h", "dimension": "velocity"}

# With inline custom unit
convert(
    value=1,
    from_unit="slug",
    to_unit="kg",
    custom_units=[{"name": "slug", "dimension": "mass", "aliases": ["slug"]}],
    custom_edges=[{"src": "slug", "dst": "kg", "factor": 14.5939}]
)
# → {"quantity": 14.5939, "unit": "kg", "dimension": "mass"}
```

---

## compute

Perform multi-step factor-label calculations with dimensional tracking.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `initial_value` | float | Yes | Starting numeric quantity |
| `initial_unit` | string | Yes | Starting unit string |
| `factors` | list[dict] | Yes | Conversion factor chain |
| `custom_units` | list[dict] | No | Inline unit definitions |
| `custom_edges` | list[dict] | No | Inline conversion edges |

**Factor dict schema:**

| Field | Type | Description |
|-------|------|-------------|
| `value` | float | Numeric coefficient (default: 1.0) |
| `numerator` | string | Numerator unit string |
| `denominator` | string | Denominator unit string (may include numeric prefix) |

### Response Schema

**Success: `ComputeResult`**

```json
{
  "quantity": 349.2,
  "unit": "mg/ea",
  "dimension": "mass/count",
  "steps": [
    {"factor": "154 lb", "dimension": "mass", "unit": "lb"},
    {"factor": "(1 kg / 2.205 lb)", "dimension": "mass", "unit": "kg"},
    {"factor": "(15 mg / kg*day)", "dimension": "mass/time", "unit": "mg/d"},
    {"factor": "(1 day / 3 ea)", "dimension": "mass/count", "unit": "mg/ea"}
  ]
}
```

### Examples

```python
# Weight-based dosing calculation
compute(
    initial_value=154,
    initial_unit="lb",
    factors=[
        {"value": 1, "numerator": "kg", "denominator": "2.205 lb"},
        {"value": 15, "numerator": "mg", "denominator": "kg*day"},
        {"value": 1, "numerator": "day", "denominator": "3 ea"},
    ]
)
# → {"quantity": 349.2, "unit": "mg/ea", "dimension": "mass/count", "steps": [...]}

# IV drip rate
compute(
    initial_value=1000,
    initial_unit="mL",
    factors=[
        {"value": 15, "numerator": "drop", "denominator": "mL"},
        {"value": 1, "numerator": "1", "denominator": "8 hr"},
        {"value": 1, "numerator": "hr", "denominator": "60 min"},
    ],
    custom_units=[{"name": "drop", "dimension": "count", "aliases": ["gtt"]}]
)
# → {"quantity": 31.25, "unit": "gtt/min", ...}
```

---

## list_units

List available units, optionally filtered by dimension.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `dimension` | string | No | Filter by dimension name |

### Response Schema

**Success: `list[UnitInfo]`**

```json
[
  {
    "name": "meter",
    "shorthand": "m",
    "aliases": ["m"],
    "dimension": "length",
    "scalable": true
  },
  {
    "name": "foot",
    "shorthand": "ft",
    "aliases": ["ft", "feet"],
    "dimension": "length",
    "scalable": false
  }
]
```

### Examples

```python
# List all units
list_units()

# Filter by dimension
list_units(dimension="mass")
# → [{"name": "gram", ...}, {"name": "kilogram", ...}, ...]
```

---

## list_scales

List available scale prefixes.

### Parameters

None.

### Response Schema

**Success: `list[ScaleInfo]`**

```json
[
  {"name": "peta", "prefix": "P", "factor": 1e15},
  {"name": "tera", "prefix": "T", "factor": 1e12},
  {"name": "giga", "prefix": "G", "factor": 1e9},
  {"name": "mega", "prefix": "M", "factor": 1e6},
  {"name": "kilo", "prefix": "k", "factor": 1000.0},
  {"name": "gibi", "prefix": "Gi", "factor": 1073741824.0},
  {"name": "mebi", "prefix": "Mi", "factor": 1048576.0},
  {"name": "kibi", "prefix": "Ki", "factor": 1024.0}
]
```

---

## list_dimensions

List available physical dimensions.

### Parameters

None.

### Response Schema

**Success: `list[str]`**

```json
[
  "acceleration", "amount_of_substance", "angle", "angular_momentum",
  "area", "capacitance", "catalytic_activity", "charge", "conductance",
  "conductivity", "count", "current", "density", "dynamic_viscosity",
  "electric_field_strength", "energy", "entropy", "force", "frequency",
  "gravitation", "illuminance", "inductance", "information",
  "kinematic_viscosity", "length", "luminous_intensity", "magnetic_flux",
  "magnetic_flux_density", "magnetic_permeability", "mass", "molar_mass",
  "molar_volume", "momentum", "none", "permittivity", "power", "pressure",
  "ratio", "resistance", "resistivity", "solid_angle",
  "specific_heat_capacity", "temperature", "thermal_conductivity", "time",
  "velocity", "voltage", "volume"
]
```

---

## check_dimensions

Check if two units have compatible dimensions.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `unit_a` | string | Yes | First unit string |
| `unit_b` | string | Yes | Second unit string |

### Response Schema

**Success: `DimensionCheck`**

```json
{
  "compatible": true,
  "dimension_a": "mass",
  "dimension_b": "mass"
}
```

### Examples

```python
# Compatible units
check_dimensions(unit_a="kg", unit_b="lb")
# → {"compatible": true, "dimension_a": "mass", "dimension_b": "mass"}

# Incompatible units
check_dimensions(unit_a="kg", unit_b="m")
# → {"compatible": false, "dimension_a": "mass", "dimension_b": "length"}
```

---

## define_unit

Register a custom unit for the session.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Canonical unit name |
| `dimension` | string | Yes | Dimension name (use `list_dimensions()`) |
| `aliases` | list[str] | No | Shorthand symbols |

### Response Schema

**Success: `UnitDefinitionResult`**

```json
{
  "success": true,
  "name": "slug",
  "dimension": "mass",
  "aliases": ["slug"],
  "message": "Unit 'slug' registered for session. Use define_conversion() to add conversion edges."
}
```

### Examples

```python
define_unit(name="slug", dimension="mass", aliases=["slug"])
define_unit(name="nautical_mile", dimension="length", aliases=["nmi", "NM"])
```

---

## define_conversion

Add a conversion edge between units.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `src` | string | Yes | Source unit name/alias |
| `dst` | string | Yes | Destination unit name/alias |
| `factor` | float | Yes | Conversion multiplier: `dst = src * factor` |

### Response Schema

**Success: `ConversionDefinitionResult`**

```json
{
  "success": true,
  "src": "slug",
  "dst": "kg",
  "factor": 14.5939,
  "message": "Conversion edge 'slug' -> 'kg' (factor=14.5939) added to session."
}
```

### Examples

```python
# After define_unit("slug", "mass", ["slug"])
define_conversion(src="slug", dst="kg", factor=14.5939)

# Now convert() can use the new unit
convert(value=1, from_unit="slug", to_unit="lb")
```

---

## reset_session

Clear all custom units and conversions.

### Parameters

None.

### Response Schema

**Success: `SessionResult`**

```json
{
  "success": true,
  "message": "Session reset. All custom units and conversions cleared."
}
```

---

## list_formulas

List registered domain formulas with their dimensional constraints.

### Parameters

None.

### Response Schema

**Success: `list[FormulaInfoResponse]`**

```json
[
  {
    "name": "bmi",
    "description": "Body Mass Index",
    "parameters": {
      "mass": "mass",
      "height": "length"
    }
  }
]
```

### Examples

```python
list_formulas()
# → [{"name": "bmi", "description": "Body Mass Index", "parameters": {"mass": "mass", "height": "length"}}]
```

---

## call_formula

Invoke a registered formula with dimensionally-validated inputs.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Formula name (from `list_formulas()`) |
| `parameters` | dict[str, dict] | Yes | Parameter values (see format below) |

**Parameter value format:**

```json
{
  "mass": {"value": 70, "unit": "kg"},
  "height": {"value": 1.75, "unit": "m"},
  "factor": {"value": 2.5}
}
```

- Use `{"value": ..., "unit": "..."}` for dimensioned quantities
- Use `{"value": ...}` for dimensionless quantities

### Response Schema

**Success: `FormulaResult`**

```json
{
  "formula": "bmi",
  "quantity": 22.86,
  "unit": "kg/m²",
  "dimension": "derived(mass/length²)",
  "uncertainty": null
}
```

**Error: `FormulaError`**

```json
{
  "error": "Missing required parameter: 'height'",
  "error_type": "missing_parameter",
  "formula": "bmi",
  "parameter": "height",
  "expected": "length",
  "hints": ["Parameter 'height' expects dimension: length"]
}
```

### Error Types

| Error Type | Description |
|------------|-------------|
| `unknown_formula` | Formula name not found in registry |
| `missing_parameter` | Required parameter not provided |
| `invalid_parameter` | Parameter format incorrect or unit unknown |
| `dimension_mismatch` | Parameter has wrong dimension |
| `execution_error` | Formula raised an exception |

### Examples

```python
# Call BMI formula
call_formula(
    name="bmi",
    parameters={
        "mass": {"value": 70, "unit": "kg"},
        "height": {"value": 1.75, "unit": "m"}
    }
)
# → {"formula": "bmi", "quantity": 22.86, "unit": "kg/m²", ...}

# Dimensionless parameter
call_formula(
    name="scale_value",
    parameters={
        "x": {"value": 10, "unit": "m"},
        "factor": {"value": 2.5}
    }
)
# → {"formula": "scale_value", "quantity": 25.0, "unit": "m", ...}
```

### Registering Formulas

Formulas are registered in Python code using `@register_formula`:

```python
from ucon import Number, Dimension, enforce_dimensions
from ucon.mcp.formulas import register_formula

@register_formula("bmi", description="Body Mass Index")
@enforce_dimensions
def bmi(
    mass: Number[Dimension.mass],
    height: Number[Dimension.length],
) -> Number:
    return mass / (height * height)
```

The `@enforce_dimensions` decorator enables runtime dimension checking. Parameter constraints are extracted automatically and exposed via `list_formulas()`.

---

## Error Types

All tools may return `ConversionError` with these error types:

| Error Type | Description | Example |
|------------|-------------|---------|
| `unknown_unit` | Unit string not recognized | `"kilgoram"` typo |
| `dimension_mismatch` | Units have incompatible dimensions | kg to m |
| `no_conversion_path` | No edge path between units | Custom unit without edge |
| `invalid_input` | Malformed parameter | Missing required field |
| `computation_error` | Runtime calculation failure | Division by zero |

### Error Response Schema

```json
{
  "error": "Human-readable error message",
  "error_type": "unknown_unit",
  "parameter": "from_unit",
  "step": 2,
  "likely_fix": "Did you mean 'kilogram'?",
  "hints": ["Check spelling", "Use list_units() to see available units"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Human-readable message |
| `error_type` | string | Machine-readable error category |
| `parameter` | string | Which parameter caused the error |
| `step` | int | For compute(), which factor step failed (0-indexed) |
| `likely_fix` | string | Suggested correction (typos, dimension swaps) |
| `hints` | list[str] | Additional guidance |

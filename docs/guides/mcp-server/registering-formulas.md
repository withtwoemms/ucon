# Registering Formulas

ucon's formula system lets you expose dimensionally-typed calculations to AI agents via MCP. Agents discover formulas through `list_formulas()` and invoke them with `call_formula()`.

## Basic Formula

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

**Key points:**

- `@register_formula` must be the outermost decorator
- `@enforce_dimensions` enables runtime dimension checking
- `Number[Dimension.X]` declares expected dimensions
- Dimension constraints are extracted and exposed via `list_formulas()`

## Agent Discovery

After registration, agents see the formula via MCP:

```python
list_formulas()
# → [
#     {
#         "name": "bmi",
#         "description": "Body Mass Index",
#         "parameters": {"mass": "mass", "height": "length"}
#     }
# ]
```

## Agent Invocation

Agents call formulas with structured parameters:

```python
call_formula(
    name="bmi",
    parameters={
        "mass": {"value": 70, "unit": "kg"},
        "height": {"value": 1.75, "unit": "m"}
    }
)
# → {"formula": "bmi", "quantity": 22.86, "unit": "kg/m²", ...}
```

## Mixed Constraints

Not all parameters need dimensional constraints:

```python
@register_formula("dosage", description="Weight-based medication dosage")
@enforce_dimensions
def dosage(
    patient_mass: Number[Dimension.mass],
    dose_per_kg: Number,  # Unconstrained
    doses_per_day: Number[Dimension.frequency],
) -> Number:
    return patient_mass * dose_per_kg * doses_per_day
```

Unconstrained parameters show `null` in the schema:

```python
list_formulas()
# → [{
#     "name": "dosage",
#     "parameters": {
#         "patient_mass": "mass",
#         "dose_per_kg": null,
#         "doses_per_day": "frequency"
#     }
# }]
```

## Error Handling

Dimension mismatches produce structured errors:

```python
call_formula(
    name="bmi",
    parameters={
        "mass": {"value": 70, "unit": "m"},  # Wrong dimension
        "height": {"value": 1.75, "unit": "m"}
    }
)
# → {
#     "error": "mass: expected dimension 'mass', got 'length'",
#     "error_type": "dimension_mismatch",
#     "parameter": "mass",
#     "expected": "mass",
#     "got": "length"
# }
```

## Registration Timing

Formulas must be registered before the MCP server starts. Typical pattern:

```python
# myapp/formulas.py
from ucon import Number, Dimension, enforce_dimensions
from ucon.mcp.formulas import register_formula

@register_formula("my_formula", description="...")
@enforce_dimensions
def my_formula(...) -> Number:
    ...
```

```python
# myapp/__init__.py or entry point
import myapp.formulas  # Triggers registration

from ucon.mcp.server import main
main()  # Start MCP server with formulas registered
```

## Formula Names

Formula names must be unique. Re-registering raises `ValueError`:

```python
@register_formula("duplicate")
def first():
    pass

@register_formula("duplicate")  # Raises ValueError
def second():
    pass
```

## Without Dimension Constraints

Formulas work without `@enforce_dimensions`, but lose pre-call validation:

```python
@register_formula("simple_multiply")
def simple_multiply(x: Number, y: Number) -> Number:
    return x * y
```

Parameters show `null` for all dimensions. Agents can still call the formula, but won't catch dimension errors until execution.

## Testing Formulas

Use `clear_formulas()` in tests to reset state:

```python
import pytest
from ucon.mcp.formulas import clear_formulas, register_formula, get_formula

@pytest.fixture(autouse=True)
def clean_registry():
    clear_formulas()
    yield
    clear_formulas()

def test_my_formula():
    @register_formula("test")
    def test_fn(x: Number) -> Number:
        return x

    info = get_formula("test")
    assert info is not None
```

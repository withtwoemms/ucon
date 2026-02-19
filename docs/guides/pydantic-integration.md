# Pydantic Integration

ucon provides first-class Pydantic v2 support for type-safe dimensional fields in your models.

## Installation

```bash
pip install ucon[pydantic]
```

## Basic Usage

Import `Number` from `ucon.pydantic` (not `ucon.core`):

```python
from pydantic import BaseModel
from ucon.pydantic import Number

class Measurement(BaseModel):
    value: Number

# From dict/JSON
m = Measurement(value={"quantity": 5, "unit": "km"})
print(m.value)  # <5 km>

# From Number instance
from ucon import units
m2 = Measurement(value=units.meter(10))
```

## JSON Serialization

Numbers serialize to a readable format:

```python
m = Measurement(value={"quantity": 9.8, "unit": "m/s^2"})
print(m.model_dump_json())
# {"value": {"quantity": 9.8, "unit": "m/s^2", "uncertainty": null}}
```

Both ASCII and Unicode unit notation are accepted:

```python
m1 = Measurement(value={"quantity": 9.8, "unit": "m/s^2"})   # ASCII
m2 = Measurement(value={"quantity": 9.8, "unit": "m/s²"})    # Unicode
```

## Dimensional Constraints

Use `Number[Dimension.X]` to enforce dimensional constraints at validation time:

```python
from pydantic import BaseModel
from ucon import Dimension
from ucon.pydantic import Number

class PhysicsModel(BaseModel):
    distance: Number[Dimension.length]
    duration: Number[Dimension.time]

# Valid
m = PhysicsModel(
    distance={"quantity": 100, "unit": "m"},
    duration={"quantity": 10, "unit": "s"}
)

# Raises ValidationError: distance must have dimension 'length'
m = PhysicsModel(
    distance={"quantity": 100, "unit": "s"},  # wrong dimension
    duration={"quantity": 10, "unit": "s"}
)
```

## The `@enforce_dimensions` Decorator

For function signatures, use `@enforce_dimensions` to validate at call time:

```python
from ucon import Number, Dimension, enforce_dimensions, units

@enforce_dimensions
def speed(
    distance: Number[Dimension.length],
    time: Number[Dimension.time],
) -> Number:
    return distance / time

# Valid
speed(units.meter(100), units.second(10))  # <10.0 m/s>

# Raises ValueError: distance: expected dimension 'length', got 'time'
speed(units.second(100), units.second(10))

# Raises TypeError: distance: expected Number, got int
speed(100, units.second(10))
```

## Runtime Introspection

The dimensional constraint is accessible via `typing.Annotated`:

```python
from typing import get_origin, get_args, Annotated
from ucon import Number, Dimension, DimConstraint

hint = Number[Dimension.time]

assert get_origin(hint) is Annotated
assert get_args(hint)[1].dimension == Dimension.time
```

This enables framework-level validation and schema generation.

## Example: Energy Market Configuration

```python
from pydantic import BaseModel
from ucon import Dimension
from ucon.pydantic import Number

class EnergyContract(BaseModel):
    capacity: Number[Dimension.power]
    price_per_kwh: Number  # No constraint, accepts any unit
    duration: Number[Dimension.time]

contract = EnergyContract(
    capacity={"quantity": 500, "unit": "MW"},
    price_per_kwh={"quantity": 0.12, "unit": "USD/kWh"},
    duration={"quantity": 1, "unit": "year"},
)
```

## Design Notes

**Serialization format:** Units serialize as human-readable shorthand strings (`"km"`, `"m/s^2"`) rather than structured dicts. This aligns with how scientists and engineers express units.

**Parsing priority:** When parsing `"kg"`, ucon returns `Scale.kilo * gram` rather than looking up a `kilogram` Unit. This ensures consistent round-trip serialization and avoids redundant unit definitions.

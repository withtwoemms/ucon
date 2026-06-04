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

## Kind Constraints

Use `Number[kind]` to enforce kind-of-quantity constraints at validation time.
Kind validation is **lattice-aware**: a child kind satisfies a parent
constraint (e.g. `kinetic_energy` passes a field typed as `Number[energy]`).

```python
from pydantic import BaseModel
from ucon import active_kinds
from ucon.pydantic import Number

energy = active_kinds().get("energy")

class Calorimetry(BaseModel):
    heat_in: Number[energy]

# Exact kind match — energy satisfies Number[energy]
m = Calorimetry(heat_in={"quantity": 500, "unit": "J", "kind": "energy"})
m.heat_in.kind.name  # "energy"

# Descendant match — kinetic_energy is a child of energy in the lattice
m2 = Calorimetry(heat_in={"quantity": 250, "unit": "J", "kind": "kinetic_energy"})
m2.heat_in.kind.name  # "kinetic_energy"

# Unkinded Number is rejected
# Calorimetry(heat_in={"quantity": 100, "unit": "J"})
# => ValidationError: expected kind 'energy', got unkinded Number

# Wrong kind is rejected (torque is not a descendant of energy)
# Calorimetry(heat_in={"quantity": 100, "unit": "J", "kind": "torque"})
# => ValidationError: expected kind 'energy', got 'torque'
```

### Joint Dimension and Kind

Combine both constraints with a tuple subscript (order-insensitive).
This matters when multiple kinds share a dimension — for example,
absorbed dose (Gy) and dose equivalent (Sv) are both `specific_energy`
(`L²·T⁻²`), but confusing them is a safety error:

```python
from ucon import Dimension

dose_equivalent = active_kinds().get("dose_equivalent")

class ExposureRecord(BaseModel):
    # Dimension alone would accept both Gy and Sv —
    # the kind constraint ensures only Sv-typed values pass.
    effective_dose: Number[Dimension.specific_energy, dose_equivalent]

# Sv with dose_equivalent kind — accepted
record = ExposureRecord(
    effective_dose={"quantity": 0.02, "unit": "Sv", "kind": "dose_equivalent"},
)

# Gy with absorbed_dose kind — same dimension, rejected by kind constraint
# ExposureRecord(
#     effective_dose={"quantity": 0.02, "unit": "Gy", "kind": "absorbed_dose"},
# )
# => ValidationError: expected kind 'dose_equivalent', got 'absorbed_dose'
```

### JSON Round-Trip

Kind survives serialization as a string name. The `"kind"` key is `null`
when absent, preserving backward compatibility with existing data.

```python
m = Calorimetry(heat_in={"quantity": 500, "unit": "J", "kind": "energy"})
print(m.model_dump())
# {"heat_in": {"quantity": 500.0, "unit": "J", "uncertainty": null, "kind": "energy"}}

# Round-trip: kind is resolved back from the active lattice
restored = Calorimetry.model_validate_json(m.model_dump_json())
restored.heat_in.kind.name  # "energy"
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
from ucon import Number, Dimension, DimensionConstraint

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

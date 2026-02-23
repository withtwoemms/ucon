# Vehicle Simulation Example

A toy example demonstrating `Number[Dimension]` type hints with Pydantic for loading dimensionally-validated configuration from YAML.

## Overview

This example shows:

1. **Pydantic models with dimensional constraints** — `Number[Dimension.mass]`, `Number[Dimension.velocity]`, etc.
2. **YAML configuration loading** — Automatic deserialization and validation
3. **Physics calculations** — `@enforce_dimensions` decorator for runtime safety

## Files

- `config.yaml` — Vehicle and simulation parameters
- `models.py` — Pydantic models with `Number[Dimension]` fields
- `physics.py` — Dimensionally-validated physics functions
- `main.py` — Example usage

## Usage

```bash
# Install dependencies
pip install pyyaml

# Run with default config
python main.py

# Run with custom config
python main.py /path/to/custom/config.yaml
```

## Example Output

```
=== Vehicle Properties ===
  Mass:             <1500 kg>
  Max speed:        <120 km/h>
  Drag coefficient: <0.32>
  Frontal area:     <2.2 m²>

=== Calculations ===
  Kinetic energy at max speed:
    <833333.33... J>
    <833.33... kJ>

  Stopping distance (8 m/s² braking):
    <69.44... m>
```

## Key Patterns

### Dimensional Type Hints

```python
class VehicleConfig(BaseModel):
    mass: Number[Dimension.mass]           # kg, lb, etc.
    max_speed: Number[Dimension.velocity]  # m/s, km/h, mph
```

### Dimension-Enforced Functions

```python
@enforce_dimensions
def kinetic_energy(
    mass: Number[Dimension.mass],
    velocity: Number[Dimension.velocity],
) -> Number[Dimension.energy]:
    return 0.5 * mass * velocity ** 2
```

### Validation at Load Time

If the YAML has wrong dimensions, Pydantic rejects it:

```yaml
# ❌ This would fail validation
max_speed: { quantity: 120, unit: "kg" }  # kg is mass, not velocity
```

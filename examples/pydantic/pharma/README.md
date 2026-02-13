# Pharmaceutical Compounding Example

An advanced example demonstrating sophisticated Pydantic patterns with `Number[Dimension]` for safety-critical pharmaceutical calculations.

## Overview

This example shows:

1. **Composite dimension validation** — `mg/kg/day` dose rates
2. **Custom validators** — Positivity constraints, range checking
3. **Cross-field validation** — Ensuring `min < max` for temperature ranges
4. **Uncertainty propagation** — Drug concentration uncertainty flows through calculations
5. **Computed properties** — Derived values like total infusion volume

## Files

- `config.yaml` — Drug, patient, and dosing parameters
- `models.py` — Advanced Pydantic models with custom validation
- `main.py` — Example usage with error demonstrations

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
=== Drug Information ===
  Name:          Amoxicillin
  Concentration: <250 ± 5 mg/mL>
  Stability:     <14 day>
  Storage temp:  <2 degC> to <8 degC>

=== Calculated Values ===
  Daily dose:    <1750 ± 35 mg>
  Single dose:   <500 ± 10 mg>    # Clamped to max
  Volume/dose:   <2.0 ± 0.05 mL>
```

## Key Patterns

### Composite Dimension Validation

```python
@field_validator('target_dose')
@classmethod
def validate_dose_rate_dimension(cls, v: Number) -> Number:
    expected = Dimension.mass / Dimension.mass / Dimension.time
    if v.dimension != expected:
        raise ValueError(f"expected {expected.name}, got {v.dimension.name}")
    return v
```

### Custom Validators with Annotated

```python
def must_be_positive(n: Number) -> Number:
    if n.quantity <= 0:
        raise ValueError(f"must be positive, got {n.quantity}")
    return n

PositiveNumber = Annotated[PydanticNumber, AfterValidator(must_be_positive)]
```

### Cross-Field Validation

```python
class TemperatureRange(BaseModel):
    min: PydanticNumber[Dimension.temperature]
    max: PydanticNumber[Dimension.temperature]

    @model_validator(mode='after')
    def min_less_than_max(self) -> 'TemperatureRange':
        min_k = self.min.to(units.kelvin).quantity
        max_k = self.max.to(units.kelvin).quantity
        if min_k >= max_k:
            raise ValueError("min must be less than max")
        return self
```

### Uncertainty Propagation

```yaml
# config.yaml
concentration: { quantity: 250, unit: "mg/mL", uncertainty: 5 }
```

```python
# Uncertainty flows through calculations automatically
volume = settings.calculate_volume_per_dose()
print(volume)  # <2.0 ± 0.05 mL>
```

### Computed Methods with Bounds Clamping

```python
def calculate_single_dose(self) -> Number:
    daily_dose = self.calculate_daily_dose()
    single_dose = daily_dose / self.dosing.frequency

    # Clamp to configured bounds
    clamped = max(min_mg, min(max_mg, dose_mg))
    return mg(clamped, uncertainty=single_dose.uncertainty)
```

## Validation Examples

The example demonstrates catching various errors:

```python
# Wrong dimension
concentration: { quantity: 250, unit: "mg" }  # Missing /mL
# → ValidationError: concentration must have dimension 'density'

# Range violation
storage_temp:
  min: { quantity: 10, unit: "degC" }
  max: { quantity: 5, unit: "degC" }
# → ValidationError: min must be less than max

# Negative value
weight: { quantity: -70, unit: "kg" }
# → ValidationError: must be positive
```

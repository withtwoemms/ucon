# Dimensional Safety for Configuration

Configuration files often contain values with implicit units. This guide shows how to make units explicit and catch dimension errors at load time.

## The Problem

Consider a typical configuration:

```yaml
timeout: 30        # seconds? milliseconds?
threshold: 99.9    # percent? ratio?
distance: 100      # meters? kilometers? miles?
```

Implicit units create bugs when:

- Someone assumes `timeout: 30` means seconds, but it's milliseconds
- A threshold is treated as a percentage when it's a raw ratio
- Units change between environments (metric vs imperial)

## The Solution: Explicit Units

Use Pydantic models with `Number` fields:

```python
from pydantic import BaseModel
from ucon import Dimension
from ucon.pydantic import Number

class ServiceConfig(BaseModel):
    timeout: Number[Dimension.time]
    retry_interval: Number[Dimension.time]
    max_distance: Number[Dimension.length]
```

Now configuration must include units:

```yaml
timeout:
  quantity: 30
  unit: s

retry_interval:
  quantity: 500
  unit: ms

max_distance:
  quantity: 100
  unit: km
```

## Loading Configuration

```python
import yaml

with open("config.yaml") as f:
    data = yaml.safe_load(f)

config = ServiceConfig(**data)
print(config.timeout)  # <30 s>
```

Dimension mismatches fail at load time:

```yaml
timeout:
  quantity: 30
  unit: km   # Wrong dimension!
```

```python
# Raises ValidationError: timeout must have dimension 'time'
config = ServiceConfig(**data)
```

## SRE Example: Availability Thresholds

SRE configurations often involve availability ("nines"), percentages, and time windows:

```python
from pydantic import BaseModel
from ucon import Dimension
from ucon.pydantic import Number

class SLOConfig(BaseModel):
    target_availability: Number[Dimension.ratio]
    error_budget_window: Number[Dimension.time]
    alert_threshold: Number[Dimension.ratio]
```

```yaml
target_availability:
  quantity: 99.99
  unit: percent

error_budget_window:
  quantity: 30
  unit: day

alert_threshold:
  quantity: 4
  unit: nines
```

Convert between representations at runtime:

```python
from ucon import units

# Convert nines to percentage
threshold_pct = config.alert_threshold.to(units.percent)
print(threshold_pct)  # <99.99 %>

# Convert percentage to nines
target_nines = config.target_availability.to(units.nines)
print(target_nines)  # <4.0 nines>
```

## Error Messages

When dimensions mismatch, you get clear error messages:

```python
# If someone puts a length where time is expected:
config = ServiceConfig(
    timeout={"quantity": 30, "unit": "km"},  # Wrong!
    ...
)
# ValidationError: timeout: expected dimension 'time', got 'length'
```

## Best Practices

1. **Always use dimensional constraints** for physical quantities
2. **Document expected units** in config comments, but enforce via types
3. **Use the most natural unit** for the domain (seconds for timeouts, nines for SLOs)
4. **Convert at the boundary** - convert to internal units after loading

```python
class ServiceConfig(BaseModel):
    timeout: Number[Dimension.time]

    @property
    def timeout_seconds(self) -> float:
        """Timeout in seconds for internal use."""
        return self.timeout.to(units.second).quantity
```

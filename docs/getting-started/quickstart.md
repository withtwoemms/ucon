# Quickstart

Get up and running with ucon in minutes.

## Create a Number

Units are callable. Pass a value to create a `Number`:

```python
from ucon import units

height = units.meter(1.8)
print(height)  # <1.8 m>
```

## Convert Between Units

Use `.to()` to convert:

```python
height_ft = height.to(units.foot)
print(height_ft)  # <5.905... ft>
```

## Work with Scaled Units

Combine prefixes with units:

```python
from ucon import Scale, units

km = Scale.kilo * units.meter
distance = km(5)

print(distance)  # <5 km>
print(distance.to(units.mile))  # <3.107... mi>
```

## Arithmetic with Units

Units propagate through arithmetic:

```python
length = units.meter(100)
time = units.second(10)

speed = length / time
print(speed)  # <10.0 m/s>
```

Incompatible dimensions raise errors:

```python
units.meter(5) + units.second(2)  # raises: incompatible dimensions
```

## Dimension Checks

Annotate functions with dimensional constraints:

```python
from ucon import Number, Dimension, enforce_dimensions

@enforce_dimensions
def speed(
    distance: Number[Dimension.length],
    time: Number[Dimension.time],
) -> Number:
    return distance / time

speed(units.meter(100), units.second(10))  # <10.0 m/s>
speed(units.second(100), units.second(10))  # raises ValueError
```

## Pydantic Integration

Use `Number` in Pydantic models:

```python
from pydantic import BaseModel
from ucon.pydantic import Number

class Measurement(BaseModel):
    value: Number

# From JSON/dict
m = Measurement(value={"quantity": 5, "unit": "km"})
print(m.value)  # <5 km>

# Serialize
print(m.model_dump_json())
# {"value": {"quantity": 5.0, "unit": "km", "uncertainty": null}}
```

## MCP Server

Expose ucon to AI agents with one command:

```bash
pip install ucon[mcp]
```

Configure in Claude Desktop (`claude_desktop_config.json`):

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

Now Claude can convert units, check dimensions, and perform factor-label calculations.

---

**Next:** See [Installation](installation.md) for all install options, or explore the [Guides](../guides/index.md) for deeper topics.

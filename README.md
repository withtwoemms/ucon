<table>
  <tr>
    <td width="200">
      <img src="https://gist.githubusercontent.com/withtwoemms/0cb9e6bc8df08f326771a89eeb790f8e/raw/221c60e85ac8361c7d202896b52c1a279081b54c/ucon-logo.png" align="left" width="200" />
    </td>
    <td>

# ucon

> Pronounced: _yoo · cahn_

[![tests](https://github.com/withtwoemms/ucon/workflows/tests/badge.svg)](https://github.com/withtwoemms/ucon/actions?query=workflow%3Atests)
[![codecov](https://codecov.io/gh/withtwoemms/ucon/graph/badge.svg?token=BNONQTRJWG)](https://codecov.io/gh/withtwoemms/ucon)
[![publish](https://github.com/withtwoemms/ucon/workflows/publish/badge.svg)](https://github.com/withtwoemms/ucon/actions?query=workflow%3Apublish)

   </td>
  </tr>
</table>

> A lightweight, **unit-aware computation library** for Python — built on first-principles.

**[Documentation](https://docs.ucon.dev)** · [Quickstart](https://docs.ucon.dev/getting-started/quickstart) · [API Reference](https://docs.ucon.dev/reference/api)

---

## What is ucon?

`ucon` helps Python understand the *physical meaning* of your numbers. It treats units, dimensions, and scales as first-class objects — enforcing physics, not just labels.

```python
from ucon import units

length = units.meter(5)
time = units.second(2)

speed = length / time      # <2.5 m/s>
invalid = length + time    # raises: incompatible dimensions
```

---

## Installation

```bash
pip install ucon
```

With extras:

```bash
pip install ucon[pydantic]  # Pydantic v2 integration
pip install ucon[mcp]       # MCP server for AI agents
```

---

## Quick Examples

### Unit Conversion

```python
from ucon import units, Scale

km = Scale.kilo * units.meter
distance = km(5)

print(distance.to(units.mile))  # <3.107... mi>
```

### Dimensional Safety

```python
from ucon import Number, Dimension, enforce_dimensions

@enforce_dimensions
def speed(
    distance: Number[Dimension.length],
    time: Number[Dimension.time],
) -> Number:
    return distance / time

speed(units.meter(100), units.second(10))   # <10.0 m/s>
speed(units.second(100), units.second(10))  # raises ValueError
```

### Pydantic Integration

```python
from pydantic import BaseModel
from ucon.pydantic import Number

class Measurement(BaseModel):
    value: Number

m = Measurement(value={"quantity": 9.8, "unit": "m/s^2"})
print(m.model_dump_json())
# {"value": {"quantity": 9.8, "unit": "m/s^2", "uncertainty": null}}
```

### MCP Server for AI Agents

Configure in Claude Desktop:

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

AI agents can then convert units, check dimensions, and perform factor-label calculations with dimensional validation at each step.

---

## Features

- **Dimensional algebra** — Units combine through multiplication/division with automatic dimension tracking
- **Scale prefixes** — Full SI (kilo, milli, micro, etc.) and binary (kibi, mebi) prefix support
- **Uncertainty propagation** — Errors propagate through arithmetic and conversions
- **Pseudo-dimensions** — Semantically isolated handling of angles, ratios, and counts
- **Pydantic v2** — Type-safe API validation and JSON serialization
- **MCP server** — AI agent integration with Claude, Cursor, and other MCP clients
- **ConversionGraph** — Extensible conversion registry with custom unit support

---

## Roadmap Highlights

| Version | Theme | Status |
|---------|-------|--------|
| **0.3.x** | Dimensional Algebra | Complete |
| **0.4.x** | Conversion System | Complete |
| **0.5.x** | Dimensionless Units + Uncertainty | Complete |
| **0.6.x** | Pydantic + MCP Server | Complete |
| **0.7.x** | Compute Tool + Extension API | Complete |
| **0.8.x** | String Parsing | Planned |
| **0.9.x** | Constants + Logarithmic Units | Planned |
| **0.10.x** | NumPy/Polars Integration | Planned |
| **1.0.0** | API Stability | Planned |

See full roadmap: [ROADMAP.md](https://github.com/withtwoemms/ucon/blob/main/ROADMAP.md)

---

## Documentation

| Section | Description |
|---------|-------------|
| [Getting Started](https://docs.ucon.dev/getting-started/) | Why ucon, quickstart, installation |
| [Guides](https://docs.ucon.dev/guides/) | MCP server, Pydantic, custom units, dimensional analysis |
| [Reference](https://docs.ucon.dev/reference/) | API docs, unit tables, MCP tool schemas |
| [Architecture](https://docs.ucon.dev/architecture/) | Design principles, ConversionGraph, comparison with Pint |

---

## Contributing

```bash
make venv                        # Create virtual environment
source .ucon-3.12/bin/activate   # Activate
make test                        # Run tests
make test-all                    # Run tests across all Python versions
```

All pull requests must include a [CHANGELOG.md](https://github.com/withtwoemms/ucon/blob/main/CHANGELOG.md) entry under the `[Unreleased]` section:

```markdown
## [Unreleased]

### Added

- Your new feature description (#PR_NUMBER)
```

Use the appropriate category: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, or `Security`.

---

## License

Apache 2.0. See [LICENSE](./LICENSE).

# Installation

## Requirements

- Python 3.7 or higher

## Basic Install

```bash
pip install ucon
```

## Optional Extras

ucon provides optional dependencies for specific use cases:

### Pydantic Integration

For API validation and JSON serialization with Pydantic v2:

```bash
pip install ucon[pydantic]
```

### MCP Server

For AI agent integration (Claude Desktop, Claude Code, Cursor, etc.):

```bash
pip install ucon[mcp]
```

!!! note "Python 3.10+"
    The MCP extra requires Python 3.10 or higher.

### Multiple Extras

Install multiple extras at once:

```bash
pip install ucon[pydantic,mcp]
```

## Verify Installation

```python
>>> from ucon import units
>>> print(units.meter(5))
<5 m>
```

## Development Install

For contributing or local development:

```bash
git clone https://github.com/withtwoemms/ucon.git
cd ucon
make venv
source .ucon-3.12/bin/activate
```

Run the test suite:

```bash
make test
```

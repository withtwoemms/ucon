# Custom Units via MCP

Define domain-specific units at runtime through the MCP server.

## Session Tools

Use `define_unit` and `define_conversion` for persistent custom units within a session:

```python
# Define a custom unit
define_unit(name="slug", dimension="mass", aliases=["slug"])

# Add conversion to standard units
define_conversion(src="slug", dst="kg", factor=14.5939)

# Now use it
convert(value=1, from_unit="slug", to_unit="kg")
# → {"quantity": 14.5939, "unit": "kg", "dimension": "mass"}
```

Custom units persist until `reset_session()` is called.

## Inline Definitions

For one-off conversions without session state, pass definitions directly:

```python
convert(
    value=1,
    from_unit="slug",
    to_unit="kg",
    custom_units=[
        {"name": "slug", "dimension": "mass", "aliases": ["slug"]}
    ],
    custom_edges=[
        {"src": "slug", "dst": "kg", "factor": 14.5939}
    ]
)
```

Inline definitions are ephemeral — they don't modify the session graph.

## When to Use Each

| Approach | Use case |
|----------|----------|
| Session tools | Multiple conversions with same custom units |
| Inline definitions | One-off conversion, stateless recovery |

## Unit Definition Schema

```python
{
    "name": "slug",           # Required: canonical name
    "dimension": "mass",      # Required: dimension name (from list_dimensions)
    "aliases": ["slug"]       # Optional: alternative names
}
```

## Edge Definition Schema

```python
{
    "src": "slug",            # Source unit name
    "dst": "kg",              # Destination unit name
    "factor": 14.5939         # Multiplier: dst = src * factor
}
```

## Error Handling

Invalid definitions return structured errors:

```python
define_unit(name="bad", dimension="nonexistent")
# → {
#     "error": "Unknown dimension: 'nonexistent'",
#     "error_type": "unknown_dimension",
#     "hints": ["Use list_dimensions() to see available dimensions"]
# }
```

## Python API

For programmatic unit definition without MCP, see [Custom Units & Graphs](../custom-units-and-graphs.md).

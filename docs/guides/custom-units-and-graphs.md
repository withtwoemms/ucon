# Custom Units & Graphs

ucon's unit system is extensible. You can define domain-specific units and conversions for aerospace, medicine, finance, or any specialized field.

!!! tip "MCP Users"
    For AI agent use cases, see [Custom Units via MCP](mcp-server/custom-units.md).

## Unit Definition

Create units programmatically:

```python
from ucon import Dimension
from ucon.core import Unit

# Define a new unit
slug = Unit(
    name="slug",
    shorthand="slug",
    dimension=Dimension.mass,
    aliases=("slug",),
)
```

## ConversionGraph

Register units and conversions in a graph:

```python
from ucon.graph import ConversionGraph, get_default_graph
from ucon.maps import LinearMap

# Start with a copy of the default graph
graph = get_default_graph().copy()

# Register the unit
graph.register_unit(slug)

# Add conversion edge (1 slug = 14.5939 kg)
from ucon import units, Scale

kilogram = Scale.kilo * units.gram
graph.add_edge(slug, kilogram, LinearMap(14.5939))
```

## Using Custom Graphs

### Context Manager

Use `using_graph` to temporarily set the active graph:

```python
from ucon.core import Scale
from ucon.graph import using_graph

with using_graph(graph):
    kilogram = Scale.kilo * units.gram
    result = slug(1).to(kilogram)
    print(result)  # <14.5939 kg>
```

### Explicit Graph Parameter

Pass the graph directly to conversion methods:

```python
result = slug(1).to(kilogram, graph=graph)
```

## Building Domain-Specific Graphs

For a specialized domain, create a dedicated graph:

```python
from ucon import Dimension
from ucon.core import Scale, Unit
from ucon.graph import ConversionGraph
from ucon.maps import LinearMap

def build_aerospace_graph() -> ConversionGraph:
    """Build a graph with aerospace-specific units."""
    graph = get_default_graph().copy()

    # Slug (imperial mass unit)
    slug = Unit("slug", "slug", Dimension.mass, aliases=("slug",))
    kilogram = Scale.kilo * units.gram
    graph.register_unit(slug)
    graph.add_edge(slug, kilogram, LinearMap(14.5939))

    # Nautical mile
    nmi = Unit("nautical_mile", "nmi", Dimension.length, aliases=("NM", "nmi"))
    graph.register_unit(nmi)
    graph.add_edge(nmi, units.meter, LinearMap(1852))

    # Knot (nautical miles per hour)
    # This is a derived unit, works automatically once nmi is defined

    return graph

aerospace = build_aerospace_graph()
```

## Graph Composition

Combine multiple domain graphs:

```python
def build_combined_graph(*sources: ConversionGraph) -> ConversionGraph:
    """Merge multiple graphs into one."""
    combined = get_default_graph().copy()
    for source in sources:
        # Copy units
        for unit in source.units():
            if unit not in combined.units():
                combined.register_unit(unit)
        # Copy edges
        for src, dst, mapping in source.edges():
            combined.add_edge(src, dst, mapping)
    return combined
```

## Testing Custom Units

Verify your custom units work correctly:

```python
def test_slug_conversion():
    graph = build_aerospace_graph()

    with using_graph(graph):
        # Forward conversion
        mass_kg = slug(1).to(kilogram)
        assert abs(mass_kg.quantity - 14.5939) < 0.001

        # Reverse conversion (automatic via BFS)
        mass_slug = kilogram(14.5939).to(slug)
        assert abs(mass_slug.quantity - 1.0) < 0.001
```

## Design Considerations

**Dimension must be correct:** The unit's dimension determines what it can convert to. A unit with `Dimension.mass` can convert to other mass units, not length units.

**Bidirectional edges:** Adding `slug → kg` automatically allows `kg → slug` via the graph's BFS pathfinding.

**Scale prefixes:** Standard units support scale prefixes (`kilo`, `milli`, etc.). Custom units can too if registered with the scalable unit set.

**Graph isolation:** Creating a copy of the default graph ensures your custom units don't affect other code using the global default.

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

## Using Custom Bases

For CGS or other non-SI workflows, use `using_basis` to set the default basis for dimension creation.

### Context Manager

```python
from ucon import using_basis, CGS, Dimension

with using_basis(CGS):
    # Dimensions created here use CGS basis by default
    velocity = Dimension.from_components(L=1, T=-1, name="velocity")
    velocity.basis  # CGS

    # Pseudo-dimensions also respect context
    angle = Dimension.pseudo("angle")
    angle.basis  # CGS
```

### Nested Contexts

Contexts can be nested; inner contexts restore to outer on exit:

```python
from ucon import using_basis, SI, CGS

with using_basis(CGS):
    # CGS is default here
    with using_basis(SI):
        # SI is default here
        pass
    # Back to CGS
```

### Explicit Basis Parameter

Explicit `basis=` argument always wins over context:

```python
from ucon import using_basis, CGS, SI, Dimension

with using_basis(CGS):
    # Explicit basis overrides context
    si_dim = Dimension.from_components(SI, L=1, name="length")
    si_dim.basis  # SI (not CGS)
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

---

## Cross-Basis Conversions

For units in different dimensional bases (e.g., SI vs CGS-ESU), use the `basis_transform` parameter.

### When You Need Cross-Basis

Standard conversions (meter ↔ foot) work within a single basis — both units use SI's dimensional structure. Cross-basis is needed when:

- Converting between SI and CGS systems
- Working with CGS-ESU electrical units (where charge is fundamental)
- Integrating legacy systems with different dimensional foundations

### Creating Units in Different Bases

```python
from fractions import Fraction
from ucon import Dimension
from ucon.basis import Vector
from ucon.bases import CGS_ESU
from ucon.core import Unit

# CGS-ESU current has dimension L^(3/2) M^(1/2) T^(-2)
# (In SI, current is fundamental; in CGS-ESU, it's derived from charge)
cgs_current_dim = Dimension(
    vector=Vector(CGS_ESU, (
        Fraction(3, 2),   # L
        Fraction(1, 2),   # M
        Fraction(-2),     # T
        Fraction(0),      # Q
    )),
    name="cgs_current",
)

statampere = Unit(name="statampere", dimension=cgs_current_dim)
```

### Adding Cross-Basis Edges

```python
from ucon import units
from ucon.bases import SI_TO_CGS_ESU
from ucon.graph import ConversionGraph
from ucon.maps import LinearMap

graph = ConversionGraph()

# The basis_transform validates dimensional compatibility
graph.add_edge(
    src=units.ampere,           # SI unit
    dst=statampere,             # CGS-ESU unit
    map=LinearMap(2.998e9),     # 1 A ≈ 3×10⁹ statA
    basis_transform=SI_TO_CGS_ESU,
)
```

The `basis_transform` does three things:

1. **Validates** that `SI_TO_CGS_ESU(ampere.dimension)` equals `statampere.dimension`
2. **Creates a RebasedUnit** bridging the two dimension partitions
3. **Enables BFS** to find paths across bases

### Bulk Registration

For multiple cross-basis edges, use `connect_systems()`:

```python
from ucon.bases import SI_TO_CGS

graph.connect_systems(
    basis_transform=SI_TO_CGS,
    edges={
        (units.meter, centimeter_cgs): LinearMap(100),
        (units.gram, gram_cgs): LinearMap(1),
        (units.second, second_cgs): LinearMap(1),
    },
)
```

### Checking Compatibility

Use `Unit.is_compatible()` to check if conversion is possible:

```python
from ucon.basis import BasisGraph
from ucon.bases import SI_TO_CGS_ESU

# Set up basis connectivity
bg = BasisGraph().with_transform(SI_TO_CGS_ESU)

# Check compatibility
units.ampere.is_compatible(statampere, basis_graph=bg)  # True
units.meter.is_compatible(statampere, basis_graph=bg)   # False (different dimensions)
```

### Further Reading

For the architectural details of how BasisGraph and ConversionGraph work together, see [Dual-Graph Architecture](../architecture/dual-graph-architecture.md).

---

## Loading Unit Packages

For reusable unit definitions, use TOML-based unit packages:

```toml
# aerospace.ucon.toml
name = "aerospace"
version = "1.0.0"

[[units]]
name = "slug"
dimension = "mass"
aliases = ["slug"]

[[units]]
name = "knot"
dimension = "velocity"
aliases = ["kn", "kt"]

[[edges]]
src = "slug"
dst = "kilogram"
factor = 14.5939

[[edges]]
src = "knot"
dst = "meter/second"
factor = 0.514444
```

Load and apply:

```python
from ucon import get_default_graph
from ucon.packages import load_package

aero = load_package("aerospace.ucon.toml")
graph = get_default_graph().with_package(aero)
```

See `examples/units/aerospace.ucon.toml` for a complete example.

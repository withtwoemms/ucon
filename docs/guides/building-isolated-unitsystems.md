# Building Isolated UnitSystems

ucon's v1.8 `UnitSystem` value type lets you bundle a basis, the unit and
dimension registries, the conversion and basis graphs, and a canonical
`BaseUnits` mapping into a single passable value. This guide covers when and
how to construct an *isolated* `UnitSystem` — one that doesn't share state
with the global default.

For the rationale and equality semantics, see the
[UnitSystem Value Type](../architecture/unitsystem-value-type.md) architecture
page.

!!! note "v1.8+"
    `UnitSystem` is available starting in ucon 1.8. The legacy import
    `from ucon import UnitSystem` still resolves to `BaseUnits` with a
    `PendingDeprecationWarning`. Import the new type explicitly:

    ```python
    from ucon.system import UnitSystem
    ```

---

## Three Construction Modes

There are three ways to obtain a `UnitSystem`:

```python
from ucon.system import UnitSystem, BaseUnits
from ucon import units

# 1. Snapshot the current globals
default = UnitSystem.from_globals()

# 2. Snapshot with a different BaseUnits mapping
imperial = UnitSystem.from_globals(base_units=units.imperial)

# 3. Construct directly to replace specific registries
isolated = UnitSystem(
    basis=default.basis,
    units=default.units,
    dimensions=default.dimensions,
    base_units=default.base_units,
    conversion_graph=my_isolated_graph,   # the one field you actually want different
    basis_graph=default.basis_graph,
    contexts={},
    constants=default.constants,
)
```

Most code uses mode 1 or 2. Mode 3 is for the case the rest of this guide
covers — when you need a *different world* in one specific axis.

---

## When You Need Isolation

The four scenarios that justify direct construction:

### 1. Test fixtures

Library tests that register custom units mutate the global conversion graph.
Run two such tests in the same process and the second test sees the first
test's units. An isolated `UnitSystem` gives each test its own
`ConversionGraph`:

```python
import pytest
from ucon.system import UnitSystem, use
from ucon.graph import ConversionGraph

@pytest.fixture
def isolated_system():
    parent = UnitSystem.from_globals()
    return UnitSystem(
        basis=parent.basis,
        units=parent.units,
        dimensions=parent.dimensions,
        base_units=parent.base_units,
        conversion_graph=ConversionGraph(),  # empty per-test graph
        basis_graph=parent.basis_graph,
        contexts={},
        constants=parent.constants,
    )

def test_custom_unit(isolated_system):
    with use(isolated_system):
        # Register and convert in isolation
        ...
    # Outside the with-block: globals are untouched
```

### 2. Multi-tenant services

A web service that registers customer-specific units per request must not let
those registrations leak into other customers' computations. Per-request
isolation matches the `UnitSystem`-per-request pattern naturally:

```python
def handle_request(request):
    tenant_system = build_tenant_system(request.tenant_id)
    with use(tenant_system):
        return run_pipeline(request)
```

### 3. Reproducible pipelines

A scientific analysis that pins exactly one basis, one conversion graph, and
one constants set produces byte-identical outputs every run — even if other
parts of the same process register units later. Construct the `UnitSystem`
once at startup, persist it (or rebuild from the same TOML package), and pin
it across the run.

### 4. Concurrent bases

A simulation in CGS-Gaussian and a downstream SI consumer in the same process
can each pin their own `UnitSystem`. The `ContextVar` underlying `use(...)`
makes this work correctly across `asyncio` tasks and threads.

---

## Step-by-Step: An Isolated UnitSystem for Aerospace

This worked example builds a fully self-contained `UnitSystem` that registers
aerospace units in its *own* conversion graph, leaving the global graph
untouched.

### Step 1: Snapshot the parent

```python
from ucon.system import UnitSystem

parent = UnitSystem.from_globals()
```

`parent` shares its `units` and `dimensions` registries with the globals (by
reference). That's fine — we only want to isolate the conversion graph.

### Step 2: Start a fresh conversion graph

```python
from ucon.graph import ConversionGraph, get_default_graph

aero_graph = get_default_graph().copy()
```

`.copy()` gives us a graph with every default edge already present (so
`meter → foot` still works) but distinct from the global default. Edges added
to `aero_graph` won't appear in `get_default_graph()`.

### Step 3: Register aerospace units on the isolated graph

```python
from ucon import Dimension
from ucon.core import Scale, Unit
from ucon.maps import LinearMap
from ucon import units

slug = Unit("slug", "slug", Dimension.mass, aliases=("slug",))
nmi  = Unit("nautical_mile", "nmi", Dimension.length, aliases=("NM", "nmi"))

kilogram = Scale.kilo * units.gram

aero_graph.register_unit(slug)
aero_graph.register_unit(nmi)
aero_graph.add_edge(slug, kilogram, LinearMap(14.5939))
aero_graph.add_edge(nmi,  units.meter, LinearMap(1852))
```

### Step 4: Wrap it in a UnitSystem

```python
aero_system = UnitSystem(
    basis=parent.basis,
    units=parent.units,
    dimensions=parent.dimensions,
    base_units=parent.base_units,
    conversion_graph=aero_graph,
    basis_graph=parent.basis_graph,
    contexts=parent.contexts,
    constants=parent.constants,
)
```

### Step 5: Activate with `use(...)`

```python
from ucon.system import use

with use(aero_system):
    mass_kg = slug(1).to(kilogram)
    print(mass_kg)         # <14.5939 kg>
```

Outside the with-block, the global graph is unchanged — `slug` is not
registered, `nautical_mile` is not registered, and the v1.8 user-facing entry
points (`Number.to`, `enforce_dimensions`, `parse`, `parse_unit`,
`parse_dimension`, `ucon.basis.ops.*`) see only what the global registries
expose.

---

## Threading `system=` Explicitly

`use(...)` sets a `ContextVar`. Every v1.8 entry point that reads the active
system also accepts `system=` as an explicit override. Use it when you want a
call-site decision rather than a contextmanager:

```python
mass_kg = slug(1).to(kilogram, system=aero_system)
```

Entry points that accept `system=`:

| Function                              | Module                       |
|---------------------------------------|------------------------------|
| `Number.to(target, *, system=None)`   | `ucon.core`                  |
| `enforce_dimensions(*, system=None)`  | `ucon.checking`              |
| `parse(s, *, system=None)`            | `ucon.parsing`               |
| `parse_unit(s, *, system=None)`       | `ucon.resolver`              |
| `parse_dimension(s, *, system=None)`  | `ucon.parsing`               |
| `get_unit_by_name(n, *, system=None)` | `ucon.resolver`              |
| `multiply_via(*, system=None)`        | `ucon.basis.ops`             |
| `divide_via(*, system=None)`          | `ucon.basis.ops`             |
| `unify(*, system=None)`               | `ucon.basis.ops`             |

Explicit `system=` wins over the active `use(...)` context. Useful for tests
where you want to assert "this call must use *that* system" without nesting.

---

## Equality and Reuse

Two snapshots produced by `from_globals()` compare equal even though they are
distinct objects:

```python
a = UnitSystem.from_globals()
b = UnitSystem.from_globals()
assert a == b
assert hash(a) == hash(b)
```

Snapshots remain equal until you mutate one of the shared registries. If your
pipeline relies on `__hash__` (e.g., as a dict key), pin one snapshot at
startup rather than re-snapshotting per call.

A directly-constructed `UnitSystem` with an isolated graph compares *unequal*
to a globals snapshot:

```python
aero_system == UnitSystem.from_globals()  # False (different graph identity)
```

That's by design: a different conversion graph means a different world.

---

## Migration from v1.7 `using_*` Stacks

In v1.7 isolating "the world" required three separate context managers:

```python
# v1.7 — three nested contexts
with using_basis(my_basis), using_conversion_graph(my_graph), using_context(my_ctx):
    ...
```

v1.8 collapses that to one:

```python
# v1.8 — one UnitSystem
my_system = UnitSystem(
    basis=my_basis,
    conversion_graph=my_graph,
    contexts={"my_ctx": my_ctx},
    # other fields from parent snapshot
    ...
)
with use(my_system):
    ...
```

The legacy `using_*` context managers continue to work in v1.8 — they're not
deprecated and still drive the underlying `ContextVar`s. `use(...)` is the
*aggregated* form when you want one value to capture all of it.

---

## Testing Checklist

When you write a test that builds an isolated `UnitSystem`, verify:

- [ ] Global graph membership is unchanged after the test
  ```python
  from ucon.graph import get_default_graph
  before = set(get_default_graph().units())
  # ... test runs ...
  after = set(get_default_graph().units())
  assert before == after
  ```
- [ ] Activating the system inside `use(...)` is what enables your custom unit
  ```python
  with pytest.raises(UnknownUnitError):
      slug(1).to(kilogram)  # no system active
  with use(aero_system):
      slug(1).to(kilogram)  # works
  ```
- [ ] `system=` kwarg matches the contextmanager
  ```python
  with_ctx = slug(1).to(kilogram)               # via use(...)
  with_kw  = slug(1).to(kilogram, system=aero_system)  # explicit
  assert with_ctx == with_kw
  ```

---

## Further Reading

- [UnitSystem Value Type](../architecture/unitsystem-value-type.md) — the rationale
- [Custom Units & Graphs](custom-units-and-graphs.md) — graph-only isolation (pre-v1.8 idiom)
- [Particle Physics walkthrough](domain-walkthroughs/particle-physics.md) — end-to-end example

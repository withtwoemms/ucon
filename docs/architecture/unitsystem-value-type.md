# UnitSystem as a Value Type

`UnitSystem` (`ucon.system.UnitSystem`) is a frozen dataclass that bundles a
basis, the registries (units, dimensions, conversion_graph, basis graph,
contexts, constants), a canonical `BaseUnits` mapping, and a per-instance
algebra cache.

This page explains *why* `UnitSystem` is a value type, what equality means for
it, and how it relates to the module-level globals that drove earlier ucon
versions.

---

## What `UnitSystem` Owns

```
UnitSystem
├── basis            : Basis                # dimensional coordinate system
├── units            : Mapping[str, Unit]   # name → Unit registry
├── dimensions       : Mapping[str, Dim]    # name → Dimension registry
├── base_units       : BaseUnits            # canonical base unit per dimension
├── conversion_graph : ConversionGraph      # Unit → Unit morphisms
├── basis_graph      : BasisGraph           # Basis → Basis transforms
├── contexts         : Mapping[str, Ctx]    # named cross-dimension contexts
├── constants        : Mapping[str, Const]  # physical-constant registry
└── _algebra_cache   : AlgebraCache         # per-instance dimension memoization
```

`BaseUnits` is a separate, smaller value type — just `(name, bases: dict)` —
that records the canonical unit for each covered dimension. It was the v1.7
class formerly named `UnitSystem`. The rename freed the `UnitSystem` slot for
the richer value type above.

The pair `(BaseUnits, UnitSystem)` is intentional:

- **`BaseUnits`** answers *"which unit represents this dimension?"* It is small,
  cheap to compare by value, and the right thing to share across pipelines.
- **`UnitSystem`** answers *"which complete world am I computing in?"* It
  bundles the registries and graphs that decide whether a parse succeeds or a
  conversion finds a path.

---

## Why a Value Type, Not Globals

Before the `UnitSystem` value type, every call into ucon read four module-level singletons:

1. `ucon._loader._UNITS` — the name → Unit registry
2. `ucon.dimension._DIMENSION_ATTRS` — the name → Dimension registry
3. `ucon.basis.graph._default_basis_graph` — the cross-basis graph
4. `ucon.graph._default_graph` — the conversion graph

That worked, but had three sharp edges:

**1. Implicit coupling.** A function that read three of those globals had no
type-level record of that fact. Threading explicit state through a pipeline
required multiple context managers (one per field), each managing its own
`ContextVar`.

**2. Test isolation.** Tests that touched the registries had to remember to
restore them in `finally` blocks. A leaked unit registration in test A could
mask a real bug in test B.

**3. Caching invariants.** Dimension algebra (mul, div, pow) memoizes results
in module-level dicts. Two callers using different bases share that cache, so
correctness depends on the cache key including basis identity. A bug in one
caller's basis handling can poison memoized entries for everyone else.

`UnitSystem` solves all three by making "the world you compute in" a single
named value:

```python
from ucon import active_system, use

system = active_system()
with use(system):
    # Every entry point sees the same system
    ...
```

Every user-facing entry point accepts `system=` and the context manager
`use(...)` sets a `ContextVar` that callees can pick up.

---

## Equality and Hashing

`UnitSystem` is `@dataclass(frozen=True)`, but its registries are mutable
`dict`s and graph objects. "Frozen" applies to the field bindings, not the
contents.

Equality splits across that line:

| Field           | Comparison    | Why                                          |
|-----------------|---------------|----------------------------------------------|
| `basis`            | by value    | `Basis` is a frozen value type               |
| `base_units`       | by value    | `BaseUnits` is a frozen value type           |
| `units`            | by identity | dict; comparing by value would be O(n)       |
| `dimensions`       | by identity | dict                                         |
| `conversion_graph` | by identity | graph; structural equality is too expensive  |
| `basis_graph`      | by identity | graph                                        |
| `contexts`         | by identity | dict                                         |
| `constants`        | by identity | dict                                         |
| `_algebra_cache`   | excluded    | per-instance memoization, not part of value  |

Two captures of `active_system()` back-to-back are equal: the basis and base
units compare by value, and the registries are passed through by reference
(the system does not copy them).

Modifying the registries between captures breaks that — by design. Mutation of
a shared world should change identity of every system pointing at it, and
identity-equality on `units`/`dimensions`/`conversion_graph` captures exactly
that.

---

## The Per-Instance AlgebraCache

`Dimension.__mul__`, `__truediv__`, and `__pow__` are hot — every parsed
compound unit lands in them. ucon memoizes results in three dicts.

Historically, those dicts lived at module level. That conflated two different
cache lifetimes:

- **Process-lifetime memoization** for repeated lookups of `LENGTH * MASS` —
  legitimate, fast, never invalidated.
- **System-scoped memoization** for `current_in_CGS_ESU * length_in_SI` — the
  result depends on the *active basis graph*. If basis-graph state changes mid
  process, stale entries linger.

The dicts now live on a per-instance `AlgebraCache` owned by the `UnitSystem`.
Two pipelines with different bases have separate algebra caches. `Dimension`
algebra routes through `_get_active_cache()`, which creates a fresh
`AlgebraCache()` when no `UnitSystem` has been activated (bootstrap only).

The cache is excluded from `__eq__` and `__hash__`. Two systems are equal even
if one has populated its cache through use.

---

## Obtaining a UnitSystem

`active_system()` returns the currently active `UnitSystem`. It does *not*
copy the registries. That makes two consecutive calls cheap and equal:

```python
from ucon import active_system

a = active_system()
b = active_system()
assert a == b          # by-identity on registries, by-value on basis
assert a is not b      # distinct AlgebraCache, but excluded from equality
```

This is the recommended entry path for code that just wants "the same world
the active context would see, but as a value I can pass around".

---

## When To Construct UnitSystem Directly

Most code should use `active_system()`. Construct one directly only when you
need to *replace* a registry — for example, an isolated test
`ConversionGraph` that shouldn't share state with the default graph:

```python
from ucon import UnitSystem, active_system
from ucon.graph import ConversionGraph

isolated_graph = ConversionGraph()       # empty; populate as needed
parent = active_system()
test_system = UnitSystem(
    basis=parent.basis,
    units=parent.units,
    dimensions=parent.dimensions,
    base_units=parent.base_units,
    conversion_graph=isolated_graph,      # different graph
    basis_graph=parent.basis_graph,
    contexts={},
    constants=parent.constants,
)
```

See [Building Isolated UnitSystems](../guides/building-isolated-unitsystems.md)
for the full walkthrough.

---

## Relationship to BaseUnits

`BaseUnits` is the dimension → base-unit mapping. It was renamed from the
pre-v2.0 `UnitSystem` so that the `UnitSystem` name could carry the richer
value type.

```python
from ucon import UnitSystem, BaseUnits
```

`UnitSystem` *contains* a `BaseUnits` (the `base_units` field). The two
abstractions compose: `BaseUnits` answers "what unit represents kg-of-mass in
this system?"; `UnitSystem` answers "in which world is that question asked?"

---

## Further Reading

- [Building Isolated UnitSystems](../guides/building-isolated-unitsystems.md) — practical guide
- [Dual-Graph Architecture](dual-graph-architecture.md) — BasisGraph vs ConversionGraph
- [Design Principles](design-principles.md) — overall philosophy

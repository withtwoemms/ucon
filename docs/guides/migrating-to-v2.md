# Migrating to v2.0

This guide covers the breaking changes in ucon v2.0 and how to update your
code.

---

## Removed Symbols

The following deprecated symbols have been removed in v2.0.

### `UnitSystem.from_globals()`

**Before:**

```python
from ucon.system import UnitSystem

system = UnitSystem.from_globals()
```

**After:**

```python
from ucon import active_system

system = active_system()
```

`active_system()` returns the currently active `UnitSystem`. It is equivalent
to the old `from_globals()` snapshot pattern.

---

### `using_basis(basis)`

**Before:**

```python
from ucon import using_basis, CGS

with using_basis(CGS):
    ...
```

**After:**

```python
from ucon import active_system, use, CGS

cgs_system = active_system().with_basis(CGS)
with use(cgs_system):
    ...
```

---

### `using_basis_graph(graph)`

**Before:**

```python
from ucon import using_basis_graph
from ucon.basis import BasisGraph

custom_bg = BasisGraph()
with using_basis_graph(custom_bg):
    ...
```

**After:**

```python
from ucon import active_system, use
from ucon.basis import BasisGraph

custom_bg = BasisGraph()
system = active_system().with_basis_graph(custom_bg)
with use(system):
    ...
```

---

### `get_default_basis()`

**Before:**

```python
from ucon import get_default_basis

basis = get_default_basis()
```

**After:**

```python
from ucon import active_system

basis = active_system().basis
```

---

### `get_basis_graph()`

**Before:**

```python
from ucon import get_basis_graph

bg = get_basis_graph()
```

**After:**

```python
from ucon import active_system

bg = active_system().basis_graph
```

---

### `set_default_basis_graph()` / `reset_default_basis_graph()`

**Before:**

```python
from ucon import set_default_basis_graph, reset_default_basis_graph

set_default_basis_graph(my_graph)
# ... later ...
reset_default_basis_graph()
```

**After:**

Use `use()` with a derived `UnitSystem`:

```python
from ucon import active_system, use

system = active_system().with_basis_graph(my_graph)
with use(system):
    ...
# Original system is automatically restored on exit
```

---

### `BaseUnits` alias via `from ucon import UnitSystem`

In v1.x, `from ucon import UnitSystem` resolved to `BaseUnits` with a
deprecation warning. In v2.0, `from ucon import UnitSystem` resolves to the
full `UnitSystem` value type.

**Before:**

```python
from ucon import UnitSystem  # was BaseUnits with warning
```

**After:**

```python
from ucon import BaseUnits   # if you want the base-unit mapping
from ucon import UnitSystem  # now the full value type
```

---

## New in v2.0

### Kind-aware Numbers

`Number` now carries an optional `kind` field:

```python
from ucon import Number, units, active_kinds

energy = active_kinds().get("energy")
n = Number(quantity=100, unit=units.joule, kind=energy)
n.kind.name  # "energy"
```

Kind is validated against the unit's dimension at construction and preserved
through conversions.

### Kind-aware Arithmetic

- **Multiplication/division:** Consults the active `FormulaRegistry` when both
  operands carry a kind.
- **Addition/subtraction:** Consults the active `KindLattice` — same-kind
  preserves, different-kind joins at LCA or raises `JoinRefused`.
- **Strict mode:** Refuses kinded + unkinded addition (`KindMismatch`).

### `Number[Kind]` Subscript

`@enforce_dimensions` and Pydantic fields support kind constraints:

```python
from ucon import enforce_dimensions, Number, active_kinds

energy = active_kinds().get("energy")

@enforce_dimensions
def heat_capacity(
    energy_in: Number[energy],
    temperature: Number[Dimension.temperature],
) -> Number:
    return energy_in / temperature
```

### `ActiveContext` Substrate

The `use()` context manager now sets an `ActiveContext` — a frozen dataclass
bundling the active `UnitSystem`, `FormulaRegistry`, `KindLattice`, and
`strict` flag. Typed accessors: `active_system()`, `active_formulas()`,
`active_kinds()`, `active_strict()`.

### `[[kinds]]` in TOML

Kind lattices can be authored in TOML and loaded via `load_package()` or
`from_toml()`:

```toml
[[kinds]]
name = "absorbed_dose"
dimension = "specific_energy"

[[kinds]]
name = "equivalent_dose"
dimension = "specific_energy"
parent = "absorbed_dose"
```

---

## Quick Reference

| v1.x | v2.0 |
|------|------|
| `UnitSystem.from_globals()` | `active_system()` |
| `using_basis(CGS)` | `use(active_system().with_basis(CGS))` |
| `using_basis_graph(bg)` | `use(active_system().with_basis_graph(bg))` |
| `get_default_basis()` | `active_system().basis` |
| `get_basis_graph()` | `active_system().basis_graph` |
| `set_default_basis_graph(bg)` | `use(active_system().with_basis_graph(bg))` |
| `from ucon import UnitSystem` (→ BaseUnits) | `from ucon import BaseUnits` |
